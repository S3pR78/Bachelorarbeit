import argparse
from core.model_manager import ModelManager
from core.download_manager import ensure_model_downloaded
from core.model_loader import load_inference_pipeline
from core.inference_engine import InferenceEngine
from benchmark.benchmark_runner import run_benchmark
from training.trainer import train_model

CONFIG_PATH = "../config/models_config.json"

def parse_args():
    parser = argparse.ArgumentParser(description="LLM Benchmark and Training Framework")
    parser.add_argument("--model", type=str, required=True, 
                        help="Model ID, Name, or Index from config.")
    parser.add_argument("--benchmark", type=str, required=True, 
                        help="Path to the benchmark JSON dataset.")
    parser.add_argument("--mode", type=str, choices=["benchmark", "train"], required=True, 
                        help="Execution mode: 'benchmark' or 'train'.")
    return parser.parse_args()

def main():
    args = parse_args()

    # 1. Load configuration and resolve model
    manager = ModelManager(CONFIG_PATH)
    selected_model_config = manager.get_model(args.model)
    model_id = selected_model_config["id"]
    model_name = selected_model_config["name"]
    model_params = selected_model_config.get("params", {})

    print(f"Selected Model: {model_name} ({model_id})")

    # 2. Route based on mode
    if args.mode == "train":
        train_model(selected_model_config, args.benchmark)
    
    elif args.mode == "benchmark":
        # 3. Download model if necessary
        local_model_path = ensure_model_downloaded(model_id)

        # 4. Load the model for inference
        pipeline = load_inference_pipeline(local_model_path, model_params)
        engine = InferenceEngine(pipeline, model_params)

        # 5. Run Benchmark
        run_benchmark(engine, args.benchmark, model_name)

if __name__ == "__main__":
    main()