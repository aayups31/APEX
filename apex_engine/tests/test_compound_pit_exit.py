import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def scripts(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "research/scripts"))
    return tuple(
        importlib.import_module(name)
        for name in (
            "prepare_compound_pit_exit",
            "prepare_compound_pit_exit_telemetry",
            "diagnose_compound_pit_exit",
        )
    )


def test_pit_exit_shift_preserves_native_boundaries_and_prior(scripts):
    cohort, _, _ = scripts
    laps = [
        {
            "driver_number": 4,
            "lap_number": n,
            "is_pit_out_lap": flag,
            "date_start": f"2025-06-15T18:{n}:00+00:00",
        }
        for n, flag in [(29, False), (30, True), (31, False), (48, True)]
    ]
    stint = {
        "driver_number": 4,
        "stint_number": 2,
        "lap_start": 29,
        "lap_end": 47,
        "tyre_age_at_start": 2,
        "compound": "MEDIUM",
    }
    tables = {"laps": laps, "stints": [stint]}
    rebuilt, _, shifts, _ = cohort.reanchor(tables)
    independent, expected = cohort.independent_tables(tables)
    assert shifts == {(4, 2): 1}
    assert expected == {(4, 2)}
    assert rebuilt == independent
    assert rebuilt["stints"][0] == {**stint, "tyre_age_at_start": 1}
    assert tables["stints"][0]["tyre_age_at_start"] == 2
    assert rebuilt["laps"] == laps


def test_pit_exit_does_not_apply_uncertain_or_nonadjacent_flags(scripts):
    cohort, _, _ = scripts
    previous = {"is_pit_out_lap": False, "date_start": "2025-06-15T18:29:00+00:00"}
    exit_lap = {"is_pit_out_lap": True, "date_start": "2025-06-15T18:30:00+00:00"}
    stint = {"lap_start": 29, "lap_end": 47}
    assert cohort.delayed_exit(stint, {29: previous, 30: exit_lap})
    assert not cohort.delayed_exit(stint, {29: previous, 31: exit_lap})
    assert not cohort.delayed_exit(stint, {29: exit_lap, 30: previous})
    assert not cohort.delayed_exit(stint, {30: exit_lap})
    assert not cohort.delayed_exit(stint, {29: previous, 30: {**exit_lap, "date_start": None}})
    assert not cohort.delayed_exit({**stint, "lap_end": 29}, {29: previous, 30: exit_lap})


def test_native_snapshot_bounds_compare_absolute_query_times(scripts):
    _, telemetry, _ = scripts
    query = {
        "session_key": 9963,
        "driver_number": 4,
        "date>": "2025-06-15T14:04:30.822999-04:00",
        "date<": "2025-06-15T15:08:25.776-04:00",
    }
    start = telemetry.timestamp("2025-06-15T18:04:30.823+00:00")
    end = telemetry.timestamp("2025-06-15T19:08:25.776+00:00")
    assert telemetry.covers(query, "9963", 4, start, end)
    assert not telemetry.covers(query, "9963", 4, start - 1, end)
    assert not telemetry.covers(query, "9963", 4, start, end + 1)
    assert not telemetry.covers(query, "9963", 14, start, end)


def test_huber_fit_bounds_the_influence_of_an_outlier(scripts):
    _, _, model = scripts
    design = np.ones((5, 1))
    offsets = np.zeros((5, 3))
    offsets[-1] = [30.0, 0.0, -30.0]
    fitted = model.solve_huber(design, offsets, np.ones(5))
    assert fitted[:, 0] == pytest.approx([0.1125, 0, -0.1125], abs=1e-7)
