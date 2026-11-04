import gzip
import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from apexsim.research.evidence import seal


def test_nested_repair_selection_and_intervals_exclude_outer_labels(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"research/scripts"))
    study = importlib.import_module("diagnose_compound_repair")
    auditor = importlib.import_module("audit_compound_repair")
    rows = [dict(session=e, driver=4, stints=[1, 2], ages=list(range(2, 14)), compounds=["MEDIUM", "HARD"],
                 current_prefix_s=[90., 90.1, 90.2], reference_target_s=[90.5, 90.6, 90.7],
                 current_target_s=[89.8, 89.9, 90.], prefix_s=-.3, pairwise_prefix_s=-.3, actual_s=.7, pairwise_actual_s=.7,
                 reference_end_s=100., forecast_at_s=200., context={"field_windows": [
                     dict(driver=d, stint=1, available_at_s=190., change_s=-.2) for d in (1, 2, 3)]}) for e in range(4)]
    settings = [dict(shrinkage=w, minimum_drivers=3, decision_margin_s=.15, bound_s=.5) for w in (0., 1.)]
    data = seal({"cases": rows, "sources": {str(e): {} for e in (2, 0, 3, 1)}})
    result = study.compare(data, settings=settings, comparators=False)
    assert study.compare(json.loads(json.dumps(data, sort_keys=True)), settings=settings, comparators=False) == result
    assert auditor.audit(data, result)["cases_audited"] == 4
    modified = deepcopy(rows)
    modified[0].update(actual_s=99., pairwise_actual_s=99., current_target_s=[999.]*3)
    changed = study.compare(seal({"cases": modified}), settings=settings, comparators=False)
    first = result["nested_predictions"][0]
    other = changed["nested_predictions"][0]
    for key in ("predicted_s", "lower_s", "upper_s", "predicted_crossover"):
        assert first[key] == other[key]
    assert result["nested_selections"][0]["setting"] == changed["nested_selections"][0]["setting"]
    corrupted = deepcopy(result)
    corrupted["nested_predictions"][0]["predicted_s"] += .1
    corrupted = seal({k: v for k, v in corrupted.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="nested_predictions"):
        auditor.audit(data, corrupted)
    assert not result["candidate_accepted"] and not result["production_promotion"]


def test_saved_repair_artifacts_preserve_every_failed_event_and_scalar_forecast(monkeypatch):
    from apexsim.provenance import file_sha256
    from apexsim.research.evidence import check_seal, read_json

    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/"research/scripts"))
    auditor = importlib.import_module("audit_compound_repair")
    folder = root/"docs/verification"
    data = read_json(folder/"compound-v10-development-data.json")
    summary = read_json(folder/"compound-v10-development-summary.json")
    check_seal(summary)
    compressed = folder/"compound-v10-development.json.gz"
    assert file_sha256(compressed) == summary["compressed_file_sha256"]
    result = json.loads(gzip.decompress(compressed.read_bytes()))
    receipt = auditor.audit(data, result)
    assert receipt["audit_passed"] and receipt["cases_audited"] == 392
    assert receipt["outer_events_audited"] == 24 and not receipt["development_qualified"]
    assert len(summary["readiness"]["failed_supported_events"]) == 13
    assert not summary["readiness"]["new_holdout_acquisition_allowed"]
