from copy import deepcopy

import numpy as np
import pytest

from apexsim.research.compound_bounded import (
    bounded_features,
    causal_weather,
    cross_event_radius,
    fit_bounded,
    predict_bounded,
    training_weights,
)


def window(event=0, driver=0, compound="HARD"):
    return dict(session=event, driver=driver, stints=[1, 2], ages=list(range(2, 14)),
                compounds=["SOFT" if compound != "SOFT" else "HARD", compound],
                current_prefix_s=[90., 90.1, 90.2], current_target_s=[90.4, 90.5, 90.6],
                reference_target_s=[91., 91.1, 91.2], prefix_s=-.2,
                actual_s=.6, pairwise_prefix_s=-.3, pairwise_actual_s=.7,
                reference_end_s=100., forecast_at_s=200.)


def corpus():
    return [window(e, d, c) for e in range(4) for d, c in enumerate(("SOFT", "MEDIUM", "HARD"))]


def test_bounded_hand_calculation_caps_influence_and_keeps_future_targets_out():
    row = window()
    model = fit_bounded(corpus())
    model["coefficients"] = [2.]+[0.]*6
    model["radius_s"] = .4
    result = predict_bounded(model, row)
    assert result["baseline_s"] == pytest.approx(1.)
    assert result["raw_correction_s"] == 2.
    assert result["applied_correction_s"] == .25
    assert result["predicted_s"] == pytest.approx(1.25)
    assert result["lower_s"] == pytest.approx(.85)
    assert result["correction_bounded"] and not result["fallback"]
    altered = {**row, "actual_s": 1000., "pairwise_actual_s": -1000., "current_target_s": [2000.]*3}
    assert predict_bounded(model, altered) == result
    model["coefficients"][0] = -2.
    assert predict_bounded(model, row)["predicted_s"] == pytest.approx(.75)


def test_support_exit_uses_declared_baseline_and_reports_case():
    model = fit_bounded(corpus(), baseline="midpoint")
    row = {**window(), "current_prefix_s": [92., 92.1, 92.2]}
    result = predict_bounded(model, row)
    assert result["fallback"] and result["applied_correction_s"] == 0.
    assert result["predicted_s"] == pytest.approx(-.6)
    assert result["fallback_reasons"] == ["OUTSIDE_TRAINING_FEATURE_RANGE"]
    model["support"]["HARD"]["events"] = 2
    assert predict_bounded(model, window())["fallback_reasons"] == ["FEWER_THAN_THREE_COMPOUND_EVENTS"]


def test_event_weighting_and_duplicate_targets_are_invariant_and_conflicts_fail():
    rows = corpus()
    duplicates = [{**r, "stints": [0, 2]} for r in rows]
    weights = training_weights(rows+duplicates)
    assert weights.sum() == pytest.approx(len(rows))
    model, repeated = fit_bounded(rows), fit_bounded(rows+duplicates)
    for key in ("mean", "scale", "coefficients"):
        assert model[key] == pytest.approx(repeated[key])
    corrupted = deepcopy(duplicates)
    corrupted[0]["current_target_s"][0] += 1.
    with pytest.raises(ValueError, match="Conflicting"):
        fit_bounded(rows+corrupted)
    # An event with more targets still carries the same total fit weight.
    unbalanced = rows+[window(0, d) for d in range(10, 20)]
    weights = training_weights(unbalanced)
    totals = [sum(w for r, w in zip(unbalanced, weights, strict=True) if r["session"] == e) for e in range(4)]
    assert totals == pytest.approx([totals[0]]*4)


def test_weather_join_is_backward_stale_explicit_and_future_mutation_invariant():
    samples = [dict(at_s=10., track_temperature_c=30.), dict(at_s=190., track_temperature_c=32.),
               dict(at_s=210., track_temperature_c=100.)]
    context = causal_weather(samples, 200.)
    assert context == dict(weather_at_s=190., track_temperature_c=32., track_change_c=2.)
    samples[-1]["track_temperature_c"] = -9999.
    assert causal_weather(samples, 200.) == context
    assert causal_weather(samples, 500.)["track_temperature_c"] is None
    assert causal_weather([], 200.)["weather_at_s"] is None
    assert causal_weather([dict(at_s=190., track_temperature_c=None)], 200.)["track_temperature_c"] is None


def test_context_rejects_future_stale_or_duplicate_contributors():
    row = window()
    row["context"] = {**causal_weather([dict(at_s=190., track_temperature_c=32.)], 200.),
                      "field_windows": [dict(driver=1, stint=1, available_at_s=199., change_s=.3)]}
    assert bounded_features(row, "context")[-1] == .3
    for mutation, message in (({"weather_at_s": 201.}, "Weather"),
                              ({"weather_at_s": 0.}, "Weather"),
                              ({"field_windows": [dict(driver=1, stint=1, available_at_s=201., change_s=.3)]}, "Field"),
                              ({"field_windows": row["context"]["field_windows"]*2}, "Duplicate")):
        altered = {**row, "context": {**row["context"], **mutation}}
        with pytest.raises(ValueError, match=message):
            bounded_features(altered, "context")


@pytest.mark.parametrize("mutation", [dict(ages=list(range(1, 12))), dict(reference_end_s=201.),
                                      dict(current_prefix_s=[np.nan]*3), dict(prefix_s=np.inf)])
def test_invalid_horizon_clock_or_numbers_fail_closed(mutation):
    with pytest.raises(ValueError):
        predict_bounded(fit_bounded(corpus()), {**window(), **mutation})


def test_cross_event_radius_is_finite_rank_and_never_training_residuals():
    assert cross_event_radius(list(range(10)), .8) == 8.
    assert cross_event_radius([.3, .1, .2]) == .3
    with pytest.raises(ValueError):
        cross_event_radius([np.nan])
