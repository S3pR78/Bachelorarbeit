#!/usr/bin/env python3
"""
enrich_dataset_with_prompt_metadata.py

Read a canonical dataset (.json or .jsonl), map each entry's "family" to a
prompt profile using prompt_profiles.json, and enrich every entry with prompt
metadata.

Expected input entry example:
{
  "uid": "nlp4-0001",
  "source_dataset": "NLP4",
  "source_id": 1,
  "family": "nlp4re",
  "question": "Which papers report ...?",
  "gold_query": "SELECT ...",
  "contribution_class": "orkgc:C121001"
}

Prompt profile config example:
{
  "version": "1.0",
  "default_query_language": "sparql",
  "default_prefix_profile": "orkg_default",
  "profiles": {
    "nlp4re_v1": {
      "family": "nlp4re",
      "template_id": "R1544125",
      "template_label": "NLP for Requirements Engineering",
      "target_class_id": "C121001",
      "contribution_class": "orkgc:C121001",
      "query_language": "sparql",
      "prefix_profile": "orkg_default",
      "prompt_artifact_path": "code/prompts/generated/nlp4re_v1.json",
      "prompt_generator_source": "EmpiRE-Compass",
      "enabled": true
    }
  },
  "family_to_profile": {
    "nlp4re": "nlp4re_v1"
  }
}

The script adds these fields to each entry:
- prompt_profile
- template_id
- template_label
- target_class_id
- query_language
- prefix_profile
- prompt_artifact_path
- prompt_generator_source

It can also optionally overwrite an existing contribution_class with the one
from the profile.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json_or_jsonl(path: Path) -> List[Dict[str, Any]]:
    """
    Load a dataset from either JSONL or JSON.

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
                    item = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON on line {line_number} in {path}: {exc}"
                    ) from exc

                if not isinstance(item, dict):
                    raise ValueError(
                        f"Line {line_number} in {path} is not a JSON object."
                    )

                entries.append(item)
        return entries

    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"JSON file must contain a list of objects: {path}")

        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Item {index} in {path} is not a JSON object."
                )

        return data

    raise ValueError(f"Unsupported file type: {path}. Use .json or .jsonl")


def load_prompt_profiles(path: Path) -> Dict[str, Any]:
    """
    Load and minimally validate the prompt profile registry.
    """
    if not path.exists():
        raise FileNotFoundError(f"Prompt profile file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    if not isinstance(config, dict):
        raise ValueError("Prompt profile config must be a JSON object.")

    if "profiles" not in config or not isinstance(config["profiles"], dict):
        raise ValueError("Prompt profile config must contain a 'profiles' object.")

    if "family_to_profile" not in config or not isinstance(config["family_to_profile"], dict):
        raise ValueError("Prompt profile config must contain a 'family_to_profile' object.")

    return config


def build_output_path(input_path: Path, output_path: str | None) -> Path:
    """
    Build the output path.

    If an explicit output path is provided, use it.
    Otherwise, generate a sibling file name automatically.
    """
    if output_path:
        return Path(output_path)

    suffix = input_path.suffix.lower()
    if suffix == ".jsonl":
        return input_path.with_name(f"{input_path.stem}_enriched.jsonl")
    if suffix == ".json":
        return input_path.with_name(f"{input_path.stem}_enriched.json")

    return input_path.with_name(f"{input_path.name}_enriched")


def enrich_entry(
    entry: Dict[str, Any],
    config: Dict[str, Any],
    overwrite_contribution_class: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Enrich a single entry with prompt metadata.

    Returns:
    - enriched entry
    - list of warnings
    """
    warnings: List[str] = []
    enriched = dict(entry)

    family = enriched.get("family")
    if not isinstance(family, str) or not family.strip():
        warnings.append("Entry is missing a valid 'family' field.")
        return enriched, warnings

    family_to_profile = config["family_to_profile"]
    profiles = config["profiles"]

    profile_name = family_to_profile.get(family)
    if not isinstance(profile_name, str):
        warnings.append(f"No prompt profile mapping found for family '{family}'.")
        return enriched, warnings

    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        warnings.append(
            f"Mapped prompt profile '{profile_name}' for family '{family}' does not exist."
        )
        return enriched, warnings

    if profile.get("enabled") is False:
        warnings.append(
            f"Prompt profile '{profile_name}' for family '{family}' is disabled."
        )

    # Add prompt-related metadata.
    enriched["prompt_profile"] = profile_name
    enriched["template_id"] = profile.get("template_id")
    enriched["template_label"] = profile.get("template_label")
    enriched["target_class_id"] = profile.get("target_class_id")
    enriched["query_language"] = profile.get(
        "query_language",
        config.get("default_query_language", "sparql"),
    )
    enriched["prefix_profile"] = profile.get(
        "prefix_profile",
        config.get("default_prefix_profile"),
    )
    enriched["prompt_artifact_path"] = profile.get("prompt_artifact_path")
    enriched["prompt_generator_source"] = profile.get("prompt_generator_source")

    # Keep contribution_class consistent with the profile if requested.
    profile_contribution_class = profile.get("contribution_class")
    existing_contribution_class = enriched.get("contribution_class")

    if overwrite_contribution_class:
        enriched["contribution_class"] = profile_contribution_class
    else:
        if not existing_contribution_class and profile_contribution_class:
            enriched["contribution_class"] = profile_contribution_class
        elif (
            isinstance(existing_contribution_class, str)
            and isinstance(profile_contribution_class, str)
            and existing_contribution_class != profile_contribution_class
        ):
            warnings.append(
                "Entry contribution_class differs from prompt profile contribution_class."
            )

    return enriched, warnings


def write_json(path: Path, entries: List[Dict[str, Any]]) -> None:
    """
    Write a list of entries as formatted JSON.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def write_jsonl(path: Path, entries: List[Dict[str, Any]]) -> None:
    """
    Write a list of entries as JSONL.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    """
    Parse arguments, enrich the dataset, and write the output.
    """
    parser = argparse.ArgumentParser(
        description="Enrich a canonical dataset with prompt metadata."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the canonical dataset (.json or .jsonl).",
    )
    parser.add_argument(
        "--prompt-profiles",
        type=str,
        default="code/config/prompt_profiles.json",
        help="Path to prompt_profiles.json.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output path. If omitted, an automatic file name is used.",
    )
    parser.add_argument(
        "--overwrite-contribution-class",
        action="store_true",
        help="Overwrite contribution_class with the value from the prompt profile.",
    )
    args = parser.parse_args()

    try:
        input_path = Path(args.input_file)
        config_path = Path(args.prompt_profiles)
        output_path = build_output_path(input_path, args.output)

        entries = load_json_or_jsonl(input_path)
        config = load_prompt_profiles(config_path)

        enriched_entries: List[Dict[str, Any]] = []
        all_warnings: List[str] = []

        for index, entry in enumerate(entries, start=1):
            enriched, warnings = enrich_entry(
                entry=entry,
                config=config,
                overwrite_contribution_class=args.overwrite_contribution_class,
            )
            enriched_entries.append(enriched)

            for warning in warnings:
                entry_id = enriched.get("uid", f"entry-{index}")
                all_warnings.append(f"{entry_id}: {warning}")

        if output_path.suffix.lower() == ".jsonl":
            write_jsonl(output_path, enriched_entries)
        else:
            write_json(output_path, enriched_entries)

        print("=" * 72)
        print("Dataset Prompt Metadata Enrichment")
        print("=" * 72)
        print(f"Input:           {input_path}")
        print(f"Prompt profiles: {config_path}")
        print(f"Output:          {output_path}")
        print(f"Entries:         {len(enriched_entries)}")
        print(f"Warnings:        {len(all_warnings)}")
        print()

        if all_warnings:
            print("Warnings")
            print("-" * 72)
            for message in all_warnings:
                print(f"[WARN] {message}")
            print()

        print("Done.")
        return 0

    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())