import importlib
from pathlib import Path

import pytest


@pytest.fixture
def traffic(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "research/scripts"))
    return importlib.import_module("compound_sector_traffic")


def test_prior_crossings_exclude_ties_self_and_unfinished_peer(traffic):
    stream = [(98.0, 2, 159.0), (98.5, 3, 165.0), (99.0, 1, 160.0), (100.0, 4, 160.0)]
    assert traffic.previous_car(stream, 1, 100.0, 160.0) == [98.0, 2, 159.0]
    assert traffic.previous_car(stream, 1, 100.0, 158.0) is None


def test_saved_traffic_forecasts_replay_and_check_all_clocks(traffic):
    data, control, base = traffic.load_sources()
    saved = traffic.read_json(traffic.FOLDER / "compound-v30-development.json")
    traffic.check_seal(saved)
    replay = traffic.study(data, control, base, saved["links"])
    compare = importlib.import_module("audit_compound_repair").compare
    for key in ("result", "finish_only", "coverage", "source_sha256_lf", "protocol_sha256_lf"):
        compare(replay[key], saved[key], key)
    assert saved["dataset_sha256"] == data["content_sha256"]
    assert saved["control_sha256"] == control["content_sha256"]
    row = data["cases"][0]
    groups = saved["links"][0]
    stamp = groups[0][0][0][0]
    groups[0][0][0][1] = [stamp - 1, row["driver"], stamp - 1]
    with pytest.raises(ValueError, match="Ineligible"):
        traffic.feature_vectors(row, groups)
