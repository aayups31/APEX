import copy
import json
import shutil
import subprocess
import sys
from datetime import timedelta
from types import SimpleNamespace

import pandas as pd
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import fastf1_archive as archive_module
from apexsim.data import fastf1_worker
from apexsim.data.fastf1_archive import (
    FastF1Query,
    download_fastf1_session,
    replay_fastf1_archive,
    verify_fastf1_archive,
)
from apexsim.provenance import file_sha256, payload_sha256

QUERY = FastF1Query(2024, 12, "Q")
ENVIRONMENT = {"python": "fixture", "fastf1": "fixture", "pandas": "fixture", "numpy": "fixture", "pyarrow": "fixture"}


def source_session():
    event = pd.Series({"RoundNumber": 12, "EventName": "Fixture GP"})
    event.year = 2024
    times = pd.to_datetime(["2024-07-06T14:00:00.000000123", "2024-07-06T14:00:00.250000123"])
    car = pd.DataFrame({"Date": times, "Speed": [180, 181], "Throttle": [80.0, float("nan")]})
    return SimpleNamespace(
        event=event, name="Qualifying", api_path="fixture/session", t0_date=times[0],
        session_start_time=timedelta(seconds=100),
        laps=pd.DataFrame({"DriverNumber": ["4"], "LapNumber": [1.0], "LapTime": pd.to_timedelta([90], unit="s")}),
        weather_data=pd.DataFrame({"Time": pd.to_timedelta([1], unit="s"), "AirTemp": [22.0]}),
        race_control_messages=pd.DataFrame({"Time": [times[0]], "Message": ["TEST FLAG"]}),
        track_status=pd.DataFrame({"Time": pd.to_timedelta([1], unit="s"), "Status": ["1"]}),
        session_status=pd.DataFrame({"Time": pd.to_timedelta([1], unit="s"), "Status": ["Started"]}),
        results=pd.DataFrame({"DriverNumber": ["4"], "Position": [1.0]}),
        car_data={"4": car}, pos_data={"4": pd.DataFrame({"Date": times, "X": [1, 2], "Y": [3, 4]})},
    )


@pytest.fixture
def fake_worker(monkeypatch):
    calls = []
    monkeypatch.setattr(archive_module, "environment_versions", lambda: ENVIRONMENT)
    monkeypatch.setattr(fastf1_worker, "environment_versions", lambda: ENVIRONMENT)

    def worker(query, root, *, offline, timeout_s):
        calls.append({"query": query, "offline": offline, "root": root})
        cached = root / "cache" / "fixture-response.json"
        if offline:
            assert cached.read_text() == '{"fixture": true}'
            # Mutating the working cache must not touch the archive.
            (root / "cache" / "worker-touched-cache").write_text("working-copy")
        else:
            cached.write_text('{"fixture": true}')
        return fastf1_worker.snapshot_session(source_session(), root, query, network_attempts=0)

    monkeypatch.setattr(archive_module, "_worker", worker)
    return calls


def test_download_relocate_and_replay_without_modifying_archive(tmp_path, fake_worker):
    source = tmp_path / "download"
    manifest = download_fastf1_session(QUERY, source)
    assert manifest["source_manifest"]["source"] == "fastf1"
    assert len(manifest["source_manifest"]["requests"]) == 2
    assert manifest["query"] == {"year": 2024, "round_number": 12, "session": "Q"}
    assert "cache/fixture-response.json" in manifest["files"]
    moved = tmp_path / "relocated"
    shutil.copytree(source, moved)
    assert verify_fastf1_archive(moved)["content_sha256"] == manifest["content_sha256"]
    before = {p: file_sha256(moved / p) for p in manifest["files"]}
    replay = replay_fastf1_archive(moved, tmp_path / "offline")
    assert replay["passed"] and replay["network_attempts"] == 0
    assert replay["table_count"] == 8
    assert replay["mismatched_tables"] == []
    assert fake_worker[-1]["offline"] is True
    assert before == {p: file_sha256(moved / p) for p in manifest["files"]}
    car = pd.read_parquet(moved / "tables/car_data/4.parquet")
    assert car.Date.iloc[0].nanosecond == 123
    assert pd.isna(car.Throttle.iloc[1])


def test_existing_outputs_and_nested_replays_fail_before_worker(tmp_path, fake_worker):
    root = tmp_path / "download"
    download_fastf1_session(QUERY, root)
    with pytest.raises(FileExistsError):
        download_fastf1_session(QUERY, root)
    with pytest.raises(ValueError, match="outside the frozen archive"):
        replay_fastf1_archive(root, root / "nested")
    with pytest.raises(FileExistsError):
        replay_fastf1_archive(root, root)
    assert len(fake_worker) == 1


@pytest.mark.parametrize("artifact", ["cache/fixture-response.json", "tables/laps.parquet", "snapshot.json"])
def test_tampering_rejected_before_offline_worker(tmp_path, fake_worker, artifact):
    root = tmp_path / "download"
    download_fastf1_session(QUERY, root)
    with (root / artifact).open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        replay_fastf1_archive(root, tmp_path / "offline")
    assert len(fake_worker) == 1
    assert not (tmp_path / "offline").exists()


def test_manifest_tampering_missing_files_and_unlisted_cache_files(tmp_path, fake_worker):
    root = tmp_path / "download"
    manifest = download_fastf1_session(QUERY, root)
    (root / "cache" / "extra-file").write_text("unexpected")
    with pytest.raises(ValueError, match="inventory mismatch"):
        verify_fastf1_archive(root)
    changed = copy.deepcopy(manifest)
    changed["query"]["year"] = 2023
    (root / "manifest.json").write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="content hash mismatch"):
        verify_fastf1_archive(root)


@pytest.mark.parametrize("path", ["../outside", "/absolute", "C:/outside", "cache/../../outside", "cache\\outside"])
def test_rehashed_manifest_cannot_escape_archive(tmp_path, fake_worker, path):
    root = tmp_path / "download"
    manifest = download_fastf1_session(QUERY, root)
    manifest["files"][path] = {"bytes": 1, "sha256": "a" * 64}
    manifest.pop("content_sha256")
    manifest["content_sha256"] = payload_sha256(manifest)
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="artifact path"):
        verify_fastf1_archive(root)


def test_environment_mismatch_requires_recorded_versions(tmp_path, fake_worker, monkeypatch):
    root = tmp_path / "download"
    download_fastf1_session(QUERY, root)
    monkeypatch.setattr(archive_module, "environment_versions", lambda: {**ENVIRONMENT, "fastf1": "different"})
    with pytest.raises(ValueError, match="environment mismatch"):
        replay_fastf1_archive(root, tmp_path / "offline")
    assert len(fake_worker) == 1


@pytest.mark.parametrize("change", ["prediction", "network"])
def test_replay_failure_gets_a_report_without_changing_original(tmp_path, fake_worker, monkeypatch, change):
    root = tmp_path / "download"
    original = download_fastf1_session(QUERY, root)

    def changed_worker(query, destination, **kwargs):
        session = source_session()
        if change == "prediction":
            session.car_data["4"]["Speed"] += 100
        return fastf1_worker.snapshot_session(session, destination, query, network_attempts=1 if change == "network" else 0)

    monkeypatch.setattr(archive_module, "_worker", changed_worker)
    with pytest.raises(ValueError, match="reconstruction differs"):
        replay_fastf1_archive(root, tmp_path / "offline")
    report = json.loads((tmp_path / "offline/replay_report.json").read_text())
    assert not report["passed"]
    assert verify_fastf1_archive(root) == original


@pytest.mark.parametrize("change", ["empty-weather", "missing-driver", "wrong-round", "wrong-session"])
def test_incomplete_or_wrong_session_is_not_sealed(tmp_path, monkeypatch, change):
    monkeypatch.setattr(fastf1_worker, "environment_versions", lambda: ENVIRONMENT)
    session = source_session()
    if change == "empty-weather":
        session.weather_data = pd.DataFrame()
    elif change == "missing-driver":
        session.pos_data = {}
    elif change == "wrong-session":
        session.name = "Race"
    else:
        session.event["RoundNumber"] = 11
    with pytest.raises(ValueError):
        fastf1_worker.snapshot_session(session, tmp_path, QUERY, network_attempts=0)
    assert not (tmp_path / "snapshot.json").exists()


def test_network_guard_blocks_real_socket_operations_in_child_process():
    code = """
import socket
from apexsim.data.fastf1_worker import install_network_guard
attempts = install_network_guard()
try:
    socket.getaddrinfo('example.test', 443)
except RuntimeError:
    pass
else:
    raise AssertionError('DNS was allowed')
with socket.socket() as sock:
    try:
        sock.connect(('127.0.0.1', 9))
    except RuntimeError:
        pass
    else:
        raise AssertionError('Connection was allowed')
assert attempts == ['socket.getaddrinfo', 'socket.connect']
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_worker_timeout_and_failure_never_publish_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(archive_module, "environment_versions", lambda: ENVIRONMENT)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)

    monkeypatch.setattr(archive_module.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="timed out"):
        download_fastf1_session(QUERY, tmp_path / "timeout", timeout_s=1)
    assert not (tmp_path / "timeout/manifest.json").exists()
    monkeypatch.setattr(archive_module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    with pytest.raises(RuntimeError, match="load failed"):
        download_fastf1_session(QUERY, tmp_path / "failure")
    assert not (tmp_path / "failure/manifest.json").exists()


def test_cli_download_verify_and_replay(tmp_path, fake_worker):
    runner = CliRunner()
    root = tmp_path / "cli"
    result = runner.invoke(app, ["download-fastf1", "--year", "2024", "--round-number", "12", "--session", "Q", "--output", str(root)])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["verify-fastf1", str(root)])
    assert result.exit_code == 0 and json.loads(result.output)["passed"]
    result = runner.invoke(app, ["replay-fastf1", str(root), "--output", str(tmp_path / "replay")])
    assert result.exit_code == 0 and json.loads(result.output)["passed"]


@pytest.mark.parametrize("query", [(2017, 1, "Q"), (2024, True, "Q"), (2024, 1, "invalid"), (2024, 31, "R")])
def test_query_rejects_unsupported_values(query):
    with pytest.raises(ValueError):
        FastF1Query(*query)
