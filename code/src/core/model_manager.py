from typing import Dict, Any
from utils.file_utils import load_json

class ModelManager:
    """Manages loading model configurations and resolving user selections."""
    
    def __init__(self, config_path: str):
        self.config = load_json(config_path)
        self.models = self.config.get("models_to_test", [])

    def get_model(self, identifier: str) -> Dict[str, Any]:
        """
        Retrieves a model configuration by ID, name, or index.
        """
        # Try by index
        if identifier.isdigit():
            idx = int(identifier)
            if 0 <= idx < len(self.models):
                return self.models[idx]
        
        # Try by ID or Name
        for model in self.models:
            if model["id"] == identifier or model["name"] == identifier:
                return model
                
        raise ValueError(f"Model with identifier '{identifier}' not found in configuration.")