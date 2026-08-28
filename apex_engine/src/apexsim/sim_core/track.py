from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TrackSample:
    s_m: float
    x_m: float
    y_m: float
    curvature_1pm: float
    elevation_m: float
    width_m: float
    drs_allowed: bool
    pit_lane: bool


@dataclass
class TrackMap:
    track_id: str
    s_m: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray
    curvature_1pm: np.ndarray
    elevation_m: np.ndarray
    width_m: np.ndarray
    drs_allowed: np.ndarray
    pit_lane: np.ndarray

    def __post_init__(self) -> None:
        arrays = [
            self.s_m,
            self.x_m,
            self.y_m,
            self.curvature_1pm,
            self.elevation_m,
            self.width_m,
            self.drs_allowed,
            self.pit_lane,
        ]
        n = len(self.s_m)
        if n < 8 or any(len(a) != n for a in arrays):
            raise ValueError("Track arrays must have equal length and at least 8 samples")
        if not np.all(np.diff(self.s_m) > 0):
            raise ValueError("Track distance must be strictly increasing")

    @property
    def length_m(self) -> float:
        spacing = float(np.median(np.diff(self.s_m)))
        return float(self.s_m[-1] + spacing)

    def wrap(self, distance_m: float) -> float:
        return float(distance_m % self.length_m)

    def sample(self, distance_m: float) -> TrackSample:
        s = self.wrap(distance_m)
        i = int(np.searchsorted(self.s_m, s, side="right") - 1)
        i = max(0, min(i, len(self.s_m) - 1))
        return TrackSample(
            s_m=s,
            x_m=float(self.x_m[i]),
            y_m=float(self.y_m[i]),
            curvature_1pm=float(self.curvature_1pm[i]),
            elevation_m=float(self.elevation_m[i]),
            width_m=float(self.width_m[i]),
            drs_allowed=bool(self.drs_allowed[i]),
            pit_lane=bool(self.pit_lane[i]),
        )

    def lookahead_curvature(self, distance_m: float, lookahead_m: float = 180.0, samples: int = 8) -> float:
        points = np.linspace(0.0, lookahead_m, samples)
        values = [abs(self.sample(distance_m + float(d)).curvature_1pm) for d in points]
        # Emphasize the most demanding corner in the near future.
        return float(max(values))

    def gradient(self, distance_m: float, delta_m: float = 10.0) -> float:
        before = self.sample(distance_m - delta_m).elevation_m
        after = self.sample(distance_m + delta_m).elevation_m
        return float((after - before) / (2.0 * delta_m))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "track_id": self.track_id,
                "s_m": self.s_m,
                "x_m": self.x_m,
                "y_m": self.y_m,
                "curvature_1pm": self.curvature_1pm,
                "elevation_m": self.elevation_m,
                "width_m": self.width_m,
                "drs_allowed": self.drs_allowed.astype(int),
                "pit_lane": self.pit_lane.astype(int),
            }
        )

    def save_csv(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.to_frame().to_csv(output, index=False)

    @classmethod
    def from_csv(cls, path: str | Path, track_id: str | None = None) -> TrackMap:
        frame = pd.read_csv(path).sort_values("s_m")
        required = {"s_m", "x_m", "y_m", "curvature_1pm"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Track CSV missing columns: {sorted(missing)}")
        n = len(frame)
        return cls(
            track_id=track_id or str(frame.get("track_id", pd.Series([Path(path).stem])).iloc[0]),
            s_m=frame.s_m.to_numpy(float),
            x_m=frame.x_m.to_numpy(float),
            y_m=frame.y_m.to_numpy(float),
            curvature_1pm=frame.curvature_1pm.to_numpy(float),
            elevation_m=frame.get("elevation_m", pd.Series(np.zeros(n))).to_numpy(float),
            width_m=frame.get("width_m", pd.Series(np.full(n, 12.0))).to_numpy(float),
            drs_allowed=frame.get("drs_allowed", pd.Series(np.zeros(n))).to_numpy(bool),
            pit_lane=frame.get("pit_lane", pd.Series(np.zeros(n))).to_numpy(bool),
        )

    @classmethod
    def synthetic(
        cls,
        track_id: str = "apex_test_track",
        length_m: float = 5200.0,
        points: int = 1500,
        seed: int = 42,
    ) -> TrackMap:
        rng = np.random.default_rng(seed)
        s = np.linspace(0.0, length_m, points, endpoint=False)
        theta = 2.0 * np.pi * s / length_m
        phase = rng.uniform(-0.5, 0.5)
        radius = 760.0 + 150.0 * np.sin(3 * theta + phase) + 65.0 * np.sin(7 * theta)
        x = radius * np.cos(theta) + 85.0 * np.sin(2 * theta)
        y = 0.78 * radius * np.sin(theta) + 55.0 * np.sin(5 * theta + phase)
        dx = np.gradient(x, s)
        dy = np.gradient(y, s)
        heading = np.unwrap(np.arctan2(dy, dx))
        curvature = np.gradient(heading, s)
        # Smooth noisy numerical derivatives without requiring scipy.
        kernel = np.ones(11) / 11.0
        curvature = np.convolve(curvature, kernel, mode="same")
        elevation = 8.0 * np.sin(theta - 0.4) + 3.0 * np.sin(4 * theta)
        width = 12.0 + 1.5 * np.sin(2 * theta)
        drs = ((s > 0.08 * length_m) & (s < 0.24 * length_m)) | (
            (s > 0.58 * length_m) & (s < 0.73 * length_m)
        )
        pit = (s > 0.92 * length_m) | (s < 0.035 * length_m)
        return cls(
            track_id=track_id,
            s_m=s,
            x_m=x,
            y_m=y,
            curvature_1pm=curvature,
            elevation_m=elevation,
            width_m=width,
            drs_allowed=drs,
            pit_lane=pit,
        )

    @classmethod
    def from_canonical_telemetry(
        cls,
        frame: pd.DataFrame,
        track_id: str | None = None,
        bins: int = 1200,
    ) -> TrackMap:
        """Reconstruct a stable track reference from public telemetry.

        Multiple laps are projected into distance bins and median-aggregated to
        reduce GPS jitter. This is intentionally transparent and should be
        replaced by a more rigorous map-matching pipeline once V1 is validated.
        """
        required = {"lap_distance_m", "x_m", "y_m"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Canonical telemetry missing track columns: {sorted(missing)}")
        clean = frame.dropna(subset=list(required)).copy()
        if clean.empty:
            raise ValueError("No usable telemetry rows for track reconstruction")
        length = float(clean.lap_distance_m.quantile(0.995))
        clean["bin"] = np.clip((clean.lap_distance_m / max(length, 1.0) * bins).astype(int), 0, bins - 1)
        grouped = clean.groupby("bin", as_index=False).median(numeric_only=True)
        grouped = grouped.set_index("bin").reindex(range(bins)).interpolate().ffill().bfill().reset_index()
        s = np.linspace(0.0, length, bins, endpoint=False)
        x = grouped.x_m.to_numpy(float)
        y = grouped.y_m.to_numpy(float)
        heading = np.unwrap(np.arctan2(np.gradient(y, s), np.gradient(x, s)))
        curvature = np.convolve(np.gradient(heading, s), np.ones(9) / 9.0, mode="same")
        drs = grouped.get("drs", pd.Series(np.zeros(bins))).to_numpy(float) > 0.5
        pit = grouped.get("is_pit", pd.Series(np.zeros(bins))).to_numpy(float) > 0.5
        return cls(
            track_id=track_id or str(clean.track_id.iloc[0]),
            s_m=s,
            x_m=x,
            y_m=y,
            curvature_1pm=curvature,
            elevation_m=np.zeros(bins),
            width_m=np.full(bins, 12.0),
            drs_allowed=drs,
            pit_lane=pit,
        )
