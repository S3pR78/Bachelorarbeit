from transformers import pipeline

def load_inference_pipeline(local_path: str, params: dict):
    """
    Loads the model and tokenizer from the local path into a text-generation pipeline.
    """
    print(f"Loading model from {local_path}...")
    
    pipe = pipeline(
        "text-generation",
        model=local_path,
        tokenizer=local_path,
        device_map="auto" 
    )
    print("Model loaded successfully.")
    return pipe