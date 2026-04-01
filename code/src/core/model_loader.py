from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


def _get_torch_dtype() -> torch.dtype:
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


def load_inference_pipeline(
    model_path: str | Path,
    model_params: dict,
    adapter_path: str | Path | None = None,
):
    """
    Load a text-generation pipeline from a local base model.
    Optionally attach a LoRA adapter.
    """
    model_path = str(Path(model_path).resolve())
    adapter_path_resolved = str(Path(adapter_path).resolve()) if adapter_path else None

    tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    torch_dtype = _get_torch_dtype()

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch_dtype,
    )

    if adapter_path_resolved:
        print(f"Loading adapter from {adapter_path_resolved}...")
        model = PeftModel.from_pretrained(model, adapter_path_resolved)
        print("Adapter loaded successfully.")

    model.eval()

    return pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
    )