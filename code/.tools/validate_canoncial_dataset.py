#!/usr/bin/env python3
"""
validate_canoncial_dataset.py

Validate a canonical benchmark dataset stored as JSON or JSONL.

Expected canonical entry structure (minimum):
{
  "uid": "nlp4re-0001",
  "source_dataset": "NLP4RE",
  "source_id": 1,
  "family": "nlp4re",
  "question": "Which papers report ...?",
  "gold_query": "SELECT ...",
  "contribution_class": "orkgc:C121001"
}

This script checks:
- the input file can be loaded
- entries are JSON objects
- required fields exist
- uid values are unique
- question exists and is not empty
- gold_query exists and is not empty
- PREFIX lines were removed from gold_query
- contribution_class exists and looks valid
- obvious empty/null values are detected

Optional report writing:
- A report can be written via --report as a base path
- Or via --save-report using the default report directory from paths.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


PREFIX_PATTERN = re.compile(r"^\s*PREFIX\s+", re.IGNORECASE | re.MULTILINE)
CONTRIBUTION_CLASS_PATTERN = re.compile(r"^orkgc:C\d+$")


def get_repo_root() -> Path:
    """
    Resolve the repository root from this file location.

    Expected file location:
        code/tools/validate_canoncial_dataset.py
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
    Normalize the report base path.

    If the user passes a path ending in .json, .jsonl, or .txt,
    remove the extension because this script writes both .json and .txt reports.
    """
    output_str = str(output_path)

    for suffix in (".jsonl", ".json", ".txt"):
        if output_str.endswith(suffix):
            output_str = output_str[: -len(suffix)]
            break

    return Path(output_str)


def load_json_object(path: Path) -> Dict[str, Any]:
    """
    Load a JSON file and return its parsed object.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}, got {type(data).__name__}")

    return data


def get_default_report_base(paths_config_path: Path, repo_root: Path, input_path: Path) -> Path:
    """
    Build a default report base path from paths.json and the input file name.
    """
    paths_config = load_json_object(paths_config_path)

    reports_section = paths_config.get("reports")
    if not isinstance(reports_section, dict):
        raise ValueError("paths.json must contain a 'reports' object.")

    validation_dir_raw = reports_section.get("validation_dir")
    if not isinstance(validation_dir_raw, str) or not validation_dir_raw.strip():
        raise ValueError("paths.json must define reports.validation_dir as a non-empty string.")

    validation_dir = resolve_path(repo_root, validation_dir_raw)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return validation_dir / f"{input_path.stem}_validation_{timestamp}"


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

    suffix = path.suffix.lower()

    if suffix == ".jsonl":
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
                        f"Invalid JSON on line {line_number} in {path}: {exc}"
                    ) from exc

                if not isinstance(obj, dict):
                    raise ValueError(
                        f"Line {line_number} in {path} does not contain a JSON object."
                    )

                entries.append(obj)
        return entries

    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"JSON file must contain a list of objects: {path}")

        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Item {index} in {path} is not a JSON object.")

        return data

    raise ValueError(f"Unsupported file type: {path}. Use .json or .jsonl")


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


def build_report_text(
    input_path: Path,
    entries: List[Dict[str, Any]],
    errors: List[str],
    warnings: List[str],
) -> str:
    """
    Build a human-readable validation report.
    """
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append("Canonical Dataset Validation Report")
    lines.append("=" * 72)
    lines.append(f"Input file:    {input_path}")
    lines.append(f"Total entries: {len(entries)}")
    lines.append(f"Errors:        {len(errors)}")
    lines.append(f"Warnings:      {len(warnings)}")
    lines.append("")

    if errors:
        lines.append("Errors")
        lines.append("-" * 72)
        for message in errors:
            lines.append(f"[ERROR] {message}")
        lines.append("")

    if warnings:
        lines.append("Warnings")
        lines.append("-" * 72)
        for message in warnings:
            lines.append(f"[WARN]  {message}")
        lines.append("")

    if not errors and not warnings:
        lines.append("No issues found.")
        lines.append("")

    if not errors:
        lines.append("Validation result: PASSED")
    else:
        lines.append("Validation result: FAILED")

    return "\n".join(lines)


def build_report_json(
    input_path: Path,
    entries: List[Dict[str, Any]],
    errors: List[str],
    warnings: List[str],
) -> Dict[str, Any]:
    """
    Build a machine-readable validation report.
    """
    return {
        "input_file": str(input_path),
        "total_entries": len(entries),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "validation_passed": len(errors) == 0,
        "generated_at": datetime.now().isoformat(),
    }


def write_reports(report_base: Path, report_text: str, report_json: Dict[str, Any]) -> Tuple[Path, Path]:
    """
    Write both TXT and JSON reports using the given base path.
    """
    txt_path = report_base.with_suffix(".txt")
    json_path = report_base.with_suffix(".json")

    txt_path.parent.mkdir(parents=True, exist_ok=True)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write(report_text)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)

    return txt_path, json_path


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.
    """
    repo_root = get_repo_root()
    default_paths_config = repo_root / "code/config/paths.json"

    parser = argparse.ArgumentParser(
        description="Validate a canonical benchmark dataset (.json or .jsonl)."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the canonical dataset file (.json or .jsonl).",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional base path for saving TXT and JSON reports.",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save the report to the default validation report directory from paths.json.",
    )
    parser.add_argument(
        "--paths-config",
        default=str(default_paths_config),
        help="Path to paths.json. Defaults to code/config/paths.json.",
    )

    return parser.parse_args()


def main() -> int:
    """
    Parse arguments, run validation, optionally write reports, and return the exit code.
    """
    args = parse_args()
    repo_root = get_repo_root()

    input_path = resolve_path(repo_root, args.input)
    paths_config_path = resolve_path(repo_root, args.paths_config)

    try:
        entries = load_dataset(input_path)
        errors, warnings = validate_dataset(entries)

        report_text = build_report_text(
            input_path=input_path,
            entries=entries,
            errors=errors,
            warnings=warnings,
        )
        report_json = build_report_json(
            input_path=input_path,
            entries=entries,
            errors=errors,
            warnings=warnings,
        )

        print(report_text)

        report_base: Path | None = None
        if args.report:
            report_base = normalize_output_base(resolve_path(repo_root, args.report))
        elif args.save_report:
            report_base = get_default_report_base(
                paths_config_path=paths_config_path,
                repo_root=repo_root,
                input_path=input_path,
            )

        if report_base is not None:
            txt_path, json_path = write_reports(report_base, report_text, report_json)
            print("")
            print(f"Saved TXT report:  {txt_path}")
            print(f"Saved JSON report: {json_path}")

        return 0 if not errors else 1

    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())