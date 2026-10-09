"""Immutable R017 in-task evaluation; fixed training budgets, never a promotion gate."""
from __future__ import annotations

import os
import platform
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import (
    continuous_reference,
    fienia_strategy,
    hybrid_sac,
    sac_env,
    sac_training,
    smooth_lap,
    strategy_env,
    strategy_solver,
)
from apexsim.research.continuous_reference import tiny_continuous_reference
from apexsim.research.fienia_strategy import PaperStrategyAction
from apexsim.research.hybrid_sac import HybridSAC, SACSettings
from apexsim.research.sac_env import DRY, StrategyLearningEnv
from apexsim.research.sac_training import train_strategy_sac
from apexsim.research.strategy_solver import EnumeratedStrategySolver, FixedPlanProblem, energy_starts
from apexsim.sim_core.types import TyreCompound


def profile_settings(profile: str) -> tuple[SACSettings, ...]:
    if profile == "smoke":
        return (SACSettings(seed=11, steps=300, batch_size=32, warmup=64),)
    if profile == "research":
        return tuple(SACSettings(seed=seed) for seed in (11, 23, 37))
    raise ValueError("SAC profile must be smoke or research")


def evaluate_strategy(compound: TyreCompound, choose: Callable, reference_time_s: float) -> dict:
    """A frozen deterministic rollout; preserve failures, actions and resource projections."""
    env = StrategyLearningEnv()
    observation, mask = env.reset(compound)
    rows, decision_time, begin = [], 0., perf_counter()
    try:
        for _ in range(env.model.p.total_laps):
            start = perf_counter()
            energy, pit = choose(env, observation, mask)
            decision_time += perf_counter() - start
            result = env.step(energy, pit)
            rows.append({"observation": observation.tolist(), "mask": mask.tolist(),
                         "requested_energy": np.asarray(energy).tolist(), "pit_code": pit,
                         "transition": asdict(result.transition), "state": asdict(env.state),
                         "reward": result.reward, "smooth_lap_time_s": result.smooth_lap_time_s,
                         "next_observation": result.observation.tolist(), "next_mask": result.mask.tolist()})
            observation, mask = result.observation, result.mask
    except (ValueError, RuntimeError) as exc:
        return {"initial_compound": compound.value, "legal": False, "failure": str(exc),
                "regret_s": None, "trajectory": rows, "decision_runtime_s": decision_time,
                "episode_runtime_s": perf_counter() - begin}
    actions = [row["transition"]["applied_action"] for row in rows]
    plan = tuple(a["pit_compound"] for a in actions)
    controls = [a["fuel_energy_mj"] / env.model.p.nominal_fuel_energy_mj() for a in actions]
    controls += [a["battery_delta_mj"] for a in actions]
    problem = FixedPlanProblem(env.model, plan, compound, env.eps)
    replay = problem.replay(controls)
    graph_time = float(problem.objective(controls))
    replay_error = max(abs(replay.smooth_race_time_s-env.smooth_time_s), abs(graph_time-env.smooth_time_s))
    allowance = env.model.p.total_laps * env.eps * abs(
        env.model.p.battery_recharge_time_s_per_mj - env.model.p.battery_deploy_time_s_per_mj) / 2
    if replay_error > 1e-8 or abs(env.smooth_time_s-env.state.race_time_s) > allowance + 1e-8:
        raise ValueError("SAC evaluation objective disagrees with independent scalar/symbolic replay")
    if env.smooth_time_s < reference_time_s - 1e-6:
        raise ValueError("SAC evaluation unexpectedly beats the matched independent minimum")
    return {"initial_compound": compound.value, "legal": env.model.final_state_is_legal(env.state), "failure": None,
            "smooth_race_time_s": env.smooth_time_s, "original_race_time_s": env.state.race_time_s,
            "regret_s": env.smooth_time_s-reference_time_s, "reference_time_s": reference_time_s,
            "trajectory": rows, "decision_runtime_s": decision_time, "episode_runtime_s": perf_counter()-begin,
            "max_objective_replay_error_s": replay_error, "piecewise_error_allowance_s": allowance,
            "max_primal_violation": replay.max_primal_violation,
            "projection_laps": sum(row["transition"]["action_projected"] for row in rows),
            "max_fuel_projection_mj": max(abs(row["transition"]["requested_action"]["fuel_energy_mj"]
                                             - row["transition"]["applied_action"]["fuel_energy_mj"]) for row in rows),
            "max_battery_projection_mj": max(abs(row["transition"]["requested_action"]["battery_delta_mj"]
                                                - row["transition"]["applied_action"]["battery_delta_mj"]) for row in rows)}


def _fixed_actions(actions: tuple[PaperStrategyAction, ...]) -> Callable:
    def choose(env, observation, mask):
        action = actions[env.state.lap]
        pit = 0 if action.pit_compound is None else DRY.index(action.pit_compound) + 1
        return env.physical_to_energy(action), pit
    return choose


def _rule(env: StrategyLearningEnv, observation: np.ndarray, mask: np.ndarray, greedy: bool) -> tuple[np.ndarray, int]:
    n, i = env.model.p.total_laps, env.state.lap
    start = energy_starts(env.model)[int(greedy)]
    pit = (2 if env.state.compound == TyreCompound.SOFT else 1) if i == 0 else 0
    action = PaperStrategyAction(start[i]*env.model.p.nominal_fuel_energy_mj(), start[n+i])
    return env.physical_to_energy(action), pit


def _baselines() -> list[dict]:
    records = []
    for compound in DRY:
        env = StrategyLearningEnv()
        start = perf_counter()
        reference = tiny_continuous_reference(env.model, compound, env.window, env.eps)
        reference_runtime = perf_counter()-start
        solver = EnumeratedStrategySolver(env.model).solve(compound, env.window)
        if abs(solver.solution.smooth_race_time_s-reference.race_time_s) > 1e-6:
            raise ValueError("R017 matched adapter/reference acceptance failed")
        rules = {}
        for name, greedy in (("uniform_energy_early_pit", False), ("greedy_energy_early_pit", True)):
            rules[name] = evaluate_strategy(compound, lambda e, o, m, g=greedy: _rule(e, o, m, g), reference.race_time_s)
        rules["local_adapter"] = evaluate_strategy(compound, _fixed_actions(solver.solution.actions), reference.race_time_s)
        if not all(row["legal"] for row in rules.values()):
            raise ValueError("R017 matched baseline produced an illegal rollout")
        records.append({"initial_compound": compound.value, "reference": asdict(reference),
                        "reference_runtime_s": reference_runtime, "solver": solver.report, "strategies": rules})
    return records


def run_sac_strategy_demo(output: Path, profile: str = "research", progress: Callable[[dict], None] | None = None) -> dict:
    """Numerical acceptance before writing; manifest written last after checkpoint reloads."""
    if output.exists():
        raise FileExistsError(f"SAC evidence output already exists: {output}")
    settings = profile_settings(profile)
    sources = [Path(m.__file__) for m in (continuous_reference, fienia_strategy, hybrid_sac, sac_env,
                                         sac_training, smooth_lap, strategy_env, strategy_solver)] + [Path(__file__)]
    before = {p.name: file_sha256(p) for p in sources}
    environment = StrategyLearningEnv().metadata()
    baselines = _baselines()
    agents, training, traces, evaluations = [], [], [], []
    for cfg in settings:
        agent, report, trace = train_strategy_sac(cfg, progress)
        agents.append(agent)
        training.append(report)
        traces.append({"seed": cfg.seed, "rows": trace})
        updates = agent.updates
        rows = [evaluate_strategy(c, lambda e, o, m, a=agent: a.act(o, m, deterministic=True), base["reference"]["race_time_s"])
                for c, base in zip(DRY, baselines, strict=True)]
        if agent.updates != updates:
            raise ValueError("Frozen policy evaluation unexpectedly changed training updates")
        evaluations.append({"seed": cfg.seed, "episodes": rows})
    if before != {p.name: file_sha256(p) for p in sources}:
        raise ValueError("SAC sources changed during the frozen experiment")
    rows = [r for seed in evaluations for r in seed["episodes"]]
    regrets = [r["regret_s"] for r in rows if r["legal"]]
    summary = {"schema_version": "apex-sac-strategy-run-v1", "classification": "ADAPTATION", "maturity": "R0",
               "profile": profile, "passed": True, "promotion_recommended": False,
               "evaluation_scope": "in-task deterministic evaluation; no held-out event generalization",
               "seeds": [s.seed for s in settings], "training_steps": sum(s.steps for s in settings),
               "training_episodes": sum(r["completed_episodes"] for r in training),
               "evaluation_attempts": len(rows), "legal_evaluation_episodes": sum(r["legal"] for r in rows),
               "evaluation_legality_fraction": sum(r["legal"] for r in rows)/len(rows),
               "mean_regret_s": float(np.mean(regrets)) if regrets else None,
               "std_regret_s": float(np.std(regrets)) if regrets else None,
               "max_regret_s": max(regrets) if regrets else None,
               "failed_evaluation_episodes": len(rows)-len(regrets),
               "mean_decision_runtime_s_per_lap": sum(r["decision_runtime_s"] for r in rows)/(len(rows)*3),
               "implementation_sha256": before,
               "runtime": {"python": platform.python_version(), "torch": str(torch.__version__), "numpy": np.__version__,
                           "casadi": __import__("casadi").__version__, "platform": platform.platform(),
                           "torch_threads": torch.get_num_threads(),
                           "thread_limits": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")}},
               "policy_metrics": [{"seed": e["seed"], "initial_compound": r["initial_compound"], "legal": r["legal"],
                                   "regret_s": r["regret_s"], "smooth_race_time_s": r.get("smooth_race_time_s"),
                                   "projection_laps": r.get("projection_laps"),
                                   "decision_runtime_s": r["decision_runtime_s"]} for e in evaluations for r in e["episodes"]],
               "baseline_metrics": [{"initial_compound": b["initial_compound"], "strategy": name,
                                     "regret_s": r["regret_s"], "smooth_race_time_s": r["smooth_race_time_s"],
                                     "decision_runtime_s": r["decision_runtime_s"],
                                     "planning_runtime_s": b["solver"]["runtime_s"] if name == "local_adapter" else None}
                                    for b in baselines for name, r in b["strategies"].items()],
               "limitations": ["Synthetic three-lap task only; no calibrated world model or deployed agent.",
                               "Legality is imposed by masks and reachability projection, not learned.",
                               "Factorized hybrid SAC, fixed alpha and gamma=1 are declared adaptations.",
                               "All seeds use final weights; no oracle supervision or evaluation selection.",
                               "Legal-only regret aggregates exclude failures, which are counted separately.",
                               "Smoke validates execution only; research evaluates three predeclared seeds.",
                               "Neural decision times exclude training and environment replay; planner time covers the full plan.",
                               "Checkpoints support inference only, not exact training resumption.",
                               "No promotion follows from in-task scores, even if a rule is outperformed."]}
    output.mkdir(parents=True, exist_ok=False)
    for agent, cfg in zip(agents, settings, strict=True):
        checkpoint = output / f"seed-{cfg.seed}.pt"
        agent.save_inference_checkpoint(checkpoint, environment)
        restored = HybridSAC.load_inference_checkpoint(checkpoint, environment)
        # Replay every evaluated state, including later-lap masks, through restored weights.
        for row in next(e["episodes"] for e in evaluations if e["seed"] == cfg.seed):
            for lap in row["trajectory"]:
                obs, mask = np.array(lap["observation"], dtype=np.float32), np.array(lap["mask"], dtype=bool)
                action, pit = restored.act(obs, mask, True)
                if not np.array_equal(action, lap["requested_energy"]) or pit != lap["pit_code"]:
                    raise ValueError("SAC inference checkpoint changed a frozen evaluation action")
    summary["checkpoint_reload_action_parity"] = True
    summary["content_sha256"] = payload_sha256(summary)
    write_manifest(output / "config.json", {"profile": profile, "settings": [asdict(s) for s in settings], "environment": environment})
    for name, payload in (("training", training), ("traces", traces), ("evaluations", evaluations), ("baselines", baselines), ("summary", summary)):
        write_manifest(output / f"{name}.json", payload)
    manifest = {"schema_version": "apex-sac-strategy-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output / "manifest.json", manifest)
    return summary
