import os
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from the .env file
load_dotenv()

class InferenceEngine:
    """Handles generating responses using either a local HF pipeline or the OpenAI API."""
    
    def __init__(self, pipeline: Any, params: dict, provider: str = "huggingface", model_id: str = ""):
        self.provider = provider
        self.model_id = model_id
        self.pipeline = pipeline
        self.params = params if params else {}

        # If it's an API model, initialize the OpenAI client
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("ERROR: OPENAI_API_KEY was not found in the .env file!")
            self.client = OpenAI(api_key=api_key)

    def generate_response(self, prompt: str) -> str:
        """Generates text based on the provided prompt and model parameters."""

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a SPARQL expert. Return ONLY valid SPARQL queries, no explanations."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.params.get("temperature", 0.0),
                max_tokens=self.params.get("max_new_tokens", 512)
            )
            generated_text = response.choices[0].message.content or ""

        else:
            gen_kwargs = self.params.copy()

            if "max_new_tokens" not in gen_kwargs:
                gen_kwargs["max_new_tokens"] = 512

            if gen_kwargs.get("do_sample") is False:
                gen_kwargs.pop("temperature", None)
                gen_kwargs.pop("top_p", None)
                gen_kwargs.pop("top_k", None)

            outputs = self.pipeline(
                prompt,
                **gen_kwargs,
                return_full_text=False
            )

            generated_text = outputs[0].get("generated_text", "")

            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):].strip()

        generated_text = generated_text.strip()

        return generated_text
    
    
    # we have to test the results for this part
    def _clean_sparql(self, text: str) -> str:
        return