from benchmark.benchmark_loader import load_benchmark
from logging_system.logger import BenchmarkLogger
from core.inference_engine import InferenceEngine
from utils.timer import measure_time

def run_benchmark(engine: InferenceEngine, benchmark_path: str, model_name: str) -> None:
    """Executes the benchmark over the provided dataset."""
    dataset = load_benchmark(benchmark_path)
    logger = BenchmarkLogger(model_name=model_name)

    with open("prompt_template.txt", "r", encoding="utf-8") as f:
        prompt = f.read()
    
    print(f"Starting benchmark for model: {model_name}...")
    
    for item in dataset:
        q_id = item.get("id")
        question = item.get("question")
        gold_query = item.get("gold_query")
        
        print(f"Processing QID: {q_id}")
        
        with measure_time() as get_time:
            response = engine.generate_response(prompt + question)
            
        elapsed_time = get_time()
        
        logger.log_entry(
            question_id = q_id,
            question=question,
            model_response=response,
            gold_query=gold_query,
            response_time=elapsed_time
        )
        
    logger.save_log()
    print("Benchmark complete.")