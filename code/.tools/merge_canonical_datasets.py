#!/usr/bin/env python3
"""
merge_canonical_datasets.py

Merge multiple canonical dataset files into one combined dataset.

Rules:
- At least two input files must be provided via --inputs.
- Input files can be either .json or .jsonl.
- The output is provided as a base path via --output.
  Example:
      --output code/data/canonical/merged/benchmark_merged
  This creates:
      code/data/canonical/merged/benchmark_merged.json
      code/data/canonical/merged/benchmark_merged.jsonl

Validation:
- Duplicate uid values are rejected by default.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def get_repo_root() -> Path:
    """
    Resolve the repository root from this file location.

    Expected file location:
        code/tools/merge_canonical_datasets.py
    """
    return Path(__file__).resolve().parents[2]


def resolve_path(repo_root: Path, raw_path: str) -> Path:
    """
    Resolve a path relative to the repository root unless it is already absolute.
    """
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return repo_root / path


def normalize_output_base(output_path: Path) -> Path:
    """
    Normalize the output base path.

    If the user passes a path ending in .json or .jsonl, remove the extension,
    because this script always writes both formats.
    """
    output_str = str(output_path)

    if output_str.endswith(".jsonl"):
        output_str = output_str[:-6]
    elif output_str.endswith(".json"):
        output_str = output_str[:-5]

    return Path(output_str)


def load_json_file(path: Path) -> List[Dict[str, Any]]:
    """
    Load a dataset from a .json file.

    Expected format:
    - a JSON list of objects
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(data).__name__}")

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} in {path} is not a JSON object.")

    return data


def load_jsonl_file(path: Path) -> List[Dict[str, Any]]:
    """
    Load a dataset from a .jsonl file.

    Expected format:
    - one JSON object per non-empty line
    """
    entries: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} in {path}: {exc}"
                ) from exc

            if not isinstance(item, dict):
                raise ValueError(
                    f"Line {line_number} in {path} does not contain a JSON object."
                )

            entries.append(item)

    return entries


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    """
    Load a dataset from either .json or .jsonl.
    """
    suffix = path.suffix.lower()

    if suffix == ".json":
        return load_json_file(path)

    if suffix == ".jsonl":
        return load_jsonl_file(path)

    raise ValueError(f"Unsupported file type for {path}. Expected .json or .jsonl.")


def validate_input_paths(paths: List[Path]) -> None:
    """
    Validate the input paths.
    """
    if len(paths) < 2:
        raise ValueError("You must provide at least two input files to merge.")

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")


def merge_datasets(input_paths: List[Path]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Merge multiple canonical datasets into one list.

    Returns:
    - merged entries
    - per-file entry counts
    """
    merged_entries: List[Dict[str, Any]] = []
    per_file_counts: Dict[str, int] = {}

    for path in input_paths:
        entries = load_dataset(path)
        merged_entries.extend(entries)
        per_file_counts[str(path)] = len(entries)

    return merged_entries, per_file_counts


def check_duplicate_uids(entries: List[Dict[str, Any]]) -> None:
    """
    Reject duplicate uid values.
    """
    seen: Dict[str, int] = {}

    for index, entry in enumerate(entries, start=1):
        uid = entry.get("uid")

        if not isinstance(uid, str) or not uid.strip():
            raise ValueError(f"Entry {index} is missing a valid 'uid' field.")

        if uid in seen:
            first_index = seen[uid]
            raise ValueError(
                f"Duplicate uid detected: '{uid}' appears in merged entries "
                f"{first_index} and {index}."
            )

        seen[uid] = index


def write_outputs(entries: List[Dict[str, Any]], output_base: Path) -> Tuple[Path, Path]:
    """
    Write both JSON and JSONL outputs using the given base path.
    """
    output_json = output_base.with_suffix(".json")
    output_jsonl = output_base.with_suffix(".jsonl")

    output_json.parent.mkdir(parents=True, exist_ok=True)

    with output_json.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    with output_jsonl.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return output_json, output_jsonl


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="Merge multiple canonical dataset files into one combined dataset."
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Input dataset files (.json or .jsonl). At least two are required.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Base output path without extension. The script will create both .json and .jsonl.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Load input datasets, merge them, validate uid uniqueness, and write outputs.
    """
    args = parse_args()
    repo_root = get_repo_root()

    input_paths = [resolve_path(repo_root, raw_path) for raw_path in args.inputs]
    output_base = normalize_output_base(resolve_path(repo_root, args.output))

    validate_input_paths(input_paths)

    merged_entries, per_file_counts = merge_datasets(input_paths)
    check_duplicate_uids(merged_entries)

    output_json, output_jsonl = write_outputs(merged_entries, output_base)

    print("Merge completed successfully.")
    print(f"Input files: {len(input_paths)}")
    for path_str, count in per_file_counts.items():
        print(f"  - {path_str}: {count} entries")

    print(f"Total merged entries: {len(merged_entries)}")
    print(f"JSON:  {output_json}")
    print(f"JSONL: {output_jsonl}")


if __name__ == "__main__":
    main()