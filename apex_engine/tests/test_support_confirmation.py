from types import SimpleNamespace

import numpy as np
import pytest

from apexsim.examples.support_confirmation import ConfirmationController, cohort
from apexsim.research.support_fallback import RuntimeController


def test_confirmation_preserves_raw_fault_amplitude(monkeypatch):
    def observed_row(self, state, track, profile, station, lateral, previous, index, nominal, row, log):
        return row[2] + 10*self.envelope["half_range"][2]*self.envelope["cutoff"]

    monkeypatch.setattr(RuntimeController, "__call__", observed_row)
    envelope = {"half_range": [1.]*8, "cutoff": 2.}
    controller = ConfirmationController("guarded", "feature_shift", envelope, {}, 1.25)
    row = np.zeros(8)
    args = (None, SimpleNamespace(length_m=100.), None, 125., 0., 0., 0, None, row, {})
    assert controller(*args) == pytest.approx(12.5)
    np.testing.assert_array_equal(row, np.zeros(8))


def test_confirmation_rejects_wrong_session_before_reading_rows(tmp_path, monkeypatch):
    monkeypatch.setattr("apexsim.examples.support_confirmation.verify_openf1_archive",
                        lambda archive: {"query": {"session_key": 9983}})
    with pytest.raises(ValueError, match="2025 Monza"):
        cohort(tmp_path)
