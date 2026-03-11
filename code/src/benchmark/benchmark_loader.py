from typing import List, Dict, Any
from utils.file_utils import load_json

def load_benchmark(filepath: str) -> List[Dict[str, Any]]:
    """Loads the benchmark dataset."""
    print(f"Loading benchmark dataset from {filepath}...")
    data = load_json(filepath)
    print(f"Loaded {len(data)} questions.")
    return data