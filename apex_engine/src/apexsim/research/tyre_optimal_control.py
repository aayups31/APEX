"""R042 finite synthetic tyre-control benchmark with a continuous reference."""

from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from functools import partial
from itertools import pairwise, product
from math import exp, isfinite
from pathlib import Path
from platform import python_version

import numpy as np
from scipy.integrate import solve_ivp

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research import tyre_thermal, tyre_wear
from apexsim.research.evidence import (
    check_seal,
    compare_numeric,
    finish_run,
    read_json,
    seal,
    verify_inventory,
)
from apexsim.research.tyre_thermal import DEFAULT_PARAMETERS, ThermalState, heat_step
from apexsim.research.tyre_wear import wear_step

VERSION = "apex-tyre-optimal-control-r042-v1"
LAPS = 4
LAP_EXPOSURE_S = 80.0
ROAD_K, AIR_K = 308.15, 298.15
CARCASS_W = 300.0
MESHES = (4, 16, 64, 256)
PIT_LOSSES_S = (2.0, 20.0)
TIME_TOLERANCE_S = 0.02
BALANCE_TOLERANCE_J = 1e-6


@dataclass(frozen=True)
class Compound:
    rate_per_j: float
    wear_penalty_s: float
    fresh_offset_s: float


@dataclass(frozen=True)
class Effort:
    tread_w: float
    pace_gain_s: float


@dataclass(frozen=True)
class Tyre:
    tread_k: float
    carcass_k: float
    wear: float


@dataclass(frozen=True)
class Strategy:
    efforts: tuple[str, ...]
    pit_before_lap: int | None = None
    replacement: str | None = None


COMPOUNDS = {"soft": Compound(1e-7, 28.0, 0.0), "hard": Compound(5e-8, 18.0, 0.9)}
EFFORTS = {"conserve": Effort(700.0, 0.0), "push": Effort(2100.0, 0.45)}
INITIAL = Tyre(333.15, 333.15, 0.14)
REPLACEMENT = Tyre(323.15, 323.15, 0.0)
FIXED = Strategy(("conserve",) * LAPS)


@dataclass(frozen=True)
class LapTransition:
    final: Tyre
    mean_wear: float
    maximum_balance_error_j: float | None


LapIntegrator = Callable[[Tyre, Compound, Effort], LapTransition]


def strategy_catalog() -> Iterator[Strategy]:
    """Enumerate every effort sequence and every optional replacement."""
    pit_choices = [(None, None), *product(range(2, LAPS + 1), COMPOUNDS)]
    for efforts in product(EFFORTS, repeat=LAPS):
        for lap, compound in pit_choices:
            yield Strategy(efforts, lap, compound)


def mesh_lap(initial: Tyre, compound: Compound, effort: Effort, steps: int) -> LapTransition:
    """Advance thermal state and integrate wear on a uniform substep mesh."""
    if type(steps) is not int or steps < 1:
        raise ValueError("Tyre integration requires a positive integer mesh")
    duration = LAP_EXPOSURE_S / steps
    temp = ThermalState(initial.tread_k, initial.carcass_k)
    wear = initial.wear
    wear_sum = maximum_balance = 0.0
    for _ in range(steps):
        updated = wear_step(wear, effort.tread_w * duration, temp.tread_k, compound.rate_per_j)
        if not wear <= updated <= 1 or not isfinite(updated):
            raise ValueError("Mesh wear left its monotone bounded domain")
        wear_sum += (wear + updated) / 2
        wear = updated
        heat = heat_step(
            temp, duration, tread_w=effort.tread_w, carcass_w=CARCASS_W, road_k=ROAD_K, air_k=AIR_K
        )
        temp = heat.state
        maximum_balance = max(maximum_balance, abs(heat.balance_error_j))
    return LapTransition(Tyre(temp.tread_k, temp.carcass_k, wear), wear_sum / steps, maximum_balance)


def reference_lap(initial: Tyre, compound: Compound, effort: Effort) -> LapTransition:
    """Independently integrate the continuous ODEs, including cumulative wear."""
    p = DEFAULT_PARAMETERS

    def rhs(_time, state):
        tread, carcass, wear, _integrated = state
        transfer = p.coupling_w_k * (tread - carcass)
        return [
            (effort.tread_w + p.road_w_k * (ROAD_K - tread) - transfer) / p.tread_capacity_j_k,
            (CARCASS_W + p.air_w_k * (AIR_K - carcass) + transfer) / p.carcass_capacity_j_k,
            (1 - wear) * compound.rate_per_j * effort.tread_w * exp((tread - 333.15) / 40),
            wear,
        ]

    result = solve_ivp(
        rhs,
        (0, LAP_EXPOSURE_S),
        (initial.tread_k, initial.carcass_k, initial.wear, 0),
        method="DOP853",
        atol=1e-11,
        rtol=1e-11,
    )
    if not result.success or not np.isfinite(result.y).all() or np.any(np.diff(result.y[2]) < -1e-12):
        raise ValueError("Reference tyre integration failed")
    tread, carcass, wear, integral = map(float, result.y[:, -1])
    return LapTransition(Tyre(tread, carcass, wear), integral / LAP_EXPOSURE_S, None)


def rollout(strategy: Strategy, integrate: LapIntegrator) -> dict:
    """Evaluate a legal plan before fixed pit loss. Lap numbers are one-based."""
    pit, replacement = strategy.pit_before_lap, strategy.replacement
    if (
        len(strategy.efforts) != LAPS
        or any(mode not in EFFORTS for mode in strategy.efforts)
        or (pit is None and replacement is not None)
        or (
            pit is not None and (type(pit) is not int or not 2 <= pit <= LAPS or replacement not in COMPOUNDS)
        )
    ):
        raise ValueError("Invalid synthetic tyre strategy")
    state, compound_name = INITIAL, "soft"
    rows = []
    for lap, mode in enumerate(strategy.efforts, start=1):
        if lap == pit:
            state, compound_name = REPLACEMENT, replacement
        compound, effort = COMPOUNDS[compound_name], EFFORTS[mode]
        step = integrate(state, compound, effort)
        if not (
            state.wear <= step.mean_wear <= step.final.wear <= 1
            and all(200 <= v <= 500 for v in (step.final.tread_k, step.final.carcass_k))
        ):
            raise ValueError("Tyre trajectory left the declared envelope")
        time = (
            LAP_EXPOSURE_S
            + compound.fresh_offset_s
            + compound.wear_penalty_s * step.mean_wear
            - effort.pace_gain_s
        )
        rows.append(
            {
                "lap": lap,
                "effort": mode,
                "compound": compound_name,
                "pit": lap == pit,
                "initial": asdict(state),
                "final": asdict(step.final),
                "mean_wear": step.mean_wear,
                "time_s": time,
                "maximum_balance_error_j": step.maximum_balance_error_j,
            }
        )
        state = step.final
    return {
        "strategy": {**asdict(strategy), "efforts": list(strategy.efforts)},
        "laps": rows,
        "time_without_pit_loss_s": sum(row["time_s"] for row in rows),
    }


def fixture() -> dict:
    """Return the full synthetic input and tolerance snapshot."""
    return {
        "evidence_domain": "SIMULATED",
        "laps": LAPS,
        "lap_exposure_s": LAP_EXPOSURE_S,
        "road_k": ROAD_K,
        "air_k": AIR_K,
        "carcass_w": CARCASS_W,
        "initial": asdict(INITIAL),
        "replacement": asdict(REPLACEMENT),
        "compounds": {k: asdict(v) for k, v in COMPOUNDS.items()},
        "efforts": {k: asdict(v) for k, v in EFFORTS.items()},
        "thermal": asdict(DEFAULT_PARAMETERS),
        "mesh_steps_per_lap": list(MESHES),
        "pit_losses_s": list(PIT_LOSSES_S),
        "time_tolerance_s": TIME_TOLERANCE_S,
        "balance_tolerance_j": BALANCE_TOLERANCE_J,
    }


def evaluate() -> tuple[dict, dict]:
    """Replay the complete catalog on each mesh and with an independent oracle."""
    strategies = list(strategy_catalog())
    ref = [rollout(plan, reference_lap) for plan in strategies]
    stopped = [plan.pit_before_lap is not None for plan in strategies]
    fixed_index = strategies.index(FIXED)
    ref_times = [row["time_without_pit_loss_s"] for row in ref]

    def decision(times):
        best = [
            min((i for i, pit in enumerate(stopped) if pit == choice), key=times.__getitem__)
            for choice in (False, True)
        ]
        crossing = times[best[0]] - times[best[1]]
        return best, crossing

    ref_best, crossover = decision(ref_times)
    meshes, paths = [], {}
    for steps in MESHES:
        integrate = partial(mesh_lap, steps=steps)
        runs = [rollout(plan, integrate) for plan in strategies]
        times = [row["time_without_pit_loss_s"] for row in runs]
        best, threshold = decision(times)
        meshes.append(
            {
                "steps_per_lap": steps,
                "best_no_stop_index": best[0],
                "best_stop_index": best[1],
                "pit_crossover_s": threshold,
                "crossover_error_s": abs(threshold - crossover),
                "maximum_time_error_s": max(abs(a - b) for a, b in zip(times, ref_times, strict=True)),
                "maximum_balance_error_j": max(
                    lap["maximum_balance_error_j"] for run in runs for lap in run["laps"]
                ),
            }
        )
        paths[str(steps)] = runs
    fine = meshes[-1]
    choices = []
    for loss in PIT_LOSSES_S:
        ref_index = ref_best[int(loss < crossover)]
        mesh_index = fine["best_stop_index"] if loss < fine["pit_crossover_s"] else fine["best_no_stop_index"]
        reference_optimum = ref_times[ref_index] + loss * stopped[ref_index]
        choices.append(
            {
                "pit_loss_s": loss,
                "reference_index": ref_index,
                "mesh_index": mesh_index,
                "reference_strategy": ref[ref_index]["strategy"],
                "mesh_strategy": ref[mesh_index]["strategy"],
                "reference_time_s": reference_optimum,
                "mesh_winner_reference_regret_s": ref_times[mesh_index]
                + loss * stopped[mesh_index]
                - reference_optimum,
                "fixed_policy_reference_regret_s": ref_times[fixed_index] - reference_optimum,
            }
        )
    checks = {
        "catalog_complete": len(strategies) == len(set(strategies)) == 112,
        "thermal_balance": all(m["maximum_balance_error_j"] <= BALANCE_TOLERANCE_J for m in meshes),
        "mesh_refinement": all(
            b["maximum_time_error_s"] < a["maximum_time_error_s"] for a, b in pairwise(meshes)
        ),
        "fine_time_accuracy": fine["maximum_time_error_s"] <= TIME_TOLERANCE_S,
        "fine_crossover_accuracy": fine["crossover_error_s"] <= TIME_TOLERANCE_S,
        "pit_decisions": all(
            PIT_LOSSES_S[0] < t < PIT_LOSSES_S[1] for t in (crossover, fine["pit_crossover_s"])
        ),
        "fine_policy_regret": all(c["mesh_winner_reference_regret_s"] <= TIME_TOLERANCE_S for c in choices),
    }
    summary = {
        "schema_version": VERSION,
        "scope": "SYNTHETIC_FINITE_TYRE_CONTROL",
        "strategy_count": len(strategies),
        "reference_pit_crossover_s": crossover,
        "reference_best_no_stop_index": ref_best[0],
        "reference_best_stop_index": ref_best[1],
        "meshes": meshes,
        "choices": choices,
        "checks": checks,
        "passed": all(checks.values()),
        "real_race_validation": False,
        "production_promotion": False,
    }
    return summary, {"reference": ref, "meshes": paths}


def run_study(output: Path) -> dict:
    """Write a new sealed benchmark run with full traces for audit and replay."""
    output.mkdir(parents=True, exist_ok=False)
    summary, trajectories = evaluate()
    write_manifest(output / "fixture.json", fixture())
    write_manifest(output / "trajectories.json", trajectories)
    sources = [Path(p) for p in (__file__, tyre_thermal.__file__, tyre_wear.__file__)]
    return finish_run(
        output,
        VERSION,
        {
            **summary,
            "python_version": python_version(),
            "source_sha256": {source.name: file_sha256(source) for source in sources},
        },
    )


def verify_study(output: Path) -> dict:
    """Check artifact integrity and independently regenerate all scored plans."""
    manifest = verify_inventory(output, VERSION)
    saved = read_json(output / "summary.json")
    check_seal(saved)
    if saved["content_sha256"] != manifest["summary_sha256"]:
        raise ValueError("R042 summary does not match the run manifest")
    compare_numeric(fixture(), read_json(output / "fixture.json"), "fixture")
    summary, trajectories = evaluate()
    recorded_metrics = {
        k: v for k, v in saved.items() if k not in {"content_sha256", "python_version", "source_sha256"}
    }
    compare_numeric(summary, recorded_metrics, "summary")
    compare_numeric(trajectories, read_json(output / "trajectories.json"), "trajectories")
    return seal(
        {
            "schema_version": VERSION + "-replay",
            "summary_sha256": saved["content_sha256"],
            "manifest_sha256": manifest["content_sha256"],
            "strategy_count": summary["strategy_count"],
            "integration_count": len(MESHES) + 1,
            "verified": True,
            "passed": summary["passed"],
        }
    )
