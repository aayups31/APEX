import importlib
from copy import deepcopy
from pathlib import Path

import pytest

from apexsim.research.evidence import read_json

ROOT = Path(__file__).resolve().parents[2]


def test_extra_windows_cannot_bridge_gaps_or_overlap_paired_ages(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    data = importlib.import_module("compound_unpaired_windows")
    stint = {
        "driver": 1,
        "stint": 2,
        "compound": "HARD",
        "values": {age: 90.0 + age / 10 for age in range(1, 38)},
        "ends": {age: 100.0 + age for age in range(1, 38)},
    }
    rows = data.additional("example", stint, set(range(1, 13)))
    assert [r["ages"] for r in rows] == [list(range(13, 25)), list(range(25, 37))]
    del stint["values"][20]
    assert data.additional("example", stint, set(range(1, 13)))[0]["ages"] == list(range(21, 33))
    stint["ends"][21] = 1000.0
    with pytest.raises(ValueError, match="Unordered"):
        data.additional("example", stint, set(range(1, 13)))


def test_unpaired_outer_fold_excludes_all_its_training_targets(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    study = importlib.import_module("diagnose_compound_unpaired")
    source = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    events = sorted({str(r["session"]) for r in source["cases"]})[:4]
    cases = [r for r in source["cases"] if str(r["session"]) in events]
    sources = [
        s
        for name in ("compound-nomination-inventory.json", "compound-v13-nomination-additions.json")
        for s in read_json(ROOT / "docs/verification" / name)["sources"]
    ]
    nominations = study.inventory(sources, set(source["sources"]))
    nominations = {e: nominations[e] for e in events}
    base = {i: {"event": str(r["session"]), "laps_s": r["current_prefix_s"]} for i, r in enumerate(cases)}
    pool = study.unique_rows(cases)
    original = study.evaluate(pool, cases, nominations, base)
    modified = deepcopy(pool)
    for r in modified:
        if r["session"] == events[0]:
            r["current_target_s"] = [999.0] * 3
    changed = study.evaluate(modified, cases, nominations, base)
    assert original["models"][events[0]] == changed["models"][events[0]]
    assert [p for p in original["predictions"] if p["event"] == events[0]] == [
        p for p in changed["predictions"] if p["event"] == events[0]
    ]


def test_saved_expansion_has_no_shared_ages_and_keeps_all_case_denominators(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    study = importlib.import_module("diagnose_compound_unpaired")
    original = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    extra = read_json(ROOT / "docs/verification/compound-v14-training-windows.json")
    windows = {}
    for r in study.unique_rows(original["cases"]):
        windows.setdefault((r["session"], r["driver"], r["stints"][1]), set()).update(r["ages"])
    for r in extra["additional_windows"]:
        occupied = windows.setdefault((r["session"], r["driver"], r["stints"][1]), set())
        assert not occupied.intersection(r["ages"])
        occupied.update(r["ages"])
        assert r["target_end_s"] > r["forecast_at_s"]
    assert len(extra["additional_windows"]) == sum(extra["additional_by_source"].values())
