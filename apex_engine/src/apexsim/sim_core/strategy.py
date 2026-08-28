from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from apexsim.sim_core.race import RaceSimulator
from apexsim.sim_core.types import PitStopPlan, TyreCompound


@dataclass(frozen=True)
class StrategyCandidate:
    name: str
    stops: tuple[PitStopPlan, ...]


@dataclass(frozen=True)
class StrategyScore:
    name: str
    mean_position: float
    position_p90: float
    mean_race_time_s: float
    race_time_p90_s: float
    finish_rate: float
    samples: int


@dataclass
class StrategyPlanResult:
    ranking: pd.DataFrame
    raw_runs: pd.DataFrame

    @property
    def best(self) -> dict:
        if self.ranking.empty:
            raise RuntimeError("No strategy results are available")
        return self.ranking.iloc[0].to_dict()


class MonteCarloStrategyPlanner:
    """Evaluate pit strategies by repeated full-race simulation.

    The planner deliberately consumes a simulator factory, rather than hiding
    assumptions in a lap-time equation. Later, the same interface can call a
    learned residual model, CEM-MPC planner, or distributed simulation service.
    """

    def __init__(
        self,
        simulator_factory: Callable[[StrategyCandidate, int], RaceSimulator],
        target_car_id: str,
    ):
        self.simulator_factory = simulator_factory
        self.target_car_id = target_car_id

    def evaluate(
        self,
        candidates: Iterable[StrategyCandidate],
        rollouts: int = 8,
        base_seed: int = 100,
    ) -> StrategyPlanResult:
        rows: list[dict] = []
        for candidate in candidates:
            for rollout in range(rollouts):
                seed = base_seed + rollout
                result = self.simulator_factory(candidate, seed).run()
                target = result.standings[result.standings.car_id == self.target_car_id]
                if target.empty:
                    raise ValueError(f"Target car {self.target_car_id!r} missing from simulation")
                row = target.iloc[0]
                rows.append(
                    {
                        "strategy": candidate.name,
                        "rollout": rollout,
                        "seed": seed,
                        "position": float(row.position),
                        "race_time_s": float(row.race_time_s) if np.isfinite(row.race_time_s) else np.nan,
                        "finished": int(row.status == "FINISHED"),
                        "pit_stops": int(row.pit_stops),
                    }
                )
        raw = pd.DataFrame(rows)
        summaries = []
        for name, group in raw.groupby("strategy"):
            finished = group[group.finished == 1]
            summaries.append(
                {
                    "strategy": name,
                    "mean_position": group.position.mean(),
                    "position_p90": group.position.quantile(0.90),
                    "mean_race_time_s": finished.race_time_s.mean() if not finished.empty else np.inf,
                    "race_time_p90_s": finished.race_time_s.quantile(0.90) if not finished.empty else np.inf,
                    "finish_rate": group.finished.mean(),
                    "samples": len(group),
                }
            )
        ranking = pd.DataFrame(summaries).sort_values(
            ["finish_rate", "mean_position", "mean_race_time_s"],
            ascending=[False, True, True],
        ).reset_index(drop=True)
        return StrategyPlanResult(ranking, raw)


def default_one_stop_candidates(total_laps: int) -> list[StrategyCandidate]:
    windows = sorted({max(2, int(total_laps * fraction)) for fraction in (0.35, 0.45, 0.55, 0.65)})
    candidates = [
        StrategyCandidate("NO_STOP", ()),
    ]
    for lap in windows:
        candidates.append(
            StrategyCandidate(
                f"MEDIUM_TO_HARD_L{lap}",
                (PitStopPlan(lap=lap, compound=TyreCompound.HARD),),
            )
        )
        candidates.append(
            StrategyCandidate(
                f"SOFT_TO_MEDIUM_L{lap}",
                (PitStopPlan(lap=lap, compound=TyreCompound.MEDIUM),),
            )
        )
    return candidates
