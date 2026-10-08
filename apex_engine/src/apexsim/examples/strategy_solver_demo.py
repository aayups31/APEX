"""Immutable matched small-case acceptance for the R016 local solver adapter."""
from __future__ import annotations

import os
import platform
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import numpy as np

from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import continuous_reference, fienia_strategy, smooth_lap, strategy_solver
from apexsim.research.continuous_reference import tiny_continuous_reference
from apexsim.research.fienia_strategy import PaperStrategyModel, PaperStrategyParameters, TireWearCoefficients
from apexsim.research.strategy_solver import EnumeratedStrategySolver, FixedPlanProblem, energy_starts
from apexsim.sim_core.types import TyreCompound


def run_strategy_solver_demo(output: Path) -> dict:
    """Check matched optima and resource replay before creating any artifact root."""
    if output.exists():
        raise FileExistsError(f"Strategy solver evidence output already exists: {output}")
    sources = [Path(m.__file__) for m in (continuous_reference, fienia_strategy, smooth_lap, strategy_solver)]
    sources.append(Path(__file__))
    before = {p.name: file_sha256(p) for p in sources}
    records = []
    for label, linear, coupled in (("linear_hand_case", True, False),
                                  ("concave_battery_vertex_case", False, False),
                                  ("mass_coupled_six_lap_case", False, True)):
        p = PaperStrategyParameters(total_laps=6 if coupled else 3, initial_fuel_kg=12 if coupled else 6,
                                    battery_capacity_mj=2 if coupled else 1, battery_delta_min_mj=-1,
                                    battery_delta_max_mj=.5,
                                    battery_deploy_time_s_per_mj=.4 if linear else .42,
                                    battery_recharge_time_s_per_mj=.4 if linear else .32)
        wear = None if coupled else {c: TireWearCoefficients(1., 0., .01) for c in
                                    (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)}
        model = PaperStrategyModel(p, wear_coefficients=wear)
        window = (2, 2) if coupled else (1, 1)
        baseline_plan = tuple(TyreCompound.SOFT if i == window[0] else None for i in range(p.total_laps))
        baseline = FixedPlanProblem(model, baseline_plan).replay(energy_starts(model)[0])
        result = EnumeratedStrategySolver(model).solve(pit_window=window)
        solution = result.solution
        record = {"case": label, "parameters": asdict(p), "pit_window": list(window),
                  "classification": "ADAPTATION", "solver": result.report,
                  "solution": asdict(solution), "baseline": asdict(baseline),
                  "baseline_improvement_s": baseline.smooth_race_time_s - solution.smooth_race_time_s}
        if solution.smooth_race_time_s > baseline.smooth_race_time_s + 1e-6:
            raise ValueError(f"Solver acceptance is worse than the matched feasible baseline: {label}")
        if not coupled:
            begin = perf_counter()
            reference = tiny_continuous_reference(model, pit_window=window)
            runtime = perf_counter() - begin
            regret = solution.smooth_race_time_s - reference.race_time_s
            if abs(regret) > 1e-6:
                raise ValueError(f"Solver acceptance missed the independent tiny optimum: {label}")
            if linear and abs(reference.race_time_s - 305.626825) > 1e-10:
                raise ValueError("Linear hand optimum no longer agrees with the frozen scalar expectation")
            ratios = [a.fuel_energy_mj/p.nominal_fuel_energy_mj() for a in solution.actions]
            if linear and max(abs(a-b) for a,b in zip(ratios, (1.1, 1., .9), strict=True)) > 1e-5:
                raise ValueError("Linear hand case did not recover front-loaded fuel allocation")
            record.update(reference=asdict(reference), reference_runtime_s=runtime, regret_s=regret)
        else:
            record.update(reference=None, regret_s=None,
                          reference_limitation="Mass-dependent wear is outside the tiny concave reference family")
        records.append(record)
    if before != {p.name: file_sha256(p) for p in sources}:
        raise ValueError("Strategy solver sources changed during acceptance")
    summary = {"schema_version": "apex-strategy-solver-run-v1", "classification": "ADAPTATION",
               "maturity": "R0", "passed": True, "training_ready": False,
               "global_solver_optimality_certified": False, "cases": len(records), "reference_cases": 2,
               "max_absolute_regret_s": max(abs(r["regret_s"]) for r in records if r["regret_s"] is not None),
               "max_primal_violation": max(r["solution"]["max_primal_violation"] for r in records),
               "max_terminal_resource_mj": max(max(abs(r["solution"]["terminal_fuel_mj"]),
                                                   abs(r["solution"]["terminal_battery_mj"])) for r in records),
               "max_legacy_action_adjustment_mj": max(r["solution"]["max_legacy_action_adjustment_mj"] for r in records),
               "implementation_sha256": before,
               "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                           "platform": platform.platform(),
                           "thread_limits": {k: os.environ.get(k) for k in
                                             ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")}},
               "acceptance_tolerances": {"regret_s": 1e-6, "graph_scalar_objective_s": 1e-8,
                                          "primal": 1e-7, "terminal_resource_mj": 1e-7,
                                          "legacy_action_adjustment_mj": 1e-7},
               "case_metrics": [{"case": r["case"], "objective_s": r["solution"]["smooth_race_time_s"],
                                 "baseline_s": r["baseline"]["smooth_race_time_s"],
                                 "baseline_improvement_s": r["baseline_improvement_s"], "regret_s": r["regret_s"],
                                 "solver_runtime_s": r["solver"]["runtime_s"],
                                 "accepted_attempts": r["solver"]["accepted_attempts"]} for r in records],
               "limitations": ["Synthetic priors only; no production promotion or paper result replication.",
                               "IPOPT is local; enumerating discrete schedules does not certify continuous global optima.",
                               "Tiny global reference requires <=3 laps, mass-independent wear and concave battery cost.",
                               "Adapter supports <=8 laps and explicit discrete budgets; no clipping in its graph.",
                               "Legacy replay may make only recorded numerical energy adjustments within tolerance.",
                               "Successful NLP calls retain better checked feasible starts; candidate provenance is recorded.",
                               "Runtime varies with machine/load; no policy-speed claim is made."]}
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True, exist_ok=False)
    write_manifest(output / "cases.json", records)
    write_manifest(output / "summary.json", summary)
    manifest = {"schema_version": "apex-strategy-solver-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output / "manifest.json", manifest)
    return summary
