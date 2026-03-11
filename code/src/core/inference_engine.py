from typing import Any

class InferenceEngine:
    """Handles generating responses using the loaded model pipeline."""
    
    def __init__(self, pipeline: Any, params: dict):
        self.pipeline = pipeline
        self.params = params

    def generate_response(self, prompt: str) -> str:
        """Generates text based on the provided prompt and model parameters."""
        
        # Prepare params, defaulting to empty dict if None
        gen_kwargs = self.params.copy() if self.params else {}
        
        # Avoid pipeline warnings about passing max_length and max_new_tokens together
        if "max_new_tokens" not in gen_kwargs:
            gen_kwargs["max_new_tokens"] = 512
            
        outputs = self.pipeline(prompt, **gen_kwargs, return_full_text=False)
        
        # Extract generated text safely
        generated_text = outputs[0]["generated_text"]
        
        # Strip the prompt from the response if the pipeline included it
        if generated_text.startswith(prompt):
            generated_text = generated_text[len(prompt):].strip()
            
        return generated_text
    
     # we have to test the results for this part
    def _clean_sparql(self, text: str) -> str:
        return