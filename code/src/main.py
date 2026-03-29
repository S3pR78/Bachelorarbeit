import argparse
import sys

from benchmark.benchmark_runner import run_benchmark
from utils.path_manager import get_path
from core.download_manager import ensure_model_downloaded
from core.inference_engine import InferenceEngine
from core.model_loader import load_inference_pipeline
from core.model_manager import ModelManager
from prompting.prompt_loader import build_prompt_for_entry, get_prompt_metadata_for_family
from training.trainer import train_model

sys.dont_write_bytecode = True


def parse_args():
    parser = argparse.ArgumentParser(description="LLM Benchmark and Training Framework")

    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Model ID, Name, or Index from config."
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["benchmark", "train", "single"],
        required=True,
        help="Execution mode: 'benchmark', 'train', or 'single'."
    )

    parser.add_argument(
        "--benchmark",
        type=str,
        help="Path to the benchmark JSON dataset. Required for benchmark/train."
    )

    parser.add_argument(
        "--family",
        type=str,
        help="Prompt family for single mode, e.g. nlp4re."
    )

    parser.add_argument(
        "--question",
        type=str,
        help="Question for single mode."
    )

    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the final generated prompt in single mode."
    )

    args = parser.parse_args()

    if args.mode in {"benchmark", "train"} and not args.benchmark:
        parser.error("--benchmark is required for mode 'benchmark' and 'train'.")

    if args.mode == "single":
        if not args.family:
            parser.error("--family is required for mode 'single'.")
        if not args.question:
            parser.error("--question is required for mode 'single'.")

    return args


def build_engine(selected_model_config: dict) -> InferenceEngine:
    model_id = selected_model_config["id"]
    model_params = selected_model_config.get("params", {})
    provider = selected_model_config.get("provider", "huggingface")

    if provider == "openai":
        return InferenceEngine(
            pipeline=None,
            params=model_params,
            provider="openai",
            model_id=model_id,
        )

    model_base_dir = get_path("models.base_dir")
    print(f"Model base directory: {model_base_dir}")

    local_model_path = ensure_model_downloaded(model_id, model_base_dir)
    pipeline = load_inference_pipeline(local_model_path, model_params)

    return InferenceEngine(
        pipeline=pipeline,
        params=model_params,
        provider="huggingface",
        model_id=model_id,
    )


def run_single_mode(engine: InferenceEngine, family: str, question: str, show_prompt: bool) -> None:
    entry = {
        "family": family,
        "question": question,
    }

    prompt_meta = get_prompt_metadata_for_family(family)
    final_prompt = build_prompt_for_entry(entry)

    print("\n" + "=" * 80)
    print("SINGLE MODE")
    print("=" * 80)
    print(f"Family        : {prompt_meta['family']}")
    print(f"Prompt profile: {prompt_meta['prompt_profile']}")
    print(f"Prompt path   : {prompt_meta['prompt_path']}")
    print(f"Question      : {question}")

    if show_prompt:
        print("\n" + "=" * 80)
        print("FINAL PROMPT")
        print("=" * 80)
        print(final_prompt)

    print("\n" + "=" * 80)
    print("MODEL RESPONSE")
    print("=" * 80)
    response = engine.generate_response(final_prompt)
    print(response)
    print("=" * 80)


def main():
    args = parse_args()

    models_config_path = get_path("config.models_config")
    manager = ModelManager(models_config_path)
    selected_model_config = manager.get_model(args.model)

    model_id = selected_model_config["id"]
    model_name = selected_model_config["name"]

    print(f"Selected Model: {model_name} ({model_id})")

    if args.mode == "train":
        train_model(selected_model_config, args.benchmark)
        return

    engine = build_engine(selected_model_config)

    if args.mode == "benchmark":
        run_benchmark(engine, args.benchmark, model_name)
        return

    if args.mode == "single":
        run_single_mode(
            engine=engine,
            family=args.family,
            question=args.question,
            show_prompt=args.show_prompt,
        )
        return


if __name__ == "__main__":
    main()