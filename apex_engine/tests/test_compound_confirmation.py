from pathlib import Path
from runpy import run_path

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import seal

STUDY = run_path(str(Path(__file__).resolve().parents[2]/"research/scripts/confirm_compound_crossover.py"))


def test_confirmation_keeps_forecast_fixed_when_future_laps_change(tmp_path):
    from datetime import UTC, datetime

    def archive(path, future_delta):
        path.mkdir()
        for session, (_, meeting) in STUDY["SESSIONS"].items():
            start = "2025-09-07T13:00:00+00:00"
            base = datetime.fromisoformat(start).timestamp()
            laps = []
            for lap in range(1, 31):
                age = (lap-1) % 15 + 1
                offset = (-.3 if age < 10 else future_delta) if lap <= 15 else 0
                laps.append(dict(driver_number=4, lap_number=lap, is_pit_out_lap=False,
                                 lap_duration=95 + offset - .042*(lap-1),
                                 date_start=datetime.fromtimestamp(base+100*lap, UTC).isoformat()))
            stints = [dict(driver_number=4, compound=c, tyre_age_at_start=0,
                           lap_start=first, lap_end=first+14, stint_number=i)
                      for i, (c, first) in enumerate((("SOFT", 1), ("HARD", 16)), 1)]
            tables = dict(sessions=[dict(year=2025, session_name="Race", meeting_key=meeting, session_key=session)],
                          laps=laps, stints=stints, race_control=[],
                          weather=[dict(date=start, rainfall=0)])
            for name, rows in tables.items():
                write_manifest(path/f"{session}-{name}.json", rows)
        write_manifest(path/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in path.iterdir()}}))
        return path

    frozen = seal({"implementation": STUDY["hashes"](), "slopes": {"SOFT": .1, "MEDIUM": .03, "HARD": .02}})
    first = STUDY["evaluate"](frozen, archive(tmp_path/"first", .4))
    second = STUDY["evaluate"](frozen, archive(tmp_path/"second", -.4))
    assert first["passed"] and not second["passed"]
    assert [c["predicted_s"] for c in first["cases"]] == [c["predicted_s"] for c in second["cases"]]
