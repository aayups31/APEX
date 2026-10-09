"""Seeded synthetic SAC training; evaluations and oracles never enter replay."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from time import perf_counter

import numpy as np
import torch

from apexsim.research.hybrid_sac import HybridSAC, SACSettings
from apexsim.research.sac_env import DRY, StrategyLearningEnv


class StrategyReplayBuffer:
    """Bounded ring buffer of requested actions; physical projection belongs to the environment."""

    def __init__(self, capacity: int, seed: int) -> None:
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("Replay capacity must be a positive integer")
        self.capacity, self.size, self.position = capacity, 0, 0
        self.rng = np.random.default_rng(seed)
        shapes = {"observation": (10,), "next_observation": (10,), "energy": (2,),
                  "mask": (4,), "next_mask": (4,), "pit": (), "reward": (), "done": ()}
        self.data = {k: np.empty((capacity, *shape), dtype=np.bool_ if "mask" in k else (
            np.int64 if k == "pit" else np.float32)) for k, shape in shapes.items()}

    def add(self, observation: np.ndarray, mask: np.ndarray, energy: np.ndarray, pit: int,
            reward: float, next_observation: np.ndarray, next_mask: np.ndarray, done: bool) -> None:
        values = {"observation": observation, "mask": mask, "energy": energy, "pit": pit,
                  "reward": reward, "next_observation": next_observation, "next_mask": next_mask, "done": float(done)}
        if type(done) is not bool or type(pit) is not int:
            raise ValueError("Replay requires an integer pit and boolean terminal flag")
        batch = {k: torch.as_tensor(np.asarray(v))[None] for k, v in values.items()}
        HybridSAC._validate_batch(batch)
        for k, value in values.items():
            self.data[k][self.position] = value
        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, count: int) -> dict[str, torch.Tensor]:
        if type(count) is not int or not 0 < count <= self.size:
            raise ValueError("Replay sampling requires a positive batch no larger than current replay")
        indices = self.rng.choice(self.size, size=count, replace=False)
        return {k: torch.from_numpy(v[indices].copy()) for k, v in self.data.items()}


def _parameters(module: torch.nn.Module) -> torch.Tensor:
    return torch.cat([p.detach().flatten().clone() for p in module.parameters()])


def train_strategy_sac(settings: SACSettings,
                       progress: Callable[[dict], None] | None = None) -> tuple[HybridSAC, dict, list[dict]]:
    """One gradient update per post-warmup step; final checkpoint only, no evaluation selection."""
    env, agent = StrategyLearningEnv(), HybridSAC(settings)
    replay = StrategyReplayBuffer(settings.replay_capacity, settings.seed + 101)
    rng = np.random.default_rng(settings.seed + 202)
    before_actor, before_critic = _parameters(agent.actor), _parameters(agent.critics)
    observation, mask = env.reset(DRY[0])
    returns, initial_counts, trace = [], {c.value: 0 for c in DRY}, []
    episode_reward, projections, max_fuel_projection, max_battery_projection = 0., 0, 0., 0.
    begin = perf_counter()
    for step in range(settings.steps):
        if step < settings.warmup:
            energy, pit = rng.uniform(-1, 1, 2), int(rng.choice(np.flatnonzero(mask)))
        else:
            energy, pit = agent.act(observation, mask)
        result = env.step(energy, pit)
        replay.add(observation, mask, energy, pit, result.reward, result.observation, result.mask, result.terminated)
        info = result.transition
        fuel = abs(info.requested_action.fuel_energy_mj - info.applied_action.fuel_energy_mj)
        battery = abs(info.requested_action.battery_delta_mj - info.applied_action.battery_delta_mj)
        projections += int(max(fuel, battery) > 1e-9)
        max_fuel_projection, max_battery_projection = max(max_fuel_projection, fuel), max(max_battery_projection, battery)
        metrics = agent.update(replay.sample(settings.batch_size)) if step >= settings.warmup else None
        episode_reward += result.reward
        observation, mask = result.observation, result.mask
        if result.terminated:
            initial_counts[DRY[len(returns) % len(DRY)].value] += 1
            returns.append(float(episode_reward))
            episode_reward = 0.
            observation, mask = env.reset(DRY[len(returns) % len(DRY)])
        interval = 1000 if settings.steps >= 1000 else 50
        if (step + 1) % interval == 0 or step + 1 == settings.steps:
            row = {"step": step + 1, "updates": agent.updates, "episodes": len(returns),
                   "recent_mean_return": float(np.mean(returns[-100:])) if returns else None,
                   "elapsed_s": perf_counter() - begin, "metrics": metrics}
            trace.append(row)
            if progress:
                progress({"seed": settings.seed, **row})
    actor_change = float(torch.linalg.vector_norm(_parameters(agent.actor) - before_actor))
    critic_change = float(torch.linalg.vector_norm(_parameters(agent.critics) - before_critic))
    if not np.isfinite([actor_change, critic_change]).all() or min(actor_change, critic_change) <= 0:
        raise ValueError("SAC training did not produce finite nonzero actor and critic changes")
    report = {"settings": asdict(settings), "environment": env.metadata(), "runtime_s": perf_counter() - begin,
              "updates": agent.updates, "completed_episodes": len(returns), "initial_compound_episodes": initial_counts,
              "legal_completed_episodes": len(returns), "unfinished_episode_steps": settings.steps % env.model.p.total_laps,
              "projection_steps": projections, "projection_fraction": projections / settings.steps,
              "max_fuel_projection_mj": max_fuel_projection, "max_battery_projection_mj": max_battery_projection,
              "actor_parameter_change_l2": actor_change, "critic_parameter_change_l2": critic_change,
              "first_100_mean_return": float(np.mean(returns[:100])) if returns else None,
              "last_100_mean_return": float(np.mean(returns[-100:])) if returns else None,
              "replay_transitions": settings.steps, "evaluation_transitions_in_replay": 0,
              "checkpoint_selection": "final step, no evaluation or best-checkpoint selection",
              "initial_compound_selection": "cycle SOFT/MEDIUM/HARD by episode"}
    return agent, report, trace
