import importlib
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import seal


def test_prospective_panel_cannot_drop_a_failed_negative_control_and_audits_native(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = importlib.import_module("confirm_compound_bounded")
    auditor = importlib.import_module("audit_compound_bounded_confirmation")
    support = {c: dict(events=3, minimum=[-1e9]*6, maximum=[1e9]*6) for c in ("SOFT", "MEDIUM", "HARD")}
    frozen = seal({"hashes": study.hashes(), "heldout_events": list(study.HELDOUT), "required_informative_events": 2,
                   "pace_head": dict(baseline="reference", feature_group="pace", mean=[0.]*6, scale=[1.]*6,
                                     coefficients=[0.]*7, bound_s=.5, radius_s=.4, support=support),
                   "event_head": dict(mean=[0.]*10, scale=[1.]*10, coefficients=[0.]*10, intercept=1., threshold=.5),
                   "unbounded_head": dict(feature_level=3, coefficients=[0.]*6,
                                          support={c: {"radius_s": .4} for c in support})})
    def archive(root, *, fail_first=False):
        root.mkdir()
        base = datetime(2025, 4, 6, tzinfo=UTC).timestamp()
        for session, (_, meeting) in study.HELDOUT.items():
            laps = []
            for lap in range(1, 31):
                age = (lap-1) % 15+1
                delta = .6 if fail_first and session == 10006 else .2
                effect = (-.3 if age < 10 else .4) if lap <= 15 else (delta if age >= 10 else 0.)
                laps.append(dict(session_key=session, driver_number=4, lap_number=lap, is_pit_out_lap=False,
                                 lap_duration=95.+effect-.042*(lap-1),
                                 date_start=datetime.fromtimestamp(base+100*lap, UTC).isoformat()))
            stints = [dict(session_key=session, driver_number=4, compound=c, tyre_age_at_start=0,
                           lap_start=first, lap_end=first+14, stint_number=i)
                      for i, (c, first) in enumerate((("SOFT", 1), ("HARD", 16)), 1)]
            start = datetime.fromtimestamp(base, UTC).isoformat()
            tables = dict(sessions=[dict(year=2025, session_name="Race", meeting_key=meeting, session_key=session)],
                          laps=laps, stints=stints,
                          race_control=[dict(session_key=session, date=start, scope="Track", flag="CLEAR")],
                          weather=[dict(session_key=session, date=start, rainfall=0, track_temperature=30.)])
            for endpoint, table in tables.items():
                write_manifest(root/f"{session}-{endpoint}.json", table)
        write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.iterdir()}}))
        return root
    source = archive(tmp_path/"source")
    result = study.evaluate(frozen, source)
    assert result["passed"] and len(result["informative_events"]) == 4
    assert auditor.audit(frozen, result, source)["candidate_passed"]
    changed_source = archive(tmp_path/"changed", fail_first=True)
    changed = study.evaluate(frozen, changed_source)
    assert not changed["passed"] and changed["failed_supported_events"] == [10006]
    assert changed["metrics"][0]["events"][0]["observed"] == 0
    assert changed["metrics"][0]["events"][0]["predicted"] == 1
    assert [r["predicted_s"] for r in result["cases"]] == [r["predicted_s"] for r in changed["cases"]]
    assert auditor.audit(frozen, changed, changed_source)["audit_passed"]
    altered = deepcopy(result)
    altered["cases"][0]["predicted_s"] += .1
    altered = seal({k: v for k, v in altered.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="predicted_s"):
        auditor.audit(frozen, altered, source)
    altered = deepcopy(changed)
    altered["metrics"] = altered["metrics"][1:]
    altered = seal({k: v for k, v in altered.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="missing or duplicated event"):
        auditor.audit(frozen, altered, changed_source)
