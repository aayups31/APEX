"""Opt-in R046 conditional next-lap forecasts and seeded residual draws."""

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from random import Random

from apexsim.research.evidence import check_seal, read_json

COMPOUNDS = ("HARD", "MEDIUM", "SOFT")


def point_pace(model: dict, last_s: float, features: list[float]) -> float:
    """Evaluate the portable ridge checkpoint in seconds."""
    return (
        last_s
        + model["intercept"]
        + sum(
            (x - center) * weight / scale
            for x, center, weight, scale in zip(
                features, model["center"], model["coefficients"], model["scale"], strict=True
            )
        )
    )


@dataclass(frozen=True)
class LapResidualForecast:
    point_s: float
    pooled: tuple[float, ...]
    driver_residuals: tuple[float, ...]

    def sample(self, rng: Random) -> float:
        """Draw one next-lap pace using the caller's random stream."""
        errors = self.driver_residuals if self.driver_residuals and rng.random() < 0.5 else self.pooled
        value = self.point_s + rng.choice(errors)
        if value <= 0 or not isfinite(value):
            raise ValueError("Sample left the positive lap-time domain")
        return value


@dataclass(frozen=True)
class CleanLapResidualModel:
    point_model: dict
    pooled: tuple[float, ...]
    by_driver: dict[str, tuple[float, ...]]
    content_sha256: str

    def forecast(
        self,
        driver: str,
        past_s: tuple[float, float, float],
        *,
        tyre_age: float,
        lap: int,
        compound: str,
    ) -> LapResidualForecast:
        """Forecast one lap after three consecutive green laps on the same stint."""
        a, b, c = past_s
        if (
            not all(isfinite(x) and x > 0 for x in past_s)
            or not isfinite(tyre_age)
            or tyre_age < 0
            or type(lap) is not int
            or lap < 3
            or compound not in COMPOUNDS
        ):
            raise ValueError("Invalid R046 clean-lap forecast history")
        features = [b - a, c - b, tyre_age, lap, *[float(compound == k) for k in COMPOUNDS]]
        return LapResidualForecast(
            point_pace(self.point_model, c, features), self.pooled, self.by_driver.get(driver, ())
        )


def load_lap_residuals(path: Path) -> CleanLapResidualModel:
    """Load the qualified research receipt without using held-out residuals."""
    record = read_json(path)
    check_seal(record)
    if record.get("schema") != "apex-r046-clean-green-lap-residuals-v1" or record.get("passed") is not True:
        raise ValueError("Expected a qualified R046 research receipt")
    grouped = defaultdict(list)
    pooled = []
    for event, driver, error in record["calibration_errors"]:
        if event not in record["training_rows"] or event in record["folds"] or not isfinite(error):
            raise ValueError("Invalid R046 residual calibration source")
        grouped[driver].append((event, error))
        pooled.append(error)
    if len(pooled) != sum(record["training_rows"].values()):
        raise ValueError("Incomplete R046 residual calibration")
    by_driver = {
        driver: tuple(e for _, e in rows)
        for driver, rows in grouped.items()
        if len(rows) >= 30 and len({event for event, _ in rows}) >= 2
    }
    return CleanLapResidualModel(record["point_model"], tuple(pooled), by_driver, record["content_sha256"])
