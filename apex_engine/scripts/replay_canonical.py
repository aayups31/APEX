from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from apexsim.sim_core.calibration import fit_longitudinal_dynamics
from apexsim.sim_core.replay import replay_controls


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate and replay one canonical telemetry file")
    parser.add_argument("canonical_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/replay"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.canonical_csv)
    calibration = fit_longitudinal_dynamics(frame)
    replay, metrics = replay_controls(frame)
    replay.to_csv(args.output_dir / "replay.csv", index=False)
    (args.output_dir / "calibration.json").write_text(json.dumps(calibration.to_dict(), indent=2), encoding="utf-8")
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics.to_dict(), indent=2), encoding="utf-8")
    print(json.dumps(metrics.to_dict(), indent=2))


if __name__ == "__main__":
    main()
