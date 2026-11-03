"""R040 irreversible effective-axle wear driven by dissipated sliding energy."""
from math import exp, expm1, isfinite


def wear_step(wear: float, sliding_j: float, tread_k: float, rate_per_j: float = 1e-7) -> float:
    """Advance the consumed fraction using a temperature-weighted energy dose."""
    if not all(map(isfinite, (wear, sliding_j, tread_k, rate_per_j))):
        raise ValueError("Wear inputs must be finite")
    if not 0 <= wear <= 1 or sliding_j < 0 or rate_per_j < 0 or not 200 <= tread_k <= 500:
        raise ValueError("Wear inputs outside the supported domain")
    dose = sliding_j * rate_per_j * exp((tread_k - 333.15) / 40)
    return wear - (1 - wear) * expm1(-dose)
