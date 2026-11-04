from datetime import UTC, datetime
from pathlib import Path
from runpy import run_path

import pytest

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_reference import COMPOUNDS, fit_drift, predict_reference
from apexsim.research.evidence import seal


def test_reference_forecast_hand_calculation_and_time_boundary():
    drift = {"HARD": {"delta_s": .3, "radius_s": .5}}
    result = predict_reference(drift, "HARD", [91., 92., 93.], [90., 91., 92.],
                               reference_end_s=100., forecast_at_s=100.)
    assert result == pytest.approx({"predicted_s": .7, "reference_persistence_s": 1.,
                                    "lower_s": .2, "upper_s": 1.2})
    with pytest.raises(ValueError, match="unavailable"):
        predict_reference(drift, "HARD", [91., 92., 93.], [90., 91., 92.],
                          reference_end_s=100.01, forecast_at_s=100.)


def test_drift_deduplicates_reference_pairs_and_rejects_conflicts():
    rows = [dict(session=9912, driver=3*index+driver, stints=[1, 2], ages=list(range(2, 14)),
                 compounds=["SOFT", compound], current_prefix_s=[90., 90., 90.],
                 current_target_s=[90.+change]*3)
            for index, compound in enumerate(COMPOUNDS) for driver, change in enumerate((.1, .3, .5))]
    model = fit_drift(rows)
    duplicate = {**rows[0], "stints": [0, 2]}
    assert fit_drift([*rows, duplicate]) == model
    assert all(m["windows"] == 3 and m["delta_s"] == pytest.approx(.3) for m in model.values())
    with pytest.raises(ValueError, match="Conflicting"):
        fit_drift([*rows, {**duplicate, "current_target_s": [94.]*3}])


def test_reference_evaluation_cannot_use_future_current_laps(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts/"confirm_compound_reference.py"))

    def archive(path, future_delta):
        path.mkdir()
        for session, (_, meeting) in study["HELDOUT"].items():
            base = datetime(2025, 6, 1, tzinfo=UTC).timestamp()
            start = datetime.fromtimestamp(base, UTC).isoformat()
            laps = []
            for lap in range(1, 31):
                age = (lap-1) % 15+1
                effect = (-.3 if age < 10 else .4) if lap <= 15 else (future_delta if age >= 10 else 0.)
                laps.append(dict(session_key=session, driver_number=4, lap_number=lap, is_pit_out_lap=False,
                                 lap_duration=95.+effect-.042*(lap-1),
                                 date_start=datetime.fromtimestamp(base+100*lap, UTC).isoformat()))
            stints = [dict(session_key=session, driver_number=4, compound=c, tyre_age_at_start=0,
                           lap_start=first, lap_end=first+14, stint_number=i)
                      for i, (c, first) in enumerate((("SOFT", 1), ("HARD", 16)), 1)]
            tables = dict(sessions=[dict(year=2025, session_name="Race", meeting_key=meeting, session_key=session)],
                          laps=laps, stints=stints,
                          race_control=[dict(session_key=session, date=start, scope="Track", flag="CLEAR")],
                          weather=[dict(session_key=session, date=start, rainfall=0)])
            for endpoint, table in tables.items():
                write_manifest(path/f"{session}-{endpoint}.json", table)
        write_manifest(path/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in path.iterdir()}}))
        return path

    frozen = seal({"hashes": study["hashes"](), "heldout_events": list(study["HELDOUT"]),
                   "drift": {c: {"delta_s": .1, "radius_s": .5} for c in COMPOUNDS},
                   "prior_slopes": dict.fromkeys(COMPOUNDS, .03)})
    first_path = archive(tmp_path/"first", .4)
    first = study["evaluate"](frozen, first_path)
    second = study["evaluate"](frozen, archive(tmp_path/"second", -.4))
    assert len(first["cases"]) == len(second["cases"]) == 2
    assert [c["predicted_s"] for c in first["cases"]] == [c["predicted_s"] for c in second["cases"]]
    assert [c["actual_s"] for c in first["cases"]] != [c["actual_s"] for c in second["cases"]]
    assert all(c["reference_end_s"] < c["forecast_at_s"] for c in first["cases"])
    next(first_path.glob("*-laps.json")).write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        study["evaluate"](frozen, first_path)
