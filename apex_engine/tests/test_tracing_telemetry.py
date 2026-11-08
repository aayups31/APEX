from copy import deepcopy

import numpy as np
import pytest

from apexsim.research.tracing_telemetry import associate_lap, export_samples, processed_features, utc_seconds


def document():
    return {
        "tel": {
            "dataKey": "known",
            "time": [0, 1, 2],
            "speed": [36, 72, 108],
            "throttle": [0, 50, 100],
            "brake": [0, 1, 0],
            "drs": [0, 1, 0],
        }
    }


def test_processed_units_and_drs_distinguish_export_from_native_code_one():
    samples = export_samples(document(), "known")
    assert samples[:, 1].tolist() == [10, 20, 30]
    assert samples[:, 2].tolist() == [0, 0.5, 1]
    assert samples[:, 4].tolist() == [0, 12, 0]
    doc = document()
    doc["tel"]["brake"] = [0, 100, 0]
    np.testing.assert_array_equal(export_samples(doc, "known"), samples)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dataKey", "wrong"),
        ("time", [0, 1, 1]),
        ("time", [0, float("nan"), 2]),
        ("time", [-1, 0, 1]),
        ("speed", [36]),
        ("drs", [0, 8, 12]),
        ("brake", [0, 1, 100]),
    ],
)
def test_processed_payload_rejects_corrupt_identity_time_and_schema(field, value):
    doc = document()
    doc["tel"][field] = value
    with pytest.raises(ValueError):
        export_samples(doc, "known")


def metadata():
    return {
        "lap": [10],
        "dNum": ["4"],
        "compound": ["HARD"],
        "stint": [2],
        "life": [5],
        "lSD": ["2025-01-01T00:00:00"],
        "time": [90.0],
    }


def bind(meta, **changes):
    values = {
        "lap": 10,
        "driver": 4,
        "compound": "HARD",
        "stint": 2,
        "age": 5,
        "start_s": utc_seconds("2025-01-01T00:00:00Z"),
        "duration_s": 90.0,
        "cutoff_s": utc_seconds("2025-01-01T00:02:00Z"),
    }
    return associate_lap(meta, **{**values, **changes})


def test_processed_clock_and_identity_tolerances_are_explicit():
    assert bind(metadata())["clock_error_s"] == 0
    assert utc_seconds("2025-01-01T00:00:00") == utc_seconds("2024-12-31T19:00:00-05:00")
    for field, value in (
        ("driver", 5),
        ("age", 6),
        ("stint", 1),
        ("compound", "SOFT"),
        ("start_s", 0),
        ("duration_s", 89.9),
    ):
        with pytest.raises(ValueError):
            bind(metadata(), **{field: value})
    with pytest.raises(ValueError, match="buffer"):
        bind(metadata(), cutoff_s=utc_seconds("2025-01-01T00:01:59Z"))
    meta = metadata()
    meta["lap"] = [10, 10]
    with pytest.raises(ValueError, match="duplicate"):
        bind(meta)


def test_processed_features_keep_missing_groups_explicit_and_use_two_laps():
    groups = [[{"coverage": 0.95, "means": [10 + i + j, 0.5, 0, 0.1, 1]} for j in range(2)] for i in range(3)]
    x = processed_features(groups)
    assert len(x) == 23
    assert x[:5] == [10.5, 0.5, 0, 0.1, 1]
    assert x[5:10] == [1, 0, 0, 0, 0]
    assert x[10:15] == [-1, 0, 0, 0, 0]
    changed = deepcopy(groups)
    changed[0][0]["coverage"] = 0.89
    assert processed_features(changed) == [0.0] * 20 + [0.0, 1.0, 1.0]
    changed = deepcopy(groups)
    changed[1][0]["coverage"] = 0.89
    assert processed_features(changed)[10:15] == [0.0] * 5
    with pytest.raises(ValueError):
        processed_features([*groups, groups[0]])
