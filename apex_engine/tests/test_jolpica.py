import json
import shutil
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import openf1_http
from apexsim.data.jolpica import (
    BASE_URL,
    JolpicaClient,
    download_jolpica_events,
    read_jolpica_events,
    verify_jolpica_archive,
)
from apexsim.data.openf1_http import DownloadPolicy
from apexsim.provenance import file_sha256, payload_sha256


def race(round_number):
    result = {"season": "2024", "round": str(round_number), "raceName": f"Fixture {round_number}",
              "date": "2024-07-07", "Circuit": {"circuitId": f"circuit_{round_number}",
                                                "Location": {"lat": "51.0", "long": "-1.0"}},
              "Qualifying": {"date": "2024-07-06", "time": "14:00:00Z"}}
    if round_number != 2:
        result["time"] = "14:00:00Z"
    return result


def page(offset, limit=2, total=5):
    return {"MRData": {"series": "f1", "limit": str(limit), "offset": str(offset), "total": str(total),
                       "RaceTable": {"season": "2024", "Races": [race(i + 1) for i in range(offset, min(offset + limit, total))]}}}


@pytest.fixture
def fake_source(monkeypatch):
    calls = []

    def get(self, endpoint, query):
        calls.append({"endpoint": endpoint, "query": dict(query), "user_agent": self.session.headers["User-Agent"]})
        payload = page(query["offset"], limit=query["limit"])
        return json.dumps(payload, indent=2).encode(), {
            "status_code": 200, "retrieved_at_utc": "2026-09-17T02:00:00+00:00", "headers": {},
            "attempts": [{"status_code": 200, "started_at_utc": "2026-09-17T02:00:00+00:00"}]}

    monkeypatch.setattr(JolpicaClient, "get", get)
    return calls


def reseal(root, manifest):
    manifest.pop("content_sha256", None)
    manifest["content_sha256"] = payload_sha256(manifest)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_all_pages_custom_user_agent_portability_and_offline_rebuild(tmp_path, fake_source):
    root = tmp_path / "archive"
    manifest = download_jolpica_events(2024, root, page_size=2)
    assert manifest["event_count"] == 5 and len(manifest["pages"]) == 3
    assert [call["query"]["offset"] for call in fake_source] == [0, 2, 4]
    assert all(call["user_agent"].startswith("APEX/") for call in fake_source)
    moved = tmp_path / "moved"
    shutil.copytree(root, moved)
    assert verify_jolpica_archive(moved) == manifest
    events = read_jolpica_events(moved)
    assert [event["event_id"] for event in events] == [f"F1_2024_R{i:02d}" for i in range(1, 6)]
    assert events[1]["race_time_utc"] is None
    assert events[1]["truth_labels"]["race_time_utc"] == "UNKNOWN"
    # Exercise reconstruction in a separate interpreter with actual socket access denied.
    code = '''
import sys
from apexsim.data.jolpica import verify_jolpica_archive
attempts = []
def guard(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto', 'socket.sendmsg'}:
        attempts.append(event)
        raise RuntimeError('network forbidden')
sys.addaudithook(guard)
assert verify_jolpica_archive(sys.argv[1])['event_count'] == 5
assert attempts == []
'''
    result = subprocess.run([sys.executable, "-c", code, str(moved)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert len(fake_source) == 3


@pytest.mark.parametrize("change", ["offset", "total", "empty", "duplicate", "season", "series", "rows", "date", "time", "http"])
def test_broken_source_pages_never_publish_a_manifest(tmp_path, fake_source, monkeypatch, change):
    original = JolpicaClient.get

    def get(self, endpoint, query):
        body, metadata = original(self, endpoint, query)
        payload = json.loads(body)
        if query["offset"] == 2:
            data = payload["MRData"]
            races = data["RaceTable"]["Races"]
            if change == "offset":
                data["offset"] = "0"
            elif change == "total":
                data["total"] = "6"
            elif change == "empty":
                data["RaceTable"]["Races"] = []
            elif change == "duplicate":
                races[0]["round"] = "1"
            elif change == "season":
                races[0]["season"] = "2023"
            elif change == "series":
                data["series"] = "f2"
            elif change == "rows":
                races.append(race(6))
            elif change == "date":
                races[0]["date"] = "invalid"
            elif change == "time":
                races[0]["time"] = "14:00:00"
            elif change == "http":
                metadata["status_code"] = 403
        return json.dumps(payload).encode(), metadata

    monkeypatch.setattr(JolpicaClient, "get", get)
    with pytest.raises(ValueError):
        download_jolpica_events(2024, tmp_path / "failed", page_size=2)
    assert not (tmp_path / "failed/manifest.json").exists()
    assert len(fake_source) == 2


def test_short_pages_advance_by_actual_count_and_empty_season(tmp_path, fake_source, monkeypatch):
    original = JolpicaClient.get

    def short(self, endpoint, query):
        _, metadata = original(self, endpoint, query)
        return json.dumps(page(query["offset"], limit=1)).encode(), metadata

    monkeypatch.setattr(JolpicaClient, "get", short)
    manifest = download_jolpica_events(2024, tmp_path / "short", page_size=5)
    assert len(manifest["pages"]) == 5
    assert [r["query"]["offset"] for r in manifest["pages"]] == list(range(5))
    verify_jolpica_archive(tmp_path / "short")

    def empty(self, endpoint, query):
        _, metadata = original(self, endpoint, query)
        return json.dumps(page(0, total=0)).encode(), metadata

    monkeypatch.setattr(JolpicaClient, "get", empty)
    manifest = download_jolpica_events(2024, tmp_path / "empty")
    assert manifest["event_count"] == 0 and len(manifest["pages"]) == 1
    assert read_jolpica_events(tmp_path / "empty") == []


@pytest.mark.parametrize("file", ["raw/0000.json", "raw/0000.request.json", "events.json"])
def test_tampered_files_fail(tmp_path, fake_source, file):
    root = tmp_path / "archive"
    download_jolpica_events(2024, root)
    with (root / file).open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        verify_jolpica_archive(root)


@pytest.mark.parametrize("change", ["manifest", "extra", "missing", "truncated", "lineage", "catalog", "path"])
def test_inventory_lineage_and_reconstruction_checks(tmp_path, fake_source, change):
    root = tmp_path / "archive"
    manifest = download_jolpica_events(2024, root, page_size=2)
    if change == "manifest":
        manifest["event_count"] = 999
        (root / "manifest.json").write_text(json.dumps(manifest))
    elif change == "extra":
        (root / "extra.json").write_text("{}")
    elif change == "missing":
        (root / "raw/0000.json").unlink()
    elif change == "truncated":
        manifest["pages"].pop()
        reseal(root, manifest)
    elif change == "lineage":
        source = manifest["source_manifest"]
        source["requests"] = []
        source.pop("content_sha256")
        source["content_sha256"] = payload_sha256(source)
        reseal(root, manifest)
    elif change == "catalog":
        (root / "events.json").write_text("{}")
        manifest["files"]["events.json"] = {"bytes": 2, "sha256": file_sha256(root / "events.json")}
        reseal(root, manifest)
    elif change == "path":
        manifest["files"]["../escape"] = {"bytes": 1, "sha256": "x"}
        reseal(root, manifest)
    with pytest.raises(ValueError):
        verify_jolpica_archive(root)


@pytest.mark.parametrize("season,limit", [(True, 5), (2024, True), (1949, 5), (2024, 0), (2024, 101), ("current", 5)])
def test_invalid_queries_do_not_create_directories(tmp_path, season, limit):
    with pytest.raises(ValueError):
        download_jolpica_events(season, tmp_path / "invalid", page_size=limit)
    assert not (tmp_path / "invalid").exists()


def test_cli_and_immutable_outputs(tmp_path, fake_source):
    runner, root = CliRunner(), tmp_path / "archive"
    result = runner.invoke(app, ["download-jolpica", "--season", "2024", "--page-size", "2", "--output", str(root)])
    assert result.exit_code == 0 and json.loads(result.output)["events"] == 5
    result = runner.invoke(app, ["verify-jolpica", str(root)])
    assert result.exit_code == 0 and json.loads(result.output)["passed"]
    result = runner.invoke(app, ["list-events", str(root)])
    assert result.exit_code == 0 and len(json.loads(result.output)) == 5
    with pytest.raises(FileExistsError):
        download_jolpica_events(2024, root)
    assert len(fake_source) == 3


def test_jolpica_transport_url_user_agent_pacing_and_rate_limit_retry(monkeypatch):
    client, calls, waits = JolpicaClient(), [], []
    assert client.policy.spacing_s == 7.3
    assert client.source_name == "Jolpica" and client.base_url == BASE_URL
    monkeypatch.setattr(openf1_http.time, "sleep", waits.append)
    responses = iter([429, 200])

    class Response:
        def __init__(self):
            self.headers = {"Retry-After": "8"}
            self.status_code = next(responses)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_content(self, **kwargs):
            yield b'{}'

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(client.session, "get", get)
    _, metadata = client.get("2024/races/", {"offset": 0, "limit": 5})
    assert all(url == f"{BASE_URL}/2024/races/" for url, _ in calls)
    assert client.session.headers["User-Agent"].startswith("APEX/")
    assert len(metadata["attempts"]) == 2 and waits[0] == 8
    client.close()
    with pytest.raises(ValueError, match="500/hour"):
        JolpicaClient(DownloadPolicy(spacing_s=2.1))
