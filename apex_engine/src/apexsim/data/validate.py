from __future__ import annotations

import numpy as np
import pandas as pd

from apexsim.contracts import ContractReport, REQUIRED_COLUMNS, assert_canonical_frame


def validate_canonical_frame(frame: pd.DataFrame, strict: bool = True) -> ContractReport:
    assert_canonical_frame(frame)
    null_cells = int(frame[REQUIRED_COLUMNS].isna().sum().sum())
    duplicate_frames = int(
        frame.duplicated(subset=["session_id", "driver_id", "timestamp_s"]).sum()
    )

    violations = np.zeros(len(frame), dtype=bool)
    range_checks = {
        "speed_mps": (0.0, 120.0),
        "throttle": (0.0, 1.0),
        "brake": (0.0, 1.0),
        "gear_norm": (0.0, 1.0),
        "drs": (0.0, 1.0),
        "steering_proxy": (-1.0, 1.0),
        "rainfall": (0.0, 1.0),
        "grip_level": (0.2, 1.5),
    }
    for column, (minimum, maximum) in range_checks.items():
        values = pd.to_numeric(frame[column], errors="coerce")
        violations |= values.lt(minimum).to_numpy() | values.gt(maximum).to_numpy()
    out_of_range_cells = int(violations.sum())

    passed = null_cells == 0 and duplicate_frames == 0 and out_of_range_cells == 0
    report = ContractReport(
        rows=len(frame),
        sessions=int(frame.session_id.nunique()),
        drivers=int(frame.driver_id.nunique()),
        tracks=int(frame.track_id.nunique()),
        null_cells=null_cells,
        duplicate_frames=duplicate_frames,
        out_of_range_cells=out_of_range_cells,
        passed=passed,
    )
    if strict and not passed:
        raise ValueError(f"Canonical data contract failed: {report.to_dict()}")
    return report
