import pandas as pd

from apexsim.research.game_validation import (
    GAME_REQUIRED_COLUMNS,
    align_engine_and_game,
    comparison_metrics,
    validate_game_evidence,
)


def _frame():
    rows = []
    for i in range(5):
        rows.append({
            "session_id": "TEST", "lap": 1, "time_s": i * 0.05, "distance_m": i * 4.0,
            "speed_mps": 80.0 + i, "throttle": 0.8, "brake": 0.0, "steering": 0.1,
            "gear": 7, "engine_rpm": 11000.0, "fuel_kg": 50.0 - 0.02 * i,
            "ers_store_mj": 3.0, "ers_deploy_mj_s": 0.4, "tyre_compound": "MEDIUM",
            "tyre_age_laps": 2, "tyre_temp_fl_c": 95.0, "tyre_temp_fr_c": 96.0,
            "tyre_temp_rl_c": 93.0, "tyre_temp_rr_c": 94.0, "surface_type": "TRACK",
            "track_state": "GREEN", "in_pit": False,
        })
    return pd.DataFrame(rows, columns=GAME_REQUIRED_COLUMNS)


def test_future_game_contract_and_alignment():
    game = _frame()
    report = validate_game_evidence(game)
    assert report.passed
    engine = game[["session_id", "lap", "time_s", "speed_mps"]].copy()
    engine["time_s"] += 0.01
    engine["speed_mps"] += 1.0
    aligned = align_engine_and_game(game, engine, value_columns=["speed_mps"], tolerance_s=0.02)
    assert aligned.coverage == 1.0
    metrics = comparison_metrics(aligned.frame, ["speed_mps"])
    assert metrics["speed_mps_mae"] == 1.0
