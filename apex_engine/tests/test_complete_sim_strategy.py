from dataclasses import replace

from apexsim.examples.complete_sim_demo import build_demo
from apexsim.sim_core.strategy import MonteCarloStrategyPlanner, StrategyCandidate
from apexsim.sim_core.types import PitStopPlan, TyreCompound


def test_strategy_planner_ranks_candidates():
    def factory(candidate, seed):
        simulator = build_demo(seed=seed, total_laps=2)
        simulator.entries[0] = replace(simulator.entries[0], strategy=list(candidate.stops))
        return simulator

    candidates = [
        StrategyCandidate("NO_STOP", ()),
        StrategyCandidate("PIT_L1", (PitStopPlan(1, TyreCompound.HARD),)),
    ]
    result = MonteCarloStrategyPlanner(factory, "CAR_01").evaluate(candidates, rollouts=1)
    assert set(result.ranking.strategy) == {"NO_STOP", "PIT_L1"}
    assert result.best["strategy"] in {"NO_STOP", "PIT_L1"}
