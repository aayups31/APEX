import importlib
from pathlib import Path

import pytest


@pytest.fixture
def sectors(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "research/scripts"))
    return importlib.import_module("compound_sectors")


def test_sector_inputs_use_only_complete_known_splits(sectors):
    row = {
        "driver": 4,
        "forecast_at_s": 9,
        "current_history": [{"end_s": t} for t in (7, 8, 9)],
        "reference_history": [{"end_s": t} for t in range(1, 7)],
        "current_target_s": [70, 71, 72],
    }
    records = {(4, t): sectors.sector_record(90, [30, 30, 30]) for t in range(1, 10)}
    records[4, 9] = sectors.sector_record(90, [36, 27, 27])
    records[4, 2] = sectors.sector_record(90, [30, 30, None])
    assert sectors.sector_record(90, [30, 30, 29.9]) is None
    inputs = sectors.link(row, records)
    x = sectors.sector_vector(inputs)
    assert x[:4] == pytest.approx([1 / 15, -1 / 30, 0, 0])
    assert x[-3:] == [1, 0, 1]
    assert sectors.link({**row, "current_target_s": [999] * 3}, records) == inputs
    with pytest.raises(ValueError, match="Future"):
        sectors.link({**row, "forecast_at_s": 8}, records)


def test_saved_sector_study_replays_forecasts_and_gates(sectors):
    folder = sectors.FOLDER
    data = sectors.read_json(folder / "compound-v11-development-data.json")
    observed = sectors.read_json(folder / "compound-v22-sector-data.json")
    saved = sectors.read_json(folder / "compound-v22-development.json")
    sectors.check_seal(saved)
    replay = sectors.study(data, observed)
    assert replay["implementation_sha256_lf"] == saved["implementation_sha256_lf"]
    assert replay["result"]["failed_events"] == saved["result"]["failed_events"]
    for actual, expected in zip(replay["result"]["predictions"], saved["result"]["predictions"], strict=True):
        assert actual["crossings"] == expected["crossings"]
        assert actual["laps_s"] == pytest.approx(expected["laps_s"], abs=1e-9, rel=0)
