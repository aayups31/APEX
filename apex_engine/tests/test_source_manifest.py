import json
from pathlib import Path

import pytest

from apexsim.data.fastf1_adapter import ingest_fastf1_session
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


@pytest.mark.parametrize("provider", ["fastf1", "openf1"])
@pytest.mark.parametrize("existing", [False, True])
def test_retired_public_adapter_never_downloads_or_writes(tmp_path, monkeypatch, provider, existing):
    def unexpected(*args, **kwargs):
        raise AssertionError("Retired converter attempted a request")

    monkeypatch.setattr("requests.get", unexpected)
    output = tmp_path / "canonical.csv"
    if existing:
        output.write_bytes(b"preserved legacy evidence")
    with pytest.raises(ValueError, match="build-observed-tables"):
        if provider == "fastf1":
            ingest_fastf1_session(2024, "British", "Q", "4", output)
        else:
            ingest_openf1_session(9554, 4, output)
    assert sorted(p.name for p in tmp_path.iterdir()) == (["canonical.csv"] if existing else [])
    if existing:
        assert output.read_bytes() == b"preserved legacy evidence"


@pytest.mark.parametrize("command,args", [
    ("ingest-fastf1", ["2024", "British", "Q", "4"]),
    ("ingest-openf1", ["9554", "4"]),
])
def test_retired_cli_gives_migration_instructions(tmp_path, command, args):
    from typer.testing import CliRunner

    from apexsim.cli import app

    result = CliRunner().invoke(app, [command, *args, "--output", str(tmp_path / "out.csv")])
    assert result.exit_code != 0
    assert "build-observed-tables" in result.output
    assert not list(tmp_path.iterdir())
