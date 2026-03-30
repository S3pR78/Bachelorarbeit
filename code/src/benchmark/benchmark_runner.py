from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from benchmark.benchmark_loader import load_benchmark
from core.inference_engine import InferenceEngine
from prompting.prompt_loader import build_prompt_for_entry
from utils.path_manager import get_path
from utils.timer import measure_time


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._-") or "value"


def _format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


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


def _build_run_directory(benchmark_path: str, model_name: str) -> Path:
    benchmark_file = Path(benchmark_path).resolve()
    runs_base_dir = Path(get_path("benchmark.runs_dir")).resolve()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model_name = _safe_name(model_name)
    safe_benchmark_name = _safe_name(benchmark_file.stem)

    run_dir_name = f"{timestamp}__{safe_model_name}__{safe_benchmark_name}"
    run_dir = runs_base_dir / run_dir_name
    run_dir.mkdir(parents=True, exist_ok=True)

    return run_dir


def _save_json(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_benchmark(
    engine: InferenceEngine,
    benchmark_path: str,
    model_name: str,
) -> None:
    started_at = datetime.now(timezone.utc)
    run_dir = _build_run_directory(benchmark_path, model_name)

    with measure_time() as get_total_runtime:
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
        print(f"Run directory   : {run_dir}")
        print(f"Total questions : {total_items}")
        print(f"Started at UTC  : {started_at.isoformat()}")
        print("=" * 80)

        for index, entry in enumerate(dataset, start=1):
            entry_id = _get_entry_id(entry, index)

            try:
                family = entry.get("family")
                question = entry.get("question")

                if not isinstance(family, str) or not family.strip():
                    raise ValueError(f"Entry {entry_id} has no valid 'family'.")

                if not isinstance(question, str) or not question.strip():
                    raise ValueError(f"Entry {entry_id} has no valid 'question'.")

                print(f"[{index}/{total_items}] START id={entry_id} family={family}")

                final_prompt = build_prompt_for_entry(entry)

                with measure_time() as get_item_runtime:
                    raw_model_output = engine.generate_raw_response(final_prompt)
                    extracted_query = engine.extract_sparql_query(raw_model_output)

                elapsed_time = get_item_runtime()

                result = {
                    "status": "ok",
                    "benchmark_entry_id": entry_id,
                    "uid": entry.get("uid"),
                    "source_id": entry.get("source_id"),
                    "source_dataset": entry.get("source_dataset"),
                    "family": family,
                    "question": question,
                    "gold_query": _get_gold_query(entry),
                    "raw_model_output": raw_model_output,
                    "extracted_query": extracted_query,
                    "response_time_seconds": round(elapsed_time, 4),
                }

                results.append(result)

                print(
                    f"[{index}/{total_items}] DONE  "
                    f"id={entry_id} time={_format_duration(elapsed_time)}"
                )

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

                print(f"[{index}/{total_items}] FAIL  id={entry_id} error={exc}")

    total_runtime_seconds = get_total_runtime()
    finished_at = datetime.now(timezone.utc)

    raw_output_path = run_dir / "benchmark_raw.json"

    payload = {
        "run_metadata": {
            "run_dir": str(run_dir),
            "started_at_utc": started_at.isoformat(),
            "finished_at_utc": finished_at.isoformat(),
            "model_name": model_name,
            "benchmark_path": str(Path(benchmark_path).resolve()),
            "total_items": total_items,
            "successful_items": sum(1 for r in results if r["status"] == "ok"),
            "failed_items": sum(1 for r in results if r["status"] == "error"),
            "total_runtime_seconds": round(total_runtime_seconds, 4),
        },
        "results": results,
    }

    _save_json(payload, raw_output_path)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print(f"Successful items : {payload['run_metadata']['successful_items']}")
    print(f"Failed items     : {payload['run_metadata']['failed_items']}")
    print(f"Total runtime    : {_format_duration(total_runtime_seconds)}")
    print(f"Saved raw output : {raw_output_path}")