"""Immutable synthetic acceptance run for FIENI equation/fixture/oracle gates."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import exact_strategy, fienia_strategy, strategy_env
from apexsim.research.exact_strategy import ExactStrategyOracle
from apexsim.research.fienia_strategy import (
    DiscreteStrategyOracle,
    PaperStrategyAction,
    PaperStrategyModel,
    PaperStrategyParameters,
    PaperStrategyState,
    TireTimeLossCoefficients,
    TireWearCoefficients,
)
from apexsim.sim_core.types import TyreCompound


def run_strategy_foundation_demo(output: Path) -> dict:
    """Validate frozen hand fixtures and exact tiny cases; never train on them."""
    if output.exists():
        raise FileExistsError(f"Strategy evidence output already exists: {output}")
    repository = Path(__file__).resolve().parents[4]
    inputs = [repository / "research/equations/fieni-2025-v1.json",
              repository / "research/fixtures/fieni-hand-transition-v1.json",
              repository / "research/user_provided_papers/learning-based-f1-strategies.pdf"]
    before = {p.relative_to(repository).as_posix(): file_sha256(p) for p in inputs}
    mapping, fixture = (json.loads(p.read_text()) for p in inputs[:2])
    if before[inputs[2].relative_to(repository).as_posix()] != mapping["paper_sha256"]:
        raise ValueError("Frozen FIENI paper hash does not match reviewed equation map")
    model = PaperStrategyModel(PaperStrategyParameters(**fixture["parameters"]),
                              {TyreCompound(k): TireWearCoefficients(**v) for k, v in fixture["wear"].items()},
                              {TyreCompound(k): TireTimeLossCoefficients(**v) for k, v in fixture["time_loss"].items()})
    checks = []
    for case in fixture["cases"]:
        state = PaperStrategyState(**{**case["state"], "compound": TyreCompound(case["state"]["compound"])})
        values = case["action"]
        action = PaperStrategyAction(**{**values, "pit_compound": TyreCompound(values["pit_compound"]) if values["pit_compound"] else None})
        next_state, info = model.transition(state, action)
        errors = []
        for actual, expected in ((asdict(next_state), case["expected"]), (asdict(info), case["expected_info"])):
            for field, value in expected.items():
                if type(value) in (int, float):
                    errors.append(abs(actual[field] - value))
                elif actual[field] != value:
                    raise ValueError(f"Fixture {case['id']} disagrees on {field}")
        error = max(errors)
        if error > fixture["tolerance"]:
            raise ValueError(f"Fixture {case['id']} error {error} exceeds declared tolerance")
        checks.append({"case": case["id"], "max_absolute_error": error,
                       "state": asdict(next_state), "transition": asdict(info)})
    comparisons = []
    for label, fuel, battery, expected_count in (
        ("single_energy_grid", (1.,), (-1.,), 4),
        ("asymmetric_projected_grid", (.9, 1.1), (-1., .5), 256),
    ):
        tiny = PaperStrategyModel(PaperStrategyParameters(total_laps=3, initial_fuel_kg=6, battery_capacity_mj=3,
                                                          battery_delta_min_mj=-1))
        grid = {"fuel_fractions": fuel, "battery_deltas_mj": battery, "pit_window": (1, 1)}
        exact = ExactStrategyOracle(tiny, **grid).solve()
        beam = DiscreteStrategyOracle(tiny, **grid, beam_width=100_000, state_bucketing="exact")
        result = beam.solve()
        regret = result.state.race_time_s - exact.solution.state.race_time_s
        if abs(regret) > 1e-9 or not beam.last_search["exact_for_grid"] or exact.terminal_sequences != expected_count:
            raise ValueError("Tiny exhaustive/beam comparison failed")
        # Replay applied actions to verify the saved best trajectory.
        states, _ = tiny.rollout(exact.solution.actions)
        if states[-1] != exact.solution.state or not tiny.final_state_is_legal(states[-1]):
            raise ValueError("Exact solution trajectory is not reproducible/legal")
        narrow = DiscreteStrategyOracle(tiny, **grid, beam_width=1, state_bucketing="exact")
        try:
            approximate = narrow.solve()
            narrow_report = {**narrow.last_search, "legal_solution": True,
                             "regret_s": approximate.state.race_time_s - exact.solution.state.race_time_s}
        except RuntimeError:
            narrow_report = {**narrow.last_search, "legal_solution": False, "abstained": True}
        comparisons.append({"case": label, "classification": "SIMULATED_FINITE_GRID",
                            "parameters": asdict(tiny.p), "grid": grid,
                            "terminal_sequences": exact.terminal_sequences,
                            "legal_terminal_sequences": exact.legal_terminal_sequences,
                            "transitions": exact.transitions,
                            "exact_race_time_s": exact.solution.state.race_time_s,
                            "beam_regret_s": regret, "beam_search": beam.last_search,
                            "narrow_beam": narrow_report,
                            "solution": {"state": asdict(exact.solution.state),
                                         "requested_actions": [asdict(a) for a in exact.requested_actions],
                                         "applied_actions": [asdict(a) for a in exact.solution.actions]},
                            "rollout": [asdict(s) for s in states]})
    if before != {p.relative_to(repository).as_posix(): file_sha256(p) for p in inputs}:
        raise ValueError("Frozen strategy inputs changed during acceptance run")
    summary = {"schema_version": "apex-fieni-foundation-run-v1", "classification": "ADAPTATION",
               "maturity": "R0", "passed": True, "training_ready": False,
               "reviewed_equation_numbers": len(mapping["equations"]),
               "hand_fixtures": len(checks), "max_fixture_error": max(c["max_absolute_error"] for c in checks),
               "exact_comparisons": len(comparisons), "max_beam_regret_s": max(abs(c["beam_regret_s"]) for c in comparisons),
               "input_sha256": before,
               "implementation_sha256": {m.__name__: file_sha256(Path(m.__file__)) for m in
                                          (fienia_strategy, exact_strategy, strategy_env)},
               "limitations": ["Synthetic coefficients and projected finite action grids only.",
                               "No continuous optimum, paper MINLP/SAC result or production maturity promotion.",
                               "Finite-width/coarse beam may lose optimum or all legal candidates."]}
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True, exist_ok=False)
    write_manifest(output / "fixtures.json", checks)
    write_manifest(output / "comparisons.json", comparisons)
    write_manifest(output / "summary.json", summary)
    manifest = {"schema_version": "apex-fieni-foundation-manifest-v1",
                "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size}
                          for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output / "manifest.json", manifest)
    return summary
