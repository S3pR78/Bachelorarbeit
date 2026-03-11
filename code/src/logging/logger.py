import os
from datetime import datetime
from utils.file_utils import save_json

class BenchmarkLogger:
    """Handles logging benchmark results to a JSON file."""
    
    def __init__(self, model_name: str, log_dir: str = "logs"):
        self.model_name = model_name.replace("/", "_")
        self.log_dir = log_dir
        self.entries = []
        os.makedirs(self.log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_filepath = os.path.join(self.log_dir, f"{self.model_name}_{timestamp}.json")

    def log_entry(self, question_id: int, question: str, model_response: str, gold_standard: str, response_time: float) -> None:
        """Adds a single benchmark entry to the log memory."""
        self.entries.append({
            "question_id": question_id,
            "question": question,
            "model_response": model_response,
            "gold_standard": gold_standard,
            "response_time_seconds": round(response_time, 4)
        })

    def save_log(self) -> None:
        """Writes the accumulated log entries to the JSON file."""
        save_json(self.entries, self.log_filepath)
        print(f"Log saved successfully to {self.log_filepath}")