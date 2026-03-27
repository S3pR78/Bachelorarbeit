#!/usr/bin/env python3
"""
convert_sparqlbook.py

Convert one .sparqlbook file into a canonical JSON and JSONL dataset.

Rules:
- The dataset metadata is resolved via --dataset and dataset_registry.json.
- The input file path is provided via --input.
- The output is provided as a base path via --output.
  Example:
      --output code/data/canonical/per_source/nlp4re
  This creates:
      code/data/canonical/per_source/nlp4re.json
      code/data/canonical/per_source/nlp4re.jsonl

Question extraction rules:
- If a markdown block contains both "DE:" and "EN:", use only the English text as "question".
- If no DE/EN structure exists, use the plain question text as "question".
- PREFIX lines at the beginning of each SPARQL query are removed.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_repo_root() -> Path:
    """
    Resolve the repository root from this file location.

    Expected file location:
        code/tools/convert_sparqlbook.py
    """
    return Path(__file__).resolve().parents[2]


def load_json_file(path: Path) -> Dict[str, Any]:
    """
    Load a JSON file and return its parsed object.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}, got {type(data).__name__}")

    return data


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


def load_dataset_metadata(paths_config_path: Path, dataset_name: str, repo_root: Path) -> Dict[str, str]:
    """
    Load dataset metadata from the dataset registry referenced by paths.json.
    """
    paths_config = load_json_file(paths_config_path)

    config_section = paths_config.get("config")
    if not isinstance(config_section, dict):
        raise ValueError("paths.json must contain a 'config' object.")

    dataset_registry_raw = config_section.get("dataset_registry")
    if not isinstance(dataset_registry_raw, str) or not dataset_registry_raw.strip():
        raise ValueError("paths.json must define config.dataset_registry as a non-empty string.")

    dataset_registry_path = resolve_path(repo_root, dataset_registry_raw)
    dataset_registry = load_json_file(dataset_registry_path)

    if dataset_name not in dataset_registry:
        available = ", ".join(sorted(dataset_registry.keys()))
        raise ValueError(
            f"Unknown dataset '{dataset_name}'. Available datasets: {available}"
        )

    metadata = dataset_registry[dataset_name]
    if not isinstance(metadata, dict):
        raise ValueError(f"Dataset entry '{dataset_name}' must be a JSON object.")

    required_fields = ["source_dataset", "family", "uid_prefix"]
    for field in required_fields:
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Dataset '{dataset_name}' is missing required field '{field}' in dataset_registry.json."
            )

    return {
        "source_dataset": metadata["source_dataset"],
        "family": metadata["family"],
        "uid_prefix": metadata["uid_prefix"],
    }


def strip_prefixes(query: str) -> str:
    """
    Remove PREFIX lines from the beginning of a SPARQL query.
    """
    lines = query.splitlines()
    kept_lines: List[str] = []
    in_prefix_block = True

    for line in lines:
        stripped = line.strip()

        if in_prefix_block and (stripped == "" or stripped.upper().startswith("PREFIX ")):
            continue

        in_prefix_block = False
        kept_lines.append(line)

    cleaned = "\n".join(kept_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def extract_contribution_class(query: str) -> Optional[str]:
    """
    Extract the first ORKG contribution class from the query, e.g. orkgc:C121001.
    """
    match = re.search(r"\b(orkgc:C\d+)\b", query)
    return match.group(1) if match else None


def extract_source_id(markdown_text: str) -> Optional[int]:
    """
    Extract a numeric source id from the beginning of the question block, e.g. '12)'.
    """
    match = re.match(r"^\s*(\d+)\)", markdown_text.strip())
    return int(match.group(1)) if match else None


def remove_leading_index(text: str) -> str:
    """
    Remove a leading numeric index such as '12)' from the text.
    """
    return re.sub(r"^\s*\d+\)\s*", "", text.strip())


def parse_question_block(markdown_text: str) -> Tuple[str, Optional[int]]:
    """
    Parse the markdown question block.

    Rules:
    - If DE/EN structure exists, use only EN as the final question.
    - Otherwise, use the plain cleaned text as the final question.
    """
    source_id = extract_source_id(markdown_text)
    cleaned_text = remove_leading_index(markdown_text)

    de_match = re.search(
        r"(?im)^\s*DE:\s*(.+?)(?=^\s*EN:|\Z)",
        cleaned_text,
        flags=re.DOTALL,
    )
    en_match = re.search(
        r"(?im)^\s*EN:\s*(.+?)(?=\Z)",
        cleaned_text,
        flags=re.DOTALL,
    )

    if de_match or en_match:
        if en_match:
            question = en_match.group(1).strip()
        else:
            question = cleaned_text.strip()
    else:
        question = cleaned_text.strip()

    question = re.sub(r"\n{2,}", "\n", question).strip()
    return question, source_id


def load_sparqlbook(path: Path) -> List[Dict[str, Any]]:
    """
    Load a .sparqlbook file as JSON.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(data).__name__}")

    return data


def normalize_entry(
    markdown_block: Dict[str, Any],
    sparql_block: Dict[str, Any],
    source_dataset: str,
    family: str,
    uid_prefix: str,
    running_index: int,
) -> Dict[str, Any]:
    """
    Convert a markdown/sparql block pair into one canonical dataset entry.
    """
    markdown_text = markdown_block.get("value", "")
    query_text = sparql_block.get("value", "")

    question, source_id = parse_question_block(markdown_text)
    gold_query = strip_prefixes(query_text)
    contribution_class = extract_contribution_class(query_text)

    entry = {
        "uid": f"{uid_prefix}-{running_index:04d}",
        "source_dataset": source_dataset,
        "source_id": source_id if source_id is not None else running_index,
        "family": family,
        "question": question,
        "gold_query": gold_query,
        "contribution_class": contribution_class,
    }

    return entry


def convert_file(
    path: Path,
    source_dataset: str,
    family: str,
    uid_prefix: str,
    start_index: int = 1,
) -> List[Dict[str, Any]]:
    """
    Convert one .sparqlbook file into canonical entries.

    The script expects the common pattern:
    - markdown block with the question
    - following sparql block with the gold query
    """
    data = load_sparqlbook(path)
    results: List[Dict[str, Any]] = []
    i = 0
    running_index = start_index

    while i < len(data) - 1:
        current_block = data[i]
        next_block = data[i + 1]

        is_markdown = current_block.get("language") == "markdown"
        is_sparql = next_block.get("language") == "sparql"

        if is_markdown and is_sparql:
            entry = normalize_entry(
                markdown_block=current_block,
                sparql_block=next_block,
                source_dataset=source_dataset,
                family=family,
                uid_prefix=uid_prefix,
                running_index=running_index,
            )
            results.append(entry)
            running_index += 1
            i += 2
        else:
            i += 1

    return results


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
    repo_root = get_repo_root()
    default_paths_config = repo_root / "code/config/paths.json"

    parser = argparse.ArgumentParser(
        description="Convert one .sparqlbook file into canonical JSON and JSONL outputs."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Dataset key from dataset_registry.json, e.g. 'nlp4re' or 'empirical_research'.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input .sparqlbook file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Base output path without extension. The script will create both .json and .jsonl.",
    )
    parser.add_argument(
        "--paths-config",
        default=str(default_paths_config),
        help="Path to paths.json. Defaults to code/config/paths.json.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Resolve dataset metadata, convert the input file, and write JSON + JSONL outputs.
    """
    args = parse_args()
    repo_root = get_repo_root()

    paths_config_path = resolve_path(repo_root, args.paths_config)
    input_path = resolve_path(repo_root, args.input)
    output_base = normalize_output_base(resolve_path(repo_root, args.output))

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    metadata = load_dataset_metadata(
        paths_config_path=paths_config_path,
        dataset_name=args.dataset,
        repo_root=repo_root,
    )

    entries = convert_file(
        path=input_path,
        source_dataset=metadata["source_dataset"],
        family=metadata["family"],
        uid_prefix=metadata["uid_prefix"],
        start_index=1,
    )

    output_json, output_jsonl = write_outputs(entries, output_base)

    print(f"Done: wrote {len(entries)} entries.")
    print(f"Dataset: {args.dataset}")
    print(f"Input:   {input_path}")
    print(f"JSON:    {output_json}")
    print(f"JSONL:   {output_jsonl}")


if __name__ == "__main__":
    main()