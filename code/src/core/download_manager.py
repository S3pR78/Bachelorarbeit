import os
from huggingface_hub import snapshot_download
from src.utils.path_manager import get_path

def ensure_model_downloaded(model_id: str, base_dir: str = get_path("models.base_dir")) -> str:
    """
    Checks if a model exists locally. If not, downloads it.
    Returns the local path to the model.
    """
    safe_model_name = model_id.replace("/", "--")
    local_path = os.path.join(base_dir, safe_model_name)
    
    if os.path.exists(local_path) and os.listdir(local_path):
        print(f"Model {model_id} already exists locally at {local_path}.")
    else:
        print(f"Downloading model {model_id} to {local_path}...")
        os.makedirs(local_path, exist_ok=True)
        snapshot_download(
            repo_id=model_id,
            local_dir=local_path,
            local_dir_use_symlinks=False
        )
        print("Download complete.")
        
    return local_path