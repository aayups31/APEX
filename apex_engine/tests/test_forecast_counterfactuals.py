import numpy as np
import pytest

from apexsim.research.forecast_counterfactuals import (
    IDENTITY_INDEX,
    SCENARIOS,
    TrainingEnvelope,
    audit_counterfactual,
    build_catalogue,
    counterfactual_result,
    history_violations,
    proxy_energies,
    robust_counterfactual_result,
    scenario_cost,
    transform_history,
    unprojected_loads,
)
from apexsim.research.forecast_explanations import FrozenForecastPredictor


def physical_history():
    """Declared simulated constant-curvature, accelerating history; all SI."""
    x = np.zeros((8, 14), np.float32)
    x[:, 0] = np.arange(8)*.5+40
    x[:, 1], x[:, 3], x[:, 6], x[:, 8], x[:, 9] = .5, 2., .05, .25, .1
    x[:, 7] = x[:, 0]
    x[:, 4] = -x[:, 0]*x[:, 6]
    x[:, 5] = np.arctan(3.6*x[:, 6]/x[:, 7])
    x[:, 10:] = proxy_energies(x)
    return x


def broad_envelope():
    return TrainingEnvelope(np.full(14, -10000.), np.full(14, 10000.))


def test_hand_coupled_scaling_preserves_curvature_and_recomputes_past_energy():
    x = physical_history()
    assert history_violations(x) == []
    changed = transform_history(x, .9, -.1)
    assert changed[-1, 0] == pytest.approx(39.15)
    assert changed[-1, 3] == pytest.approx(1.8)
    assert changed[-1, 4] == pytest.approx(-43.5*.05*.81)
    np.testing.assert_allclose(changed[:, 6]/changed[:, 7], x[:, 6]/x[:, 7])
    np.testing.assert_array_equal(changed[:, [2, 5, 8, 9]], x[:, [2, 5, 8, 9]])
    np.testing.assert_allclose(changed[:, 10:], proxy_energies(changed), rtol=5e-5)
    assert history_violations(changed) == []
    assert np.all(changed[:, 10:] < x[:, 10:])
    np.testing.assert_array_equal(transform_history(x, 1., 0.), x)
    # Static900kg weight splits total8829N. No hidden normal-load projection.
    zero_accel = x.copy()
    zero_accel[:, 3:5] = 0
    np.testing.assert_allclose(unprojected_loads(zero_accel)[0], [2030.67, 2030.67, 2383.83, 2383.83])


@pytest.mark.parametrize(("column", "value", "reason"), [
    (0, 106., "speed"), (1, 1.1, "throttle"), (2, .5, "brake_boolean"),
    (3, 31., "longitudinal_accel"), (4, 61., "lateral_accel"),
    (5, .7, "steering"), (6, 1.6, "heading_rate"),
    (7, 0., "geometry_speed"), (8, .51, "dt"), (9, -.1, "position_lag"),
    (10, -1., "negative_energy"),
])
def test_bounds_are_rejected_without_clipping(column, value, reason):
    x = physical_history()
    x[3, column] = value
    assert reason in history_violations(x)
    catalogue = build_catalogue(x, broad_envelope())
    assert not catalogue.valid.any()
    assert reason in catalogue.source_violations


def test_dependent_features_and_wheel_load_cannot_be_edited_independently():
    for col, reason in [(4, "lateral_equation"), (5, "steering_equation"), (10, "past_energy_equation")]:
        x = physical_history()
        x[2, col] += .1
        assert reason in history_violations(x)
    x = physical_history()
    x[:, 3] = 29.
    x[:, 4] = 50.
    assert "unprojected_wheel_load" in history_violations(x)
    with pytest.raises(ValueError, match="no clipping"):
        transform_history(physical_history(), 1., .6)


def test_training_marginal_support_and_source_abstention():
    x = physical_history()
    support = TrainingEnvelope(x.min(axis=0).astype(float), x.max(axis=0).astype(float))
    assert history_violations(x, support) == []
    changed = transform_history(x, .9, 0.)
    assert "training_marginal_support" in history_violations(changed, support)
    catalogue = build_catalogue(changed, support)
    report = counterfactual_result(catalogue, np.zeros((55, 3, 4)), np.ones((3, 4)))
    assert report["status"] == "ABSTAIN_SOURCE_CONSTRAINT_OR_SUPPORT"
    assert report["selected_index"] is None


def test_exact_finite_catalogue_oracle_minimality_and_deterministic_tie_break():
    catalogue = build_catalogue(physical_history(), broad_envelope())
    assert catalogue.valid.all() and len(SCENARIOS) == 55
    raw = np.array([np.full((3, 4), factor) for factor, _ in SCENARIOS])
    result = counterfactual_result(catalogue, raw, np.ones((3, 4)))
    selected = result["selected_index"]
    assert SCENARIOS[selected] == (.9, 0.)
    assert result["cost"] == pytest.approx(.5)
    assert result["crossing_margin_kj_by_seed"][0] == pytest.approx(0)
    assert result["speed_only_index"] == selected and result["throttle_only_index"] is None
    assert result["physical_realizability"] == "UNKNOWN"
    with pytest.raises(ValueError, match="optimality audit"):
        audit_counterfactual(catalogue, raw[None], np.ones((1, 3, 4)), SCENARIOS.index((.8, 0.)))
    # Equal-cost crossing candidates use (factor,offset), never iteration accident.
    raw.fill(1.)
    a, b = SCENARIOS.index((.9, 0.)), SCENARIOS.index((1., -.1))
    raw[[a, b]] = .8
    result = counterfactual_result(catalogue, raw, np.ones((3, 4)))
    assert result["selected_index"] == min([a, b], key=lambda i: (scenario_cost(i), *SCENARIOS[i]))
    assert result["selected_index"] == a


def test_seed_robust_crossing_cannot_hide_a_failing_seed_in_ensemble_mean():
    catalogue = build_catalogue(physical_history(), broad_envelope())
    raw = np.ones((2, 55, 3, 4))
    raw[0, SCENARIOS.index((.95, 0.))] = .1
    raw[:, SCENARIOS.index((.8, 0.))] = .8
    result = robust_counterfactual_result(catalogue, raw, np.ones((2, 3, 4)))
    assert SCENARIOS[result["selected_index"]] == (.8, 0.)
    raw.fill(1.)
    assert robust_counterfactual_result(catalogue, raw, np.ones((2, 3, 4)))["status"] == "ABSTAIN_NO_FEASIBLE_CROSSING"


def test_zero_baseline_and_nonfinite_predictions_abstain_or_fail_explicitly():
    catalogue = build_catalogue(physical_history(), broad_envelope())
    result = counterfactual_result(catalogue, np.zeros((55, 3, 4)), np.zeros((3, 4)))
    assert result["selected_index"] is None
    with pytest.raises(ValueError, match="finite counterfactual"):
        counterfactual_result(catalogue, np.full((55, 3, 4), np.nan), np.ones((3, 4)))
    assert history_violations(np.full((8, 14), np.inf)) == ["nonfinite_or_shape"]


def test_persistence_loaded_predictor_never_receives_future_target():
    predictor = FrozenForecastPredictor(None, {"kind": "persistence"}, None,
                                       {"driver_id": ["UNKNOWN"], "compound": ["UNKNOWN"], "track_id": ["UNKNOWN"]})
    x = physical_history()
    raw = predictor(x[None], np.ones((1, 3)))
    np.testing.assert_array_equal(raw[0, 0], x[-1, 10:])
    np.testing.assert_array_equal(raw[:, 0], raw[:, 2])
    assert IDENTITY_INDEX == 27
