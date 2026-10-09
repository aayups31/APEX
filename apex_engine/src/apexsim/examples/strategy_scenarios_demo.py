"""R018 immutable evaluation of existing R017 inference weights, without training."""
from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from apexsim.examples import sac_strategy_demo
from apexsim.examples.sac_strategy_demo import profile_settings
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import (
    continuation_reference,
    continuous_reference,
    fienia_strategy,
    hybrid_sac,
    sac_env,
    sac_training,
    smooth_lap,
    strategy_disturbances,
    strategy_env,
    strategy_scenarios,
    strategy_solver,
)
from apexsim.research.continuation_reference import tiny_continuation_reference
from apexsim.research.hybrid_sac import HybridSAC
from apexsim.research.sac_env import DRY, StrategyLearningEnv
from apexsim.research.strategy_scenarios import SCENARIOS, PlanController, evaluate_scenario
from apexsim.research.strategy_solver import EnumeratedStrategySolver


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _checked_digest(payload: dict) -> str:
    copy = dict(payload)
    digest = copy.pop("content_sha256", None)
    if digest != payload_sha256(copy):
        raise ValueError("Artifact content digest mismatch")
    return digest


def load_frozen_run(root: Path) -> tuple[dict, list[HybridSAC], dict]:
    """Verify exact artifact inventory before loading weights with weights_only=True."""
    manifest, config, summary = (_read(root / f"{n}.json") for n in ("manifest", "config", "summary"))
    _checked_digest(manifest)
    _checked_digest(summary)
    if (manifest.get("schema_version") != "apex-sac-strategy-manifest-v1"
            or summary.get("schema_version") != "apex-sac-strategy-run-v1"
            or manifest.get("summary_sha256") != summary.get("content_sha256")
            or summary.get("passed") is not True or summary.get("promotion_recommended") is not False):
        raise ValueError("Input must be a complete unpromoted R017 run")
    settings = profile_settings(config["profile"])
    expected = {"config.json", "training.json", "traces.json", "evaluations.json", "baselines.json", "summary.json"}
    expected.update(f"seed-{cfg.seed}.pt" for cfg in settings)
    if set(manifest["files"]) != expected or {p.name for p in root.iterdir()} != expected | {"manifest.json"}:
        raise ValueError("Frozen run file inventory mismatch")
    for name, record in manifest["files"].items():
        path = root / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size != record["bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError("Frozen run file hash/size mismatch")
    if (config["environment"] != StrategyLearningEnv().metadata()
            or config["settings"] != [asdict(s) for s in settings]
            or summary["profile"] != config["profile"] or summary["seeds"] != [s.seed for s in settings]):
        raise ValueError("Frozen run config/environment mismatch")
    original_modules = (continuous_reference, fienia_strategy, hybrid_sac, sac_env,
                        sac_training, smooth_lap, strategy_env, strategy_solver, sac_strategy_demo)
    current = {Path(m.__file__).name: file_sha256(Path(m.__file__)) for m in original_modules}
    if current != summary["implementation_sha256"]:
        raise ValueError("R017 implementation differs from frozen training source")
    training = _read(root / "training.json")
    if [r["settings"] for r in training] != [asdict(s) for s in settings]:
        raise ValueError("Frozen training seed inventory mismatch")
    agents = []
    for cfg, report in zip(settings, training, strict=True):
        checkpoint = root / f"seed-{cfg.seed}.pt"
        payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if payload.get("checkpoint_kind") != "inference_not_training_resume":
            raise ValueError("Unexpected checkpoint kind")
        agent = HybridSAC.load_inference_checkpoint(checkpoint, config["environment"])
        if (agent.settings != cfg or type(agent.updates) is not int or agent.updates != cfg.steps - cfg.warmup
                or report["updates"] != agent.updates or report["completed_episodes"] != cfg.steps // 3):
            raise ValueError("Frozen checkpoint settings/final update count mismatch")
        agents.append(agent)
    return config, agents, {p.name: file_sha256(p) for p in root.iterdir()}


def _fingerprint(agent: HybridSAC) -> tuple:
    return (agent.updates, agent.generator.get_state().clone(),
            [p.detach().clone() for module in (agent.actor, agent.critics, agent.target) for p in module.parameters()])


def _unchanged(before: tuple, agent: HybridSAC) -> bool:
    after = _fingerprint(agent)
    return before[0] == after[0] and torch.equal(before[1], after[1]) and all(
        torch.equal(a, b) for a, b in zip(before[2], after[2], strict=True))


def _gates(rows: list[dict], original_evaluations: list[dict]) -> dict:
    index = {(r["method"], r["initial_compound"], r["scenario"]): r for r in rows}
    methods = sorted({r["method"] for r in rows})
    if not all(r["legal"] for r in rows):
        return {"all_episodes_legal": False, "failures_preserved": True}
    for method in methods:
        for compound in DRY:
            nominal = index[method, compound.value, "nominal"]
            zero = index[method, compound.value, "zero_at_1"]
            if nominal["trajectory"] != zero["trajectory"]:
                raise ValueError("Zero-dose intervention changed a trajectory")
            for case in ("wear_06_at_1", "wear_10_at_1"):
                if nominal["trajectory"][0] != index[method, compound.value, case]["trajectory"][0]:
                    raise ValueError("Controller received future disturbance information")
    for compound in DRY:
        committed = [index["committed_nominal", compound.value, case]["smooth_race_time_s"]
                     for case in ("nominal", "wear_06_at_1", "wear_10_at_1")]
        if not committed[0] <= committed[1] <= committed[2]:
            raise ValueError("Committed plan cost decreased under increased wear")
        for case in SCENARIOS:
            causal = index["causal_replan", compound.value, case.name]
            if causal["smooth_race_time_s"] > index["committed_nominal", compound.value, case.name]["smooth_race_time_s"] + 1e-8:
                raise ValueError("Causal replan worsened its committed feasible continuation")
            if abs(causal["matched_state_regret_s"]) > 1e-6:
                raise ValueError("Causal replan did not attain matched reference")
    nominal_soft = index["causal_replan", "SOFT", "nominal"]["trajectory"]
    shock_soft = index["causal_replan", "SOFT", "wear_06_at_0"]["trajectory"]
    if nominal_soft[0]["pit_code"] != 0 or shock_soft[0]["pit_code"] != 2:
        raise ValueError("Initial SOFT shock did not advance the stop")
    for seed in original_evaluations:
        for episode in seed["episodes"]:
            row = index[f"frozen_SAC_{seed['seed']}", episode["initial_compound"], "nominal"]
            if abs(row["smooth_race_time_s"] - episode["smooth_race_time_s"]) > 1e-8:
                raise ValueError("Frozen nominal policy cost changed from R017")
            for old, new in zip(episode["trajectory"], row["trajectory"], strict=True):
                if old["requested_energy"] != new["requested_energy"] or old["pit_code"] != new["pit_code"]:
                    raise ValueError("Frozen nominal policy actions changed from R017")
    return {"all_episodes_legal": True, "zero_dose_equivalence": True, "nonanticipation": True,
            "committed_cost_monotonic": True, "causal_no_worse": True, "initial_soft_stop_advanced": True,
            "nominal_R017_action_parity": True, "independent_replay": True}


def run_strategy_scenarios_demo(policy_run: Path, output: Path) -> dict:
    policy_run, output = policy_run.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"Scenario evidence output already exists: {output}")
    if policy_run == output or policy_run in output.parents:
        raise ValueError("Output must be outside the frozen input root")
    config, agents, input_hashes = load_frozen_run(policy_run)
    sources = [Path(m.__file__) for m in (continuation_reference, strategy_disturbances, strategy_scenarios)] + [Path(__file__)]
    source_hashes = {p.name: file_sha256(p) for p in sources}
    catalog_path = Path(__file__).resolve().parents[4] / "research/fixtures/fieni-scenarios-v1.json"
    catalog_hash, catalog = file_sha256(catalog_path), _read(catalog_path)
    fingerprints = [_fingerprint(a) for a in agents]
    rows, plans = [], []
    for compound in DRY:
        env = StrategyLearningEnv()
        solver = EnumeratedStrategySolver(env.model).solve(compound, env.window)
        reference = tiny_continuation_reference(env.model, env.model.initial_state(compound), env.window, env.eps)
        if abs(solver.solution.smooth_race_time_s - reference.remaining_time_s) > 1e-6:
            raise ValueError("Nominal R016 adapter/reference mismatch")
        plans.append({"initial_compound": compound.value, "actions": asdict(solver.solution)["actions"], "solver": solver.report})
        for scenario in SCENARIOS:
            controllers = [(name, PlanController(solver.solution.actions, name)) for name in (
                "committed_nominal", "causal_replan", "greedy_energy_early_pit", "conservative_hard")]
            controllers += [(f"frozen_SAC_{a.settings.seed}", lambda e, o, m, d, a=a: a.act(o, m, True)) for a in agents]
            for name, controller in controllers:
                row = evaluate_scenario(compound, scenario, controller)
                row["method"] = name
                rows.append(row)
    gates = _gates(rows, _read(policy_run / "evaluations.json"))
    index = {(r["initial_compound"], r["scenario"]): r for r in rows if r["method"] == "causal_replan"}
    for row in rows:
        baseline = index[row["initial_compound"], row["scenario"]]
        row["signed_full_race_gap_to_causal_s"] = (row["smooth_race_time_s"] - baseline["smooth_race_time_s"]
                                                  if row["legal"] and baseline["legal"] else None)
        nominal = next(r for r in rows if r["method"] == row["method"] and
                       r["initial_compound"] == row["initial_compound"] and r["scenario"] == "nominal")
        boundary = next(s.boundary for s in SCENARIOS if s.name == row["scenario"])
        if boundary is not None and row["legal"] and nominal["legal"]:
            current, old = row["trajectory"][boundary], nominal["trajectory"][boundary]
            row["observed_boundary_response_vs_nominal"] = {
                "energy_action_l2": float(np.linalg.norm(np.array(current["requested_energy"]) - old["requested_energy"])),
                "pit_choice_changed": current["pit_code"] != old["pit_code"]}
        else:
            row["observed_boundary_response_vs_nominal"] = None
    if not all(_unchanged(f, a) for f, a in zip(fingerprints, agents, strict=True)):
        raise ValueError("Evaluation changed frozen policy parameters, updates or RNG")
    if input_hashes != {p.name: file_sha256(p) for p in policy_run.iterdir()}:
        raise ValueError("Frozen input changed during evaluation")
    if source_hashes != {p.name: file_sha256(p) for p in sources} or catalog_hash != file_sha256(catalog_path):
        raise ValueError("Scenario implementation/catalog changed during evaluation")
    # Recheck original training source hashes as well as weights after evaluation.
    load_frozen_run(policy_run)
    metrics = []
    for method in sorted({r["method"] for r in rows}):
        all_rows = [r for r in rows if r["method"] == method]
        legal = [r for r in all_rows if r["legal"]]
        metrics.append({"method": method, "attempts": len(all_rows), "failed_episodes": len(all_rows) - len(legal),
                        "aggregate_scope": "legal episodes only; failures counted separately",
                        "mean_matched_state_regret_s": float(np.mean([r["matched_state_regret_s"] for r in legal])) if legal else None,
                        "mean_signed_full_race_gap_to_causal_s": float(np.mean([r["signed_full_race_gap_to_causal_s"] for r in legal])) if legal and index and all(index[r["initial_compound"], r["scenario"]]["legal"] for r in legal) else None,
                        "mean_decision_runtime_s_per_lap": sum(r["decision_runtime_s"] for r in all_rows) / (3 * len(all_rows))})
    summary = {"schema_version": "apex-strategy-scenarios-run-v1", "classification": "ADAPTATION", "maturity": "R0",
               "profile": config["profile"], "passed": all(gates.values()), "promotion_recommended": False,
               "directional_status": "DIRECTIONAL_MATCH" if all(gates.values()) else "FAILED",
               "published_magnitude_comparison": "INCONCLUSIVE", "seeds": [a.settings.seed for a in agents],
               "training_steps": 0, "evaluation_attempts": len(rows), "failed_episodes": sum(not r["legal"] for r in rows),
               "gates": gates, "frozen_policy_state_unchanged": True, "input_hashes": input_hashes,
               "implementation_sha256": source_hashes, "catalog_sha256": catalog_hash, "method_metrics": metrics,
               "runtime": {"python": platform.python_version(), "torch": str(torch.__version__), "numpy": np.__version__,
                           "casadi": __import__("casadi").__version__, "platform": platform.platform(),
                           "torch_threads": torch.get_num_threads(),
                           "thread_limits": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")}},
               "case_rankings": [{"initial_compound": c.value, "scenario": s.name,
                                  "ranking_scope": "descriptive legal full-race costs; different prefix states",
                                  "methods_in_cost_order": [r["method"] for r in sorted(
                                      (r for r in rows if r["initial_compound"] == c.value and r["scenario"] == s.name and r["legal"]),
                                      key=lambda r: r["smooth_race_time_s"])]} for c in DRY for s in SCENARIOS],
               "max_objective_replay_error_s": max((r.get("max_objective_replay_error_s", 0.) for r in rows), default=0.),
               "limitations": ["Three-lap synthetic priors; no published magnitude replication or real-race claim.",
                               "Higher-wear states were not part of R017 training; no retraining or winner selection.",
                               "Masks and energy projection enforce legality; policy does not learn those guarantees.",
                               "Matched-state regret and signed full-race gaps have different reference states.",
                               "Small fixed case set; seed differences are descriptive, not calibrated uncertainty.",
                               "Smoke verifies execution only. No maturity promotion follows."]}
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in (("catalog", catalog), ("config", {"environment": config["environment"], "scenarios": [asdict(s) for s in SCENARIOS], "policy_run": str(policy_run), "input_hashes": input_hashes}),
                          ("nominal_plans", plans), ("rollouts", rows), ("summary", summary)):
        write_manifest(output / f"{name}.json", payload)
    manifest = {"schema_version": "apex-strategy-scenarios-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output / "manifest.json", manifest)
    return summary
