from copy import deepcopy

import pytest

from apexsim.research.compound_adaptive import predict_adaptive
from apexsim.research.compound_readiness import assess_panel


def case(event=1, driver=4):
    return dict(session=event, driver=driver, stints=[1, 2], ages=list(range(2, 14)),
                compounds=["MEDIUM", "HARD"], current_prefix_s=[90., 90.1, 90.2],
                reference_target_s=[90.5, 90.6, 90.7], current_target_s=[89.8, 89.9, 90.],
                prefix_s=-.3, pairwise_prefix_s=-.3, actual_s=.7, pairwise_actual_s=.7,
                reference_end_s=100., forecast_at_s=200., context={"field_windows": [
                    dict(driver=d, stint=1, available_at_s=190., change_s=v) for d, v in ((1, -.2), (2, -.3), (3, -.4))]})


def test_adaptive_hand_calculation_equal_driver_support_and_future_targets():
    row = case()
    result = predict_adaptive(row)
    assert result["field_drift_s"] == -.3
    assert result["predicted_s"] == pytest.approx(.8)
    assert result["predicted_crossover"] and not result["fallback"]
    row["context"]["field_windows"] += [dict(driver=1, stint=i, available_at_s=180., change_s=-.2) for i in range(2, 8)]
    assert predict_adaptive(row) == result
    changed = {**row, "actual_s": 999., "pairwise_actual_s": -999., "current_target_s": [999.]*3}
    assert predict_adaptive(changed) == result


def test_self_contributors_do_not_count_and_fallback_stays_in_panel():
    row = case()
    row["context"]["field_windows"][0]["driver"] = row["driver"]
    result = predict_adaptive(row)
    assert result["fallback"] and result["field_drivers"] == 2
    assert result["excluded_self_windows"] == 1
    assert result["predicted_s"] == pytest.approx(.5)
    panel = assess_panel([{**row, **result}], [1, 2])
    assert panel["events"][0]["fallback_cases"] == 1
    assert panel["unsupported_events"] == ["2"] and not panel["development_qualified"]


def test_correction_bound_and_both_prefix_event_agreement():
    row = case()
    for w in row["context"]["field_windows"]:
        w["change_s"] = -5.
    result = predict_adaptive(row, radius_s=.2)
    assert result["raw_correction_s"] == 5. and result["applied_correction_s"] == .5
    assert result["correction_bounded"] and result["lower_s"] == pytest.approx(.8)
    assert not predict_adaptive({**row, "pairwise_prefix_s": .3})["predicted_crossover"]


@pytest.mark.parametrize("alteration", [dict(prefix_s=float('nan')), dict(reference_end_s=201.),
                                       dict(ages=list(range(1, 12))), dict(compounds=["HARD", "HARD"]),
                                       dict(current_prefix_s=[True]*3), dict(current_prefix_s=["90"]*3)])
def test_invalid_forecast_inputs_fail_closed(alteration):
    with pytest.raises(ValueError):
        predict_adaptive({**case(), **alteration})


def test_invalid_or_future_field_observations_fail_and_future_weather_is_unused():
    row = case()
    result = predict_adaptive(row)
    row["context"]["future_weather"] = {"at_s": 9999., "temperature": -999.}
    assert predict_adaptive(row) == result
    for change in ({"available_at_s": 201.}, {"change_s": float("inf")}):
        altered = deepcopy(row)
        altered["context"]["field_windows"][0].update(change)
        with pytest.raises(ValueError):
            predict_adaptive(altered)
    row["context"]["field_windows"] *= 2
    with pytest.raises(ValueError, match="Duplicate"):
        predict_adaptive(row)


def test_strict_readiness_cannot_hide_failed_race_in_pooled_success():
    rows = [{**case(e), **predict_adaptive(case(e))} for e in (1, 2)]
    assert assess_panel(rows, [1, 2])["development_qualified"]
    # Nine correct positive cases cannot hide one failed zero-event control.
    rows += [{**case(3, d), **predict_adaptive(case(3, d))} for d in range(10, 19)]
    bad = {**case(4), **predict_adaptive(case(4)), "actual_s": -.4, "pairwise_actual_s": -.4}
    failed = assess_panel([*rows, bad], [1, 2, 3, 4])
    assert failed["failed_supported_events"] == ["4"] and not failed["new_holdout_acquisition_allowed"]
    assert "FALSE_ALARM_ON_NEGATIVE_CONTROL" in failed["events"][-1]["failure_codes"]
    assert "PACE_WORSE_THAN_CONTRAST" in failed["events"][-1]["failure_codes"]
    with pytest.raises(ValueError, match="Duplicate comparison"):
        assess_panel(rows+rows[:1], [1, 2, 3])


def test_nonfinite_intermediate_arithmetic_cannot_be_hidden_by_bounding():
    row = case()
    row["context"]["field_windows"] = [dict(driver=d, stint=1, available_at_s=190., change_s=1e308) for d in (1, 2)]
    with pytest.raises(ValueError, match="field aggregation"):
        predict_adaptive(row, minimum_drivers=1)
    valid = {**case(), **predict_adaptive(case())}
    with pytest.raises(ValueError, match="error arithmetic"):
        assess_panel([{**valid, "predicted_s": 1e308, "actual_s": -1e308}], [1])
