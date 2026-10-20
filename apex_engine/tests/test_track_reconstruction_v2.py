import copy
import json
import shutil

import numpy as np
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples.track_reconstruction_v2 import (
    COUNTS,
    run_track_reconstruction_v2,
    verify_track_reconstruction_v2,
)
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.research.supported_geometry import fit_supported_case


def test_v2_benchmark_refusal_precedes_native_or_mask_access(tmp_path):
    archive = tmp_path/"protected"
    archive.mkdir()
    (archive/"manifest.json").write_text(json.dumps({"query": {"year": 2023, "round_number": 4, "session": "R"}}))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        run_track_reconstruction_v2([archive], tmp_path/"missing-mask", tmp_path/"missing-mask2", tmp_path/"output")


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    path = tmp_path_factory.mktemp("track-support")/"smoke"
    result = CliRunner().invoke(app, ["track-reconstruction-v2-smoke", "--output", str(path)])
    assert result.exit_code == 0, result.output+repr(result.exception)
    return path


def _laps(study, track="sim_circle"):
    metadata = json.loads((study/f"{track}_lap_metadata.json").read_text())
    with np.load(study/f"{track}_lap_inputs.npz", allow_pickle=False) as raw:
        return [{"metadata": m, "xy_m": raw[m["lap_id"]+"_xy"], "time_s": raw[m["lap_id"]+"_time"],
                 "native_parents": raw[m["lap_id"]+"_native_parents"], "interval_supported": np.diff(raw[m["lap_id"]+"_time"]) <= .75} for m in metadata]


def test_complementary_dropout_controls_pass_without_public_promotion(study):
    summary = json.loads((study/"summary.json").read_text())
    assert summary["input_truth"] == "SIMULATED" and not summary["R029_complete"]
    assert all(c["gate"]["passed"] for c in summary["cases"].values())
    assert all(c["coverage"]["minimum_donor_laps"] >= 3 for c in summary["cases"].values())
    assert any((~lap["interval_supported"]).any() for lap in _laps(study))


def test_held_out_geometry_and_missingness_cannot_change_fit_or_selection(study):
    summary = json.loads((study/"summary.json").read_text())["cases"]["sim_circle"]
    laps = copy.deepcopy(_laps(study))
    for lap in laps:
        if lap["metadata"]["role"] == "test":
            lap["xy_m"][:, 0] *= 1.08
            lap["interval_supported"][:] = False
    changed, arrays = fit_supported_case(laps, "sim_circle", expected_counts=COUNTS["smoke_v2"])
    assert changed["selected_config"] == summary["selected_config"]
    assert not changed["gate"]["passed"]
    with np.load(study/"sim_circle_geometry_predictions.npz") as saved:
        np.testing.assert_array_equal(arrays["coefficients"], saved["coefficients"])


def test_periodic_curve_cannot_hide_a_hole_shared_by_all_training_laps(study):
    laps = copy.deepcopy(_laps(study))
    for lap in laps:
        if lap["metadata"]["role"] == "train":
            keep = ~((lap["native_parents"][:, 0] >= 180)&(lap["native_parents"][:, 0] < 190))
            for name in ("xy_m", "time_s", "native_parents"):
                lap[name] = lap[name][keep]
            lap["interval_supported"] = np.diff(lap["time_s"]) <= .75
    result, _ = fit_supported_case(laps, "sim_circle", expected_counts=COUNTS["smoke_v2"])
    assert not result["gate"]["coverage_passed"] and not result["gate"]["passed"]
    assert result["coverage"]["minimum_donor_laps"] == 0


def test_portable_native_support_replay_and_immutable_outputs(study, tmp_path):
    before = {p.name: file_sha256(p) for p in study.iterdir()}
    moved = tmp_path/"portable"
    shutil.copytree(study, moved)
    assert verify_track_reconstruction_v2(moved)["verified"]
    with pytest.raises(FileExistsError):
        run_track_reconstruction_v2([], study, study, study)
    assert before == {p.name: file_sha256(p) for p in study.iterdir()}
    with (moved/"sim_circle_geometry_predictions.npz").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_track_reconstruction_v2(moved)


def test_resealed_smoke_cannot_claim_real_source_acceptance(study, tmp_path):
    moved = tmp_path/"fake-public"
    shutil.copytree(study, moved)
    summary = json.loads((moved/"summary.json").read_text())
    summary.update(profile="research_v2", R029_complete=True, task_closure_eligible=True)
    summary["content_sha256"] = payload_sha256({k:v for k,v in summary.items() if k != "content_sha256"})
    (moved/"summary.json").write_text(json.dumps(summary))
    manifest = json.loads((moved/"manifest.json").read_text())
    manifest["summary_sha256"] = summary["content_sha256"]
    manifest["files"]["summary.json"] = {"sha256": file_sha256(moved/"summary.json"), "bytes": (moved/"summary.json").stat().st_size}
    manifest["content_sha256"] = payload_sha256({k:v for k,v in manifest.items() if k != "content_sha256"})
    (moved/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="source/cohort mismatch"):
        verify_track_reconstruction_v2(moved)


def test_v2_1_partial_observation_cli_replays_and_cannot_promote(tmp_path):
    path = tmp_path/"observed-boundaries"
    result = CliRunner().invoke(app, ["track-reconstruction-v2-smoke", "--observed-boundaries", "--output", str(path)])
    assert result.exit_code == 0, result.output+repr(result.exception)
    summary = json.loads((path/"summary.json").read_text())
    assert summary["profile"] == "smoke_v2_1" and not summary["task_closure_eligible"]
    for case in summary["cases"].values():
        assert case["gate"]["passed"]
        partial = [m for m in case["lap_metrics"] if m["raw_closure_gap_m"] is None]
        assert len(partial) == 1 and partial[0]["observed_time_fraction"] >= .98
        assert len(partial[0]["registration"]["nearest_curve_rms_steps_m"]) == 9
