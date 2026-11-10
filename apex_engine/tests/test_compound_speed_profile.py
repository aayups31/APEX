import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def scripts(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "research/scripts"))
    return (
        importlib.import_module("compound_speed_profile"),
        importlib.import_module("audit_compound_pit_exit_residuals"),
    )


def test_distance_alignment_uses_only_samples_inside_the_native_lap(scripts):
    speed, _ = scripts
    clock = np.arange(-0.5, 25.5, 0.25)
    values = np.where((clock >= 0) & (clock < 25), 50.0, np.nan)
    samples = np.column_stack((clock, values))
    native = speed.native_profile(samples, 0, 25)
    independent = speed.scalar_profile(samples, 0, 25)
    assert native == independent == (1250.0, [50.0] * 64)
    gapped = samples[(clock < 5) | (clock > 8)]
    assert speed.native_profile(gapped, 0, 25) is None
    assert speed.scalar_profile(gapped, 0, 25) is None


def test_slow_and_fast_bins_are_chosen_from_completed_reference(scripts):
    speed, _ = scripts
    reference = (1250, [30.0] * 16 + [50.0] * 32 + [70.0] * 16)
    current = (1250, [33.0] * 16 + [50.0] * 32 + [66.0] * 16)
    groups = [[reference, current, current], [reference] * 3, [reference] * 3]
    result = speed.speed_groups(groups)
    assert result == speed.independent_groups(groups)
    assert (
        speed.profile_vector(result) == speed.scalar_vector(result) == [3.0, -4.0, 3.0, -4.0, 3.0, -4.0, 1.0]
    )
    groups[0][0] = (1300, reference[1])
    assert speed.speed_groups(groups) is None
    assert speed.independent_groups(groups) is None
    assert speed.profile_vector(None) == [0.0] * 7


def test_fuel_sensitivity_detects_crossing_only_inside_the_range(scripts):
    _, fuel = scripts

    def laps(first, duration):
        return [(n, duration, duration - 0.03 * fuel.mass(n)) for n in range(first, first + 3)]

    groups = [laps(5, 81.13), laps(25, 80), laps(14, 80.55), laps(34, 80)]
    assert fuel.reconstruct(groups, 0.02)["observed"] == [False, False]
    assert fuel.reconstruct(groups, 0.03)["observed"] == [True, True]
    assert fuel.reconstruct(groups, 0.04)["observed"] == [False, False]
    assert fuel.stable_labels(groups) == [False, False]
