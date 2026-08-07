from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from apexsim.sim_core.track import TrackMap


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct an APEX track map from canonical telemetry")
    parser.add_argument("canonical_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/processed/track_map.csv"))
    parser.add_argument("--bins", type=int, default=1200)
    args = parser.parse_args()

    frame = pd.read_csv(args.canonical_csv)
    track = TrackMap.from_canonical_telemetry(frame, bins=args.bins)
    track.save_csv(args.output)
    print({"track_id": track.track_id, "length_m": track.length_m, "points": len(track.s_m), "output": str(args.output)})


if __name__ == "__main__":
    main()
