import importlib
from copy import deepcopy
from pathlib import Path

import pytest
from test_compound_trajectory import example

from apexsim.research.evidence import seal


def test_backward_history_stops_at_gaps_and_cannot_consume_future(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"research/scripts"))
    builder = importlib.import_module("prepare_compound_trajectory")
    row = example()
    field = [dict(driver=4, stint=i, compound=c, values={p["age"]: p["pace_s"] for p in observations},
                  ends={p["age"]: p["end_s"] for p in observations})
             for i, c, observations in ((1, "MEDIUM", row["reference_history"]), (2, "HARD", row["current_history"]))]
    field[1]["values"][8] = 999.
    field[1]["ends"][8] = 208.
    before = builder.attach(row, field)
    assert before == row
    field[1]["values"][8] = -999.
    assert builder.attach(row, field) == before
    del field[1]["values"][4]
    assert len(builder.attach(row, field)["current_history"]) == 3


def test_whole_event_fit_isolation_scalar_reload_and_tamper(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"research/scripts"))
    study = importlib.import_module("diagnose_compound_trajectory")
    auditor = importlib.import_module("audit_compound_trajectory")
    rows = [example(e, d) for e in range(4) for d in range(4)]
    data = seal({"cases": rows, "sources": {str(e): {} for e in range(4)}})
    recipes = [("full_boost", "full", "boost"), ("full_ridge", "full", "ridge")]
    result = study.compare(data, recipes=recipes)
    assert auditor.audit(data, result)["forecasts_audited"] == 32
    changed_rows = deepcopy(rows)
    for row in changed_rows:
        if row["session"] == 0:
            row.update(actual_s=999., pairwise_actual_s=999., current_target_s=[999.]*3)
    changed = study.compare(seal({"cases": changed_rows, "sources": data["sources"]}), recipes=recipes)
    for name, _, _ in recipes:
        assert result["recipes"][name]["predictions"][:4] == changed["recipes"][name]["predictions"][:4]
    corrupt = deepcopy(result)
    corrupt["recipes"]["full_boost"]["predictions"][0]["predicted_s"] += .1
    corrupt = seal({k: v for k, v in corrupt.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="prediction"):
        auditor.audit(data, corrupt)
