"""Opt-in R045 pit timing for the research strategy model."""

from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path

from apexsim.research.evidence import check_seal, read_json
from apexsim.research.fienia_strategy import PaperStrategyParameters


@dataclass(frozen=True)
class PitTiming:
    """Incremental pace proxy and separate measured lane-time estimate, in seconds."""

    circuit_id: str
    inlap_s: float
    outlap_s: float
    total_s: float
    lane_s: float
    pooled: bool
    source_sha256: str

    def apply(self, parameters: PaperStrategyParameters) -> PaperStrategyParameters:
        """Use the calibrated split and joint total in the research lap map."""
        return replace(
            parameters,
            pit_inlap_penalty_s=self.inlap_s,
            pit_outlap_penalty_s=self.outlap_s,
            consecutive_pit_penalty_s=self.total_s,
        )


def load_pit_timing(path: Path, circuit_id: str, *, allow_pooled: bool = False) -> PitTiming:
    """Load a qualified calibration and require explicit opt-in for pooled estimates."""
    record = read_json(path)
    check_seal(record)
    if (
        record.get("schema") != "apex-pit-timing-r045-v3"
        or record.get("passed") is not True
        or record.get("production_promotion") is not False
    ):
        raise ValueError("Expected qualified R045 research pit timing")
    if not circuit_id.strip():
        raise ValueError("A circuit ID is required")
    model = record["calibration"]
    pooled = circuit_id not in model["circuits"]
    if pooled and not allow_pooled:
        raise ValueError(f"No circuit-specific pit timing for {circuit_id}")
    row = model["pooled"] if pooled else model["circuits"][circuit_id]
    inlap, outlap, total, lane = (
        row[k] for k in ("inlap_proxy_s", "outlap_proxy_s", "total_proxy_s", "lane_s")
    )
    if not all(isfinite(v) and v > 0 for v in (inlap, outlap, total, lane)):
        raise ValueError("Expected finite positive pit timing estimates")
    # The two marginal medians determine shares. Joint median calibrates the sum.
    split = total * (inlap / (inlap + outlap))
    return PitTiming(circuit_id, split, total - split, total, lane, pooled, record["content_sha256"])
