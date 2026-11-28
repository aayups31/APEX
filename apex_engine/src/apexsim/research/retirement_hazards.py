"""Opt-in competing retirement hazards for the two evaluated F1 seasons."""

from dataclasses import dataclass
from math import isclose, isfinite
from pathlib import Path
from random import Random
from typing import Literal

from apexsim.research.evidence import check_seal, read_json


@dataclass(frozen=True)
class RetirementHazard:
    """Per-driver-lap probabilities for mutually exclusive outcomes."""

    stay: float
    incident: float
    mechanical: float

    def __post_init__(self) -> None:
        values = (self.stay, self.incident, self.mechanical)
        if not all(isfinite(v) and 0 <= v <= 1 for v in values) or not isclose(sum(values), 1, abs_tol=1e-12):
            raise ValueError("Invalid competing retirement probabilities")

    def sample(self, rng: Random) -> Literal["stay", "incident", "mechanical"]:
        """Draw a single outcome with the caller's random stream."""
        draw = rng.random()
        if draw < self.incident:
            return "incident"
        if draw < self.incident + self.mechanical:
            return "mechanical"
        return "stay"


@dataclass(frozen=True)
class RetirementHazardModel:
    by_season: dict[int, tuple[RetirementHazard, RetirementHazard]]
    content_sha256: str

    def for_lap(self, season: int, lap: int) -> RetirementHazard:
        """Resolve the first or later lap hazard for a supported season."""
        if type(season) is not int or season not in self.by_season:
            raise ValueError("Season outside the evaluated R048 scope")
        if type(lap) is not int or lap < 1:
            raise ValueError("R048 race laps are positive one-based integers")
        return self.by_season[season][int(lap > 1)]


def load_retirement_hazards(path: Path) -> RetirementHazardModel:
    """Load the qualified, sealed historical research calibration."""
    record = read_json(path)
    check_seal(record)
    if (
        record.get("schema") != "apex-r048-cause-hazards-v2"
        or record.get("production_promotion") is not False
        or record["result"].get("passed") is not True
    ):
        raise ValueError("Expected a qualified R048 research receipt")
    years = record["result"]["hazards_by_year"]
    if set(years) != {"2024", "2025"} or any(set(x) != {"first", "later"} for x in years.values()):
        raise ValueError("Invalid R048 season or lap-band inventory")
    return RetirementHazardModel(
        {
            int(year): (RetirementHazard(**bands["first"]), RetirementHazard(**bands["later"]))
            for year, bands in years.items()
        },
        record["content_sha256"],
    )
