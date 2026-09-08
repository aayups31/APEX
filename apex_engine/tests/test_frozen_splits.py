import copy
import json

import pandas as pd
import pytest

from apexsim.config import DataConfig, ProjectConfig
from apexsim.contracts import MODEL_INPUT_COLUMNS, TARGET_COLUMNS
from apexsim.data.splits import freeze_splits, load_splits, validate_assignments
from apexsim.data.tables import make_table, read_dataset
from apexsim.examples.public_data_demo import run_public_data_demo
from apexsim.pipeline.stages import dataset_stage
from apexsim.provenance import payload_sha256


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "evidence"
    run_public_data_demo(root)
    return root


def test_split_is_frozen_deterministic_and_bound_to_dataset(bundle):
    first = load_splits(bundle / "splits.json", bundle / "dataset")
    second = freeze_splits(bundle / "dataset", {name: list(reversed(members)) for name, members in first["partitions"].items()},
                           bundle / "same.json", purpose=first["purpose"])
    assert first == second
    assert (bundle / "splits.json").read_bytes() == (bundle / "same.json").read_bytes()
    with pytest.raises(FileExistsError):
        freeze_splits(bundle / "dataset", first["partitions"], bundle / "splits.json", purpose="new")
    with pytest.raises(ValueError, match="exactly match"):
        load_splits(bundle / "splits.json", bundle / "dataset", session_ids=["unexpected-session"])
    # A different source retrieval creates a different evidence identity even if the values match.
    other = bundle.parent / "other"
    run_public_data_demo(other)
    with pytest.raises(ValueError, match="dataset identity mismatch"):
        load_splits(bundle / "splits.json", other / "dataset")


def test_reject_event_leakage_even_when_sessions_are_disjoint(bundle):
    tables, _ = read_dataset(bundle / "dataset")
    splits = load_splits(bundle / "splits.json", bundle / "dataset")["partitions"]
    changed = copy.deepcopy(splits)
    changed["train"][1], changed["test"][1] = changed["test"][1], changed["train"][1]
    with pytest.raises(ValueError, match="Event leakage"):
        validate_assignments(tables["sessions"], changed)


@pytest.mark.parametrize(("case", "message"), [
    ("duplicate", "duplicate or overlapping"),
    ("overlap", "duplicate or overlapping"),
    ("missing", "Unassigned sessions"),
    ("unknown", "unknown session_id"),
    ("empty", "nonempty session list"),
    ("string", "nonempty session list"),
    ("partition", "exactly train, val and test"),
])
def test_bad_partition_contracts(bundle, case, message):
    tables, _ = read_dataset(bundle / "dataset")
    splits = load_splits(bundle / "splits.json", bundle / "dataset")["partitions"]
    if case == "duplicate":
        splits["train"].append(splits["train"][0])
    elif case == "overlap":
        splits["val"].append(splits["train"][0])
    elif case == "missing":
        splits["train"].pop()
    elif case == "unknown":
        splits["val"].append("not-a-session")
    elif case == "empty":
        splits["test"] = []
    elif case == "string":
        splits["test"] = "SYNTH_2_Q"
    else:
        splits["holdout"] = splits.pop("test")
    with pytest.raises(ValueError, match=message):
        validate_assignments(tables["sessions"], splits)


def test_same_public_session_cannot_hide_under_two_event_identities(bundle):
    # Source aliases must not permit one physical session to leak across events.
    tables, _ = read_dataset(bundle / "dataset")
    rows = tables["sessions"].to_pylist()
    rows[2]["source_session_id"] = rows[0]["source_session_id"]
    assignments = load_splits(bundle / "splits.json", bundle / "dataset")["partitions"]
    with pytest.raises(ValueError, match="source session identity"):
        validate_assignments(make_table("sessions", rows), assignments)


def test_tampering_and_rehashed_leakage_are_rejected(bundle):
    path = bundle / "splits.json"
    payload = json.loads(path.read_text())
    payload["purpose"] = "changed"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="content hash mismatch"):
        load_splits(path, bundle / "dataset")
    payload["partitions"]["train"][1], payload["partitions"]["test"][1] = payload["partitions"]["test"][1], payload["partitions"]["train"][1]
    payload.pop("content_sha256")
    payload["content_sha256"] = payload_sha256(payload)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Event leakage"):
        load_splits(path, bundle / "dataset")


def test_event_aliases_cannot_split_the_same_season_round(bundle):
    tables, _ = read_dataset(bundle / "dataset")
    rows = tables["sessions"].to_pylist()
    rows[2]["round"] = rows[0]["round"]
    assignments = load_splits(bundle / "splits.json", bundle / "dataset")["partitions"]
    with pytest.raises(ValueError, match="season/round"):
        validate_assignments(make_table("sessions", rows), assignments)


def test_pipeline_uses_frozen_partitions_and_fits_scaler_only_on_training(bundle, tmp_path):
    config = ProjectConfig(data=DataConfig(public_dataset_path=bundle / "dataset", split_manifest_path=bundle / "splits.json"))
    rows = []
    for event in range(3):
        for session_type in ("Q", "R"):
            row = dict.fromkeys(set(MODEL_INPUT_COLUMNS + TARGET_COLUMNS), 10.0 if event == 0 else 10000.0)
            rows.append({**row, "session_id": f"SYNTH_{event}_{session_type}"})
    canonical = tmp_path / "canonical.csv"
    pd.DataFrame(rows).to_csv(canonical, index=False)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = dataset_stage(config, canonical, run_dir)
    assert result["splits"] == load_splits(bundle / "splits.json", bundle / "dataset")["partitions"]
    assert set(result["standardizer"]["input_mean"]) == {10.0}
    assert (run_dir / "split_manifest.json").is_file()
    second_run = tmp_path / "second-run"
    second_run.mkdir()
    pd.DataFrame(rows[:-1]).to_csv(canonical, index=False)
    with pytest.raises(ValueError, match="exactly match"):
        dataset_stage(config, canonical, second_run)
    assert not (second_run / "standardizer.json").exists()


def test_frozen_split_config_requires_both_paths():
    with pytest.raises(ValueError, match="supplied together"):
        DataConfig(split_manifest_path="split.json")
