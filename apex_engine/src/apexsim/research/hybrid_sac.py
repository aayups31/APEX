"""R017 hybrid SAC adaptation: Gaussian energy, exact categorical pit expectation.

CPU, fixed temperature and finite-horizon gamma=1. No oracle supervision.
All random draws use local generators; initialization restores Torch global RNG.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from math import isfinite, log, pi
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


@dataclass(frozen=True)
class SACSettings:
    seed: int = 11
    steps: int = 12000
    hidden: int = 64
    batch_size: int = 128
    warmup: int = 512
    replay_capacity: int = 8192
    learning_rate: float = .0003
    alpha: float = .01
    target_mix: float = .005
    max_gradient_norm: float = 10.
    gamma: float = 1.

    def __post_init__(self) -> None:
        counts = (self.seed, self.steps, self.hidden, self.batch_size, self.warmup, self.replay_capacity)
        if any(type(v) is not int for v in counts) or self.seed < 0 or min(counts[1:]) <= 0:
            raise ValueError("SAC seed/budgets require integers and positive counts")
        if not self.batch_size <= self.warmup < self.steps or self.replay_capacity < self.batch_size or self.steps > 100000:
            raise ValueError("SAC requires batch<=warmup<steps, adequate replay and at most 100000 steps")
        if any(not isfinite(v) or v <= 0 for v in (self.learning_rate, self.alpha, self.target_mix, self.max_gradient_norm)):
            raise ValueError("SAC numerical settings must be finite and positive")
        if self.target_mix > 1 or self.gamma != 1:
            raise ValueError("Finite-horizon strategy SAC requires gamma=1 and target_mix<=1")


def _mlp(inputs: int, hidden: int, outputs: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(inputs, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, outputs))


def tanh_log_density(raw: torch.Tensor, noise: torch.Tensor, log_std: torch.Tensor) -> torch.Tensor:
    """Stable Gaussian density plus exact tanh change-of-variables correction."""
    gaussian = -.5 * (noise.square() + 2 * log_std + log(2 * pi))
    correction = 2 * (log(2) - raw - F.softplus(-2 * raw))
    return (gaussian - correction).sum(-1)


def soft_value(q: torch.Tensor, probabilities: torch.Tensor, log_probabilities: torch.Tensor,
               energy_log_density: torch.Tensor, alpha: float) -> torch.Tensor:
    """Exact discrete expectation with continuous/discrete entropy; q has shape B,4."""
    return (probabilities * (q - alpha * log_probabilities)).sum(-1) - alpha * energy_log_density


class HybridActor(nn.Module):
    def __init__(self, hidden: int) -> None:
        super().__init__()
        self.network = _mlp(10, hidden, 8)  # mean[2], log_std[2], categorical logits[4]

    def sample(self, observation: torch.Tensor, mask: torch.Tensor, generator: torch.Generator,
               deterministic: bool = False) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        output = self.network(observation)
        mean, log_std, logits = output[:, :2], output[:, 2:4].clamp(-5, 2), output[:, 4:]
        noise = torch.zeros_like(mean) if deterministic else torch.randn(mean.shape, generator=generator)
        raw = mean + log_std.exp() * noise
        log_probs = F.log_softmax(logits.masked_fill(~mask, -1e9), dim=-1)
        return raw.tanh(), tanh_log_density(raw, noise, log_std), log_probs.exp(), log_probs


class TwinCritics(nn.Module):
    def __init__(self, hidden: int) -> None:
        super().__init__()
        self.q1, self.q2 = _mlp(16, hidden, 1), _mlp(16, hidden, 1)

    def forward(self, observation: torch.Tensor, energy: torch.Tensor, pit: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        features = torch.cat((observation, energy, F.one_hot(pit, 4).to(observation.dtype)), dim=-1)
        return self.q1(features).squeeze(-1), self.q2(features).squeeze(-1)

    def all_pits(self, observation: torch.Tensor, energy: torch.Tensor) -> torch.Tensor:
        batch = len(observation)
        q1, q2 = self(observation.repeat_interleave(4, dim=0), energy.repeat_interleave(4, dim=0),
                      torch.arange(4).repeat(batch))
        return torch.minimum(q1, q2).reshape(batch, 4)


class HybridSAC:
    """Trainable hybrid actor/twin critics; checkpoints explicitly serve inference."""

    def __init__(self, settings: SACSettings | None = None) -> None:
        self.settings = settings or SACSettings()
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(self.settings.seed)
            self.actor, self.critics = HybridActor(self.settings.hidden), TwinCritics(self.settings.hidden)
        self.target = deepcopy(self.critics).requires_grad_(False)
        self.generator = torch.Generator(device="cpu").manual_seed(self.settings.seed + 303)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.settings.learning_rate)
        self.critic_optimizer = torch.optim.Adam(self.critics.parameters(), lr=self.settings.learning_rate)
        self.updates = 0

    def act(self, observation: np.ndarray, mask: np.ndarray, deterministic: bool = False) -> tuple[np.ndarray, int]:
        observation, mask = np.asarray(observation, dtype=np.float32), np.asarray(mask)
        if (observation.shape != (10,) or not np.isfinite(observation).all() or mask.shape != (4,)
                or mask.dtype != np.bool_ or not mask.any()):
            raise ValueError("SAC inference requires ten finite state values and a nonempty boolean pit mask")
        with torch.no_grad():
            energy, _, probs, _ = self.actor.sample(torch.from_numpy(observation)[None], torch.from_numpy(mask)[None],
                                                   self.generator, deterministic)
            pit = probs.argmax(-1) if deterministic else torch.multinomial(probs, 1, generator=self.generator).squeeze(-1)
        if not torch.isfinite(energy).all() or not torch.isfinite(probs).all():
            raise ValueError("SAC inference produced nonfinite actions")
        return energy[0].numpy().copy(), int(pit.item())

    @staticmethod
    def _validate_batch(batch: dict[str, torch.Tensor]) -> None:
        n = len(batch["observation"])
        shapes = {"observation": (n, 10), "next_observation": (n, 10), "energy": (n, 2),
                  "mask": (n, 4), "next_mask": (n, 4), "pit": (n,), "reward": (n,), "done": (n,)}
        if n == 0 or any(batch[k].shape != shape for k, shape in shapes.items()):
            raise ValueError("SAC minibatch has invalid shapes")
        if any(not torch.isfinite(batch[k]).all() for k in shapes):
            raise ValueError("SAC minibatch is nonfinite")
        if (batch["mask"].dtype != torch.bool or batch["next_mask"].dtype != torch.bool
                or not batch["mask"].any(-1).all() or not batch["next_mask"].any(-1).all()
                or batch["pit"].dtype != torch.long or torch.any((batch["pit"] < 0) | (batch["pit"] > 3))
                or torch.any(abs(batch["energy"]) > 1) or torch.any((batch["done"] != 0) & (batch["done"] != 1))):
            raise ValueError("SAC minibatch violates action/mask/terminal contracts")
        if not batch["mask"].gather(1, batch["pit"][:, None]).all():
            raise ValueError("SAC replay contains a masked pit action")

    def update(self, batch: dict[str, torch.Tensor]) -> dict[str, float]:
        self._validate_batch(batch)
        cfg = self.settings
        with torch.no_grad():
            energy, density, probs, log_probs = self.actor.sample(batch["next_observation"], batch["next_mask"], self.generator)
            value = soft_value(self.target.all_pits(batch["next_observation"], energy), probs, log_probs, density, cfg.alpha)
            backup = batch["reward"] + cfg.gamma * (1 - batch["done"]) * value
        q1, q2 = self.critics(batch["observation"], batch["energy"], batch["pit"])
        critic_loss = F.mse_loss(q1, backup) + F.mse_loss(q2, backup)
        if not torch.isfinite(critic_loss):
            raise ValueError("SAC critic loss is nonfinite")
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        critic_norm = nn.utils.clip_grad_norm_(self.critics.parameters(), cfg.max_gradient_norm, error_if_nonfinite=True)
        self.critic_optimizer.step()
        self.critics.requires_grad_(False)
        try:
            energy, density, probs, log_probs = self.actor.sample(batch["observation"], batch["mask"], self.generator)
            actor_loss = -soft_value(self.critics.all_pits(batch["observation"], energy), probs, log_probs, density, cfg.alpha).mean()
            if not torch.isfinite(actor_loss):
                raise ValueError("SAC actor loss is nonfinite")
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            actor_norm = nn.utils.clip_grad_norm_(self.actor.parameters(), cfg.max_gradient_norm, error_if_nonfinite=True)
            self.actor_optimizer.step()
        finally:
            self.critics.requires_grad_(True)
        with torch.no_grad():
            for target, online in zip(self.target.parameters(), self.critics.parameters(), strict=True):
                target.lerp_(online, cfg.target_mix)
        if any(not torch.isfinite(p).all() for m in (self.actor, self.critics, self.target) for p in m.parameters()):
            raise ValueError("SAC update produced nonfinite parameters")
        self.updates += 1
        return {"critic_loss": float(critic_loss.detach()), "actor_loss": float(actor_loss.detach()),
                "critic_gradient_norm": float(critic_norm), "actor_gradient_norm": float(actor_norm),
                "target_mean": float(backup.mean())}

    def save_inference_checkpoint(self, path: Path, environment: dict) -> None:
        if path.exists():
            raise FileExistsError(f"SAC checkpoint already exists: {path}")
        torch.save({"schema_version": "apex-hybrid-sac-inference-v1", "checkpoint_kind": "inference_not_training_resume",
                    "settings": asdict(self.settings), "environment": environment, "updates": self.updates,
                    "actor": self.actor.state_dict(), "critics": self.critics.state_dict(),
                    "target": self.target.state_dict()}, path)

    @classmethod
    def load_inference_checkpoint(cls, path: Path, environment: dict) -> HybridSAC:
        payload = torch.load(path, map_location="cpu", weights_only=True)
        if payload["schema_version"] != "apex-hybrid-sac-inference-v1" or payload["environment"] != environment:
            raise ValueError("SAC checkpoint schema/environment mismatch")
        agent = cls(SACSettings(**payload["settings"]))
        for name in ("actor", "critics", "target"):
            getattr(agent, name).load_state_dict(payload[name], strict=True)
        if any(not torch.isfinite(p).all() for m in (agent.actor, agent.critics, agent.target) for p in m.parameters()):
            raise ValueError("SAC checkpoint contains nonfinite parameters")
        agent.updates = payload["updates"]
        return agent
