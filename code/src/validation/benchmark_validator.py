from __future__ import annotations
import re

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from rdflib.plugins.sparql.parser import parseQuery


VALID_QUERY_STARTS = ("SELECT", "ASK", "CONSTRUCT", "DESCRIBE")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}, got {type(data).__name__}")

    return data


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def has_extracted_query(query: str) -> bool:
    return isinstance(query, str) and bool(query.strip())


def has_valid_query_start(query: str) -> bool:
    if not has_extracted_query(query):
        return False

    stripped = query.lstrip()
    upper = stripped.upper()
    return upper.startswith(VALID_QUERY_STARTS)


def has_balanced_braces(query: str) -> bool:
    balance = 0
    for ch in query:
        if ch == "{":
            balance += 1
        elif ch == "}":
            balance -= 1
            if balance < 0:
                return False
    return balance == 0


def ends_suspiciously(query: str) -> bool:
    if not has_extracted_query(query):
        return False

    stripped = query.rstrip()
    lower = stripped.lower()

    suspicious_endings = (
        "?",
        "or",
        "and",
        "prefix",
        "select",
        "where",
        "{",
        "(",
        ",",
        ";",
    )

    return any(lower.endswith(ending) for ending in suspicious_endings)

def build_parse_error_hint(error_message: str) -> str:
    lower = error_message.lower()

    if "empty query" in lower:
        return "No SPARQL query could be extracted from the model output."

    if "found '?'" in error_message:
        return (
            "Likely missing whitespace before a variable or malformed triple pattern, "
            "e.g. use 'SELECT ?x' instead of 'SELECT?x' and 'orkgc:P29 ?year' instead of 'orkgc:P29?year'."
        )

    return "SPARQL parser could not parse the extracted query."


def parse_error_details(error_message: str | None) -> Dict[str, Any]:
    if not error_message:
        return {
            "parse_error_line": None,
            "parse_error_column": None,
            "parse_error_char": None,
            "parse_error_hint": None,
        }

    line_match = re.search(r"line:(\d+)", error_message)
    col_match = re.search(r"col:(\d+)", error_message)
    char_match = re.search(r"char (\d+)", error_message)

    line = int(line_match.group(1)) if line_match else None
    column = int(col_match.group(1)) if col_match else None
    char = int(char_match.group(1)) if char_match else None

    hint = build_parse_error_hint(error_message)

    return {
        "parse_error_line": line,
        "parse_error_column": column,
        "parse_error_char": char,
        "parse_error_hint": hint,
    }


def looks_truncated(query: str) -> bool:
    if not has_extracted_query(query):
        return False

    if not has_balanced_braces(query):
        return True

    if ends_suspiciously(query):
        return True

    return False


def validate_sparql_syntax(query: str) -> tuple[bool, str | None]:
    if not has_extracted_query(query):
        return False, "Empty query"

    try:
        parseQuery(query)
        return True, None
    except Exception as exc:
        return False, str(exc)


def determine_validation_status(
    extracted_query: str,
    valid_start: bool,
    truncated: bool,
    parse_ok: bool,
) -> str:
    if not has_extracted_query(extracted_query):
        return "empty"

    if not valid_start:
        return "invalid_start"

    if not parse_ok:
        return "syntax_error"

    if truncated:
        return "needs_review"

    return "looks_ok"

def determine_repair_candidate(
    extracted_query: str,
    valid_start: bool,
    truncated: bool,
    parse_ok: bool,
) -> tuple[bool, str]:
    if not has_extracted_query(extracted_query):
        return False, "empty_query"

    if not valid_start:
        return False, "invalid_query_start"

    if parse_ok:
        return False, "query_already_parseable"

    if truncated:
        return True, "non_empty_query_with_valid_start_but_truncated"

    return True, "non_empty_query_with_valid_start_but_syntax_error"





def validate_result_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    extracted_query = entry.get("extracted_query", "")
    if not isinstance(extracted_query, str):
        extracted_query = ""

    valid_start = has_valid_query_start(extracted_query)
    truncated = looks_truncated(extracted_query)
    parse_ok, parse_error = validate_sparql_syntax(extracted_query)

    error_details = parse_error_details(parse_error)

    repair_candidate, repair_candidate_reason = determine_repair_candidate(
        extracted_query=extracted_query,
        valid_start=valid_start,
        truncated=truncated,
        parse_ok=parse_ok,
    )


    return {
        "benchmark_entry_id": entry.get("benchmark_entry_id"),
        "uid": entry.get("uid"),
        "source_id": entry.get("source_id"),
        "source_dataset": entry.get("source_dataset"),
        "family": entry.get("family"),
        "question": entry.get("question"),
        "extracted_query": extracted_query,
        "gold_query": entry.get("gold_query"),
        "has_extracted_query": has_extracted_query(extracted_query),
        "is_empty_query": not has_extracted_query(extracted_query),
        "has_valid_query_start": valid_start,
        "looks_truncated": truncated,
        "parse_ok": parse_ok,
        "parse_error_raw": parse_error,
        "parse_error_line": error_details["parse_error_line"],
        "parse_error_column": error_details["parse_error_column"],
        "parse_error_char": error_details["parse_error_char"],
        "parse_error_hint": error_details["parse_error_hint"],
        "is_repair_candidate": repair_candidate,
        "repair_candidate_reason": repair_candidate_reason,
        "validation_status": determine_validation_status(
            extracted_query=extracted_query,
            valid_start=valid_start,
            truncated=truncated,
            parse_ok=parse_ok,
        ),
    }



def build_validation_output_path(raw_benchmark_path: Path) -> Path:
    return raw_benchmark_path.parent / "validation_report.json"


def validate_benchmark_run(raw_benchmark_path: str) -> Path:
    input_path = Path(raw_benchmark_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Raw benchmark file not found: {input_path}")

    payload = load_json(input_path)

    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        raise ValueError("Expected 'results' to be a list in benchmark_raw.json")

    started_at = datetime.now(timezone.utc)

    validated_results: List[Dict[str, Any]] = [
        validate_result_entry(entry) for entry in raw_results
    ]

    finished_at = datetime.now(timezone.utc)

    output_payload = {
        "run_metadata": {
            "validation_started_at_utc": started_at.isoformat(),
            "validation_finished_at_utc": finished_at.isoformat(),
            "raw_benchmark_path": str(input_path),
            "total_items": len(validated_results),
            "items_with_query": sum(1 for item in validated_results if item["has_extracted_query"]),
            "empty_query_items": sum(1 for item in validated_results if item["is_empty_query"]),
            "valid_query_start_items": sum(1 for item in validated_results if item["has_valid_query_start"]),
            "truncated_items": sum(1 for item in validated_results if item["looks_truncated"]),
            "parse_ok_items": sum(1 for item in validated_results if item["parse_ok"]),
            "syntax_error_items": sum(1 for item in validated_results if not item["parse_ok"]),
            "repair_candidate_items": sum(1 for item in validated_results if item["is_repair_candidate"]),
            "non_repair_candidate_items": sum(1 for item in validated_results if not item["is_repair_candidate"]),
        },
        "results": validated_results,
    }

    output_path = build_validation_output_path(input_path)
    save_json(output_payload, output_path)

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate benchmark_raw.json and write validation_report.json"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to benchmark_raw.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = validate_benchmark_run(args.input)

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print(f"Saved validation report to: {output_path}")


if __name__ == "__main__":
    main()