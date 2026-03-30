import os
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI
import re

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

    def generate_raw_response(self, prompt: str) -> str:
        """Generate raw model output without SPARQL cleaning."""
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

        return generated_text.strip()

    def extract_sparql_query(self, text: str) -> str:
        """Extract only the SPARQL query from raw model output. Return empty string if none is found."""
        text = text.strip()
        text = self._strip_thinking_and_labels(text)
        text = self._extract_code_block(text)
        text = self._extract_query_region(text)
        text = self._remove_comments(text)
        text = self._remove_prefixes(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def generate_response(self, prompt: str) -> str:
        """
        Backward-compatible helper:
        generate raw output and return extracted SPARQL query.
        """
        raw_text = self.generate_raw_response(prompt)
        return self.extract_sparql_query(raw_text)

    def _extract_code_block(self, text: str) -> str:
        """Extract the first fenced code block, preferably ```sparql ... ```."""
        sparql_match = re.search(r"```sparql\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        if sparql_match:
            return sparql_match.group(1).strip()

        generic_match = re.search(r"```\s*(.*?)```", text, flags=re.DOTALL)
        if generic_match:
            return generic_match.group(1).strip()

        return text.strip()

    def _strip_thinking_and_labels(self, text: str) -> str:
        """Remove reasoning blocks and common wrapper labels."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"^##\s*Output\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r"^SPARQL\s*Query\s*:?\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r"^Output\s*:?\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
        return text.strip()

    def _extract_query_region(self, text: str) -> str:
        """
        Keep only the SPARQL query region.
        Starts at the first PREFIX or SPARQL query keyword.
        If no such start is found, return an empty string.
        """
        lines = text.splitlines()

        start_idx = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            upper = stripped.upper()

            if (
                upper.startswith("PREFIX ")
                or upper.startswith("SELECT")
                or upper.startswith("ASK")
                or upper.startswith("CONSTRUCT")
                or upper.startswith("DESCRIBE")
            ):
                start_idx = i
                break

        if start_idx is None:
            return ""

        candidate = "\n".join(lines[start_idx:]).strip()
        candidate = candidate.split("```")[0].strip()
        return candidate

    def _remove_comments(self, text: str) -> str:
        """
        Remove SPARQL comments.
        SPARQL comments start with # and go until end of line.
        """
        cleaned_lines = []

        for line in text.splitlines():
            stripped = line.strip()

            # whole-line comments
            if stripped.startswith("#"):
                continue

            # inline comments
            if "#" in line:
                line = re.sub(r"\s+#.*$", "", line)

            cleaned_lines.append(line.rstrip())

        return "\n".join(cleaned_lines).strip()

    def _remove_prefixes(self, text: str) -> str:
        """
        Remove PREFIX declarations from the query.
        """
        lines = []

        for line in text.splitlines():
            if re.match(r"^\s*PREFIX\s+\w+:\s*<[^>]+>\s*$", line, flags=re.IGNORECASE):
                continue
            lines.append(line)

        return "\n".join(lines).strip()