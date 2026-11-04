from pathlib import Path
from runpy import run_path

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from apexsim.research.compound_crossover_head import crossover, event_features, fit_event, predict_event


def window(index=0):
    return dict(session=9912, driver=index, stints=[1, 2], ages=list(range(2, 14)),
                compounds=["MEDIUM", "HARD"], current_prefix_s=[90., 90.1, 90.2],
                reference_target_s=[91., 91.1, 91.2], prefix_s=-.3+.1*index,
                pairwise_prefix_s=-.35+.1*index, actual_s=.4, pairwise_actual_s=.45,
                forecast_at_s=200., reference_end_s=100.)


def test_event_score_hand_calculation_bounds_and_causality():
    model = {"mean": [0.]*10, "scale": [1.]*10, "coefficients": [0.]*10,
             "intercept": 0., "threshold": .5}
    row = window()
    assert predict_event(model, row) == {"crossover_score": .5, "predicted_crossover": True}
    changed = {**row, "actual_s": -10., "pairwise_actual_s": -20., "current_target_s": [1000.]*3}
    assert predict_event(model, row) == predict_event(model, changed)
    assert predict_event({**model, "intercept": 1000.}, row)["crossover_score"] == 1.
    assert predict_event({**model, "intercept": -1000.}, row)["crossover_score"] == 0.
    with pytest.raises(ValueError, match="unavailable"):
        predict_event(model, {**row, "reference_end_s": 201.})


def test_plain_json_event_inference_matches_library_classifier():
    rows = [window(i) for i in range(8)]
    saved = fit_event(rows)
    x = np.asarray([event_features(r) for r in rows for _ in range(2)])
    y = [int(crossover(r[p], r[t])) for r in rows for p, t in
         (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s"))]
    scaler = StandardScaler().fit(x)
    classifier = LogisticRegression(C=.1, class_weight="balanced", max_iter=1000).fit(
        scaler.transform(x), y, sample_weight=np.full(len(x), .5))
    expected = classifier.predict_proba(scaler.transform([event_features(r) for r in rows]))[:, 1]
    assert [predict_event(saved, r)["crossover_score"] for r in rows] == pytest.approx(expected, abs=1e-12)


def test_event_gate_reports_decision_separately_from_point_forecast(monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    score = run_path(str(scripts/"confirm_compound_event.py"))["score_heads"]
    row = dict(prefix_s=-.3, pairwise_prefix_s=-.3, actual_s=.2, pairwise_actual_s=.2,
               predicted_s=-.1, reference_persistence_s=-.3, prior_prediction_s=-.3,
               lower_s=-.5, upper_s=.5, predicted_crossover=True)
    result = score([row])
    assert result["passed"] and result["matched"] == 1 and result["point_matched"] == 0
    assert result["event_point_disagreements"] == 1
