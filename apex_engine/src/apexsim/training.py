from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from apexsim.config import ProjectConfig
from apexsim.models.rssm import RSSMWorldModel


@dataclass
class TrainingResult:
    best_val_loss: float
    epochs_completed: int
    checkpoint_path: Path
    history_path: Path


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _batch_loss(model: nn.Module, batch: dict, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    history = batch["history"].to(device)
    future_inputs = batch["future_inputs"].to(device)
    targets = batch["future_targets"].to(device)
    if isinstance(model, RSSMWorldModel):
        predictions, kl = model(history, future_inputs, future_targets=targets)
        reconstruction = torch.nn.functional.smooth_l1_loss(predictions, targets)
        # KL weight is intentionally modest for a small educational dataset.
        loss = reconstruction + 0.02 * kl
    else:
        predictions = model(history, future_inputs)
        loss = torch.nn.functional.smooth_l1_loss(predictions, targets)
    return loss, predictions


def train_world_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: ProjectConfig,
    run_dir: str | Path,
) -> TrainingResult:
    seed_everything(config.seed)
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    device = torch.device(config.training.device)
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )
    history: list[dict[str, float | int]] = []
    best_val = float("inf")
    stale_epochs = 0
    checkpoint = run_path / "world_model.pt"

    for epoch in range(1, config.training.epochs + 1):
        model.train()
        train_losses = []
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss, _ = _batch_loss(model, batch, device)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.training.grad_clip)
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))

        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch in val_loader:
                loss, _ = _batch_loss(model, batch, device)
                val_losses.append(float(loss.detach().cpu()))
        train_loss = float(np.mean(train_losses))
        val_loss = float(np.mean(val_losses))
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})

        if val_loss < best_val - 1e-6:
            best_val = val_loss
            stale_epochs = 0
            torch.save(model.state_dict(), checkpoint)
        else:
            stale_epochs += 1
            if stale_epochs >= config.training.patience:
                break

    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
    history_path = run_path / "training_history.json"
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return TrainingResult(best_val, len(history), checkpoint, history_path)
