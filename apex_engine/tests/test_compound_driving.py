import importlib
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def driving(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    return importlib.import_module("compound_driving_data")


def test_driving_summary_integrates_measured_time_without_future_or_tail_fill(driving):
    samples = np.array(
        [
            [0.0, 10, 0.0, 0, 0],
            [0.25, 20, 0.5, 1, 10],
            [1.0, 30, 1.0, 0, 12],
            [1.5, 40, 0.0, 0, 8],
            [2.2, 50, 0.9, 1, 0],
        ]
    )
    result = driving.lap_summary(samples, 0.0, 2.5)
    assert result["samples"] == 5
    assert result["coverage"] == pytest.approx(2.2 / 2.5)
    assert result["means"] == pytest.approx(
        [
            (10 * 0.25 + 20 * 0.75 + 30 * 0.5 + 40 * 0.7) / 2.2,
            (0.5 * 0.75 + 1.0 * 0.5) / 2.2,
            0.75 / 2.2,
            (0.25 + 0.7) / 2.2,
            (0.75 + 0.5) / 2.2,
        ]
    )
    future = np.array([[2.5, 120, 0, 1, 14], [3.0, 0, 1, 0, 0]])
    assert driving.lap_summary(np.vstack((samples, future)), 0.0, 2.5) == result


def test_driving_summary_drops_invalid_neighbors_and_large_gaps(driving):
    samples = np.array(
        [
            [0.0, 10, 1, 0, 0],
            [0.5, 20, 1, 0, 0],
            [1.0, np.nan, 1, 0, 0],
            [2.5, 30, 1, 0, 0],
            [3.0, 40, 1, 0, 0],
            [3.5, 50, 1, 0, 0],
        ]
    )
    result = driving.lap_summary(samples, 0, 4)
    assert result["coverage"] == pytest.approx(1.5 / 4)
    assert result["means"] == pytest.approx([(10 + 30 + 40) / 3, 1, 0, 0, 0])
    for values in (np.empty((0, 5)), samples[:1]):
        assert driving.lap_summary(values, 0, 4)["coverage"] == 0
        assert driving.lap_summary(values, 0, 4)["means"] == [0] * 5


@pytest.mark.parametrize("column,bad", [(1, -1), (1, 121), (2, 1.01), (3, 0.5), (4, 99)])
def test_driving_summary_rejects_bad_channels_through_explicit_zero_coverage(driving, column, bad):
    samples = np.array([[0, 30, 0.5, 0, 0], [0.5, 30, 0.5, 0, 0]], dtype=float)
    samples[0, column] = bad
    assert driving.lap_summary(samples, 0, 1)["coverage"] == 0


def test_driving_clocks_must_be_ordered_and_distinct(driving):
    samples = np.array([[0, 30, 0.5, 0, 0], [0, 30, 0.5, 0, 0]], dtype=float)
    with pytest.raises(ValueError, match="Unordered or duplicate"):
        driving.lap_summary(samples, 0, 1)
    samples[1, 0] = -0.5
    with pytest.raises(ValueError, match="Unordered or duplicate"):
        driving.lap_summary(samples, -1, 1)
    for start, end in [(1, 1), (2, 1), (float("nan"), 1)]:
        with pytest.raises(ValueError, match="lap clocks"):
            driving.lap_summary(samples, start, end)


def test_openf1_native_controls_are_converted_and_bound_to_driver_session(driving):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    records = [
        {
            "session_key": 9912,
            "driver_number": 4,
            "date": (start + timedelta(seconds=i)).isoformat(),
            "speed": 108,
            "throttle": 50,
            "brake": brake,
            "drs": 10,
        }
        for i, brake in enumerate((0, 100))
    ]
    matrix = driving.sample_matrix(records, "9912", 4)
    assert matrix[:, 1:] == pytest.approx(np.array([[30, 0.5, 0, 10], [30, 0.5, 1, 10]]))
    assert matrix[:, 0] == pytest.approx([start.timestamp(), start.timestamp() + 1])
    with pytest.raises(ValueError, match="identity mismatch"):
        driving.sample_matrix(records, "9912", 5)
    with pytest.raises(ValueError, match="identity mismatch"):
        driving.sample_matrix(records, "9913", 4)
    with pytest.raises(ValueError, match="telemetry clock"):
        driving.sample_matrix(records[::-1], "9912", 4)
    with pytest.raises(ValueError, match="telemetry clock"):
        driving.sample_matrix([records[0], records[0]], "9912", 4)
    invalid = driving.sample_matrix([{**records[0], "brake": 1, "throttle": None}], "9912", 4)
    assert np.isnan(invalid[0, 2:4]).all()


def test_driving_features_preserve_support_masks_and_hand_arithmetic(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    features = importlib.import_module("diagnose_compound_driving").driving_features
    scales = np.array([1.0, 0.1, 0.05, 1 / 30, 0.025])
    groups = [
        [{"coverage": 0.9, "means": (value * scales).tolist(), "samples": 100} for value in values]
        for values in ([1.0, 2.0, 6.0], [0.0, 1.0, 2.0], [4.0, 5.0, 6.0])
    ]
    found = features(groups)
    assert len(found) == 23
    assert found == pytest.approx(
        [*(3 * scales), *(5 * scales), *(2 * scales), *(-2 * scales), 1.0, 1.0, 1.0]
    )
    missing = deepcopy(groups)
    missing[1][0]["coverage"] = 0.899
    missing[1][0]["means"] = [119.0, 1.0, 1.0, 1.0, 1.0]
    assert features(missing) == pytest.approx(
        [*(3 * scales), *(5 * scales), *([0.0] * 5), *(-2 * scales), 1.0, 0.0, 1.0]
    )
    missing[0][0]["coverage"] = 0
    assert features(missing) == pytest.approx([0.0] * 20 + [0.0, 0.0, 1.0])
    before = features(groups)
    case = {"current_target_s": [90.0, 90.0, 90.0], "groups": groups}
    case["current_target_s"] = [999.0] * 3
    assert features(case["groups"]) == before


@pytest.mark.parametrize("status,body", [(401, b'{"detail":"Authentication required"}\n'), (200, b" [ ] \n")])
def test_car_snapshot_keeps_exact_http_bytes_and_reuses_verified_receipt(driving, tmp_path, status, body):
    from hashlib import sha256

    class Client:
        calls = 0

        def get(self, endpoint, query):
            assert endpoint == "car_data" and query == {"session_key": 9912, "driver_number": 4}
            self.calls += 1
            assert self.calls == 1
            return body, {"status_code": status}

    client = Client()
    query = {"session_key": 9912, "driver_number": 4}
    raw = tmp_path / f"{sha256(body).hexdigest()}.json"
    if status == 401:
        with pytest.raises(ValueError, match="HTTP 401"):
            driving.car_snapshot(tmp_path, "9912", 4, query, client)
        assert raw.read_bytes() == body
        with pytest.raises(ValueError, match="HTTP 401"):
            driving.car_snapshot(tmp_path, "9912", 4, query, client)
        with pytest.raises(ValueError, match="HTTP 401"):
            driving.car_snapshot(tmp_path, "9912", 4, query, None)
    else:
        records, binding = driving.car_snapshot(tmp_path, "9912", 4, query, client)
        assert records == [] and raw.read_bytes() == body
        assert driving.car_snapshot(tmp_path, "9912", 4, query, None) == (records, binding)
    assert client.calls == 1
    with pytest.raises(ValueError, match="query or raw path"):
        driving.car_snapshot(tmp_path, "9912", 4, {**query, "driver_number": 5}, None)
    raw.write_bytes(body + b" ")
    with pytest.raises(ValueError, match="raw body changed"):
        driving.car_snapshot(tmp_path, "9912", 4, query, None)
