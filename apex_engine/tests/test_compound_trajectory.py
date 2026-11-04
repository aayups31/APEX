from copy import deepcopy
from statistics import median

import pytest

from apexsim.research.compound_bounded import training_weights
from apexsim.research.compound_trajectory import (
    fit_trajectory,
    predict_trajectory,
    robust_line,
    trajectory_features,
    validate_history,
)


def example(event=0, driver=4):
    current = [dict(age=a, pace_s=90.+a*.1, end_s=200.+a) for a in range(1, 8)]
    reference = [dict(age=a, pace_s=91.+a*.05, end_s=100.+a) for a in range(5, 17)]
    prefix = [p["pace_s"] for p in current[-3:]]
    target = [91.4, 91.5, 91.6]
    ref_prefix, ref_target = [p["pace_s"] for p in reference[:3]], [p["pace_s"] for p in reference[-3:]]
    return dict(session=event, driver=driver, stints=[1, 2], compounds=["MEDIUM", "HARD"], ages=list(range(5, 17)),
                reference_end_s=116., forecast_at_s=207., reference_target_s=ref_target,
                current_prefix_s=prefix, current_target_s=target,
                prefix_s=median(ref_prefix)-median(prefix), actual_s=median(ref_target)-median(target),
                pairwise_prefix_s=median(a-b for a, b in zip(ref_prefix, prefix, strict=True)),
                pairwise_actual_s=median(a-b for a, b in zip(ref_target, target, strict=True)),
                current_history=current, reference_history=reference, context={})


def test_hand_calculated_line_and_horizon_features():
    row = example()
    slope, spread = robust_line(row["current_history"])
    assert slope == pytest.approx(.1) and spread == pytest.approx(0.)
    features = trajectory_features(row)
    assert features[6:] == pytest.approx([5., 7., .9, .9, .9, 0., .2, .45, 0., .45])
    changed = deepcopy(row["current_history"])
    changed[3]["pace_s"] += 50.
    assert robust_line(changed)[0] == pytest.approx(.1)


@pytest.mark.parametrize("fault", ["future", "gap", "duplicate", "nan", "clock", "prefix", "reference", "bool", "overflow"])
def test_trajectory_rejects_invalid_history(fault):
    row = example()
    if fault == "future":
        row["current_history"][0]["end_s"] = 999.
    elif fault == "gap":
        del row["current_history"][1]
    elif fault == "duplicate":
        row["current_history"][0]["age"] = 2
    elif fault == "nan":
        row["reference_history"][1]["pace_s"] = float("nan")
    elif fault == "clock":
        row["current_history"][-1]["end_s"] -= .1
    elif fault == "prefix":
        row["current_history"][-1]["pace_s"] += .1
    elif fault == "reference":
        row["reference_history"][-1]["end_s"] -= .1
    elif fault == "bool":
        row["current_history"][0]["age"] = True
    else:
        row["current_history"][0]["pace_s"] = 1e308
        row["current_history"][1]["pace_s"] = 1e308
        row["current_history"][2]["pace_s"] = 1e308
    with pytest.raises(ValueError):
        trajectory_features(row)


def test_model_ignores_future_targets_and_reports_fallback():
    train = [example(e, d) for e in range(4) for d in range(20)]
    row = example(99)
    model = fit_trajectory(train)
    before = predict_trajectory(model, row)
    changed = {**row, "current_target_s": [999.]*3, "actual_s": -999., "pairwise_actual_s": 999.}
    assert predict_trajectory(model, changed) == before
    assert before["raw_correction_s"] == pytest.approx(-.9)
    model["support"]["HARD"] = 2
    fallback = predict_trajectory(model, row)
    assert fallback["fallback"] and fallback["predicted_s"] == fallback["reference_persistence_s"]


def test_training_weights_do_not_inflate_repeated_target_mass():
    train = [example(e, d) for e in range(4) for d in range(3)]
    original = training_weights(train)
    repeated = training_weights([*train, deepcopy(train[0])])
    assert repeated[0]+repeated[-1] == pytest.approx(original[0])
    assert repeated[1:-1] == pytest.approx(original[1:])


def test_no_fractional_age_or_reversed_clock_passes_validation():
    row = example()
    row["current_history"][0]["age"] = .5
    with pytest.raises(ValueError):
        validate_history(row)
    row = example()
    row["current_history"][0]["end_s"] = 202.5
    with pytest.raises(ValueError, match="clocks"):
        validate_history(row)
