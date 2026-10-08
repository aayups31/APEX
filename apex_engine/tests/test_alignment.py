import copy
import json

import pandas as pd
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import alignment_report as module
from apexsim.data.alignment import AlignmentPolicy, stream_quality, temporal_join, utc_times
from apexsim.provenance import file_sha256, payload_sha256


def times(milliseconds):
    base = pd.Timestamp("2024-07-06T14:00:00Z")
    return pd.DatetimeIndex([pd.NaT if value is None else pd.Timestamp(
        base.value + pd.Timedelta(value, unit="ms").value, unit="ns", tz="UTC")
                             for value in milliseconds], tz="UTC")


def test_backward_is_causal_preserves_left_order_and_rejects_stale_values():
    pairs, stats = temporal_join(times([100, None, 0, 30, 200]), times([20, 90]), tolerance_ms=50)
    assert pairs.reason.tolist() == ["matched", "missing_left_timestamp", "no_target_in_direction", "matched", "outside_tolerance"]
    assert pairs.right_row.dropna().tolist() == [1, 0]
    assert pairs.right_minus_left_ms.dropna().tolist() == [-10, -10]
    assert stats["matched_rows"] == 2 and stats["join_rate_all_rows"] == 0.4
    assert stats["future_matches"] == 0 and pairs.left_row.tolist() == list(range(5))


def test_nearest_ties_prefer_past_and_future_matches_are_labelled():
    pairs, stats = temporal_join(times([10, 19, 25]), times([0, 20]), tolerance_ms=10, direction="nearest")
    assert pairs.right_row.tolist() == [0, 1, 1]
    assert pairs.right_minus_left_ms.tolist() == [-10, 1, -5]
    assert stats["future_matches"] == 1 and stats["reused_right_rows"] == 1


@pytest.mark.parametrize("direction", ["backward", "nearest"])
def test_duplicate_targets_are_ambiguous_not_silently_deduplicated(direction):
    pairs, stats = temporal_join(times([10, 11, 30]), times([10, 10, 30]), tolerance_ms=10, direction=direction)
    assert pairs.reason.tolist() == ["ambiguous_target_timestamp", "ambiguous_target_timestamp", "matched"]
    assert stats["matched_rows"] == 1


def test_nanosecond_precision_and_inclusive_tolerance_boundary():
    left = utc_times(["2024-07-06T14:00:00.000000123Z", "2024-07-06T14:00:00.001000124Z"])
    right = utc_times(["2024-07-06T14:00:00.000000123+00:00"])
    pairs, _ = temporal_join(left, right, tolerance_ms=1)
    assert pairs.matched.tolist() == [True, False]
    assert pairs.left_utc.iloc[0].nanosecond == 123
    pairs, _ = temporal_join(times([1]), times([0]), tolerance_ms=1)
    assert pairs.matched.tolist() == [True]


@pytest.mark.parametrize("left,right", [([], []), ([None], []), ([0, 10], [None]), ([], [0])])
def test_empty_and_all_missing_streams(left, right):
    pairs, report = temporal_join(times(left), times(right), tolerance_ms=0)
    assert len(pairs) == len(left) and report["matched_rows"] == 0
    assert report["join_rate_all_rows"] == (0.0 if left else None)


def test_gap_report_counts_duplicates_reversals_and_missingness():
    report = stream_quality(times([100, 0, None, 100, 2000]), gap_ms=500)
    assert report["missing_timestamps"] == 1
    assert report["duplicate_timestamp_rows"] == 1
    assert report["source_order_reversals"] == 1
    assert report["gap_count"] == 1 and report["gaps"][0]["duration_ms"] == 1900


def test_naive_timestamps_require_explicit_provider_convention():
    with pytest.raises(ValueError, match="explicit UTC offset"):
        utc_times(["2024-07-06T14:00:00"])
    assert utc_times(["2024-07-06T14:00:00"], naive_is_utc=True)[0] == times([0])[0]
    assert utc_times(["2024-07-06T15:00:00+01:00"])[0] == times([0])[0]
    with pytest.raises(ValueError, match="1950-2100"):
        utc_times(["1900-01-01T00:00:00Z"])
    with pytest.raises(ValueError, match="timezone-aware"):
        temporal_join(pd.DatetimeIndex(["2024-01-01"]), times([0]), tolerance_ms=0)


@pytest.mark.parametrize("value", [-1, 0.5, True, 86400001])
def test_bad_tolerances_fail(value):
    with pytest.raises(ValueError):
        AlignmentPolicy(cross_telemetry_ms=value)
    with pytest.raises(ValueError):
        temporal_join(times([0]), times([0]), tolerance_ms=value)


@pytest.fixture
def sources(tmp_path, monkeypatch):
    fast, opened, catalog = (tmp_path / name for name in ("fast", "open", "catalog"))
    for root in (fast, opened, catalog):
        (root / "tables").mkdir(parents=True)
    link = {"schema_version": module.LINK_VERSION, "season": 2024, "round_number": 12, "session_code": "Q",
            "session_date": "2024-07-06", "fastf1_event_name": "Fixture GP", "openf1_session_key": 9554,
            "openf1_meeting_key": 1240, "openf1_circuit_key": 2, "jolpica_circuit_id": "fixture",
            "rationale": "Synthetic explicitly linked source metadata"}
    link_path = tmp_path / "link.json"
    link_path.write_text(json.dumps(link))
    fast_manifest = {"content_sha256": "fast-hash", "query": {"year": 2024, "round_number": 12, "session": "Q"},
                     "identity": {"event_name": "Fixture GP", "session_name": "Qualifying", "drivers": ["4"],
                                  "t0_date": "2024-07-06T14:00:00", "session_start_time_s": 0}}
    open_manifest = {"content_sha256": "open-hash", "identity": {"year": 2024, "session_key": 9554,
                     "meeting_key": 1240, "circuit_key": 2, "session_name": "Qualifying",
                     "date_start": "2024-07-06T14:00:00Z"}}
    catalog_manifest = {"content_sha256": "catalog-hash", "query": {"season": 2024}, "pages": [{"path": "page.json"}]}
    (catalog / "page.json").write_text(json.dumps({"MRData": {"RaceTable": {"Races": [
        {"round": "12", "Circuit": {"circuitId": "fixture"}, "Qualifying": {"date": "2024-07-06", "time": "14:00:00Z"}}]}}}))
    monkeypatch.setattr(module, "verify_fastf1_archive", lambda root: fast_manifest)
    monkeypatch.setattr(module, "verify_openf1_archive", lambda root: open_manifest)
    monkeypatch.setattr(module, "verify_jolpica_archive", lambda root: catalog_manifest)
    for kind in ("car_data", "pos_data"):
        (fast / "tables" / kind).mkdir()
        pd.DataFrame({"Date": times([0, 100, 200]).tz_localize(None)}).to_parquet(fast / f"tables/{kind}/4.parquet")
    pd.DataFrame({"Time": pd.to_timedelta([0], unit="s")}).to_parquet(fast / "tables/weather_data.parquet")
    fast_laps = pd.DataFrame({"DriverNumber": ["4"], "LapNumber": [1.0], "LapStartDate": times([0]).tz_localize(None),
                              "LapTime": pd.to_timedelta([90.0], unit="s")})
    fast_laps.to_parquet(fast / "tables/laps.parquet")
    pd.DataFrame({"Time": times([0]).tz_localize(None), "Message": ["FLAG"], "Category": ["Flag"]}).to_parquet(fast / "tables/race_control_messages.parquet")
    tables = {"car_data": [{"driver_number": 4, "date": t.isoformat()} for t in times([0, 100, 200])],
              "location": [{"driver_number": 4, "date": t.isoformat()} for t in times([0, 90, 190])],
              "drivers": [{"driver_number": 4}], "weather": [{"date": times([0])[0].isoformat()}],
              "laps": [{"driver_number": 4, "lap_number": 1, "date_start": None, "lap_duration": 90.1}],
              "race_control": [{"date": times([0])[0].isoformat(), "message": "FLAG", "category": "Flag"},
                               {"date": times([100])[0].isoformat(), "message": "EXTRA", "category": "Other"}]}
    for name, rows in tables.items():
        (opened / f"tables/{name}.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return fast, opened, catalog, link_path, fast_manifest, open_manifest


def test_complete_report_preserves_sources_emits_pair_lineage_and_does_not_claim_training_ready(tmp_path, sources):
    fast, opened, catalog, link, _, _ = sources
    before = {str(p): file_sha256(p) for root in (fast, opened, catalog) for p in root.rglob("*") if p.is_file()}
    report = module.build_alignment_report(fast, opened, catalog, link, tmp_path / "report")
    assert report["report_complete"] and not report["training_ready"]
    assert len(report["joins"]) == 7 and report["laps"]["matched_keys"] == 1
    assert report["laps"]["start_openf1_minus_fastf1_ms"]["comparable_rows"] == 0
    assert report["race_control"]["matched_records"] == 1 and len(report["race_control"]["openf1_only"]) == 1
    assert all(j["future_matches"] == 0 for j in report["joins"].values() if j["direction"] == "backward")
    manifest = json.loads((tmp_path / "report/manifest.json").read_text())
    assert all(file_sha256(tmp_path / "report" / name) == record["sha256"] for name, record in manifest["files"].items())
    digest = report.pop("content_sha256")
    assert payload_sha256(report) == digest
    assert before == {path: file_sha256(path) for path in before}
    with pytest.raises(FileExistsError):
        module.build_alignment_report(fast, opened, catalog, link, tmp_path / "report")
    with pytest.raises(ValueError, match="outside source archives"):
        module.build_alignment_report(fast, opened, catalog, link, fast / "nested")


@pytest.mark.parametrize("field,value", [("openf1_session_key", 2), ("round_number", 11), ("session_code", "R"),
                                         ("session_date", "2024-07-07"), ("jolpica_circuit_id", "wrong"), ("season", True)])
def test_wrong_link_fails_before_creating_report(tmp_path, sources, field, value):
    fast, opened, catalog, link, _, _ = sources
    data = json.loads(link.read_text())
    data[field] = value
    link.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        module.build_alignment_report(fast, opened, catalog, link, tmp_path / "failed")
    assert not (tmp_path / "failed").exists()


def test_driver_mismatch_and_source_mutation_are_rejected(tmp_path, sources, monkeypatch):
    fast, opened, catalog, link, fm, _ = sources
    changed = copy.deepcopy(fm)
    changed["identity"]["drivers"] = ["44"]
    monkeypatch.setattr(module, "verify_fastf1_archive", lambda root: changed)
    with pytest.raises(ValueError, match="driver inventories differ"):
        module.build_alignment_report(fast, opened, catalog, link, tmp_path / "mismatch")
    calls = iter([fm, {**fm, "content_sha256": "changed"}])
    monkeypatch.setattr(module, "verify_fastf1_archive", lambda root: next(calls))
    with pytest.raises(ValueError, match="changed during alignment"):
        module.build_alignment_report(fast, opened, catalog, link, tmp_path / "changed")
    assert not (tmp_path / "changed/manifest.json").exists()


def test_duplicate_lap_keys_fail(tmp_path, sources):
    fast, opened, catalog, link, _, _ = sources
    path = fast / "tables/laps.parquet"
    rows = pd.read_parquet(path)
    pd.concat([rows, rows]).to_parquet(path, index=False)
    with pytest.raises(ValueError, match="duplicate driver/lap"):
        module.build_alignment_report(fast, opened, catalog, link, tmp_path / "failed")
    assert not (tmp_path / "failed/manifest.json").exists()


def test_cli(tmp_path, sources):
    fast, opened, catalog, link, _, _ = sources
    result = CliRunner().invoke(app, ["align-public-data", "--fastf1", str(fast), "--openf1", str(opened),
                                     "--jolpica", str(catalog), "--link", str(link), "--output", str(tmp_path / "cli")])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["joins"] == 7
