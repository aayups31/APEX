from __future__ import annotations

import torch
from torch import nn


class GRUWorldModel(nn.Module):
    """Deterministic sequence model that predicts future telemetry states.

    The history encoder compresses the observed past into a hidden state. During rollout, the model
    consumes the planned future actions/context and its own previous predicted state.
    """

    def __init__(
        self,
        input_dim: int,
        state_dim: int,
        hidden_dim: int = 64,
        layers: int = 1,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.state_dim = state_dim
        self.input_dim = input_dim
        self.encoder = nn.GRU(
            input_dim,
            hidden_dim,
            num_layers=layers,
            batch_first=True,
            dropout=dropout if layers > 1 else 0.0,
        )
        self.transition = nn.GRUCell(input_dim, hidden_dim)
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, state_dim),
        )

    def forward(self, history: torch.Tensor, future_inputs: torch.Tensor) -> torch.Tensor:
        _, hidden = self.encoder(history)
        hidden_t = hidden[-1]
        predictions = []
        future_t = future_inputs.clone()
        previous_state = history[:, -1, : self.state_dim]
        for step in range(future_t.shape[1]):
            step_input = future_t[:, step].clone()
            step_input[:, : self.state_dim] = previous_state
            hidden_t = self.transition(step_input, hidden_t)
            previous_state = self.decoder(hidden_t)
            predictions.append(previous_state)
        return torch.stack(predictions, dim=1)
