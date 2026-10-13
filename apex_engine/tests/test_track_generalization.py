import copy
import json
import shutil

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples.track_generalization_demo import (
    make_generalization_smoke_dataset,
    run_track_generalization,
    verify_track_generalization,
)
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.research import forecast_benchmark
from apexsim.research.forecast_benchmark import build_forecast_windows
from apexsim.research.track_generalization import (
    COHORT,
    EVENTS,
    classify_tracks,
    frozen_family_decision,
    generalization_scores,
)
from apexsim.research.tyre_energy_dataset import build_tyre_energy_dataset


def hand_case():
    metadata, values = [], []
    for i, (event, track) in enumerate(COHORT.items()):
        for _ in range(1 if i % 2 == 0 else 9):
            metadata.append({"event_id": event, "track_id": track, "sequence_id": event+"_sequence",
                             "driver_id": "4", "compound": "MEDIUM"})
            values.append(np.full((3, 4), (1, 3, 2, 4)[i], dtype=float))
    actual = np.array(values)
    return actual, metadata


def test_equal_event_mse_and_paired_uncertainty_hand_fixture():
    actual, metadata = hand_case()
    scores = generalization_scores(actual, {"persistence": np.zeros_like(actual), "perfect": actual}, metadata,
                                   ["bahrain", "albert_park"], {"xgboost": ["perfect"]}, resamples=40)
    seen = scores["strata"]["seen"]["methods"]
    unseen = scores["strata"]["unseen"]["methods"]
    assert seen["persistence"]["equal_event_mse_kj2"] == pytest.approx((1+9)/2)
    assert seen["persistence"]["frame_weighted"]["rmse_kj"]**2 == pytest.approx((1+9*9)/10)
    assert unseen["persistence"]["equal_event_mse_kj2"] == pytest.approx((4+16)/2)
    assert seen["perfect"]["equal_event_rmse_interval_95_kj"] == [0, 0]
    assert scores["unseen_minus_seen"]["persistence"]["unseen_minus_seen_equal_event_mse_kj2"] == pytest.approx(5)
    assert frozen_family_decision(scores, "xgboost") == "SUPPORTED_IN_FROZEN_DEVELOPMENT_COHORT"
    changed = copy.deepcopy(scores)
    changed["strata"]["unseen"]["methods"]["xgboost_family"]["paired_mse_minus_persistence_interval_95_kj2"][1] = 0
    assert frozen_family_decision(changed, "xgboost") == "NO_CROSS_TRACK_PROMOTION"


def test_seed_losses_are_not_ensemble_predictions_or_independent_events():
    actual, metadata = hand_case()
    predictions = {"persistence": np.zeros_like(actual), "seed11": actual-1, "seed23": actual+1}
    scores = generalization_scores(actual, predictions, metadata, ["bahrain", "albert_park"], {"xgboost": ["seed11", "seed23"]}, resamples=40)
    assert scores["strata"]["seen"]["methods"]["xgboost_family"]["equal_event_mse_kj2"] == pytest.approx(1)
    assert not scores["bootstrap"]["seeds_resampled"]
    assert scores["strata"]["seen"]["event_count"] == 2


def test_cluster_duplication_local_rng_and_reproducibility():
    actual, metadata = hand_case()
    predictions = {"persistence": np.zeros_like(actual), "model": actual*.5}
    before = np.random.get_state()
    a = generalization_scores(actual, predictions, metadata, ["bahrain", "albert_park"], {"linear": ["model"]}, resamples=40)
    after = np.random.get_state()
    assert before[0] == after[0] and np.array_equal(before[1], after[1]) and before[2:] == after[2:]
    b = generalization_scores(np.repeat(actual, 2, axis=0), {k: np.repeat(v, 2, axis=0) for k, v in predictions.items()},
                              [m for m in metadata for _ in range(2)], ["bahrain", "albert_park"], {"linear": ["model"]}, resamples=40)
    for stratum in ("seen", "unseen"):
        for name in a["strata"][stratum]["methods"]:
            for field in ("equal_event_mse_kj2", "equal_event_rmse_interval_95_kj", "paired_mse_minus_persistence_interval_95_kj2"):
                assert a["strata"][stratum]["methods"][name][field] == b["strata"][stratum]["methods"][name][field]


def test_stratum_and_sequence_identity_fail_closed():
    actual, metadata = hand_case()
    with pytest.raises(ValueError, match="two distinct"):
        classify_tracks(metadata, [])
    bad = copy.deepcopy(metadata)
    bad[1]["track_id"] = "UNKNOWN_OTHER_CIRCUIT"
    with pytest.raises(ValueError, match="changes circuit"):
        classify_tracks(bad, ["bahrain", "albert_park"])
    bad = copy.deepcopy(metadata)
    bad[2]["driver_id"] = "44"
    with pytest.raises(ValueError, match="sequence crosses"):
        generalization_scores(actual, {"persistence": actual}, bad, ["bahrain", "albert_park"], {}, resamples=40)


def test_explicit_proxy_cohort_guard_precedes_any_payload(tmp_path):
    with pytest.raises(ValueError, match="Permanent benchmark"):
        build_tyre_energy_dataset([], tmp_path/"nonexistent-input", tmp_path/"output", expected_events=("F1_2023_R16",))
    with pytest.raises(ValueError, match="unique"):
        build_tyre_energy_dataset([], tmp_path/"nonexistent-input", tmp_path/"output", expected_events=(EVENTS[0], EVENTS[0]))


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    root = tmp_path_factory.mktemp("r026-frozen-smoke")
    reference = root/"reference"
    result = CliRunner().invoke(app, ["tyre-forecast-smoke", "--output", str(reference)])
    assert result.exit_code == 0, result.output+repr(result.exception)
    source = make_generalization_smoke_dataset(reference, root/"evaluation-input")
    return reference, source, root


def test_new_cohort_requires_frozen_vocabulary_and_ignores_unknown_levels(reference):
    base, source, _ = reference
    vocabulary = json.loads((base/"summary.json").read_text())["vocabulary"]
    before = copy.deepcopy(vocabulary)
    frame = pd.read_parquet(source/"samples.parquet")
    with pytest.raises(ValueError, match="frozen training vocabulary"):
        build_forecast_windows(frame, expected_events=EVENTS)
    windows = build_forecast_windows(frame, expected_events=EVENTS, vocabulary=vocabulary)
    frame.loc[frame.event_id.isin(EVENTS[2:]), "track_id"] = "NOVEL_TEST_CATEGORY"
    changed = build_forecast_windows(frame, expected_events=EVENTS, vocabulary=vocabulary)
    assert vocabulary == before == changed.vocabulary
    np.testing.assert_array_equal(windows.static, changed.static)


def test_new_cohort_future_targets_cannot_enter_past_inputs(reference):
    base, source, _ = reference
    vocabulary = json.loads((base/"summary.json").read_text())["vocabulary"]
    frame = pd.read_parquet(source/"samples.parquet")
    windows = build_forecast_windows(frame, expected_events=EVENTS, vocabulary=vocabulary)
    frame.loc[frame.native_car_row == 79, "tyre_energy_rear_left_kj"] += 500
    changed = build_forecast_windows(frame, expected_events=EVENTS, vocabulary=vocabulary)
    np.testing.assert_array_equal(windows.dynamic, changed.dynamic)
    assert np.any(windows.target != changed.target)


@pytest.fixture(scope="module")
def study(reference):
    base, source, root = reference
    output = root/"evaluation"
    patch = pytest.MonkeyPatch()
    def forbidden(*args, **kwargs):
        pytest.fail("R026 must never fit models on evaluation events")
    patch.setattr(forecast_benchmark, "fit_statistical", forbidden)
    patch.setattr(forecast_benchmark, "train_neural", forbidden)
    before = {p.name: file_sha256(p) for p in base.iterdir()}
    try:
        summary = run_track_generalization(source, base, output, "smoke")
    finally:
        patch.undo()
    assert before == {p.name: file_sha256(p) for p in base.iterdir()}
    assert summary["input_truth"] == "SIMULATED"
    return output


def test_all_frozen_families_and_confidence_replay(study):
    result = verify_track_generalization(study)
    assert result["verified"] and result["checkpoints"] == 6 and not result["task_closure_eligible"]
    summary = json.loads((study/"summary.json").read_text())
    assert summary["target_quality"] == "PROXY_NOT_MEASURED" and not summary["promotion"]
    assert set(summary["scores"]["strata"]) == {"seen", "unseen"}
    assert all(s["event_count"] == 2 for s in summary["scores"]["strata"].values())
    assert set(summary["models_requested"]) == {"linear", "ridge", "xgboost", "gru", "lstm", "tft"}


def test_research_cannot_close_with_smoke_reference(reference, tmp_path):
    base, source, _ = reference
    with pytest.raises(ValueError, match="frozen public R025"):
        run_track_generalization(source, base, tmp_path/"fake-research")


def test_portable_reload_reuse_and_tamper(study, tmp_path):
    before = {p.name: file_sha256(p) for p in study.iterdir()}
    with pytest.raises(FileExistsError):
        run_track_generalization(study, study, study)
    assert before == {p.name: file_sha256(p) for p in study.iterdir()}
    relocated = tmp_path/"relocated"
    shutil.copytree(study, relocated)
    assert verify_track_generalization(relocated)["verified"]
    with (relocated/"linear_seed11.npz").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_track_generalization(relocated)


def test_resealed_scaler_still_bound_to_original_reference(study, tmp_path):
    moved = tmp_path/"resealed"
    shutil.copytree(study, moved)
    scaler = json.loads((moved/"scaler.json").read_text())
    scaler["input_mean"][0] += 1
    (moved/"scaler.json").write_text(json.dumps(scaler, sort_keys=True, indent=2), encoding="utf-8")
    manifest = json.loads((moved/"manifest.json").read_text())
    manifest["files"]["scaler.json"] = {"sha256": file_sha256(moved/"scaler.json"), "bytes": (moved/"scaler.json").stat().st_size}
    manifest["content_sha256"] = payload_sha256({k:v for k,v in manifest.items() if k != "content_sha256"})
    (moved/"manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen reference weight/scaler"):
        verify_track_generalization(moved)
