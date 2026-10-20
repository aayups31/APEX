"""R029 v2 source support and mathematical controls, independent of public outcomes."""
import numpy as np
import pytest
from test_reference_geometry import native_fixture

from apexsim.research.position_laps import extract_position_lap


def test_native_gaps_are_explicit_without_adding_or_replacing_vertices():
    laps, positions, selection = native_fixture()
    broken = positions.drop(index=range(40, 48)).reset_index(drop=True)
    with pytest.raises(ValueError, match="gaps"):
        extract_position_lap(laps, broken, selection)
    trace = extract_position_lap(laps, broken, selection, allow_interior_gaps=True)
    assert len(trace["xy_m"]) == 394  # 400 original native rows -8, plus two anchors.
    assert (~trace["interval_supported"]).sum() == 1
    gap = trace["metadata"]["unsupported_intervals"][0]
    assert (gap["start_s"], gap["end_s"], gap["gap_s"]) == (9.75, 12., 2.25)
    np.testing.assert_array_equal(trace["time_s"][1:-1], broken.SessionTime.dt.total_seconds().to_numpy()[1:393])
    assert "lower-bound" in trace["metadata"]["chord_phase_truth"]


def test_gap_mode_never_relaxes_boundary_or_native_status_rules():
    laps, positions, selection = native_fixture()
    with pytest.raises(ValueError, match="boundary bracket"):
        extract_position_lap(laps, positions.iloc[1:].reset_index(drop=True), selection, allow_interior_gaps=True)
    positions.loc[20, "Status"] = "OffTrack"
    with pytest.raises(ValueError, match="supported native"):
        extract_position_lap(laps, positions, selection, allow_interior_gaps=True)
