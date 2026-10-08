import itertools
import json
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

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

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "research/fixtures/fieni-hand-transition-v1.json").read_text())


def fixture_model():
    return PaperStrategyModel(
        PaperStrategyParameters(**FIXTURE["parameters"]),
        {TyreCompound(k): TireWearCoefficients(**v) for k, v in FIXTURE["wear"].items()},
        {TyreCompound(k): TireTimeLossCoefficients(**v) for k, v in FIXTURE["time_loss"].items()},
    )


def state_from(values):
    return PaperStrategyState(**{**values, "compound": TyreCompound(values["compound"])})


def action_from(values):
    return PaperStrategyAction(**{**values, "pit_compound": TyreCompound(values["pit_compound"]) if values["pit_compound"] else None})


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["id"])
def test_frozen_hand_calculated_transitions(case):
    model = fixture_model()
    original = state_from(case["state"])
    next_state, info = model.transition(original, action_from(case["action"]))
    for field, expected in case["expected"].items():
        actual = getattr(next_state, field)
        if type(expected) in (int, float):
            assert actual == pytest.approx(expected, abs=1e-9, rel=0)
        else:
            assert actual == expected
    for field, expected in case["expected_info"].items():
        assert getattr(info, field) == (expected if type(expected) is bool else pytest.approx(expected, abs=1e-9, rel=0))
    if "expected_applied" in case:
        assert info.applied_action == action_from(case["expected_applied"])
        assert len(info.projection_reasons) == 2
    else:
        assert not info.projection_reasons
    assert original == state_from(case["state"])


def test_fixture_decimal_arithmetic_independent_of_transition():
    # No call to the engine: verify the frozen decimal expectations themselves.
    with localcontext() as ctx:
        ctx.prec = 40
        d = Decimal
        normal = FIXTURE["cases"][0]
        wear = d("1.1") * d(".1") + d(".01") * d(806) / d(808) + d(".02")
        lap = d(90) + d(".025") * d(6) + d(".5") * d("-.5") + d(2) * d(".1") + d(3) * d(".1")**2
        assert abs(wear - d(str(normal["expected"]["tyre_wear"]))) < d("1e-15")
        assert lap == d(str(normal["expected"]["last_lap_time_s"]))
        terminal = FIXTURE["cases"][-1]
        wear = d("1.05") * d(".2") + d(".005") * d(802) / d(808) + d(".01")
        assert abs(wear - d(str(terminal["expected"]["tyre_wear"]))) < d("1e-15")


@pytest.mark.parametrize("battery,expected", [(-1, .75), (0, -.25), (1, -1.25), (-2, .75), (2, -1.25)])
def test_normalized_affine_battery_map(battery, expected):
    action = fixture_model().action_from_normalized(.5, battery)
    assert action.fuel_energy_mj == 80
    assert action.battery_delta_mj == expected


def test_projection_intersects_capacity_input_and_next_state_reachability():
    model = fixture_model()
    state = model.initial_state()
    next_state, info = model.transition(state, PaperStrategyAction(88, .75))
    assert info.applied_action.battery_delta_mj == -.25
    assert next_state.battery_mj == 3.75
    assert next_state.fuel_energy_mj == 232
    assert info.projection_reasons == ("battery_input_capacity_or_reachability",)
    # Every extreme requested action produces a bounded, reachable transition.
    for fuel, battery in itertools.product((-1000, 72, 80, 88, 1000), (-1000, -1.25, 0, .75, 1000)):
        next_state, info = model.transition(state, PaperStrategyAction(fuel, battery))
        assert 72 <= info.applied_action.fuel_energy_mj <= 88
        assert -1.25 <= info.applied_action.battery_delta_mj <= .75
        model.validate_state(next_state)


@pytest.mark.parametrize("change", [
    {"battery_mj": 4}, {"fuel_energy_mj": 100, "car_mass_kg": 802.5},
    {"fuel_energy_mj": -1}, {"car_mass_kg": 900}, {"battery_mj": float("nan")},
    {"lap": 5}, {"race_time_s": -1}, {"tyre_wear": 2},
])
def test_invalid_or_unreachable_states_fail_without_projection(change):
    state = state_from(FIXTURE["cases"][-1]["state"])
    with pytest.raises(ValueError):
        fixture_model().transition(replace(state, **change), PaperStrategyAction(80, -.5))


def test_short_horizon_cannot_force_illegal_deployment_and_bad_actions_fail():
    with pytest.raises(ValueError, match="Initial battery"):
        PaperStrategyModel(PaperStrategyParameters(total_laps=3))
    model = fixture_model()
    with pytest.raises(ValueError, match="finite"):
        model.transition(model.initial_state(), PaperStrategyAction(float("nan"), 0))
    with pytest.raises(ValueError, match="pit_code"):
        model.action_from_normalized(.5, 0, True)
    bad = replace(state_from(FIXTURE["cases"][-1]["expected"]), battery_mj=-.01)
    assert not model.final_state_is_legal(bad)


def test_same_compound_pit_does_not_satisfy_change_and_wear_saturation_is_logged():
    model = fixture_model()
    state = state_from(FIXTURE["cases"][0]["state"])
    next_state, _ = model.transition(state, PaperStrategyAction(80, -.5, TyreCompound.SOFT))
    assert not next_state.compound_changed and next_state.tyre_wear == 0
    model.wear[TyreCompound.SOFT] = TireWearCoefficients(20, .01, .02)
    next_state, info = model.transition(state, PaperStrategyAction(80, -.5))
    assert next_state.tyre_wear == 1.25 and info.wear_clipped


@pytest.mark.parametrize("grid,expected_count", [
    ({"fuel_fractions": (1.,), "battery_deltas_mj": (-1.,), "pit_window": (1, 1)}, 4),
    ({"fuel_fractions": (.9, 1.1), "battery_deltas_mj": (-1., .5), "pit_window": (1, 1)}, 256),
])
def test_exact_enumeration_matches_lossless_beam_and_independent_cartesian_rollouts(grid, expected_count):
    model = PaperStrategyModel(PaperStrategyParameters(total_laps=3, initial_fuel_kg=6, battery_capacity_mj=3,
                                                       battery_delta_min_mj=-1))
    exact = ExactStrategyOracle(model, **grid).solve()
    beam = DiscreteStrategyOracle(model, **grid, beam_width=100_000, state_bucketing="exact")
    solution = beam.solve()
    assert exact.terminal_sequences == expected_count
    assert beam.last_search["exact_for_grid"]
    assert model.final_state_is_legal(exact.solution.state)
    assert solution.state.race_time_s == pytest.approx(exact.solution.state.race_time_s, rel=0, abs=1e-9)
    # Independent Cartesian traversal, not either solver's action generator/DFS.
    choices = []
    for lap in range(3):
        pits = (None, TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD) if lap == 1 else (None,)
        choices.append([PaperStrategyAction(model.p.nominal_fuel_energy_mj()*f, b, p)
                        for f, b, p in itertools.product(grid["fuel_fractions"], grid["battery_deltas_mj"], pits)])
    times = []
    for actions in itertools.product(*choices):
        states, _ = model.rollout(actions)
        if model.final_state_is_legal(states[-1]):
            times.append(states[-1].race_time_s)
    assert exact.legal_terminal_sequences == len(times)
    assert exact.solution.state.race_time_s == min(times)


def test_search_budget_and_infeasible_grid_never_return_partial_or_illegal_solution(monkeypatch):
    model = fixture_model()
    def unexpected(*args, **kwargs):
        pytest.fail("Budget must be checked before transitions")
    with monkeypatch.context() as patch:
        patch.setattr(model, "transition", unexpected)
        with pytest.raises(ValueError, match="no partial optimum"):
            ExactStrategyOracle(model, max_sequences=1).solve()
    grid = {"fuel_fractions": (1.,), "battery_deltas_mj": (-1.,), "pit_window": (10, 10)}
    with pytest.raises(RuntimeError, match="No legal terminal"):
        ExactStrategyOracle(model, **grid).solve()
    with pytest.raises(RuntimeError, match="no legal terminal"):
        DiscreteStrategyOracle(model, **grid).solve()


def test_finite_width_beam_cannot_claim_exactness():
    model = fixture_model()
    model.p = replace(model.p, require_compound_change=False)
    beam = DiscreteStrategyOracle(model, beam_width=1, state_bucketing="exact")
    assert model.final_state_is_legal(beam.solve().state)
    assert beam.last_search["width_pruned_states"] > 0
    assert not beam.last_search["exact_for_grid"]


def test_frozen_equation_and_symbol_map_is_complete():
    mapping = json.loads((ROOT / "research/equations/fieni-2025-v1.json").read_text())
    assert [r["equation"] for r in mapping["equations"]] == list(range(1, 71))
    assert set(mapping["parameter_units"]) == set(vars(PaperStrategyParameters()))
    assert mapping["paper_sha256"] == "fc609aa9dcff9179d5e6cba8ce96eb7785f8db45daeef2fc6c4aad32ad133270"
    assert all(r["status"] in {"MATCH", "ADAPTED", "SURROGATE", "OMITTED", "SOURCE_ANOMALY"} for r in mapping["equations"])
    assert all(r["notes"] and r["symbols"] and r["units"] for r in mapping["equations"])
    assert mapping["classification"] == "ADAPTATION"


def test_foundation_cli_artifacts_integrity_and_exclusive_output(tmp_path):
    from typer.testing import CliRunner

    from apexsim.cli import app
    from apexsim.provenance import file_sha256, payload_sha256

    output = tmp_path / "acceptance"
    result = CliRunner().invoke(app, ["strategy-foundation-demo", "--output", str(output)])
    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    assert summary["passed"] and summary["hand_fixtures"] == 5 and summary["max_fixture_error"] < 1e-9
    assert not summary["training_ready"] and summary["max_beam_regret_s"] < 1e-9
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["content_sha256"] == payload_sha256({k: v for k, v in manifest.items() if k != "content_sha256"})
    before = {p.name: file_sha256(p) for p in output.iterdir()}
    assert all(before[n] == record["sha256"] for n, record in manifest["files"].items())
    comparisons = json.loads((output / "comparisons.json").read_text())
    assert [c["terminal_sequences"] for c in comparisons] == [4, 256]
    assert all(not c["narrow_beam"]["exact_for_grid"] for c in comparisons)
    repeated = CliRunner().invoke(app, ["strategy-foundation-demo", "--output", str(output)])
    assert isinstance(repeated.exception, FileExistsError)
    assert before == {p.name: file_sha256(p) for p in output.iterdir()}
