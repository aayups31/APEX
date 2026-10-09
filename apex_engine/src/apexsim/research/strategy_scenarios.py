"""Frozen causal disturbance evaluation; scenario schedules never enter controllers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from time import perf_counter

import numpy as np

from apexsim.research.continuation_reference import tiny_continuation_reference
from apexsim.research.fienia_strategy import PaperStrategyAction
from apexsim.research.sac_env import DRY, StrategyLearningEnv
from apexsim.research.smooth_lap import LapMode, SmoothLapMap
from apexsim.research.strategy_disturbances import apply_wear_shock
from apexsim.research.strategy_solver import energy_starts
from apexsim.sim_core.types import TyreCompound


@dataclass(frozen=True)
class Scenario:
    name: str
    boundary: int | None
    dose: float


SCENARIOS = (Scenario("nominal", None, 0.), Scenario("zero_at_1", 1, 0.),
             Scenario("wear_06_at_0", 0, .6), Scenario("wear_06_at_1", 1, .6),
             Scenario("wear_10_at_1", 1, 1.))


class PlanController:
    """Receives an event only now; no scenario identifier or future event parameters."""

    def __init__(self, actions: tuple[PaperStrategyAction, ...], method: str):
        if method not in ("committed_nominal", "causal_replan", "conservative_hard", "greedy_energy_early_pit"):
            raise ValueError("Unknown scenario controller")
        self.actions, self.method, self.reacted = list(actions), method, False

    def __call__(self, env, observation, mask, observed_dose):
        i, n = env.state.lap, env.model.p.total_laps
        event = observed_dose is not None and observed_dose > 0
        if self.method == "causal_replan" and event:
            reference = tiny_continuation_reference(env.model, env.state, env.window, env.eps)
            self.actions[i:] = reference.actions
        action = self.actions[i]
        pit = 0 if action.pit_compound is None else DRY.index(action.pit_compound) + 1
        if self.method == "conservative_hard" and event:
            self.reacted = True
            pit = 1 if env.state.compound == TyreCompound.HARD else 3
            if not mask[pit]:
                pit = int(np.flatnonzero(mask)[0])
        elif self.method == "conservative_hard" and self.reacted:
            pit = 0 if mask[0] else int(np.flatnonzero(mask)[0])
        if self.method == "greedy_energy_early_pit":
            pit = (2 if env.state.compound == TyreCompound.SOFT else 1) if i == 0 else 0
        if self.method == "greedy_energy_early_pit" or (self.method == "conservative_hard" and self.reacted):
            start = energy_starts(env.model)[1]
            action = PaperStrategyAction(start[i] * env.model.p.nominal_fuel_energy_mj(), start[n + i])
        return env.physical_to_energy(action), pit


def evaluate_scenario(compound: TyreCompound, scenario: Scenario, choose: Callable) -> dict:
    """Record failures, matched-state regret and independent per-lap symbolic/model replay."""
    if scenario not in SCENARIOS:
        raise ValueError("Scenario is outside the frozen protocol")
    env = StrategyLearningEnv()
    env.reset(compound)
    lap_map = SmoothLapMap(env.model.p, env.model.time_loss, env.eps)
    rows, event_record, reference = [], None, None
    prefix, runtime, error = 0., 0., 0.
    replay_state = env.state
    began = perf_counter()
    result = {"initial_compound": compound.value, "scenario": scenario.name}
    try:
        for i in range(env.model.p.total_laps):
            observed_dose = None
            if i == scenario.boundary:
                before = env.state
                apply_wear_shock(env, scenario.dose)
                # Independent state history gets the same declared exogenous intervention.
                replay_state = replace(replay_state, tyre_wear=replay_state.tyre_wear + scenario.dose)
                observed_dose = scenario.dose
                event_record = {"before": asdict(before), "after": asdict(env.state), "dose": scenario.dose}
            if i == (scenario.boundary if scenario.boundary is not None else 0):
                reference = tiny_continuation_reference(env.model, env.state, env.window, env.eps)
                prefix = env.smooth_time_s
            observation, mask, state = env.observe(), env.action_mask(), env.state
            start = perf_counter()
            energy, pit = choose(env, observation.copy(), mask.copy(), observed_dose)
            runtime += perf_counter() - start
            step = env.step(energy, pit)
            applied = step.transition.applied_action
            replay_state, info = env.model.transition(replay_state, applied)
            if replay_state != env.state or info.wear_clipped:
                raise ValueError("Disturbance model replay disagrees with recorded history")
            mode = (LapMode.OUT_INLAP if state.outlap else LapMode.INLAP) if pit else (
                LapMode.OUTLAP if state.outlap else LapMode.NORMAL)
            expected = float(lap_map.functions(state.compound, mode).value(
                [applied.fuel_energy_mj, applied.battery_delta_mj, state.car_mass_kg, state.tyre_wear]))
            error = max(error, abs(expected - step.smooth_lap_time_s))
            if error > 1e-8:
                raise ValueError("Independent smooth-map replay disagrees")
            rows.append({"observation": observation.tolist(), "mask": mask.tolist(), "before": asdict(state),
                         "requested_energy": np.asarray(energy).tolist(), "pit_code": pit,
                         "transition": asdict(step.transition), "state": asdict(env.state),
                         "smooth_lap_time_s": step.smooth_lap_time_s, "reward": step.reward,
                         "next_observation": step.observation.tolist(), "next_mask": step.mask.tolist()})
        remaining = env.smooth_time_s - prefix
        regret = remaining - reference.remaining_time_s
        allowance = env.model.p.total_laps * lap_map.approximation_bound_s
        if regret < -1e-8 or abs(env.smooth_time_s - env.state.race_time_s) > allowance + 1e-8:
            raise ValueError("Matched-state minimum or smoothing bound violated")
        result.update(legal=env.model.final_state_is_legal(env.state), failure=None,
                      smooth_race_time_s=env.smooth_time_s, original_race_time_s=env.state.race_time_s,
                      prefix_smooth_time_s=prefix, remaining_time_s=remaining, matched_state_regret_s=regret,
                      reference=asdict(reference), max_objective_replay_error_s=error,
                      piecewise_error_allowance_s=allowance,
                      projection_laps=sum(r["transition"]["action_projected"] for r in rows))
        result["max_fuel_projection_mj"] = max(abs(r["transition"]["requested_action"]["fuel_energy_mj"] -
                                                   r["transition"]["applied_action"]["fuel_energy_mj"]) for r in rows)
        result["max_battery_projection_mj"] = max(abs(r["transition"]["requested_action"]["battery_delta_mj"] -
                                                      r["transition"]["applied_action"]["battery_delta_mj"]) for r in rows)
    except (ValueError, RuntimeError) as exc:
        result.update(legal=False, failure=str(exc), matched_state_regret_s=None)
    result.update(trajectory=rows, event=event_record, decision_runtime_s=runtime,
                  episode_runtime_s=perf_counter() - began)
    return result
