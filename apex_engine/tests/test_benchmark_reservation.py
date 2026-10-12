import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import benchmark_guard as guard
from apexsim.data import benchmark_reservation as module
from apexsim.data.benchmark_guard import (
    assert_development_event,
    assert_development_sessions,
    protected_events,
)
from apexsim.data.benchmark_reservation import freeze_benchmark_reservation, load_benchmark_reservation
from apexsim.data.splits import validate_assignments
from apexsim.data.tables import make_table, read_dataset
from apexsim.examples.public_data_demo import run_public_data_demo
from apexsim.pipeline.stages import dataset_stage
from apexsim.provenance import payload_sha256


def seal(path, value):
    value = {k: v for k, v in value.items() if k != "content_sha256"}
    value["content_sha256"] = payload_sha256(value)
    path.write_text(json.dumps(value))
    return value


@pytest.fixture
def metadata(tmp_path, monkeypatch):
    calendars = []
    for year in (2023, 2024):
        root = tmp_path / str(year)
        root.mkdir()
        rows = [{"event_id": f"F1_{year}_R{r:02d}", "season": year, "round_number": r,
                 "circuit_id": f"track_{r}"} for r in (1, 4, 8, 12)]
        (root / "events.json").write_text(json.dumps({"events": rows}))
        seal(root / "manifest.json", {"query": {"season": year}, "environment": {"python": "fixture"}})
        calendars.append(root)
    corpus = tmp_path / "development.json"
    seal(corpus, {"schema_version": "apex-development-event-corpus-v1", "role": "DEVELOPMENT", "entries": [
        {"season": 2024, "round_number": 12, "provider_session_keys": {"openf1": 9554}}]})
    archive_root = tmp_path / "managed"
    archive_root.mkdir()
    known = archive_root / "fastf1-test"
    known.mkdir()
    (known / "manifest.json").write_text(json.dumps({"schema_version": "apex-fastf1-archive-v1",
                                                   "identity": {"year": 2023, "round_number": 4}}))
    # The selector must never open native tables.
    (known / "tables").mkdir()
    (known / "tables" / "laps.parquet").write_text("NOT A PARQUET FILE; do not read")
    monkeypatch.setattr(module, "verify_jolpica_archive", lambda p: json.loads((p / "manifest.json").read_text()))
    return calendars, corpus, archive_root


def test_metadata_only_freeze_rule_exclusion_and_immutability(metadata, tmp_path):
    calendars, corpus, root = metadata
    path = tmp_path / "reservation.json"
    result = freeze_benchmark_reservation(calendars, corpus, root, path, purpose="Predeclared fixture rule")
    assert [r["event_id"] for r in result["members"]] == ["F1_2023_R08", "F1_2023_R12", "F1_2024_R04", "F1_2024_R08"]
    assert not result["telemetry_acquired_by_this_task"] and not result["calibration_allowed"]
    assert load_benchmark_reservation(path) == result
    with pytest.raises(FileExistsError):
        freeze_benchmark_reservation(calendars, corpus, root, path, purpose="No overwrite")


@pytest.mark.parametrize("tamper", ["bytes", "member", "scope", "calibration", "count", "pin"])
def test_invalid_policy_refused(metadata, tmp_path, tamper):
    calendars, corpus, root = metadata
    path = tmp_path / "bad.json"
    result = freeze_benchmark_reservation(calendars, corpus, root, path, purpose="Fixture")
    if tamper == "bytes":
        result["purpose"] += "changed"
        path.write_text(json.dumps(result))
    elif tamper == "pin":
        with pytest.raises(ValueError, match="digest"):
            load_benchmark_reservation(path, expected_digest="a" * 64)
        return
    else:
        if tamper == "member":
            result["members"] = result["members"][1:]
        elif tamper == "scope":
            result["scope"] = "QUALIFYING_ONLY"
        elif tamper == "calibration":
            result["calibration_allowed"] = True
        else:
            result["event_count"] += 1
        seal(path, result)
    with pytest.raises(ValueError):
        load_benchmark_reservation(path)


def test_default_protects_whole_weekends_and_aliases():
    assert len(protected_events()) == 9
    for label in ("F1_2023_R04", "renamed_weekend"):
        with pytest.raises(ValueError, match="Permanent benchmark"):
            assert_development_event(2023, 4, event_id=label)
    assert_development_event(2024, 12)
    assert_development_event(2024, 16)
    with pytest.raises(ValueError, match="Conflicting"):
        assert_development_event(2024, 12, event_id="F1_2023_R04")


def test_missing_or_replaced_packaged_policy_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "DEFAULT_POLICY_PATH", tmp_path / "missing.json")
    with pytest.raises(RuntimeError, match="missing"):
        protected_events()
    original = json.loads(Path(module.__file__).with_name("benchmark_policy.json").read_text())
    original["purpose"] = "resigned replacement"
    path = tmp_path / "other.json"
    seal(path, original)
    monkeypatch.setattr(guard, "DEFAULT_POLICY_PATH", path)
    with pytest.raises(ValueError, match="digest"):
        protected_events()


def test_unknown_real_identity_and_synthetic_namespace():
    with pytest.raises(ValueError, match="Unresolved"):
        assert_development_sessions([{"season": 2024, "round": None, "event_id": "unknown", "source": "fastf1"}])
    assert_development_sessions([{"season": 2024, "round": None, "event_id": "SYNTH_EVENT", "source": "synthetic",
                                  "truth_labels": {"event_id": "SIMULATED"}}])
    with pytest.raises(ValueError, match="Conflicting"):
        assert_development_sessions([{"season": 2024, "round": 12, "event_id": "F1_2023_R04"}])


@pytest.mark.parametrize("partition", ["train", "val", "test"])
def test_every_ordinary_experiment_partition_excludes_benchmark(tmp_path, partition):
    root = tmp_path / "fixture"
    run_public_data_demo(root)
    tables, _ = read_dataset(root / "dataset")
    assignments = json.loads((root / "splits.json").read_text())["partitions"]
    rows = tables["sessions"].to_pylist()
    member = assignments[partition][0]
    row = next(r for r in rows if r["session_id"] == member)
    row.update(season=2023, round=4, event_id="renamed_to_evade_filter")
    with pytest.raises(ValueError, match="Permanent benchmark"):
        validate_assignments(make_table("sessions", rows), assignments)


@pytest.mark.parametrize("cached", [False, True])
def test_dataset_stage_refuses_legacy_benchmark_membership_before_scaler(tmp_path, monkeypatch, cached):
    from apexsim.config import DataConfig, ProjectConfig
    from apexsim.data.tables import write_dataset
    from apexsim.pipeline import stages
    fixture = tmp_path / "fixture"
    run_public_data_demo(fixture)
    tables, _ = read_dataset(fixture / "dataset")
    rows = tables["sessions"].to_pylist()
    for row in rows[:2]:
        row.update(season=2023, round=4, event_id="protected_weekend_alias")
    tables["sessions"] = make_table("sessions", rows)
    dataset = tmp_path / "protected-fixture"
    manifest = write_dataset(dataset, tables, [fixture / "fixture-source.json"])
    # Emulate a correctly sealed legacy split created before the permanent policy.
    legacy = json.loads((fixture / "splits.json").read_text())
    legacy.update(dataset_sha256=manifest["content_sha256"], sessions_sha256=manifest["tables"]["sessions"]["sha256"])
    split = tmp_path / "legacy.json"
    seal(split, legacy)
    root = tmp_path / "cached"
    root.mkdir()
    if cached:
        (root / "splits.json").write_text('{}')
        (root / "standardizer.json").write_text('{}')
    def never_fit(*args, **kwargs):
        pytest.fail("Protected data reached scaler fitting")
    monkeypatch.setattr(stages.Standardizer, "fit", never_fit)
    config = ProjectConfig(data=DataConfig(public_dataset_path=dataset, split_manifest_path=split))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        dataset_stage(config, tmp_path / "telemetry-not-opened.csv", root)


def test_cli_metadata_reservation(metadata, tmp_path):
    calendars, corpus, root = metadata
    output = tmp_path / "cli.json"
    result = CliRunner().invoke(app, ["freeze-benchmark-reservation", "--calendars", str(calendars[0]),
        "--calendars", str(calendars[1]), "--development-corpus", str(corpus), "--evidence-root", str(root),
        "--output", str(output), "Fixture reservation"])
    assert result.exit_code == 0, result.output
    result = CliRunner().invoke(app, ["verify-benchmark-reservation", str(output)])
    assert result.exit_code == 0, result.output


def test_changed_metadata_does_not_publish(metadata, tmp_path, monkeypatch):
    calendars, corpus, root = metadata
    original = module.audit_managed_archive_identities
    calls = [0]
    def changing(*args):
        rows = original(*args)
        calls[0] += 1
        if calls[0] > 1:
            rows[0]["metadata_sha256"] = "changed"
        return rows
    monkeypatch.setattr(module, "audit_managed_archive_identities", changing)
    with pytest.raises(ValueError, match="changed during"):
        freeze_benchmark_reservation(calendars, corpus, root, tmp_path / "changed.json", purpose="Fixture")
    assert not (tmp_path / "changed.json").exists()
