#!/usr/bin/env python3
"""
validate_canoncial_dataset.py

Validate a canonical benchmark dataset stored as JSONL or JSON.

Expected canonical entry structure (minimum):
{
  "uid": "nlp4-0001",
  "source_dataset": "NLP4",
  "source_id": 1,
  "family": "nlp4re",
  "question": "Which papers report ...?",
  "gold_query": "SELECT ...",
  "contribution_class": "orkgc:C121001"
}

This script checks:
- file can be loaded
- entries are dictionaries
- required fields exist
- uid values are unique
- question exists and is not empty
- gold_query is not empty
- PREFIX lines were removed from gold_query
- contribution_class is present and looks valid
- obvious empty/null values are detected

Exit codes:
- 0: validation passed (warnings may still exist)
- 1: validation failed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


PREFIX_PATTERN = re.compile(r"^\s*PREFIX\s+", re.IGNORECASE | re.MULTILINE)
CONTRIBUTION_CLASS_PATTERN = re.compile(r"^orkgc:C\d+$")


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    """
    Load a dataset from either a JSONL file or a JSON file.

    JSONL:
        One JSON object per line.

    JSON:
        A list of JSON objects.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() == ".jsonl":
        entries: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON on line {line_number}: {exc}"
                    ) from exc
                if not isinstance(obj, dict):
                    raise ValueError(
                        f"Line {line_number} does not contain a JSON object."
                    )
                entries.append(obj)
        return entries

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of objects.")
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Item {index} in JSON file is not an object.")
        return data

    raise ValueError("Unsupported file type. Please use .json or .jsonl")


def is_blank(value: Any) -> bool:
    """
    Return True if a value is effectively blank.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def validate_entry(entry: Dict[str, Any], index: int) -> Tuple[List[str], List[str]]:
    """
    Validate a single dataset entry.

    Returns:
    - errors: critical validation problems
    - warnings: non-critical issues
    """
    errors: List[str] = []
    warnings: List[str] = []

    required_fields = [
        "uid",
        "source_dataset",
        "source_id",
        "family",
        "question",
        "gold_query",
        "contribution_class",
    ]

    for field in required_fields:
        if field not in entry:
            errors.append(f"Entry {index}: missing required field '{field}'.")

    if errors:
        return errors, warnings

    uid = entry.get("uid")
    if is_blank(uid):
        errors.append(f"Entry {index}: 'uid' is empty.")
    elif not isinstance(uid, str):
        errors.append(f"Entry {index}: 'uid' must be a string.")

    source_dataset = entry.get("source_dataset")
    if is_blank(source_dataset):
        errors.append(f"Entry {index}: 'source_dataset' is empty.")
    elif not isinstance(source_dataset, str):
        errors.append(f"Entry {index}: 'source_dataset' must be a string.")

    source_id = entry.get("source_id")
    if source_id is None:
        errors.append(f"Entry {index}: 'source_id' is null.")
    elif not isinstance(source_id, (int, str)):
        errors.append(
            f"Entry {index}: 'source_id' must be an integer or string, got {type(source_id).__name__}."
        )

    family = entry.get("family")
    if is_blank(family):
        errors.append(f"Entry {index}: 'family' is empty.")
    elif not isinstance(family, str):
        errors.append(f"Entry {index}: 'family' must be a string.")

    question = entry.get("question")
    if not isinstance(question, str) or question.strip() == "":
        errors.append(f"Entry {index}: 'question' is empty or not a string.")

    gold_query = entry.get("gold_query")
    if not isinstance(gold_query, str) or gold_query.strip() == "":
        errors.append(f"Entry {index}: 'gold_query' is empty or not a string.")
    else:
        if PREFIX_PATTERN.search(gold_query):
            errors.append(
                f"Entry {index}: 'gold_query' still contains PREFIX lines."
            )

        if not re.search(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", gold_query, re.IGNORECASE):
            warnings.append(
                f"Entry {index}: 'gold_query' does not seem to contain a common SPARQL query form."
            )

    contribution_class = entry.get("contribution_class")
    if not isinstance(contribution_class, str) or contribution_class.strip() == "":
        errors.append(
            f"Entry {index}: 'contribution_class' is empty or not a string."
        )
    elif not CONTRIBUTION_CLASS_PATTERN.match(contribution_class.strip()):
        warnings.append(
            f"Entry {index}: 'contribution_class' does not match the expected pattern 'orkgc:C<digits>'."
        )

    if "tags" in entry and not isinstance(entry["tags"], list):
        warnings.append(f"Entry {index}: 'tags' should be a list.")

    if "difficulty" in entry:
        allowed_difficulties = {"easy", "medium", "hard"}
        difficulty = entry["difficulty"]
        if difficulty is not None and difficulty not in allowed_difficulties:
            warnings.append(
                f"Entry {index}: 'difficulty' should be one of {sorted(allowed_difficulties)}."
            )

    return errors, warnings


def validate_dataset(entries: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """
    Validate the full dataset and also check cross-entry constraints,
    such as duplicate uid values.
    """
    errors: List[str] = []
    warnings: List[str] = []

    seen_uids: Dict[str, int] = {}

    for index, entry in enumerate(entries, start=1):
        entry_errors, entry_warnings = validate_entry(entry, index)
        errors.extend(entry_errors)
        warnings.extend(entry_warnings)

        uid = entry.get("uid")
        if isinstance(uid, str) and uid.strip():
            if uid in seen_uids:
                errors.append(
                    f"Duplicate uid '{uid}' found in entries {seen_uids[uid]} and {index}."
                )
            else:
                seen_uids[uid] = index

    return errors, warnings


def print_report(entries: List[Dict[str, Any]], errors: List[str], warnings: List[str]) -> None:
    """
    Print a readable validation summary.
    """
    print("=" * 72)
    print("Canonical Dataset Validation Report")
    print("=" * 72)
    print(f"Total entries: {len(entries)}")
    print(f"Errors:        {len(errors)}")
    print(f"Warnings:      {len(warnings)}")
    print()

    if errors:
        print("Errors")
        print("-" * 72)
        for message in errors:
            print(f"[ERROR] {message}")
        print()

    if warnings:
        print("Warnings")
        print("-" * 72)
        for message in warnings:
            print(f"[WARN]  {message}")
        print()

    if not errors and not warnings:
        print("No issues found.")
        print()

    if not errors:
        print("Validation result: PASSED")
    else:
        print("Validation result: FAILED")


def main() -> int:
    """
    Parse arguments, run validation, and return the process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Validate a canonical benchmark dataset (.json or .jsonl)."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the canonical dataset file (.json or .jsonl).",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)

    try:
        entries = load_dataset(input_path)
        errors, warnings = validate_dataset(entries)
        print_report(entries, errors, warnings)
        return 0 if not errors else 1
    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())