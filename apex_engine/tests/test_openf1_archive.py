import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import requests
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import openf1_archive as archive_module
from apexsim.data import openf1_http
from apexsim.data.openf1_archive import (
    ENDPOINTS,
    _decode,
    download_openf1_session,
    replay_openf1_archive,
    verify_openf1_archive,
)
from apexsim.data.openf1_http import DownloadPolicy, OpenF1Client
from apexsim.provenance import file_sha256, payload_sha256

SESSION_KEY = 9554
MEETING_KEY = 1240


def fixture_rows(endpoint, query):
    base = {"session_key": SESSION_KEY, "meeting_key": MEETING_KEY}
    if endpoint == "sessions":
        return [{**base, "year": 2024, "session_name": "Qualifying", "session_type": "Qualifying",
                 "date_start": "2024-07-06T14:00:00+00:00", "date_end": "2024-07-06T15:00:00+00:00"}]
    if endpoint == "meetings":
        return [{"meeting_key": MEETING_KEY, "meeting_name": "Fixture Grand Prix"}]
    if endpoint == "drivers":
        return [{**base, "driver_number": driver} for driver in (4, 81)]
    if endpoint in {"laps", "stints", "position"}:
        return [{**base, "driver_number": driver, "lap_number": 1, "duration": None,
                 "segments": [None, 2049]} for driver in (4, 81)]
    if endpoint in {"car_data", "location"}:
        row = {**base, **query, "date": "2024-07-06T14:05:00.000000123+00:00",
               "speed": 301, "nullable": None}
        return [row, {**row, "date": "2024-07-06T14:05:00.250000123+00:00", "extra": "preserved"}]
    if endpoint == "weather":
        return [{**base, "date": "2024-07-06T14:00:00+00:00", "air_temperature": 17.5}]
    return []


@pytest.fixture
def fake_source(monkeypatch):
    calls = []

    def get(self, endpoint, query):
        calls.append((endpoint, dict(query)))
        rows = fixture_rows(endpoint, query)
        status = 200 if rows else 404
        payload = rows if rows else {"detail": "No results found."}
        # Whitespace deliberately differs from the native JSONL reconstruction.
        body = json.dumps(payload, indent=2).encode()
        return body, {"status_code": status, "retrieved_at_utc": "2026-09-16T12:00:00+00:00",
                      "headers": {"content-type": "application/json"},
                      "attempts": [{"status_code": status, "started_at_utc": "2026-09-16T12:00:00+00:00"}]}

    monkeypatch.setattr(OpenF1Client, "get", get)
    return calls


def reseal(root, manifest):
    manifest.pop("content_sha256", None)
    manifest["content_sha256"] = payload_sha256(manifest)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_all_endpoints_relocate_and_rebuild_in_real_offline_worker(tmp_path, fake_source):
    root = tmp_path / "source"
    manifest = download_openf1_session(SESSION_KEY, root)
    assert len(manifest["requests"]) == 20
    assert {endpoint for endpoint, _ in fake_source} == set(ENDPOINTS)
    assert len(manifest["source_manifest"]["requests"]) == 20
    assert all(record["rows"] >= 0 for record in manifest["requests"])
    moved = tmp_path / "moved"
    shutil.copytree(root, moved)
    report = replay_openf1_archive(moved, tmp_path / "replay")
    assert report["passed"] and report["archive_unchanged"]
    assert report["network_attempts"] == 0
    assert report["endpoint_count"] == 18 and report["request_count"] == 20
    assert report["mismatched_tables"] == []
    assert "intervals" in report["empty_endpoints"]
    assert verify_openf1_archive(moved) == manifest
    snapshot = json.loads((moved / "snapshot.json").read_text())
    assert snapshot["tables"]["car_data"]["null_counts"]["nullable"] == 4
    assert snapshot["tables"]["car_data"]["missing_counts"]["extra"] == 2
    rows = [json.loads(line) for line in (moved / "tables/car_data.jsonl").read_text().splitlines()]
    assert rows[0]["date"] == "2024-07-06T14:05:00.000000123+00:00"
    assert rows[0]["speed"] == 301 and rows[0]["nullable"] is None and "extra" not in rows[0]
    assert len(fake_source) == 20  # Replay never calls the acquisition client.


def test_no_overwrite_or_nested_replay(tmp_path, fake_source):
    root = tmp_path / "source"
    download_openf1_session(SESSION_KEY, root)
    with pytest.raises(FileExistsError):
        download_openf1_session(SESSION_KEY, root)
    with pytest.raises(FileExistsError):
        replay_openf1_archive(root, root)
    with pytest.raises(ValueError, match="outside the frozen archive"):
        replay_openf1_archive(root, root / "nested")
    assert len(fake_source) == 20


@pytest.mark.parametrize("path", ["raw/0000.json", "raw/0000.request.json", "tables/laps.jsonl", "snapshot.json"])
def test_tampered_files_rejected_before_replay(tmp_path, fake_source, path):
    root = tmp_path / "source"
    download_openf1_session(SESSION_KEY, root)
    with (root / path).open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        replay_openf1_archive(root, tmp_path / "replay")
    assert not (tmp_path / "replay").exists()


@pytest.mark.parametrize("path", ["../escape", "/absolute", "C:/escape", "raw\\escape", "raw/../../escape"])
def test_rehashed_manifest_path_escape_rejected(tmp_path, fake_source, path):
    root = tmp_path / "source"
    manifest = download_openf1_session(SESSION_KEY, root)
    manifest["files"][path] = {"bytes": 1, "sha256": "x"}
    reseal(root, manifest)
    with pytest.raises(ValueError, match="artifact path"):
        verify_openf1_archive(root)


@pytest.mark.parametrize("change", ["unlisted", "missing", "manifest", "rows", "query", "source", "table"])
def test_archive_inventory_lineage_and_raw_equivalence(tmp_path, fake_source, change):
    root = tmp_path / "source"
    manifest = download_openf1_session(SESSION_KEY, root)
    if change == "unlisted":
        (root / "raw/extra.json").write_text("[]")
    elif change == "missing":
        (root / "raw/0000.json").unlink()
    elif change == "manifest":
        manifest["identity"]["year"] = 1999
        (root / "manifest.json").write_text(json.dumps(manifest))
    elif change == "rows":
        manifest["requests"][0]["rows"] = 200
        reseal(root, manifest)
    elif change == "query":
        manifest["requests"][0]["query"]["session_key"] = 1
        reseal(root, manifest)
    elif change == "source":
        source = manifest["source_manifest"]
        source["requests"] = []
        source.pop("content_sha256")
        source["content_sha256"] = payload_sha256(source)
        reseal(root, manifest)
    else:
        (root / "tables/laps.jsonl").write_text('{}\n')
        manifest["files"]["tables/laps.jsonl"] = {"bytes": (root / "tables/laps.jsonl").stat().st_size,
                                                   "sha256": file_sha256(root / "tables/laps.jsonl")}
        reseal(root, manifest)
    with pytest.raises(ValueError):
        verify_openf1_archive(root)


@pytest.mark.parametrize("change", ["session", "meeting", "driver", "duplicate-driver", "empty-weather", "missing-car", "live"])
def test_incomplete_or_incorrect_source_never_publishes_manifest(tmp_path, fake_source, monkeypatch, change):
    original = OpenF1Client.get

    def changed(self, endpoint, query):
        body, metadata = original(self, endpoint, query)
        rows = json.loads(body)
        if change == "session" and endpoint == "sessions":
            rows[0]["session_key"] = 1
        if change == "meeting" and endpoint == "meetings":
            rows[0]["meeting_key"] = 1
        if change == "driver" and endpoint == "car_data":
            rows[0]["driver_number"] = 999
        if change == "duplicate-driver" and endpoint == "drivers":
            rows.append(rows[0])
        if (change == "empty-weather" and endpoint == "weather") or (
                change == "missing-car" and endpoint == "car_data" and query["driver_number"] == 81):
            rows = []
        if change == "live" and endpoint == "sessions":
            rows[0]["date_end"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        return json.dumps(rows).encode(), metadata

    monkeypatch.setattr(OpenF1Client, "get", changed)
    with pytest.raises(ValueError):
        download_openf1_session(SESSION_KEY, tmp_path / "source")
    assert not (tmp_path / "source/manifest.json").exists()
    assert (tmp_path / "source/raw/0000.json").exists()


@pytest.mark.parametrize("body,status", [(b'{}', 200), (b'[1]', 200), (b'[{"x":NaN}]', 200),
                                        (b'[{"x":1e999}]', 200), (b'[{"x":1,"x":2}]', 200),
                                        (b'{"detail":"Not Found"}', 404), (b'[]', 403), (b'<html>', 200)])
def test_bad_json_or_http_status_is_not_an_empty_endpoint(body, status):
    with pytest.raises(ValueError):
        _decode(body, status)


@pytest.mark.parametrize("session_key", [0, -1, True, "latest", 9554.0])
def test_invalid_session_identity_fails_before_output(tmp_path, session_key):
    with pytest.raises(ValueError, match="positive integer"):
        download_openf1_session(session_key, tmp_path / "source")
    assert not (tmp_path / "source").exists()


def test_worker_failure_and_timeout(tmp_path, fake_source, monkeypatch):
    root = tmp_path / "source"
    download_openf1_session(SESSION_KEY, root)
    monkeypatch.setattr(archive_module.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))
    with pytest.raises(RuntimeError, match="replay failed"):
        replay_openf1_archive(root, tmp_path / "failed")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)

    monkeypatch.setattr(archive_module.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="timed out"):
        replay_openf1_archive(root, tmp_path / "timeout")
    verify_openf1_archive(root)


def test_cli_download_verify_and_replay(tmp_path, fake_source):
    runner = CliRunner()
    root = tmp_path / "cli"
    result = runner.invoke(app, ["download-openf1", "--session-key", str(SESSION_KEY), "--output", str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["requests"] == 20
    result = runner.invoke(app, ["verify-openf1", str(root)])
    assert result.exit_code == 0 and json.loads(result.output)["passed"]
    result = runner.invoke(app, ["replay-openf1", str(root), "--output", str(tmp_path / "replay")])
    assert result.exit_code == 0 and json.loads(result.output)["passed"]


def test_network_guard_rejects_real_dns_and_socket_in_child_process():
    code = '''
import socket
from apexsim.data.openf1_worker import install_network_guard
attempts = install_network_guard()
for operation in [lambda: socket.getaddrinfo("example.test", 443),
                  lambda: socket.socket().connect(("127.0.0.1", 9))]:
    try:
        operation()
    except RuntimeError:
        pass
    else:
        raise AssertionError("network was allowed")
assert attempts == ["socket.getaddrinfo", "socket.connect"]
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


class FakeResponse:
    def __init__(self, status=200, body=b"[]", headers=None):
        self.status_code, self.body, self.headers = status, body, headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, **kwargs):
        yield self.body


def http_client(monkeypatch, responses, policy=None):
    client = OpenF1Client(policy or DownloadPolicy())
    calls, delays = [], []
    responses = iter(responses)

    def get(*args, **kwargs):
        calls.append(kwargs)
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(client.session, "get", get)
    monkeypatch.setattr(openf1_http.time, "sleep", delays.append)
    return client, calls, delays


def test_http_bounded_retries_throttling_and_metadata(monkeypatch):
    client, calls, delays = http_client(monkeypatch, [FakeResponse(429, headers={"Retry-After": "3"}),
                                                    FakeResponse(503), requests.Timeout(), FakeResponse()])
    body, metadata = client.get("weather", {"session_key": SESSION_KEY})
    assert body == b"[]" and len(metadata["attempts"]) == 4
    assert delays[0] == 3.0 and len(calls) == 4
    assert all(not call["allow_redirects"] and call["stream"] for call in calls)
    assert "APEX/" in client.session.headers["User-Agent"]
    client.close()


def test_http_exhaustion_size_limit_and_retry_after_bound(monkeypatch):
    client, calls, _ = http_client(monkeypatch, [FakeResponse(500)] * 2, DownloadPolicy(max_attempts=2))
    with pytest.raises(RuntimeError, match="after 2 attempts"):
        client.get("weather", {})
    assert len(calls) == 2
    client, _, _ = http_client(monkeypatch, [FakeResponse(body=b"123")], DownloadPolicy(max_response_bytes=2))
    with pytest.raises(ValueError, match="byte limit"):
        client.get("weather", {})
    client, calls, _ = http_client(monkeypatch, [FakeResponse(429, headers={"Retry-After": "3600"})])
    with pytest.raises(RuntimeError, match="bounded wait"):
        client.get("weather", {})
    assert len(calls) == 1


@pytest.mark.parametrize("policy", [{"spacing_s": 0}, {"timeout_s": float("nan")}, {"max_attempts": 0},
                                    {"max_response_bytes": True}, {"max_retry_wait_s": -1}])
def test_invalid_download_policy(policy):
    with pytest.raises(ValueError):
        DownloadPolicy(**policy)
