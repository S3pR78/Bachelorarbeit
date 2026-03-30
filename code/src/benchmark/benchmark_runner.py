from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from benchmark.benchmark_loader import load_benchmark
from core.inference_engine import InferenceEngine
from prompting.prompt_loader import build_prompt_for_entry
from utils.timer import measure_time


def _safe_model_name(model_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", model_name).strip("._-") or "model"


def _get_entry_id(entry: Dict[str, Any], index: int) -> str:
    for key in ("uid", "id", "source_id"):
        value = entry.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return f"item-{index}"


def _get_gold_query(entry: Dict[str, Any]) -> str:
    for key in ("gold_query", "sparql", "query"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _build_output_path(benchmark_path: str, model_name: str) -> Path:
    benchmark_file = Path(benchmark_path).resolve()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = _safe_model_name(model_name)
    filename = f"{benchmark_file.stem}__{safe_model}__results_{timestamp}.json"
    return benchmark_file.parent / filename


def _save_json(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_benchmark(
    engine: InferenceEngine,
    benchmark_path: str,
    model_name: str,
) -> None:
    dataset: List[Dict[str, Any]] = load_benchmark(benchmark_path)

    if not isinstance(dataset, list):
        raise ValueError("Benchmark dataset must be a JSON list.")

    total_items = len(dataset)
    results: List[Dict[str, Any]] = []

    print("\n" + "=" * 80)
    print("BENCHMARK MODE")
    print("=" * 80)
    print(f"Model           : {model_name}")
    print(f"Benchmark file  : {Path(benchmark_path).resolve()}")
    print(f"Total questions : {total_items}")
    print("=" * 80)

    for index, entry in enumerate(dataset, start=1):
        entry_id = _get_entry_id(entry, index)

        print(f"\n[{index}/{total_items}] Question {index} started")
        print(f"Benchmark Entry ID : {entry_id}")

        try:
            family = entry.get("family")
            question = entry.get("question")

            if not isinstance(family, str) or not family.strip():
                raise ValueError(f"Entry {entry_id} has no valid 'family'.")

            if not isinstance(question, str) or not question.strip():
                raise ValueError(f"Entry {entry_id} has no valid 'question'.")

            final_prompt = build_prompt_for_entry(entry)

            with measure_time() as get_time:
                model_response = engine.generate_response(final_prompt)

            elapsed_time = get_time()

            result = {
                "status": "ok",
                "benchmark_entry_id": entry_id,
                "uid": entry.get("uid"),
                "source_id": entry.get("source_id"),
                "source_dataset": entry.get("source_dataset"),
                "family": family,
                "question": question,
                "gold_query": _get_gold_query(entry),
                "model_response": model_response,
                "response_time_seconds": round(elapsed_time, 4),
            }

            results.append(result)

            print(f"[{index}/{total_items}] Question {index} completed")
            print(f"Family   : {family}")
            print(f"Time     : {elapsed_time:.4f}s")
            print("Response :")
            print(model_response)

        except Exception as exc:
            error_result = {
                "status": "error",
                "benchmark_entry_id": entry_id,
                "uid": entry.get("uid"),
                "source_id": entry.get("source_id"),
                "source_dataset": entry.get("source_dataset"),
                "family": entry.get("family"),
                "question": entry.get("question"),
                "gold_query": _get_gold_query(entry),
                "error": str(exc),
            }

            results.append(error_result)

            print(f"[{index}/{total_items}] Question {index} failed")
            print(f"Error: {exc}")

    output_path = _build_output_path(benchmark_path, model_name)

    payload = {
        "run_metadata": {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "benchmark_path": str(Path(benchmark_path).resolve()),
            "total_items": total_items,
            "successful_items": sum(1 for r in results if r["status"] == "ok"),
            "failed_items": sum(1 for r in results if r["status"] == "error"),
        },
        "results": results,
    }

    _save_json(payload, output_path)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print(f"Saved results to: {output_path}")