import numpy as np
import pandas as pd

from apexsim.research.tyre_forecasting import (
    RidgeTyreEnergyForecaster,
    TrackStateEncoding,
    build_tyre_energy_windows,
    make_event_split,
    rmse,
    subset_by_events,
    temporal_permutation_importance,
)


def _frame() -> pd.DataFrame:
    rows = []
    for event_i in range(5):
        for t in range(12):
            speed = 40 + event_i + t
            steering = np.sin(t / 3)
            rows.append(
                {
                    "event_id": f"E{event_i}",
                    "time_s": t * 0.1,
                    "speed": speed,
                    "steering": steering,
                    "track_state": "GREEN" if t < 10 else "YELLOW",
                    "tyre_energy_front_left_kj": 0.2 * speed + abs(steering),
                    "tyre_energy_front_right_kj": 0.2 * speed + 0.8 * abs(steering),
                    "tyre_energy_rear_left_kj": 0.25 * speed + abs(steering),
                    "tyre_energy_rear_right_kj": 0.25 * speed + 0.8 * abs(steering),
                }
            )
    return pd.DataFrame(rows)


def test_windows_do_not_cross_events_and_split_is_disjoint():
    data = build_tyre_energy_windows(
        _frame(),
        feature_columns=["speed", "steering", "track_state"],
        window=4,
        encoding=TrackStateEncoding.ONE_HOT,
    )
    assert data.x.shape[1] == 4
    assert data.y.shape[1] == 4
    split = make_event_split(data.event_ids, seed=3)
    split.validate()
    assert len(subset_by_events(data, split.train_events).x) > 0


def test_ridge_baseline_and_temporal_importance_run():
    data = build_tyre_energy_windows(
        _frame(),
        feature_columns=["speed", "steering"],
        window=3,
        encoding=TrackStateEncoding.EXCLUDE,
    )
    model = RidgeTyreEnergyForecaster(alpha=0.01).fit(data.x, data.y)
    pred = model.predict(data.x)
    assert rmse(data.y, pred) < 0.2
    importance = temporal_permutation_importance(model.predict, data.x, data.y, data.feature_names)
    assert set(importance.feature) == {"speed", "steering"}
