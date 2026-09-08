import json
from pathlib import Path

import pytest

from apexsim.data.manifest import SOURCE_MANIFEST_SCHEMA, SourceManifest, load_source_manifest
from apexsim.data.openf1_adapter import ingest_openf1_session


def test_source_manifest_is_immutable_and_tamper_evident(tmp_path: Path):
    source = tmp_path / "raw.json"
    source.write_text('[{"speed": 300}]\n', encoding="utf-8")
    manifest_path = tmp_path / "source-manifest.json"
    manifest = SourceManifest(
        source="fixture",
        query={"session": 99},
        terms_url="https://example.test/terms",
        license_id="TEST-ONLY",
    )
    manifest.add_request(
        "https://example.test/api/telemetry",
        {"session": 99},
        [{"speed": 300}],
        records=1,
    )
    manifest.add_file(source, rows=1)
    manifest.save(manifest_path)

    loaded = load_source_manifest(manifest_path)
    assert loaded["schema_version"] == SOURCE_MANIFEST_SCHEMA
    assert loaded["requests"][0]["payload_sha256"]
    assert loaded["files"][0]["sha256"]
    assert loaded["content_sha256"]

    with pytest.raises(FileExistsError):
        manifest.save(manifest_path)


def test_source_manifest_detects_content_and_file_tampering(tmp_path: Path):
    source = tmp_path / "raw.json"
    source.write_text("{}\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = SourceManifest("fixture", {"id": 1}, "https://example.test/terms")
    manifest.add_file(source)
    manifest.save(manifest_path)

    source.write_text('{"changed": true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        load_source_manifest(manifest_path)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["query"] = {"id": 2}
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        load_source_manifest(manifest_path, verify_files=False)


def test_openf1_adapter_records_each_request_and_refuses_overwrite(tmp_path: Path, monkeypatch):
    dates = [
        "2026-01-01T00:00:00.000Z",
        "2026-01-01T00:00:00.250Z",
        "2026-01-01T00:00:00.500Z",
        "2026-01-01T00:00:00.750Z",
    ]
    payloads = {
        "car_data": [
            {
                "date": date,
                "speed": 180 + index,
                "throttle": 80,
                "brake": 0,
                "n_gear": 6,
                "drs": 1,
                "rpm": 10_500,
            }
            for index, date in enumerate(dates)
        ],
        "location": [
            {"date": date, "x": index * 10.0, "y": index * 2.0}
            for index, date in enumerate(dates)
        ],
        "weather": [
            {
                "date": date,
                "air_temperature": 24.0,
                "track_temperature": 31.0,
                "rainfall": 0.0,
                "wind_speed": 2.5,
            }
            for date in dates
        ],
    }
    requests = []

    def fake_get(endpoint, params, timeout=60):
        requests.append((endpoint, params, timeout))
        return payloads[endpoint]

    monkeypatch.setattr("apexsim.data.openf1_adapter._get", fake_get)
    output = tmp_path / "canonical.csv"
    canonical = ingest_openf1_session(99, 4, output, sample_hz=4)
    manifest_path = tmp_path / "canonical.csv.source.json"
    manifest = load_source_manifest(manifest_path)

    assert len(canonical) == 3
    assert [request[0] for request in requests] == ["car_data", "location", "weather"]
    assert len(manifest["requests"]) == 3
    assert all(request["payload_sha256"] for request in manifest["requests"])
    assert manifest["files"][0]["role"] == "derived_canonical"

    with pytest.raises(FileExistsError):
        ingest_openf1_session(99, 4, output, sample_hz=4)
