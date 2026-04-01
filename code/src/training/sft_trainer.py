from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

from core.download_manager import ensure_model_downloaded
from utils.path_manager import get_path


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._-") or "value"


def _resolve_export_paths(dataset_path: str) -> Dict[str, Path]:
    """
    dataset_path must point to the exporter output directory, e.g.
    code/data/finetuning/gold/TrainDataset_V1

    Expected files:
    - train.jsonl
    - dev.jsonl
    """
    export_dir = Path(dataset_path).resolve()

    if not export_dir.exists():
        raise FileNotFoundError(f"Training dataset directory not found: {export_dir}")

    if not export_dir.is_dir():
        raise ValueError(f"Expected dataset directory, got file: {export_dir}")

    train_path = export_dir / "train.jsonl"
    dev_path = export_dir / "dev.jsonl"

    if not train_path.exists():
        raise FileNotFoundError(f"Missing train split: {train_path}")

    if not dev_path.exists():
        raise FileNotFoundError(f"Missing dev split: {dev_path}")

    return {
        "export_dir": export_dir,
        "train_path": train_path,
        "dev_path": dev_path,
    }


def _resolve_output_dir(model_id: str, export_dir: Path) -> Path:
    """
    Save LoRA adapters under models.base_dir/finetuned/<model>__<dataset>
    """
    models_base_dir = Path(get_path("models.base_dir")).resolve()
    finetuned_base_dir = models_base_dir / "finetuned"
    finetuned_base_dir.mkdir(parents=True, exist_ok=True)

    safe_model = _safe_name(model_id)
    safe_dataset = _safe_name(export_dir.name)

    output_dir = finetuned_base_dir / f"{safe_model}__{safe_dataset}"
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def _get_local_model_path(model_id: str) -> Path:
    model_base_dir = get_path("models.base_dir")
    print(f"Model base directory: {model_base_dir}")

    local_model_path = ensure_model_downloaded(model_id, model_base_dir)
    return Path(local_model_path).resolve()


def _get_torch_dtype() -> torch.dtype:
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


def _print_trainable_parameters(model: torch.nn.Module) -> None:
    trainable_params = 0
    all_params = 0

    for param in model.parameters():
        all_params += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()

    percentage = 100.0 * trainable_params / all_params if all_params > 0 else 0.0

    print("\n" + "=" * 80)
    print("TRAINABLE PARAMETERS")
    print("=" * 80)
    print(f"Trainable params : {trainable_params}")
    print(f"All params       : {all_params}")
    print(f"Trainable %      : {percentage:.4f}")
    print("=" * 80)


def _tokenize_prompt_completion(
    example: Dict[str, Any],
    tokenizer: AutoTokenizer,
    max_length: int,
) -> Dict[str, List[int]]:
    """
    Convert one training example into token ids.

    We train the model only on the completion part.
    The prompt tokens get label -100, so loss is not computed on them.
    """
    prompt = example["prompt"]
    completion = example["completion"]

    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    completion_ids = tokenizer(completion, add_special_tokens=False)["input_ids"]

    if tokenizer.eos_token_id is not None:
        completion_ids = completion_ids + [tokenizer.eos_token_id]

    input_ids = (prompt_ids + completion_ids)[:max_length]
    attention_mask = [1] * len(input_ids)
    labels = ([-100] * len(prompt_ids) + completion_ids)[:max_length]

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


def _save_training_metadata(
    output_dir: Path,
    model_id: str,
    export_dir: Path,
    train_size: int,
    dev_size: int,
    training_config: Dict[str, Any],
) -> None:
    metadata = {
        "model_id": model_id,
        "dataset_dir": str(export_dir),
        "train_examples": train_size,
        "dev_examples": dev_size,
        "training_config": training_config,
    }

    metadata_path = output_dir / "training_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def train_sft_model(model_config: dict, dataset_path: str) -> None:
    """
    First working SFT trainer for prompt_completion exports.

    dataset_path must point to an exporter output directory containing:
    - train.jsonl
    - dev.jsonl
    """
    provider = model_config.get("provider", "huggingface")
    if provider != "huggingface":
        raise ValueError(
            f"SFT training only supports local Hugging Face models, got provider='{provider}'."
        )

    model_id = model_config["id"]
    training_config = model_config.get("training", {})

    training_mode = training_config.get("mode", "sft").lower()
    if training_mode != "sft":
        raise ValueError(
            f"train_sft_model received training mode '{training_mode}', expected 'sft'."
        )

    dataset_format = training_config.get("dataset_format", "prompt_completion")
    if dataset_format != "prompt_completion":
        raise ValueError(
            f"This first SFT trainer only supports dataset_format='prompt_completion', "
            f"got '{dataset_format}'."
        )

    task_type = training_config.get("task_type", "causal_lm")
    if task_type != "causal_lm":
        raise ValueError(
            f"This first SFT trainer only supports task_type='causal_lm', got '{task_type}'."
        )

    max_length = int(training_config.get("max_length", 1024))
    num_train_epochs = float(training_config.get("num_train_epochs", 3))
    learning_rate = float(training_config.get("learning_rate", 2e-4))
    per_device_train_batch_size = int(training_config.get("per_device_train_batch_size", 1))
    per_device_eval_batch_size = int(training_config.get("per_device_eval_batch_size", 1))
    gradient_accumulation_steps = int(training_config.get("gradient_accumulation_steps", 8))
    warmup_ratio = float(training_config.get("warmup_ratio", 0.05))
    logging_steps = int(training_config.get("logging_steps", 10))
    save_total_limit = int(training_config.get("save_total_limit", 2))
    lora_r = int(training_config.get("lora_r", 16))
    lora_alpha = int(training_config.get("lora_alpha", 32))
    lora_dropout = float(training_config.get("lora_dropout", 0.05))
    early_stopping_patience = int(training_config.get("early_stopping_patience", 2))

    target_modules = training_config.get(
        "lora_target_modules",
        ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    print("\n" + "=" * 80)
    print("SFT TRAINING MODE")
    print("=" * 80)
    print(f"Model ID        : {model_id}")
    print(f"Dataset path    : {dataset_path}")
    print("=" * 80)

    dataset_paths = _resolve_export_paths(dataset_path)
    export_dir = dataset_paths["export_dir"]
    train_path = dataset_paths["train_path"]
    dev_path = dataset_paths["dev_path"]

    local_model_path = _get_local_model_path(model_id)
    output_dir = _resolve_output_dir(model_id, export_dir)

    print(f"Local model path: {local_model_path}")
    print(f"Train split     : {train_path}")
    print(f"Dev split       : {dev_path}")
    print(f"Output dir      : {output_dir}")

    raw_datasets = load_dataset(
        "json",
        data_files={
            "train": str(train_path),
            "validation": str(dev_path),
        },
    )

    tokenizer = AutoTokenizer.from_pretrained(local_model_path, use_fast=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    torch_dtype = _get_torch_dtype()

    model = AutoModelForCausalLM.from_pretrained(
        local_model_path,
        torch_dtype=torch_dtype,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        target_modules=target_modules,
    )

    model = get_peft_model(model, lora_config)
    _print_trainable_parameters(model)

    def tokenize_fn(example: Dict[str, Any]) -> Dict[str, List[int]]:
        return _tokenize_prompt_completion(
            example=example,
            tokenizer=tokenizer,
            max_length=max_length,
        )

    tokenized_datasets = raw_datasets.map(
        tokenize_fn,
        remove_columns=raw_datasets["train"].column_names,
        desc="Tokenizing dataset",
    )

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=None,
        padding=True,
        label_pad_token_id=-100,
        return_tensors="pt",
    )

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    use_fp16 = torch.cuda.is_available() and not use_bf16

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        overwrite_output_dir=True,
        num_train_epochs=num_train_epochs,
        learning_rate=learning_rate,
        per_device_train_batch_size=per_device_train_batch_size,
        per_device_eval_batch_size=per_device_eval_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        warmup_ratio=warmup_ratio,
        logging_steps=logging_steps,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=use_fp16,
        bf16=use_bf16,
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=early_stopping_patience)],
    )

    print("\n" + "=" * 80)
    print("START TRAINING")
    print("=" * 80)

    trainer.train()

    print("\n" + "=" * 80)
    print("SAVING ADAPTER")
    print("=" * 80)

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    _save_training_metadata(
        output_dir=output_dir,
        model_id=model_id,
        export_dir=export_dir,
        train_size=len(raw_datasets["train"]),
        dev_size=len(raw_datasets["validation"]),
        training_config=training_config,
    )

    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)
    print(f"Saved fine-tuned adapter to: {output_dir}")