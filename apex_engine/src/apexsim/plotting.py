from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_track_map(frame: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    session = frame[frame.session_id == frame.session_id.iloc[0]]
    ax.plot(session.x_m, session.y_m, linewidth=2)
    ax.scatter(session.x_m.iloc[0], session.y_m.iloc[0], s=50, label="Start")
    ax.set_title("Synthetic track geometry")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal", adjustable="box")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def save_training_curve(history: list[dict], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(history)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(frame.epoch, frame.train_loss, marker="o", label="Train")
    ax.plot(frame.epoch, frame.val_loss, marker="o", label="Validation")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("World-model training")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
