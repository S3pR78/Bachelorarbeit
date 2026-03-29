from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from core.download_manager import ensure_model_downloaded
from core.model_loader import load_inference_pipeline
from core.inference_engine import InferenceEngine
from prompting.prompt_loader import build_prompt_for_entry, get_prompt_metadata_for_family
from utils.file_utils import load_json

DEFAULT_MODEL_ID = "Qwen/Qwen3-0.6B"
DEFAULT_MODEL_PARAMS = {
    "max_new_tokens": 400,
    "temperature": 0.0,
    "do_sample": False,
}

SYSTEM_INSTRUCTION = """You are a SPARQL expert for ORKG templates.
Return ONLY one valid SPARQL query.
Do not explain anything.
Do not use markdown code fences.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a single prompt-generation smoke test."
    )

    parser.add_argument(
        "--model-id",
        type=str,
        default=DEFAULT_MODEL_ID,
        help="HF model id, e.g. Qwen/Qwen3-0.6B",
    )

    parser.add_argument(
        "--entry-file",
        type=str,
        help="Path to canonical dataset JSON (list or dict with entries/data).",
    )
    parser.add_argument(
        "--entry-index",
        type=int,
        default=0,
        help="Index of the entry inside --entry-file.",
    )

    parser.add_argument(
        "--family",
        type=str,
        help="Family for direct question mode, e.g. nlp4re or empirical_research.",
    )
    parser.add_argument(
        "--question",
        type=str,
        help="Question for direct question mode.",
    )

    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the final prompt before generation.",
    )

    return parser.parse_args()


def normalize_entries(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("entries"), list):
            return data["entries"]
        if isinstance(data.get("data"), list):
            return data["data"]

    raise ValueError(
        "Dataset must be either a list or a dict containing 'entries' or 'data'."
    )


def load_entry_from_file(entry_file: str, entry_index: int) -> Dict[str, Any]:
    raw = load_json(entry_file)
    entries = normalize_entries(raw)

    if not (0 <= entry_index < len(entries)):
        raise IndexError(
            f"entry-index {entry_index} is out of range. Dataset has {len(entries)} entries."
        )

    entry = entries[entry_index]
    if not isinstance(entry, dict):
        raise ValueError(f"Entry at index {entry_index} is not a JSON object.")

    return entry


def build_entry_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    if args.entry_file:
        return load_entry_from_file(args.entry_file, args.entry_index)

    if not args.family or not args.question:
        raise ValueError(
            "Use either --entry-file ... or both --family and --question."
        )

    return {
        "family": args.family,
        "question": args.question,
    }


def maybe_apply_chat_template(pipe: Any, user_prompt: str) -> str:
    tokenizer = getattr(pipe, "tokenizer", None)

    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION.strip()},
            {"role": "user", "content": user_prompt},
        ]
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    return SYSTEM_INSTRUCTION.strip() + "\n\n" + user_prompt


def main() -> None:
    args = parse_args()

    entry = build_entry_from_args(args)

    family = entry.get("family")
    question = entry.get("question")

    if not isinstance(family, str) or not family.strip():
        raise ValueError("Entry has no valid 'family'.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Entry has no valid 'question'.")

    print(f"[INFO] family   : {family}")
    print(f"[INFO] question : {question}")

    prompt_meta = get_prompt_metadata_for_family(family)
    print(f"[INFO] profile  : {prompt_meta.get('prompt_profile')}")
    print(f"[INFO] prompt   : {prompt_meta.get('prompt_path')}")

    final_user_prompt = build_prompt_for_entry(entry)

    if args.show_prompt:
        print("\n" + "=" * 80)
        print("FINAL USER PROMPT")
        print("=" * 80)
        print(final_user_prompt)
        print("=" * 80 + "\n")

    print(f"[INFO] Download/load model: {args.model_id}")
    local_model_path = ensure_model_downloaded(args.model_id)
    pipe = load_inference_pipeline(local_model_path, DEFAULT_MODEL_PARAMS)
    engine = InferenceEngine(pipe, DEFAULT_MODEL_PARAMS, provider="huggingface", model_id=args.model_id)

    generation_prompt = maybe_apply_chat_template(pipe, final_user_prompt)

    print("[INFO] Generating...\n")
    raw_response = engine.generate_response(generation_prompt)

    print("=" * 80)
    print("RAW MODEL RESPONSE")
    print("=" * 80)
    print(raw_response)
    print("=" * 80)


if __name__ == "__main__":
    main()