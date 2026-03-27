#!/usr/bin/env python3
"""
convert_sparqlbook.py

Convert .sparqlbook files into a canonical JSON and JSONL dataset.

Question extraction rules:
- If a markdown block contains both "DE:" and "EN:", use only the English text as "question".
- If no DE/EN structure exists, use the plain question text as "question".
- PREFIX lines at the beginning of each SPARQL query are removed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


INPUT_FILES = [
    {
        "path": "data/raw/Emperical_Research/question.sparqlbook",
        "source_dataset": "Emperical_Research",
        "family": "empirical_research",
        "uid_prefix": "empirical-research",
    },
    {
        "path": "data/raw/NLP4RE/question.sparqlbook",
        "source_dataset": "NLP4RE",
        "family": "nlp4re",
        "uid_prefix": "nlp4re",
    },
]

OUTPUT_JSON = "data/benchmark_from_sparqlbook.json"
OUTPUT_JSONL = "data/benchmark_from_sparqlbook.jsonl"


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
    start_index: int,
) -> Tuple[List[Dict[str, Any]], int]:
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

    return results, running_index


def main() -> None:
    """
    Convert all configured .sparqlbook files and write JSON + JSONL outputs.
    """
    all_entries: List[Dict[str, Any]] = []
    next_index = 1

    for cfg in INPUT_FILES:
        path = Path(cfg["path"])

        if not path.exists():
            print(f"Skipped missing file: {path}")
            continue

        entries, next_index = convert_file(
            path=path,
            source_dataset=cfg["source_dataset"],
            family=cfg["family"],
            uid_prefix=cfg["uid_prefix"],
            start_index=next_index,
        )
        all_entries.extend(entries)

    output_json = Path(OUTPUT_JSON)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    with output_json.open("w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    output_jsonl = Path(OUTPUT_JSONL)
    with output_jsonl.open("w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Done: wrote {len(all_entries)} entries.")
    print(f"JSON:  {output_json}")
    print(f"JSONL: {output_jsonl}")


if __name__ == "__main__":
    main()