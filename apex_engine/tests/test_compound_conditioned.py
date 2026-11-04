import numpy as np
import pytest

from apexsim.research.compound_conditioned import feature_vector, fit_conditioned, predict_conditioned
from apexsim.research.compound_reference import COMPOUNDS


def window(compound="HARD", driver=0):
    return dict(session=9912, driver=driver, stints=[1, 2], ages=list(range(2, 14)),
                compounds=["SOFT", compound], current_prefix_s=[90., 90.1, 90.2],
                current_target_s=[90.3, 90.4, 90.5], reference_target_s=[91., 91.1, 91.2],
                prefix_s=-.2, reference_end_s=100., forecast_at_s=200.)


def test_conditioned_hand_features_and_forecast_ignore_future_targets():
    row = window()
    assert feature_vector(row) == pytest.approx([0., 0., 1., 1.2, .9, -.2])
    model = {"feature_level": 3, "coefficients": [0., 0., .1, .2, 0., .5],
             "support": {"HARD": {"radius_s": .2}}}
    prediction = predict_conditioned(model, row)
    assert prediction["predicted_s"] == pytest.approx(.76)
    assert predict_conditioned(model, {**row, "current_target_s": [120.]*3}) == prediction
    with pytest.raises(ValueError, match="unavailable"):
        predict_conditioned(model, {**row, "reference_end_s": 201.})


def test_conditioned_ridge_matches_independent_augmented_least_squares():
    rows = [window(compound, 3*j+i) for j, compound in enumerate(COMPOUNDS) for i in range(3)]
    model = fit_conditioned(rows)
    x = np.asarray([feature_vector(r) for r in rows])
    # An independent augmented system gives ridge without normal equations.
    expected = np.linalg.lstsq(np.vstack([x, np.sqrt(10.)*np.eye(6)]),
                               np.concatenate([np.full(9, .3), np.zeros(6)]), rcond=None)[0]
    assert model["coefficients"] == pytest.approx(expected)
    repeated = [{**r, "stints": [0, 2]} for r in rows]
    assert fit_conditioned(rows+repeated)["coefficients"] == pytest.approx(expected)


def test_conditioned_archive_and_independent_audit_detect_false_prediction(tmp_path, monkeypatch):
    from datetime import UTC, datetime
    from pathlib import Path
    from runpy import run_path

    from apexsim.provenance import file_sha256, write_manifest
    from apexsim.research.evidence import seal

    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts/"confirm_compound_conditioned.py"))
    auditor = run_path(str(scripts/"audit_compound_conditioned.py"))
    base = datetime(2025, 3, 23, tzinfo=UTC).timestamp()
    for session, (_, meeting) in study["HELDOUT"].items():
        start = datetime.fromtimestamp(base, UTC).isoformat()
        laps = []
        for lap in range(1, 31):
            age = (lap-1) % 15+1
            effect = (-.3 if age < 10 else .4) if lap <= 15 else (.2 if age >= 10 else 0.)
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
            write_manifest(tmp_path/f"{session}-{endpoint}.json", table)
    write_manifest(tmp_path/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in tmp_path.iterdir()}}))
    frozen = seal({"hashes": study["hashes"](), "heldout_events": list(study["HELDOUT"]),
                   "model": {"feature_level": 3, "coefficients": [0., 0., .2, 0., 0., 0.],
                             "support": {c: {"radius_s": .3} for c in COMPOUNDS}},
                   "prior_slopes": dict.fromkeys(COMPOUNDS, .03)})
    result = study["evaluate"](frozen, tmp_path)
    assert result["passed"]
    audit = auditor["audit"](frozen, result, tmp_path)
    assert audit["audit_passed"] and audit["candidate_passed"] and audit["cases_audited"] == 2
    result["cases"][0]["predicted_s"] += .1
    altered = seal({k: v for k, v in result.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="predicted_s"):
        auditor["audit"](frozen, altered, tmp_path)
