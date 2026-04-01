from __future__ import annotations

from training.sft_trainer import train_sft_model


def train_model(model_config: dict, dataset_path: str) -> None:
    """
    Training dispatcher.

    Supported modes:
    - sft
    - distillation (later)
    """
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