from __future__ import annotations

import torch
from torch import nn


class SelectiveSSMCell(nn.Module):
    """Small educational selective state-space cell.

    This is intentionally not a full Mamba kernel. It demonstrates the central idea: a persistent
    state with input-dependent write/forget gates and stable diagonal decay.
    """

    def __init__(self, input_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.logit_decay = nn.Parameter(torch.zeros(hidden_dim))
        self.input_projection = nn.Linear(input_dim, hidden_dim)
        self.gate_projection = nn.Linear(input_dim, hidden_dim)

    def forward(self, x: torch.Tensor, state: torch.Tensor) -> torch.Tensor:
        decay = torch.sigmoid(self.logit_decay).unsqueeze(0)
        candidate = torch.tanh(self.input_projection(x))
        gate = torch.sigmoid(self.gate_projection(x))
        return decay * state + (1.0 - decay) * gate * candidate


class SSMWorldModel(nn.Module):
    def __init__(self, input_dim: int, state_dim: int, hidden_dim: int = 64, layers: int = 2) -> None:
        super().__init__()
        self.state_dim = state_dim
        self.cells = nn.ModuleList(
            [SelectiveSSMCell(input_dim if i == 0 else hidden_dim, hidden_dim) for i in range(layers)]
        )
        self.decoder = nn.Sequential(nn.LayerNorm(hidden_dim), nn.Linear(hidden_dim, state_dim))

    def _step(self, x: torch.Tensor, states: list[torch.Tensor]) -> tuple[torch.Tensor, list[torch.Tensor]]:
        updated: list[torch.Tensor] = []
        value = x
        for cell, state in zip(self.cells, states):
            state = cell(value, state)
            updated.append(state)
            value = state
        return self.decoder(value), updated

    def forward(self, history: torch.Tensor, future_inputs: torch.Tensor) -> torch.Tensor:
        batch = history.shape[0]
        hidden_dim = self.cells[0].logit_decay.shape[0]
        states = [history.new_zeros((batch, hidden_dim)) for _ in self.cells]
        for step in range(history.shape[1]):
            _, states = self._step(history[:, step], states)
        previous_state = history[:, -1, : self.state_dim]
        outputs = []
        for step in range(future_inputs.shape[1]):
            x = future_inputs[:, step].clone()
            x[:, : self.state_dim] = previous_state
            previous_state, states = self._step(x, states)
            outputs.append(previous_state)
        return torch.stack(outputs, dim=1)
