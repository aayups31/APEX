from __future__ import annotations

import torch
from torch import nn
from torch.distributions import Normal, kl_divergence


class RSSMWorldModel(nn.Module):
    """Compact Dreamer-style recurrent state-space model for telemetry.

    h_t is deterministic memory. z_t is a stochastic latent state. The posterior sees the observed
    state during training; the prior is used for imagination when future observations are unavailable.
    """

    def __init__(self, input_dim: int, state_dim: int, hidden_dim: int = 64, latent_dim: int = 12) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.action_context_dim = input_dim - state_dim
        self.gru = nn.GRUCell(latent_dim + self.action_context_dim, hidden_dim)
        self.prior = nn.Linear(hidden_dim, 2 * latent_dim)
        self.posterior = nn.Linear(hidden_dim + state_dim, 2 * latent_dim)
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim + latent_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, state_dim),
        )

    @staticmethod
    def _distribution(parameters: torch.Tensor) -> Normal:
        mean, raw_std = parameters.chunk(2, dim=-1)
        std = torch.nn.functional.softplus(raw_std) + 0.1
        return Normal(mean, std)

    def forward(
        self,
        history: torch.Tensor,
        future_inputs: torch.Tensor,
        future_targets: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch = history.shape[0]
        h = history.new_zeros((batch, self.hidden_dim))
        z = history.new_zeros((batch, self.latent_dim))
        # Observe history to initialize belief state.
        for step in range(history.shape[1]):
            state = history[:, step, : self.state_dim]
            action_context = history[:, step, self.state_dim :]
            h = self.gru(torch.cat([z, action_context], dim=-1), h)
            posterior = self._distribution(self.posterior(torch.cat([h, state], dim=-1)))
            z = posterior.rsample()

        outputs = []
        kl_terms = []
        previous_state = history[:, -1, : self.state_dim]
        for step in range(future_inputs.shape[1]):
            action_context = future_inputs[:, step, self.state_dim :]
            h = self.gru(torch.cat([z, action_context], dim=-1), h)
            prior = self._distribution(self.prior(h))
            if future_targets is not None:
                posterior = self._distribution(
                    self.posterior(torch.cat([h, future_targets[:, step]], dim=-1))
                )
                z = posterior.rsample()
                kl_terms.append(kl_divergence(posterior, prior).sum(dim=-1))
            else:
                z = prior.rsample()
            previous_state = self.decoder(torch.cat([h, z], dim=-1))
            outputs.append(previous_state)
        prediction = torch.stack(outputs, dim=1)
        kl = torch.stack(kl_terms, dim=1).mean() if kl_terms else prediction.new_tensor(0.0)
        return prediction, kl
