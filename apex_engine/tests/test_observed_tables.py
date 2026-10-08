import copy
import json
import shutil

import pandas as pd
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import observed as module
from apexsim.data.alignment_report import LINK_VERSION
from apexsim.data.manifest import SourceManifest
from apexsim.data.observed import Mapper, map_fastf1, map_openf1, timestamp
from apexsim.data.tables import make_table, read_dataset, validate_tables
from apexsim.provenance import file_sha256, payload_sha256

START = pd.Timestamp("2024-07-06T14:00:05Z")
ANCHOR = pd.Timestamp("2024-07-06T14:00:00Z")


def fast_frames():
    return {
        "laps": pd.DataFrame({"DriverNumber": ["4", "4"], "LapNumber": [1.0, 2.0], "Stint": [1.0, 1.0],
                              "LapStartDate": pd.to_datetime(["2024-07-06T14:00:10", "2024-07-06T14:01:40"]),
                              "LapTime": pd.to_timedelta([90, None], unit="s"), "TyreLife": [1.0, None],
                              "Compound": ["INTERMEDIATE", None], "IsAccurate": [True, False], "TrackStatus": ["1", "2"],
                              "PitInTime": pd.to_timedelta([None, 200], unit="s"),
                              "PitOutTime": pd.to_timedelta([10, None], unit="s")}),
        "weather_data": pd.DataFrame({"Time": pd.to_timedelta([5, 65], unit="s"), "AirTemp": [12.4, None],
                                      "TrackTemp": [19.4, 20.1], "Pressure": [986.6, None], "Rainfall": [True, None],
                                      "WindSpeed": [1.2, None]}),
        "race_control_messages": pd.DataFrame({"Time": [pd.Timestamp("2024-07-06T14:00:10")],
                                               "Message": ["YELLOW IN TRACK SECTOR 10"], "Category": ["Flag"],
                                               "Scope": ["Sector"], "Sector": [10.0], "Flag": ["YELLOW"]}),
    }


def open_frames():
    return {"laps": [{"driver_number": 4, "lap_number": 1, "date_start": "2024-07-06T14:00:10Z", "lap_duration": 90.0},
                     {"driver_number": 4, "lap_number": 2, "date_start": None, "lap_duration": None}],
            "stints": [{"driver_number": 4, "stint_number": 1, "lap_start": 1, "lap_end": 2,
                        "compound": "SOFT", "tyre_age_at_start": 0}],
            "weather": [{"date": "2024-07-06T14:00:05Z", "air_temperature": 28.1, "track_temperature": None,
                         "rainfall": 0, "pressure": 1020.0, "wind_speed": 3.7}],
            "race_control": [{"date": "2024-07-06T14:00:10Z", "category": "Flag", "flag": "YELLOW",
                              "scope": "Sector", "sector": 10, "message": "YELLOW IN TRACK SECTOR 10"}],
            "pit": [{"date": "2024-07-06T14:00:10Z", "driver_number": 4, "lap_number": 1, "lane_duration": 23.0}],
            "drivers": [{"driver_number": 4}]}


def mapper(provider):
    return Mapper(provider, "a" * 64, f"F1_2024_R12_Q_{provider}", START)


def test_fast_fields_use_one_time_origin_and_missing_values_keep_unknown_labels():
    m = mapper("fastf1")
    map_fastf1(m, fast_frames(), ANCHOR)
    lap1, lap2 = m.rows["laps"]
    assert lap1["start_time_s"] == lap1["pit_out_time_s"] == 5.0
    assert lap2["pit_in_time_s"] == 195.0
    assert lap1["compound"] == "INTERMEDIATE" and lap2["compound"] is None
    assert lap2["lap_time_s"] is None and lap2["tyre_age_laps"] is None
    assert lap2["truth_labels"]["compound"] == "UNKNOWN"
    assert m.rows["stints"][0]["tyre_age_at_start_laps"] is None
    weather1, weather2 = m.rows["weather"]
    assert weather1["air_temp_c"] == 12.4 and weather1["pressure_pa"] == 98660.0
    assert weather1["rainfall"] is True and weather1["timestamp_utc"] == START
    assert weather2["air_temp_c"] is weather2["rainfall"] is weather2["wind_speed_mps"] is None
    assert weather1["truth_labels"]["pressure_pa"] == "RECONSTRUCTED"
    assert m.rows["race_control"][0]["sector"] is None
    assert m.rows["race_control"][0]["message"] == "YELLOW IN TRACK SECTOR 10"
    assert any("sector_namespace" in issue["reason"] for issue in m.issues)
    assert m.lineage["stints"] == [{"laps": [0, 1]}]
    for name, rows in m.rows.items():
        make_table(name, rows)
        assert all("IMPUTED" not in row["truth_labels"].values() for row in rows)


def test_open_fields_preserve_known_compound_but_do_not_invent_pit_boundaries_or_lap_tyre_age():
    m = mapper("openf1")
    map_openf1(m, open_frames())
    assert m.rows["laps"][0]["compound"] == "SOFT"
    assert m.rows["laps"][0]["stint_id"] == 1
    assert m.rows["laps"][0]["start_time_s"] == 5.0
    assert m.rows["stints"][0]["tyre_age_at_start_laps"] == 0.0
    for lap in m.rows["laps"]:
        assert lap["tyre_age_laps"] is lap["pit_in_time_s"] is lap["pit_out_time_s"] is None
        assert lap["is_accurate"] is None
    assert m.rows["weather"][0]["air_temp_c"] == 28.1
    assert m.rows["weather"][0]["rainfall"] is False
    assert m.rows["weather"][0]["pressure_pa"] == 102000.0


@pytest.mark.parametrize("second_compound", ["SOFT", "HARD"])
def test_overlapping_stints_do_not_choose_a_boundary_compound_even_when_strings_agree(second_compound):
    frames, m = open_frames(), mapper("openf1")
    frames["stints"].append({"driver_number": 4, "stint_number": 2, "lap_start": 2, "lap_end": 3,
                             "compound": second_compound, "tyre_age_at_start": 0})
    map_openf1(m, frames)
    assert m.rows["stints"] == []
    assert m.rows["laps"][0]["compound"] == "SOFT" and m.rows["laps"][0]["stint_id"] is None
    assert m.rows["laps"][1]["compound"] is None
    assert m.lineage["laps"][1]["stint_candidates"] == [0, 1]
    assert len([i for i in m.issues if i["native_table"] == "stints"]) == 2


def test_unbounded_and_reversed_ranges_are_quarantined_without_fake_extents():
    frames, m = open_frames(), mapper("openf1")
    frames["stints"][0]["lap_end"] = None
    frames["stints"].append({"driver_number": 4, "stint_number": 2, "lap_start": 3, "lap_end": 2})
    map_openf1(m, frames)
    assert m.rows["stints"] == []
    assert all(row["compound"] is None for row in m.rows["laps"])
    assert len([i for i in m.issues if "unbounded_or_invalid" in i["reason"]]) == 2


def test_unsupported_compounds_nonpositive_duration_and_before_start_are_reported_not_clipped():
    frames, m = fast_frames(), mapper("fastf1")
    frames["laps"].loc[0, "Compound"] = "SUPER_SOFT"
    frames["laps"].loc[0, "LapTime"] = pd.Timedelta(0, unit="s")
    frames["laps"].loc[0, "LapStartDate"] = pd.Timestamp("2024-07-06T13:59:00")
    map_fastf1(m, frames, ANCHOR)
    first = m.rows["laps"][0]
    assert first["compound"] is first["lap_time_s"] is first["start_time_s"] is None
    assert len(m.issues) == 4  # Three lap issues plus the native sector namespace.


@pytest.mark.parametrize("value", [None, 0, -1, 4.5, True])
def test_missing_or_invalid_driver_identity_is_not_stringified(value):
    frames = open_frames()
    frames["laps"][0]["driver_number"] = value
    with pytest.raises(ValueError):
        map_openf1(mapper("openf1"), frames)


def test_conflicting_fast_compounds_and_duplicate_open_stint_keys_fail():
    frames = fast_frames()
    frames["laps"].loc[1, "Compound"] = "SOFT"
    with pytest.raises(ValueError, match="compound conflict"):
        map_fastf1(mapper("fastf1"), frames, ANCHOR)
    opened = open_frames()
    opened["stints"].append(copy.deepcopy(opened["stints"][0]))
    with pytest.raises(ValueError, match="Duplicate OpenF1"):
        map_openf1(mapper("openf1"), opened)


def test_datetime_precision_and_timezone_are_explicit():
    with pytest.raises(ValueError, match="microsecond"):
        timestamp("2024-07-06T14:00:00.000000123Z")
    with pytest.raises(ValueError, match="explicit UTC offset"):
        timestamp("2024-07-06T14:00:00")


@pytest.fixture
def archives(tmp_path, monkeypatch):
    roots = {name: tmp_path / name for name in ("fastf1", "openf1", "jolpica")}
    for root in roots.values():
        (root / "tables").mkdir(parents=True)
    for name, frame in fast_frames().items():
        frame.to_parquet(roots["fastf1"] / f"tables/{name}.parquet", index=False)
    for name, rows in open_frames().items():
        (roots["openf1"] / f"tables/{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    link = {"schema_version": LINK_VERSION, "season": 2024, "round_number": 12, "session_code": "Q",
            "session_date": "2024-07-06", "fastf1_event_name": "Fixture GP", "openf1_session_key": 9554,
            "openf1_meeting_key": 1240, "openf1_circuit_key": 2, "jolpica_circuit_id": "fixture",
            "rationale": "Synthetic provider metadata for converter integration"}
    link_path = tmp_path / "link.json"
    link_path.write_text(json.dumps(link))
    manifests = {
        "fastf1": {"query": {"year": 2024, "round_number": 12, "session": "Q"},
                   "identity": {"event_name": "Fixture GP", "session_name": "Qualifying", "drivers": ["4"],
                                "t0_date": "2024-07-06T14:00:00", "session_start_time_s": 5, "api_path": "fixture/session"}},
        "openf1": {"identity": {"year": 2024, "session_key": 9554, "meeting_key": 1240,
                                "circuit_key": 2, "session_name": "Qualifying", "date_start": START.isoformat()}},
        "jolpica": {"query": {"season": 2024}, "pages": [{"path": "page.json"}]},
    }
    (roots["jolpica"] / "page.json").write_text(json.dumps({"MRData": {"RaceTable": {"Races": [
        {"round": "12", "Circuit": {"circuitId": "fixture"}, "Qualifying": {"date": "2024-07-06", "time": "14:00:00Z"}}]}}}))
    for name, manifest in manifests.items():
        source = SourceManifest(name, {"fixture": True}, "https://example.test/terms")
        source.add_request("fixture://native", {"fixture": True}, None)
        manifest["source_manifest"] = source.to_dict()
        manifest["content_sha256"] = payload_sha256(manifest)
        (roots[name] / "manifest.json").write_text(json.dumps(manifest))
        monkeypatch.setattr(module, f"verify_{name}_archive", lambda root, name=name: manifests[name])
    return roots, link_path, manifests


def build(archives, output):
    roots, link, _ = archives
    return module.build_observed_tables(roots["fastf1"], roots["openf1"], roots["jolpica"], link, output)


def test_complete_bundle_lineage_unknowns_integrity_and_portability(tmp_path, archives):
    roots, _, _ = archives
    before = {p: file_sha256(p) for r in roots.values() for p in r.rglob("*") if p.is_file()}
    output = tmp_path / "observed"
    report = build(archives, output)
    assert module.verify_observed_tables(output) == report
    assert report["report_complete"] and not report["training_ready"]
    tables, _ = read_dataset(output / "fastf1")
    assert validate_tables(tables)["passed"]
    assert tables["laps"]["compound"].to_pylist() == ["INTERMEDIATE", None]
    opened, _ = read_dataset(output / "openf1")
    assert opened["laps"]["pit_in_time_s"].null_count == 2
    assert tables["sessions"]["event_id"].to_pylist() == opened["sessions"]["event_id"].to_pylist()
    assert tables["sessions"]["session_id"].to_pylist() != opened["sessions"]["session_id"].to_pylist()
    manifest = json.loads((output / "manifest.json").read_text())
    assert all(file_sha256(output / name) == record["sha256"] for name, record in manifest["files"].items())
    assert payload_sha256({k: v for k, v in report.items() if k != "content_sha256"}) == report["content_sha256"]
    assert before == {p: file_sha256(p) for p in before}
    moved = tmp_path / "moved"
    shutil.copytree(output / "openf1", moved)
    assert read_dataset(moved)[0]["weather"].equals(opened["weather"], check_metadata=True)
    portable = tmp_path / "portable"
    shutil.copytree(output, portable)
    for root in roots.values():
        shutil.rmtree(root)
    assert module.verify_observed_tables(portable) == report
    with pytest.raises(FileExistsError):
        build(archives, output)
    with pytest.raises(ValueError, match="outside source archives"):
        build(archives, roots["fastf1"] / "nested")


def test_wrong_link_driver_inventory_and_source_mutation_do_not_complete(tmp_path, archives, monkeypatch):
    roots, link, manifests = archives
    original = link.read_text()
    link.write_text(original.replace('"round_number": 12', '"round_number": 11'))
    with pytest.raises(ValueError, match="FastF1 query"):
        build(archives, tmp_path / "wrong")
    assert not (tmp_path / "wrong").exists()
    link.write_text(original)
    drivers = roots["openf1"] / "tables/drivers.jsonl"
    previous = drivers.read_text()
    drivers.write_text('{"driver_number": 44}\n')
    with pytest.raises(ValueError, match="driver inventories differ"):
        build(archives, tmp_path / "mismatch")
    assert not (tmp_path / "mismatch").exists()
    drivers.write_text(previous)
    calls = iter([manifests["fastf1"], {**manifests["fastf1"], "content_sha256": "changed"}])
    monkeypatch.setattr(module, "verify_fastf1_archive", lambda root: next(calls))
    with pytest.raises(ValueError, match="changed during"):
        build(archives, tmp_path / "changed")
    assert not (tmp_path / "changed/manifest.json").exists()


def test_observed_cli(tmp_path, archives):
    roots, link, _ = archives
    result = CliRunner().invoke(app, ["build-observed-tables", "--fastf1", str(roots["fastf1"]),
                                     "--openf1", str(roots["openf1"]), "--jolpica", str(roots["jolpica"]),
                                     "--link", str(link), "--output", str(tmp_path / "cli")])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["training_ready"] is False
    verified = CliRunner().invoke(app, ["verify-observed-tables", str(tmp_path / "cli")])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output)["passed"]


@pytest.mark.parametrize("mutation", ["lineage", "extra_file", "missing_completion"])
def test_observed_run_verifier_rejects_incomplete_or_tampered_runs(tmp_path, archives, mutation):
    output = tmp_path / "observed"
    build(archives, output)
    if mutation == "lineage":
        (output / "fastf1.lineage.json").write_text("{}")
    elif mutation == "extra_file":
        (output / "extra.json").write_text("{}")
    else:
        (output / "manifest.json").unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        module.verify_observed_tables(output)


def test_resealed_out_of_range_lineage_fails_semantic_verification(tmp_path, archives):
    output = tmp_path / "observed"
    build(archives, output)
    path = output / "openf1.lineage.json"
    lineage = json.loads(path.read_text())
    lineage["laps"][0]["stint_candidates"] = [999]
    path.write_text(json.dumps(lineage))
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][path.name] = {"sha256": file_sha256(path), "bytes": path.stat().st_size}
    manifest["content_sha256"] = payload_sha256({k: v for k, v in manifest.items() if k != "content_sha256"})
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="lineage row index"):
        module.verify_observed_tables(output)
