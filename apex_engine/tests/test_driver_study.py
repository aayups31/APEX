import numpy as np
import pytest

from apexsim.examples.driver_study import calibration_scores, refinement_metrics
from apexsim.research.driver_audit import compare_path
from apexsim.research.transparent_driver import DriverMap, simulate_driver


def circle():
    theta = np.arange(256)*2*np.pi/256
    return DriverMap(2*np.pi*60, np.column_stack([60*np.cos(theta), 60*np.sin(theta)]),
                     np.column_stack([-np.sin(theta), np.cos(theta)]), np.full(256, 1/60))


def test_selection_is_validation_only_and_test_labels_are_refused():
    track = circle()
    rows, targets = [], {}
    for event, role in (("F1_2023_R01", "train"), ("F1_2024_R01", "validation")):
        for driver in ("4", "44"):
            key = event+driver
            rows.append({"event_id": event, "role": role, "driver_id": driver, "lap_id": key, "track_id": "bahrain", "matched_rows": 20})
            targets[key+"_station_m"] = np.arange(20)*10.
            targets[key+"_speed_mps"] = np.full(20, 30.)
    scores = calibration_scores({"bahrain": track}, rows, targets)
    changed = {k: (v+50 if "2023" in k and k.endswith("speed_mps") else v) for k, v in targets.items()}
    assert calibration_scores({"bahrain": track}, rows, changed)["selected"] == scores["selected"]
    assert not scores["test_outcomes_used"] and len(scores["candidates"]) == 9
    assert scores["selected"]["maximum_mps"] == 60  # exact tie chooses slower maximum
    with pytest.raises(ValueError, match="forbids test"):
        calibration_scores({"bahrain": track}, [dict(rows[0], event_id="F1_2024_R16", role="test")], {})


def test_refinement_and_independent_error_gates_cannot_accept_missing_or_drifting_lap():
    track = circle()
    t = {"station_m": np.array([0., track.length_m]), "states": np.array([[0., 0, 0, 10, 0, 0], [1., 0, 0, 10, 0, 0]])}
    good = {"completed": True, "completion_time_s": 40.}
    assert refinement_metrics(track, t, t, good, good)["passed"]
    assert not refinement_metrics(track, t, t, good, {"completed": False})["passed"]
    shifted = dict(t, states=t["states"]+np.array([.6, 0, 0, 0, 0, 0]))
    assert not refinement_metrics(track, t, shifted, good, good)["passed"]
    assert not compare_path(t["states"], shifted["states"])["passed"]


def test_synthetic_numeric_refinement():
    track = circle()
    result, nominal = simulate_driver(track, (.35, 60.), 15.)
    refined_result, refined = simulate_driver(track, (.35, 60.), 15., max_step=.01)
    assert result["passed"] and refined_result["passed"]
    assert refinement_metrics(track, nominal, refined, result, refined_result)["passed"]
