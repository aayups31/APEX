import json
import shutil
from dataclasses import replace

import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import event_corpus as module
from apexsim.data.event_corpus import CorpusSession, freeze_event_corpus, verify_event_corpus
from apexsim.data.manifest import SourceManifest
from apexsim.provenance import payload_sha256


def sealed(path, value):
    value = {k: v for k, v in value.items() if k != "content_sha256"}
    value["content_sha256"] = payload_sha256(value)
    path.write_text(json.dumps(value))
    return value


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    """Provider metadata fixture; provider byte/row integrity has its own existing tests."""
    specs = []
    for round_number in (12, 16):
        base = tmp_path / f"event-{round_number}"
        roots = {n: base / n for n in ("fastf1", "openf1", "jolpica", "observed")}
        for path in roots.values():
            path.mkdir(parents=True)
        key = 9500 + round_number
        link = {"schema_version": "apex-session-link-v1", "season": 2024, "round_number": round_number,
                "session_code": "Q", "session_date": "2024-07-06", "fastf1_event_name": "Fixture GP",
                "openf1_session_key": key, "openf1_meeting_key": round_number, "openf1_circuit_key": 2,
                "jolpica_circuit_id": "fixture", "rationale": "Synthetic link"}
        (roots["observed"] / "session_link.json").write_text(json.dumps(link))
        manifests = {
            "fastf1": {"query": {"year": 2024, "round_number": round_number, "session": "Q"},
                       "identity": {"event_name": "Fixture GP", "session_name": "Qualifying", "drivers": ["4"],
                                    "t0_date": "2024-07-06T14:00:00", "session_start_time_s": 0,
                                    "api_path": f"fixture/{round_number}"}},
            "openf1": {"query": {"session_key": key}, "identity": {"year": 2024, "session_key": key,
                       "meeting_key": round_number, "circuit_key": 2, "session_name": "Qualifying",
                       "date_start": "2024-07-06T14:00:00+00:00"}},
            "jolpica": {"query": {"season": 2024}, "pages": [{"path": "page.json"}]}}
        (roots["jolpica"] / "page.json").write_text(json.dumps({"MRData": {"RaceTable": {"Races": [
            {"round": str(round_number), "Circuit": {"circuitId": "fixture"},
             "Qualifying": {"date": "2024-07-06", "time": "14:00:00Z"}}]}}}))
        for name, value in manifests.items():
            source = SourceManifest(name, value["query"], "https://example.test/terms")
            value.update(schema_version=f"fixture-{name}-v1", environment={"python": "fixture"},
                         source_manifest=source.to_dict(), files={"fixture": {"bytes": 1}})
            manifests[name] = sealed(roots[name] / "manifest.json", value)
        identity = module.validate_link(link, manifests["fastf1"], manifests["openf1"], manifests["jolpica"], roots["jolpica"])
        providers = {n: {"table_rows": {"sessions": 1}, "null_counts": {}, "issues": []} for n in ("fastf1", "openf1")}
        report = {"identity": identity, "source_archives_sha256": {n: m["content_sha256"] for n, m in manifests.items()},
                  "providers": providers, "schema_version": "fixture-observed-v1", "environment": {"python": "fixture"},
                  "implementation_sha256": "a" * 64}
        sealed(roots["observed"] / "report.json", report)
        (roots["observed"] / "manifest.json").write_text('{}')
        for name in providers:
            (roots["observed"] / name).mkdir()
            sealed(roots["observed"] / name / "manifest.json", {"schema_version": module.DATASET_VERSION})
        specs.append(CorpusSession(**{n: p.relative_to(tmp_path).as_posix() for n, p in roots.items()}, rationale="Synthetic development event"))

    def verified(path):
        value = json.loads((path / "manifest.json").read_text())
        assert value["content_sha256"] == payload_sha256({k: v for k, v in value.items() if k != "content_sha256"})
        return value
    for name in ("fastf1", "openf1", "jolpica"):
        monkeypatch.setattr(module, f"verify_{name}_archive", verified)
    monkeypatch.setattr(module, "verify_observed_tables", lambda path: json.loads((path / "report.json").read_text()))
    return tmp_path, specs


def test_collection_relocation_and_exclusive_output(evidence):
    root, specs = evidence
    output = root / "corpus.json"
    manifest = freeze_event_corpus(root, specs[::-1], output, purpose="Development acquisition evidence")
    assert manifest["event_count"] == manifest["session_count"] == 2
    assert not manifest["training_ready"] and not manifest["benchmark_frozen"]
    assert [e["round_number"] for e in manifest["entries"]] == [12, 16]
    assert verify_event_corpus(output, root) == manifest
    moved = root / "moved"
    moved.mkdir()
    for name in ("event-12", "event-16"):
        shutil.copytree(root / name, moved / name)
    assert verify_event_corpus(output, moved) == manifest
    with pytest.raises(FileExistsError):
        freeze_event_corpus(root, specs, output, purpose="Cannot overwrite")


@pytest.mark.parametrize("failure", ["one_event", "duplicate", "benchmark", "rationale", "traversal", "absolute", "nested", "lineage", "provider_alias", "missing_version"])
def test_invalid_collection_never_publishes(evidence, failure):
    root, specs = evidence
    output = root / "failed.json"
    if failure == "one_event":
        specs = specs[:1]
    elif failure == "duplicate":
        specs = [*specs, specs[0]]
    elif failure in ("benchmark", "rationale", "traversal", "absolute"):
        changes = {"benchmark": {"role": "BENCHMARK"}, "rationale": {"rationale": ""},
                   "traversal": {"fastf1": "../outside"}, "absolute": {"fastf1": "/outside"}}[failure]
        specs[0] = replace(specs[0], **changes)
    elif failure == "nested":
        output = root / specs[0].fastf1 / "bad.json"
    elif failure == "lineage":
        path = root / specs[0].observed / "report.json"
        report = json.loads(path.read_text())
        report["source_archives_sha256"]["fastf1"] = "bad"
        path.write_text(json.dumps(report))
    else:
        path = root / specs[1].fastf1 / "manifest.json"
        value = json.loads(path.read_text())
        if failure == "provider_alias":
            value["identity"]["api_path"] = "fixture/12"
        else:
            value["environment"] = {}
        value = sealed(path, value)
        report_path = root / specs[1].observed / "report.json"
        report = json.loads(report_path.read_text())
        report["source_archives_sha256"]["fastf1"] = value["content_sha256"]
        report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        freeze_event_corpus(root, specs, output, purpose="Rejected collection")
    assert not output.exists()


def test_manifest_and_bound_metadata_tampering(evidence):
    root, specs = evidence
    output = root / "corpus.json"
    manifest = freeze_event_corpus(root, specs, output, purpose="Fixture")
    output.write_text(output.read_text() + ' ')
    assert verify_event_corpus(output, root) == manifest  # JSON whitespace is not content.
    manifest["event_count"] = 1
    output.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="hash"):
        verify_event_corpus(output, root)
    sealed(output, manifest)
    with pytest.raises(ValueError, match="membership"):
        verify_event_corpus(output, root)


def test_corpus_cli(evidence):
    root, specs = evidence
    from dataclasses import asdict
    config = root / "members.json"
    config.write_text(json.dumps([asdict(s) for s in specs]))
    runner = CliRunner()
    output = root / "cli.json"
    result = runner.invoke(app, ["freeze-event-corpus", str(root), str(config), str(output), "Development fixture"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["verify-event-corpus", str(output), str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["event_count"] == 2


def test_source_mutation_during_freeze(evidence, monkeypatch):
    root, specs = evidence
    original = module._entry
    calls = [0]
    def changing(*args):
        result = original(*args)
        calls[0] += 1
        if calls[0] > 2:
            result["observed_manifest_sha256"] = "changed"
        return result
    monkeypatch.setattr(module, "_entry", changing)
    with pytest.raises(ValueError, match="changed during"):
        freeze_event_corpus(root, specs, root / "mutation.json", purpose="Fixture")
    assert not (root / "mutation.json").exists()
