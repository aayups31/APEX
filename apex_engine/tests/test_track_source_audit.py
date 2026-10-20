"""Native fixtures test acceptance/refusal mechanics, never public research closure."""
import json
import shutil

import pandas as pd
import pytest
from test_reference_geometry import native_fixture

from apexsim.examples import track_reconstruction_source_audit as audit
from apexsim.provenance import payload_sha256


def test_pre_fit_gap_audit_localizes_native_intervals_without_filling():
    laps, positions, selection = native_fixture()
    broken = positions.drop(index=range(40, 48)).reset_index(drop=True)
    result = audit.audit_lap(laps, broken, selection)
    assert not result["source_gate_passed"]
    assert result["max_gap_s"] == 2.25
    assert result["unsupported_intervals"] == [{"start_s": 9.75, "end_s": 12., "gap_s": 2.25, "native_parent_rows": [39, 40]}]
    assert result["raw_closure_gap_m"] < 1e-8
    assert "gaps" in result["failure_reason"]
    pd.testing.assert_frame_equal(audit._restore_lap(audit._lap_snapshot(laps.iloc[0]), selection), laps, check_like=True)


@pytest.mark.parametrize("missing_support", [True, False])
def test_complete_source_audit_replays_native_snapshots_and_never_closes_geometry(tmp_path, monkeypatch, missing_support):
    # Archive verification alone is stubbed for explicitly synthetic test fixtures.
    # The real research command still requires verify_fastf1_archive and frozen mask seals.
    archives, masks = [], {2023: {"sources": [], "segments": []}, 2024: {"sources": [], "segments": []}}
    for event in audit.EVENT_TRACKS:
        path = tmp_path/event
        (path/"tables/pos_data").mkdir(parents=True)
        archives.append(path)
        year, round_number = int(event[3:7]), int(event[-2:])
        manifest = {"query": {"year": year, "round_number": round_number, "session": "R"}, "truth": "SIMULATED_TEST_FIXTURE"}
        manifest["content_sha256"] = payload_sha256(manifest)
        (path/"manifest.json").write_text(json.dumps(manifest))
        masks[year]["sources"].append({"event_id": event, "archive_sha256": manifest["content_sha256"]})
        all_laps = []
        for driver in ("4", "44"):
            laps, positions, _ = native_fixture()
            if missing_support:
                positions = positions.drop(index=range(40, 48)).reset_index(drop=True)
            positions.to_parquet(path/f"tables/pos_data/{driver}.parquet", index=False)
            rows = []
            for lap_number in (2, 3, 4):
                row = laps.iloc[0].copy()
                row.DriverNumber, row.LapNumber = driver, float(lap_number)
                rows.append({"lap": lap_number, "native_row": len(all_laps)})
                all_laps.append(row)
            masks[year]["segments"].append({"event_id": event, "driver": driver, "rows": rows})
        pd.DataFrame(all_laps).reset_index(drop=True).to_parquet(path/"tables/laps.parquet", index=False)
    mask_paths = {}
    for year, mask in masks.items():
        mask["content_sha256"] = payload_sha256(mask)
        monkeypatch.setitem(audit.MASK_SEALS, year, mask["content_sha256"])
        mask_paths[year] = tmp_path/f"mask-{year}.json"
        mask_paths[year].write_text(json.dumps(mask))
    monkeypatch.setattr(audit, "verify_fastf1_archive", lambda path: json.loads((path/"manifest.json").read_text()))
    output = tmp_path/"audit"
    summary = audit.run_source_audit(archives, mask_paths[2024], mask_paths[2023], output)
    assert summary["source_gate_passed"] == (not missing_support)
    assert summary["supported_laps"] == (0 if missing_support else 24)
    assert not summary["fit_performed"] and not summary["R029_complete"] and not summary["task_closure_eligible"]
    relocated = tmp_path/"portable"
    shutil.copytree(output, relocated)
    assert audit.verify_source_audit(relocated)["verified"]
    with pytest.raises(FileExistsError):
        audit.run_source_audit([], mask_paths[2024], mask_paths[2023], output)
    with (relocated/"native_position_inputs.npz").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        audit.verify_source_audit(relocated)
