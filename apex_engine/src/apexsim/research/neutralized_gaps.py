"""Opt-in R049 order-preserving timing-line gap replay."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import isfinite
from pathlib import Path

from apexsim.research.evidence import check_seal, read_json
from apexsim.sim_core.types import FlagState

MODES = {"4": FlagState.SAFETY_CAR, "6": FlagState.VSC}


def scale_gaps(before: Sequence[float], factor: float) -> list[float]:
    """Scale cumulative gaps in seconds while preserving the leader and order."""
    if (
        not before
        or before[0] != 0
        or any(a > b for a, b in pairwise(before))
        or not all(map(isfinite, before))
        or not isfinite(factor)
        or factor <= 0
    ):
        raise ValueError("Invalid ordered gap vector or scale")
    result = [v * factor for v in before]
    if not all(map(isfinite, result)):
        raise ValueError("Invalid scaled gap")
    return result


@dataclass(frozen=True)
class GapReplay:
    mode: FlagState
    start_s: float
    release_s: float
    before_s: tuple[float, ...]
    neutralized_s: tuple[float, ...]
    first_green_lap_s: tuple[float, ...]

    def flag_at(self, clock_s: float) -> FlagState:
        """Use the bounded episode clock. Release is immediately green."""
        if not isfinite(clock_s):
            raise ValueError("Expected a finite race clock")
        return self.mode if self.start_s <= clock_s < self.release_s else FlagState.GREEN


@dataclass(frozen=True)
class NeutralizationGapModel:
    factors: dict[FlagState, tuple[float, float]]
    source_sha256: str

    def replay(
        self, mode: FlagState, before_s: Sequence[float], *, start_s: float, release_s: float
    ) -> GapReplay:
        """Produce the two calibrated snapshots for a bounded episode."""
        if mode not in self.factors or not all(map(isfinite, (start_s, release_s))) or start_s >= release_s:
            raise ValueError("Invalid mode or neutralization interval")
        middle, after = self.factors[mode]
        return GapReplay(
            mode,
            start_s,
            release_s,
            tuple(before_s),
            tuple(scale_gaps(before_s, middle)),
            tuple(scale_gaps(before_s, after)),
        )


def load_neutralization_gaps(path: Path) -> NeutralizationGapModel:
    """Load only a passed research replay receipt."""
    data = read_json(path)
    check_seal(data)
    if (
        data.get("schema") != "apex-r049-per-car-gaps-v1"
        or data.get("passed") is not True
        or data.get("production_promotion") is not False
        or set(data["fit"]) != set(MODES)
    ):
        raise ValueError("Expected qualified R049 gap replay")
    factors = {}
    for code, mode in MODES.items():
        middle, after = data["fit"][code]
        if not all(isfinite(v) and v > 0 for v in (middle, after)):
            raise ValueError("Invalid R049 gap factors")
        factors[mode] = middle, after
    return NeutralizationGapModel(factors, data["content_sha256"])
