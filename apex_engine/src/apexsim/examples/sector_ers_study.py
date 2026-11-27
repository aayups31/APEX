"""R043/R044 synthetic sector energy and disturbance verification."""

from dataclasses import asdict, replace
from itertools import product
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.evidence import finish_run
from apexsim.research.sector_ers import (
    EPS,
    Battery,
    InfeasibleEnergyPlan,
    Sector,
    advance,
    allocate,
    feedback_step,
)

VERSION = "apex-sector-ers-v1"
BATTERY = Battery(2.0, 1.0)
INITIAL_MJ = 1.0
GRID_MJ = 0.25
RUNTIME_LIMIT_S = 5.0
DEPLOY = Sector("deploy", 5.0, 80_000.0, 0.4, 2.0)
HARVEST = Sector("harvest", 5.0, 125_000.0, 0.625, 0.1)
NOMINAL = (
    DEPLOY,
    HARVEST,
    replace(DEPLOY, seconds_per_storage_mj=1.0),
    HARVEST,
    replace(DEPLOY, seconds_per_storage_mj=3.0),
    Sector("coast", 5.0, 0, 0, 0),
)
DISTURBED = (
    NOMINAL[0],
    replace(NOMINAL[1], wheel_opportunity_mj=0.3125),
    *NOMINAL[2:4],
    replace(NOMINAL[4], wheel_opportunity_mj=0.3),
    NOMINAL[5],
)


def grid_oracle() -> tuple[float, int]:
    """Enumerate independent integer quarter-MJ paths for the nominal fixture."""
    deltas = (range(-2, 1), range(3), range(-2, 1), range(3), range(-2, 1), (0,))
    objectives = []
    for sequence in product(*deltas):
        level = 4
        for delta in sequence:
            level += delta
            if not 0 <= level <= 8:
                break
        else:
            if level >= 4:
                coefficients = (2, 0.1, 1, 0.1, 3, 0)
                objectives.append(GRID_MJ * sum(c * d for c, d in zip(coefficients, sequence, strict=True)))
    return min(objectives), len(objectives)


def run_policy(actual: tuple[Sector, ...], fixed: tuple[float, ...] | None) -> dict:
    """Feed only current realization and still-nominal future opportunities."""
    state = INITIAL_MJ
    trace = []
    for i, sector in enumerate(actual):
        runtime = None
        if fixed is None:
            transition, runtime = feedback_step(BATTERY, state, sector, NOMINAL[i + 1 :])
        else:
            lo, hi = sector.bounds(BATTERY)
            action = min(hi, BATTERY.capacity_mj - state, max(lo, -state, fixed[i]))
            transition = advance(BATTERY, state, sector, action)
        trace.append(
            {
                "sector": i + 1,
                "prior_charge_mj": state,
                **asdict(transition),
                "solve_seconds": runtime,
            }
        )
        state = transition.charge_mj
    return {
        "trace": trace,
        "terminal_charge_mj": state,
        "terminal_feasible": state >= BATTERY.terminal_minimum_mj - EPS,
        "time_delta_s": sum(step["time_delta_s"] for step in trace),
    }


def evaluate() -> tuple[dict, dict]:
    actions = allocate(BATTERY, INITIAL_MJ, NOMINAL)
    nominal = run_policy(NOMINAL, actions)
    stationary = run_policy(NOMINAL, (0.0,) * len(NOMINAL))
    oracle_time, oracle_count = grid_oracle()
    feasible_rejection = False
    try:
        allocate(BATTERY, 0.0, (NOMINAL[-1],))
    except InfeasibleEnergyPlan:
        feasible_rejection = True
    nominal_feedback = run_policy(NOMINAL, None)
    disturbed_feedback = run_policy(DISTURBED, None)
    disturbed_fixed = run_policy(DISTURBED, actions)
    full_knowledge = run_policy(DISTURBED, allocate(BATTERY, INITIAL_MJ, DISTURBED))
    maximum_runtime = max(
        step["solve_seconds"] for policy in (nominal_feedback, disturbed_feedback) for step in policy["trace"]
    )
    checks = {
        "r043": {
            "grid_objective_agreement": abs(nominal["time_delta_s"] - oracle_time) <= EPS,
            "terminal_bound": nominal["terminal_feasible"],
            "strict_gain_over_zero": nominal["time_delta_s"] < stationary["time_delta_s"],
            "infeasible_target_rejected": feasible_rejection,
        },
        "r044": {
            "nominal_matches_plan": abs(nominal_feedback["time_delta_s"] - nominal["time_delta_s"]) <= EPS,
            "nominal_terminal_bound": nominal_feedback["terminal_feasible"],
            "disturbed_terminal_bound": disturbed_feedback["terminal_feasible"],
            "fixed_policy_misses_terminal": not disturbed_fixed["terminal_feasible"],
            "disturbance_hidden_at_first_action": (
                disturbed_feedback["trace"][0]["storage_delta_mj"]
                == nominal_feedback["trace"][0]["storage_delta_mj"]
            ),
            "solve_runtime": maximum_runtime <= RUNTIME_LIMIT_S,
        },
    }
    summary = {
        "schema_version": VERSION,
        "evidence_domain": "SIMULATED",
        "grid_terminal_feasible_paths": oracle_count,
        "grid_optimum_time_delta_s": oracle_time,
        "nominal_time_delta_s": nominal["time_delta_s"],
        "disturbed_feedback_time_delta_s": disturbed_feedback["time_delta_s"],
        "disturbed_feedback_terminal_mj": disturbed_feedback["terminal_charge_mj"],
        "disturbed_open_loop_terminal_mj": disturbed_fixed["terminal_charge_mj"],
        "disturbed_full_information_time_delta_s": full_knowledge["time_delta_s"],
        "maximum_feedback_solve_seconds": maximum_runtime,
        "checks": checks,
        "passed": all(all(group.values()) for group in checks.values()),
        "production_promotion": False,
    }
    return summary, {
        "fixture": {
            "battery": asdict(BATTERY),
            "initial_mj": INITIAL_MJ,
            "nominal": [asdict(s) for s in NOMINAL],
            "disturbed": [asdict(s) for s in DISTURBED],
            "grid_mj": GRID_MJ,
            "runtime_limit_s": RUNTIME_LIMIT_S,
        },
        "nominal": nominal,
        "zero": stationary,
        "nominal_feedback": nominal_feedback,
        "disturbed_feedback": disturbed_feedback,
        "disturbed_open_loop": disturbed_fixed,
        "disturbed_full_information": full_knowledge,
    }


def run_study(output: Path) -> dict:
    """Write sealed evidence from the deterministic fixture and timed controller."""
    output.mkdir(parents=True, exist_ok=False)
    summary, paths = evaluate()
    write_manifest(output / "trajectories.json", paths)
    return finish_run(output, VERSION, summary)
