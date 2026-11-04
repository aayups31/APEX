import copy
from datetime import UTC, datetime
from pathlib import Path
from runpy import run_path

import pytest

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import seal


def test_coverage_extension_preserves_original_and_cannot_hide_supported_failure(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts/"confirm_compound_v8.py"))
    coverage = run_path(str(scripts/"confirm_compound_v8_coverage.py"))
    original_audit = run_path(str(scripts/"audit_compound_v8.py"))["audit"]
    audit = run_path(str(scripts/"audit_compound_v8_coverage.py"))["audit"]

    def archive(root, events, future_delta=.2):
        root.mkdir()
        base = datetime(2025, 5, 18, tzinfo=UTC).timestamp()
        start = datetime.fromtimestamp(base, UTC).isoformat()
        for session, (_, meeting) in events.items():
            laps = []
            for lap in range(1, 31):
                age = (lap-1) % 15+1
                effect = (-.3 if age < 10 else .4) if lap <= 15 else (future_delta if age >= 10 else 0.)
                laps.append(dict(session_key=session, driver_number=4, lap_number=lap, is_pit_out_lap=False,
                                 lap_duration=95.+effect-.042*(lap-1),
                                 date_start=datetime.fromtimestamp(base+100*lap, UTC).isoformat()))
            # A genuine empty comparison cohort: no different-compound pair.
            compounds = ("SOFT", "SOFT") if session == 10033 else ("SOFT", "HARD")
            stints = [dict(session_key=session, driver_number=4, compound=c, tyre_age_at_start=0,
                           lap_start=first, lap_end=first+14, stint_number=i)
                      for i, (c, first) in enumerate(zip(compounds, (1, 16), strict=True), 1)]
            tables = dict(sessions=[dict(year=2025, session_name="Race", meeting_key=meeting, session_key=session)],
                          laps=laps, stints=stints,
                          race_control=[dict(session_key=session, date=start, scope="Track", flag="CLEAR")],
                          weather=[dict(session_key=session, date=start, rainfall=0)])
            for endpoint, table in tables.items():
                write_manifest(root/f"{session}-{endpoint}.json", table)
        write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.iterdir()}}))
        return root

    frozen = seal({"hashes": study["hashes"](), "heldout_events": list(study["HELDOUT"]),
                   "pace_head": {"feature_level": 3, "coefficients": [0., 0., .2, 0., 0., 0.],
                                 "support": {c: {"radius_s": .3} for c in ("SOFT", "MEDIUM", "HARD")}},
                   "event_head": {"mean": [0.]*10, "scale": [1.]*10, "coefficients": [0.]*10,
                                  "intercept": 1., "threshold": .5},
                   "prior_slopes": dict.fromkeys(("SOFT", "MEDIUM", "HARD"), .03)})
    base = archive(tmp_path/"base", study["HELDOUT"])
    original = study["evaluate"](frozen, base)
    assert not original["passed"] and original["metrics"][0]["primary"]["blocks"] == 0
    assert original_audit(frozen, original, base)["audit_passed"]
    extension = coverage["freeze"](frozen, original)
    extra = archive(tmp_path/"extra", coverage["ADDITIONAL"])
    panel = tmp_path/"panel"
    coverage["assemble"](panel, base, extra)
    result = coverage["evaluate"](extension, frozen, original, panel)
    assert result["passed"] and result["unsupported_events"] == [10033]
    assert result["metrics"][:2] == original["metrics"]
    assert result["calibration_sha256"] == frozen["content_sha256"]
    assert audit(frozen, result, panel)["candidate_passed"]

    # Change only future current-stint targets: forecasts stay fixed, but the
    # supported event fails. It cannot be treated as an empty event and dropped.
    bad_extra = archive(tmp_path/"bad-extra", coverage["ADDITIONAL"], future_delta=1.5)
    bad_panel = tmp_path/"bad-panel"
    coverage["assemble"](bad_panel, base, bad_extra)
    failed = coverage["evaluate"](extension, frozen, original, bad_panel)
    assert not failed["passed"] and failed["metrics"][-1]["primary"]["blocks"] == 1
    assert [r["predicted_s"] for r in result["cases"]] == [r["predicted_s"] for r in failed["cases"]]
    assert audit(frozen, failed, bad_panel)["audit_passed"]

    bad_original = copy.deepcopy(original)
    bad_original["metrics"][1]["passed"] = False
    bad_original = seal({k: v for k, v in bad_original.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="supported failed"):
        coverage["freeze"](frozen, bad_original)
