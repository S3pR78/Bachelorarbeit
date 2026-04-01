from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from prompting.prompt_loader import build_prompt_for_entry
from utils.path_manager import get_path


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._-") or "dataset"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _save_jsonl(rows: Sequence[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _extract_entries(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]

    raise ValueError(
        "Input file must be either a JSON list of benchmark/canonical entries "
        "or a JSON object with a 'results' list."
    )


def _validate_entry(entry: Dict[str, Any], index: int) -> None:
    family = entry.get("family")
    question = entry.get("question")
    gold_query = entry.get("gold_query")

    if not isinstance(family, str) or not family.strip():
        raise ValueError(f"Entry {index} has no valid 'family'.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Entry {index} has no valid 'question'.")
    if not isinstance(gold_query, str) or not gold_query.strip():
        raise ValueError(f"Entry {index} has no valid 'gold_query'.")


def _build_prompt_completion_example(entry: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_prompt_for_entry(entry)
    gold_query = entry["gold_query"].strip()

    return {
        "uid": entry.get("uid"),
        "benchmark_entry_id": entry.get("benchmark_entry_id", entry.get("uid")),
        "source_id": entry.get("source_id"),
        "source_dataset": entry.get("source_dataset"),
        "family": entry.get("family"),
        "question": entry.get("question"),
        "prompt": prompt,
        "completion": gold_query,
    }


def _build_messages_example(entry: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_prompt_for_entry(entry)
    gold_query = entry["gold_query"].strip()

    return {
        "uid": entry.get("uid"),
        "benchmark_entry_id": entry.get("benchmark_entry_id", entry.get("uid")),
        "source_id": entry.get("source_id"),
        "source_dataset": entry.get("source_dataset"),
        "family": entry.get("family"),
        "question": entry.get("question"),
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": gold_query},
        ],
    }


def _build_examples(
    entries: Sequence[Dict[str, Any]],
    export_format: str,
) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []

    for index, entry in enumerate(entries, start=1):
        _validate_entry(entry, index)

        if export_format == "prompt_completion":
            example = _build_prompt_completion_example(entry)
        elif export_format == "messages":
            example = _build_messages_example(entry)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        examples.append(example)

    return examples


def _split_examples(
    examples: Sequence[Dict[str, Any]],
    train_ratio: float,
    dev_ratio: float,
    test_ratio: float,
    seed: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    total_ratio = train_ratio + dev_ratio + test_ratio
    if abs(total_ratio - 1.0) > 1e-9:
        raise ValueError("train_ratio + dev_ratio + test_ratio must sum to 1.0")

    shuffled = list(examples)
    rng = random.Random(seed)
    rng.shuffle(shuffled)

    total = len(shuffled)
    train_end = int(total * train_ratio)
    dev_end = train_end + int(total * dev_ratio)

    train_split = shuffled[:train_end]
    dev_split = shuffled[train_end:dev_end]
    test_split = shuffled[dev_end:]

    return train_split, dev_split, test_split


def _build_output_dir(input_path: Path, dataset_name: str | None) -> Path:
    gold_base_dir = Path(get_path("finetuning.gold_dir")).resolve()

    if dataset_name and dataset_name.strip():
        export_name = _safe_name(dataset_name)
    else:
        export_name = _safe_name(input_path.stem)

    output_dir = gold_base_dir / export_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def export_gold_finetuning_dataset(
    input_path_str: str,
    dataset_name: str | None = None,
    export_format: str = "prompt_completion",
    split: bool = True,
    train_ratio: float = 0.8,
    dev_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> Path:
    input_path = Path(input_path_str).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    payload = _load_json(input_path)
    entries = _extract_entries(payload)
    examples = _build_examples(entries, export_format=export_format)

    output_dir = _build_output_dir(input_path, dataset_name)

    metadata: Dict[str, Any] = {
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "export_format": export_format,
        "total_examples": len(examples),
        "split_enabled": split,
        "seed": seed,
    }

    if split:
        train_split, dev_split, test_split = _split_examples(
            examples=examples,
            train_ratio=train_ratio,
            dev_ratio=dev_ratio,
            test_ratio=test_ratio,
            seed=seed,
        )

        _save_jsonl(train_split, output_dir / "train.jsonl")
        _save_jsonl(dev_split, output_dir / "dev.jsonl")
        _save_jsonl(test_split, output_dir / "test.jsonl")

        metadata["train_ratio"] = train_ratio
        metadata["dev_ratio"] = dev_ratio
        metadata["test_ratio"] = test_ratio
        metadata["train_examples"] = len(train_split)
        metadata["dev_examples"] = len(dev_split)
        metadata["test_examples"] = len(test_split)
    else:
        _save_jsonl(examples, output_dir / "all.jsonl")
        metadata["all_examples"] = len(examples)

    _save_json(metadata, output_dir / "export_metadata.json")

    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a gold fine-tuning dataset from a canonical/benchmark JSON file."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to canonical dataset JSON or benchmark_raw.json",
    )
    parser.add_argument(
        "--dataset-name",
        help="Optional output folder name. Defaults to the input filename stem.",
    )
    parser.add_argument(
        "--format",
        choices=["prompt_completion", "messages"],
        default="prompt_completion",
        help="Export format for fine-tuning.",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Write a single all.jsonl instead of train/dev/test splits.",
    )
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--dev-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output_dir = export_gold_finetuning_dataset(
        input_path_str=args.input,
        dataset_name=args.dataset_name,
        export_format=args.format,
        split=not args.no_split,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )

    print("\n" + "=" * 80)
    print("GOLD FINETUNING EXPORT COMPLETE")
    print("=" * 80)
    print(f"Saved export to: {output_dir}")


if __name__ == "__main__":
    main()