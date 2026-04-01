from __future__ import annotations

from training.sft_trainer import train_sft_model


def train_model(model_config: dict, dataset_path: str) -> None:
    """
    Training dispatcher.

    Supported:
    - local Hugging Face models for SFT

    Not supported here:
    - OpenAI/API-based fine-tuning
    - distillation (later)
    """
    provider = model_config.get("provider", "huggingface").lower()
    model_id = model_config.get("id", "<unknown>")

    if provider == "openai":
        raise ValueError(
            f"Model '{model_id}' uses provider='openai'. "
            "API-based OpenAI models cannot be trained with this local trainer. "
            "Use the OpenAI fine-tuning workflow separately."
        )

    if provider != "huggingface":
        raise ValueError(
            f"Unsupported provider '{provider}' for local training. "
            "Currently only provider='huggingface' is supported."
        )

    training_config = model_config.get("training", {})
    training_mode = training_config.get("mode", "sft").lower()

    if training_mode == "sft":
        train_sft_model(model_config=model_config, dataset_path=dataset_path)
        return

    if training_mode == "distillation":
        raise NotImplementedError(
            "Distillation training is not implemented yet."
        )

    raise ValueError(
        f"Unsupported training mode '{training_mode}'. "
        f"Supported modes: sft, distillation"
    )