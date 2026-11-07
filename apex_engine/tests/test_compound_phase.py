import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_fuel_sensitivity_reconstructs_original_targets_and_phase_only_uses_prefix(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    audit = importlib.import_module("audit_compound_fuel_sensitivity")
    study = importlib.import_module("diagnose_compound_phase")
    fuel = study.read_json(study.FOLDER / "compound-v17-fuel-sensitivity.json")
    data = study.read_json(study.FOLDER / "compound-v11-development-data.json")
    for row, item in zip(data["cases"], fuel["cases"], strict=True):
        for coeff, expected in zip(fuel["coefficients_s_per_kg"], item["sensitivity"], strict=True):
            found = audit.reconstruct(item["windows"], coeff)
            assert found["target_s"] == pytest.approx(expected["target_s"])
            assert found["observed"] == expected["observed"]
        first = study.phase_features(row, item["windows"][:2])
        assert study.phase_features({**row, "current_target_s": [999] * 3}, item["windows"][:2]) == first
    with pytest.raises(ValueError, match="Unavailable"):
        study.phase_features({**row, "forecast_at_s": 0}, item["windows"][:2])


def test_phase_refit_and_both_forecast_gates_replay(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    study = importlib.import_module("diagnose_compound_phase")
    audit = importlib.import_module("audit_compound_race_context")
    data = study.read_json(study.FOLDER / "compound-v11-development-data.json")
    saved = study.read_json(study.FOLDER / "compound-v18-development.json")
    audit.check_result(data, saved)
    actual = study.study()
    for found, expected in zip(actual["feedback"], saved["feedback"], strict=True):
        assert found["peer_windows"] == expected["peer_windows"]
        assert found["shift_s"] == pytest.approx(expected["shift_s"], rel=0, abs=1e-9)
    for name in ("phase_only", "result"):
        assert actual[name]["failed_events"] == saved[name]["failed_events"]
        for found, expected in zip(actual[name]["predictions"], saved[name]["predictions"], strict=True):
            assert found["crossings"] == expected["crossings"]
            assert found["laps_s"] == pytest.approx(expected["laps_s"], rel=0, abs=1e-9)
