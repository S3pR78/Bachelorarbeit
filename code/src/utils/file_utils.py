import json
import os
from typing import Any

def load_json(filepath: str) -> Any:
    """Loads a JSON file and returns its contents."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Any, filepath: str) -> None:
    """Saves data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)