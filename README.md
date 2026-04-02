# Bachelor's thesis


Technical pipeline for SPARQL generation with LLMs for ORKG templates.


This repository contains tooling for:

- converting `.sparqlbook` files into canonical JSON / JSONL datasets
- generating template-specific prompts
- running benchmarks with local or API-backed models
- validating generated SPARQL queries
- exporting gold datasets for fine-tuning
- running LoRA-based supervised fine-tuning (SFT) for local Hugging Face models

## Draft notice

This README is a **technical draft**.  
It is not the final project description and it may change as the repository evolves.

The goal of this document is to explain:

- which files and configuration files are important
- from which directory commands should be executed
- which steps are optional
- which scripts create which outputs
- how to add or change models
- how the current pipeline is used in practice

## Prompt generation attribution

The prompt-generation logic in this project is based on and adapted from `promptGenerator.ts` in the **EmpiRE-Compass** repository:

- `https://github.com/okarras/EmpiRE-Compass/blob/main/src/utils/promptGenerator.ts`

---

## 1. Working directory

All commands in this README are meant to be run from the **repository root**:

```bash
cd /path/to/BA
```

Many scripts under `code/src/...` use imports such as `from prompting...` or `from utils...`.
To make these imports work when running scripts directly, set `PYTHONPATH` first:

```bash
export PYTHONPATH=code:code/src
```

---


## 2. Project structure

```text
Bachelorarbeit/
├── code/
│   ├── config/
│   │   ├── paths.json
│   │   ├── dataset_registry.json
│   │   ├── prompt_profiles.json
│   │   └── models_config.json
│   ├── data/
│   │   ├── raw/
│   │   ├── canonical/
│   │   ├── benchmark_runs/
│   │   └── finetuning/
│   ├── prompts/
│   │   └── generated/
│   ├── src/
│   │   ├── benchmark/
│   │   ├── core/
│   │   ├── prompting/
│   │   ├── training/
│   │   ├── validation/
│   │   └── utils/
│   └── tools/
└── README.md
```

---

## 3. Main configuration files

### `code/config/paths.json`
Central path configuration.

Typical entries:
- model storage directory
- benchmark run directory
- fine-tuning export directories
- validation / report directories

### `code/config/dataset_registry.json`
Dataset metadata used during conversion.

Typical fields:
- `source_dataset`
- `family`
- `uid_prefix`

### `code/config/prompt_profiles.json`
Maps a template family to its prompt profile.

Examples:
- `nlp4re`
- `empirical_research`

### `code/config/models_config.json`
Defines available models, inference parameters, and training parameters.

This is the main file to edit when:
- adding a new model
- changing generation settings
- changing training settings
- configuring an optional LoRA adapter for inference

---

## 4. Pipeline overview

There are two common starting points.

### Option A: Start from `.sparqlbook` (recommended)
Use the conversion step first.

### Option B: Start from canonical JSON / JSONL
If you already have a canonical dataset, you can skip the conversion step and continue with:
- merge
- benchmark
- validation
- fine-tuning export
- training

---

## 5. Step 1: Convert `.sparqlbook` to canonical JSON / JSONL

Script:

```text
code/.tools/convert_sparqlbook.py
```

This script:
- reads one `.sparqlbook` file
- extracts questions and gold SPARQL queries
- removes leading `PREFIX` lines from the query
- removes full-line comments starting with `#`
- uses only the English version if a question block contains both `DE:` and `EN:`
- writes both `.json` and `.jsonl`

### Example

```bash
export PYTHONPATH=code:code/src

python3 code/.tools/convert_sparqlbook.py \
  --dataset nlp4re \
  --input code/data/raw/NLP4RE/question.sparqlbook \
  --output code/data/canonical/per_source/nlp4re
```

### Output

```text
code/data/canonical/per_source/nlp4re.json
code/data/canonical/per_source/nlp4re.jsonl
```

### Arguments

- `--dataset`  
  Dataset key from `dataset_registry.json`

- `--input`  
  Input `.sparqlbook` file

- `--output`  
  Output base path without extension

### If you already have canonical JSON

You can skip this step.

---

## 6. Step 2: Merge canonical datasets

Script:

```text
code/tools/merge_canonical_datasets.py
```

This script merges multiple canonical datasets into one dataset.

### Example

```bash
python3 code/tools/merge_canonical_datasets.py \
  --inputs code/data/canonical/per_source/nlp4re.json code/data/canonical/per_source/empirical_research.json \
  --output code/data/canonical/merged/benchmark/benchmark_dataset_V1.json
```

---

## 7. Step 3: Prompt generation

Prompt generation is handled through the prompt-loading / prompt-building logic in the repository.
The generated prompt is built dynamically from:
- the selected template family
- the configured prompt profile
- the input question

Relevant modules:

```text
code/src/prompting/prompt_loader.py
code/prompts/generated/
```

### What happens here

For a benchmark entry or a single question, the system:
1. finds the correct prompt profile via `family`
2. loads the latest generated prompt template
3. injects the question into the final prompt

### Important note

This project’s prompt-generation logic is based on and adapted from the EmpiRE-Compass `promptGenerator.ts` implementation.

---

## 8. Step 4: Run a benchmark

Entry point:

```text
code/src/main.py
```

Benchmark mode:
- loads the benchmark dataset
- builds the final prompt for each entry
- calls the selected model
- stores both raw model output and extracted SPARQL
- creates a dedicated run directory for each benchmark run

### Example

```bash
export PYTHONPATH=code:code/src

python3 code/src/main.py \
  --model Qwen/Qwen3-0.6B \
  --mode benchmark \
  --benchmark code/data/canonical/merged/benchmark/benchmark_dataset_V1.json
```

### Output

A new run directory is created under the benchmark runs directory configured in `paths.json`.

Example:

```text
code/data/benchmark_runs/20260330_181901__Qwen3-0.6B__benchmark_dataset_V1/
  benchmark_raw.json
```

### What is stored in `benchmark_raw.json`

For each entry, the benchmark runner stores:
- `question`
- `gold_query`
- `raw_model_output`
- `extracted_query`
- timing metadata

---

## 9. Step 5: Validate benchmark outputs

Script:

```text
code/src/validation/benchmark_validator.py
```

Validation currently checks:
- whether a query was extracted
- whether the query looks truncated
- whether the query is syntactically parseable
- readable parse-error hints
- repair-candidate labels

### Example

```bash
export PYTHONPATH=code:code/src

python3 code/src/validation/benchmark_validator.py \
  --input code/data/benchmark_runs/20260330_181901__Qwen3-0.6B__benchmark_dataset_V1/benchmark_raw.json
```

### Output

```text
code/data/benchmark_runs/20260330_181901__Qwen3-0.6B__benchmark_dataset_V1/validation_report.json
```

### Current purpose of validation

At the moment, validation focuses on:
- extraction quality
- syntax quality
- repair suitability

It is **not yet** the final benchmark comparison against gold query execution results.

---

## 10. Step 6: Export a gold dataset for fine-tuning

Script:

```text
code/src/training/gold_finetuning_exporter.py
```

This module is a **data-preparation step**, not the training itself.

It:
- reads a gold dataset
- converts each entry into a training format
- optionally creates train / dev / test splits
- writes JSONL files for training

### Supported export format

Current main format:
- `prompt_completion`

### Example with split

```bash
export PYTHONPATH=code:code/src

python3 code/src/training/gold_finetuning_exporter.py \
  --input code/data/canonical/merged/benchmark/benchmark_dataset_V1.json \
  --dataset-name TrainDataset_V1 \
  --format prompt_completion
```

### Output

```text
code/data/finetuning/gold/TrainDataset_V1/
  train.jsonl
  dev.jsonl
  test.jsonl
  export_metadata.json
```

### Example without split

```bash
python3 code/src/training/gold_finetuning_exporter.py \
  --input code/data/canonical/merged/benchmark/benchmark_dataset_V1.json \
  --dataset-name TrainDataset_V1 \
  --format prompt_completion \
  --no-split
```

This produces:

```text
code/data/finetuning/gold/TrainDataset_V1/
  all.jsonl
  export_metadata.json
```

### Why this module exists

Your benchmark / canonical data is not yet in the exact format expected by training.
The exporter separates:
- **content data** (`question`, `gold_query`, `family`)
- **training format** (`prompt`, `completion`, train/dev/test splits)

---

## 11. Step 7: Supervised fine-tuning (SFT)

### What is SFT?

SFT = **Supervised Fine-Tuning**

The model learns from pairs such as:
- input prompt
- gold SPARQL query

In this project, the current SFT implementation uses **LoRA** for local Hugging Face models.

This means:
- the base model remains unchanged
- a trainable adapter is learned
- the adapter can later be loaded optionally during inference

### Training files

Dispatcher:

```text
code/src/training/trainer.py
```

Current SFT implementation:

```text
code/src/training/sft_trainer.py
```

### Example

```bash
export PYTHONPATH=code:code/src

python3 code/src/main.py \
  --model Qwen/Qwen3-0.6B \
  --mode train \
  --benchmark code/data/finetuning/gold/TrainDataset_V1
```

> Note: the CLI argument is currently still called `--benchmark`, but in training mode it is used as the path to the fine-tuning export directory.

### Output

The trained LoRA adapter is stored under the model base directory, typically in:

```text
models/finetuned/<model>__<dataset>/
```

---

## 12. Base model vs. base model + adapter

You can still load the normal base model without any adapter.

You can also define a second config entry that loads the same base model plus a trained LoRA adapter.

### Example model config entry with adapter

```json
{
  "name": "Qwen3-0.6B-SFT-TrainDataset-V1",
  "id": "Qwen/Qwen3-0.6B",
  "provider": "huggingface",
  "adapter_subdir": "finetuned/Qwen_Qwen3-0.6B__TrainDataset_V1",
  "params": {
    "max_new_tokens": 400,
    "do_sample": false
  }
}
```

If `adapter_subdir` is missing, only the base model is loaded.

If `adapter_subdir` is present, the system loads:
- the base model
- the LoRA adapter on top of it

---

## 13. Adding a new model

New models are added in:

```text
code/config/models_config.json
```

### Minimal example

```json
{
  "name": "Qwen3-0.6B",
  "id": "Qwen/Qwen3-0.6B",
  "provider": "huggingface",
  "params": {
    "max_new_tokens": 400,
    "do_sample": false
  },
  "training": {
    "mode": "sft",
    "task_type": "causal_lm",
    "dataset_format": "prompt_completion",
    "max_length": 1024,
    "num_train_epochs": 3,
    "learning_rate": 0.0002,
    "per_device_train_batch_size": 1,
    "per_device_eval_batch_size": 1,
    "gradient_accumulation_steps": 8,
    "warmup_ratio": 0.05,
    "logging_steps": 10,
    "save_total_limit": 2,
    "early_stopping_patience": 2,
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "lora_target_modules": [
      "q_proj",
      "k_proj",
      "v_proj",
      "o_proj",
      "gate_proj",
      "up_proj",
      "down_proj"
    ]
  }
}
```

### Main fields

- `name`  
  Name used in the CLI

- `id`  
  Hugging Face model ID

- `provider`  
  Currently only local `huggingface` models are supported for local training

- `params`  
  Generation parameters for inference

- `training`  
  Training parameters for SFT

- `adapter_subdir`  
  Optional; used when loading a fine-tuned LoRA adapter during inference

### What you are allowed to change

Usually safe to change:
- `params`
- `training.*`
- `adapter_subdir`
- additional model entries

Be careful with:
- wrong `lora_target_modules`
- wrong `task_type`
- wrong `dataset_format`

---

## 14. `argparse` in this repository

Many scripts in this repository use `argparse`.

This means:
- the script expects command-line arguments
- these arguments are passed when the script is started

### Example

```bash
python3 code/tools/convert_sparqlbook.py \
  --dataset nlp4re \
  --input code/data/raw/NLP4RE/question.sparqlbook \
  --output code/data/canonical/per_source/nlp4re
```

Here:
- `--dataset`
- `--input`
- `--output`

are command-line arguments read by the script.

If an argument is marked as required in the script, it must be provided.

---

## 15. Current technical status

Currently implemented:
- `.sparqlbook` to canonical conversion
- canonical dataset merge
- prompt loading
- benchmark runner
- benchmark validation
- gold fine-tuning export
- first LoRA-based SFT pipeline
- optional LoRA adapter loading for inference

Partially implemented or planned:
- stronger benchmark comparison against gold queries
- repair dataset exporter
- teacher-student / distillation
- ACE-based agentic context engineering workflows
- richer evaluation and query-result comparison

---

## 16. Typical quick-start paths

### If you start from `.sparqlbook`

```bash
export PYTHONPATH=code:code/src

python3 code/tools/convert_sparqlbook.py ...
python3 code/tools/merge_canonical_datasets.py ...
python3 code/src/main.py --model ... --mode benchmark --benchmark ...
python3 code/src/validation/benchmark_validator.py --input ...
python3 code/src/training/gold_finetuning_exporter.py --input ...
python3 code/src/main.py --model ... --mode train --benchmark ...
```

### If you already have canonical JSON

You can start directly from a later step, for example:
- merge
- benchmark
- validation
- fine-tuning export
- training

---

## 17. Main entry point

The main CLI entry point of this project is:

```bash
python3 code/src/main.py
```

Before running it, make sure you are in the repository root and set:

```bash
export PYTHONPATH=code:code/src
```

### General command structure
python3 code/src/main.py --model <MODEL> --mode <MODE> [additional arguments]

### General required arguments
--model
    Model name, model ID, or model key from models_config.json
--mode
    Execution mode. Currently supported:
        - single
        - benchmark
        - train

#### Mode: single
This mode is used to test one question directly.

It:

- builds the final prompt for one question
- optionally prints the prompt
- runs inference once
- prints the model response


Required arguments for single
- --model
- --mode single
- --family
- --question

Optional arguments for single
- --show-prompt

Prints the final generated prompt before running inference

Example


```bash
export PYTHONPATH=code:code/src

python3 code/src/main.py \
  --model Qwen/Qwen3-0.6B \
  --mode single \
  --family nlp4re \
  --question "Which RE tasks are discussed in the papers?" \
  --show-prompt
```
Typical use case

Use single mode when:

- testing whether prompt loading works
- testing one question quickly
- checking raw model behavior
- debugging prompt generation

#### Mode: benchmark

This mode is used to run a full benchmark dataset.

It:

    loads a benchmark JSON dataset
    generates one prompt per entry
    runs the model on all entries
    stores raw model output and extracted query
    creates a dedicated run directory
    
Required arguments for benchmark
-    --model
-    --mode benchmark
-    --benchmark

Example

```bash
export PYTHONPATH=code:code/src

python3 code/src/main.py \
  --model Qwen/Qwen3-0.6B \
  --mode benchmark \
  --benchmark code/data/canonical/merged/benchmark/benchmark_dataset_V1.json
```

Output

This creates a new run directory under the benchmark runs path, for example:

```bash
code/data/benchmark_runs/20260330_181901__Qwen3-0.6B__benchmark_dataset_V1/
  benchmark_raw.json
```

Typical use case

Use benchmark mode when:

- evaluating one model on many benchmark questions
- collecting raw outputs for validation
- preparing repair candidates
- comparing different model variants later

#### Mode: train

This mode is used to start model training.

At the moment, this is mainly used for SFT (Supervised Fine-Tuning) on exported gold datasets.

Required arguments for train
- --model
- --mode train
- --benchmark

Note: in training mode, the argument is currently still called --benchmark, but it is used as the path to the exported fine-tuning dataset directory.

Expected input for train

The training path should point to a fine-tuning export directory, for example:

```bash
code/data/finetuning/gold/TrainDataset_V1/
```

This directory is expected to contain at least:

```bash
train.jsonl
dev.jsonl
```

Example

```bash
export PYTHONPATH=code:code/src

python3 code/src/main.py \
  --model Qwen/Qwen3-0.6B \
  --mode train \
  --benchmark code/data/finetuning/gold/TrainDataset_V1
```

Typical use case

Use train mode when:

- a gold fine-tuning export has already been created
- train.jsonl and dev.jsonl already exist
- you want to train a LoRA adapter for a local Hugging Face model


## 18. Notes

- All commands in this README assume the repository root as the working directory.
- If imports fail, first set:

```bash
export PYTHONPATH=code:code/src
```

- Local training currently supports local Hugging Face models.
- OpenAI / API models are not trained with the local LoRA trainer.
- Prompt generation is adapted from the EmpiRE-Compass prompt generation utility.