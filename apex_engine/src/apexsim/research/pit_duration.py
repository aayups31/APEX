"""Opt-in seeded draws from the confirmed green pit-lane distribution."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from random import Random
from statistics import quantiles

from apexsim.research.evidence import check_seal, read_json


@dataclass(frozen=True)
class PitDurationDistribution:
    """Entry-to-exit seconds including service for a green-flag pit stop."""

    seconds: tuple[float, ...]
    pooled: bool
    confirmation_sha256: str

    def central_interval_s(self) -> tuple[float, float]:
        lower, *_, upper = quantiles(self.seconds, n=10, method="inclusive")
        return lower, upper

    def sample(self, rng: Random) -> float:
        """Draw a pit-lane duration using the supplied random stream."""
        return rng.choice(self.seconds)


def load_pit_duration(
    fitted_path: Path,
    development_path: Path,
    confirmation_path: Path,
    circuit_id: str,
    *,
    allow_pooled: bool = False,
) -> PitDurationDistribution:
    """Load the confirmed research model and make pooled fallback explicit."""
    fitted, development, confirmation = [
        read_json(path) for path in (fitted_path, development_path, confirmation_path)
    ]
    for record in (fitted, development, confirmation):
        check_seal(record)
    if (
        fitted.get("schema") != "apex-pit-duration-distributions-r047-v1"
        or development.get("parent_sha256") != fitted["content_sha256"]
        or development.get("passed") is not True
        or confirmation.get("schema") != "apex-r047-direct-green-lane-confirmation"
        or confirmation.get("frozen_sha256") != development["content_sha256"]
        or confirmation.get("passed") is not True
    ):
        raise ValueError("Expected the confirmed R047 green pit-lane distribution")
    if not circuit_id.strip():
        raise ValueError("A circuit ID is required")
    fit = fitted["calibration"]
    center = fit["circuit_median_seconds"].get(circuit_id)
    if center is None and not allow_pooled:
        raise ValueError(f"No circuit-specific pit duration for {circuit_id}")
    seconds = (
        sorted(
            center * ratio * scale
            for ratio in fit["relative_samples"]
            for scale in development["scale_multipliers"]
        )
        if center is not None
        else fit["pooled_seconds"]
    )
    if len(seconds) < 2 or not all(isfinite(value) and value > 0 for value in seconds):
        raise ValueError("Confirmed R047 samples must be positive and finite")
    return PitDurationDistribution(tuple(seconds), center is None, confirmation["content_sha256"])
