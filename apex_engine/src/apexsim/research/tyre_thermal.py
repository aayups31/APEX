"""R039 lumped tread and carcass heat balance, in SI units."""
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite

import numpy as np
from scipy.linalg import expm


@dataclass(frozen=True)
class ThermalParameters:
    """Declared effective axle priors for the bicycle replay adapter."""

    tread_capacity_j_k: float = 6000.0
    carcass_capacity_j_k: float = 20000.0
    coupling_w_k: float = 100.0
    road_w_k: float = 45.0
    air_w_k: float = 35.0

    def __post_init__(self):
        capacities = (self.tread_capacity_j_k, self.carcass_capacity_j_k)
        conductances = (self.coupling_w_k, self.road_w_k, self.air_w_k)
        if any(not isfinite(x) or x <= 0 for x in capacities):
            raise ValueError("Heat capacities must be finite and positive")
        if any(not isfinite(x) or x < 0 for x in conductances):
            raise ValueError("Conductances must be finite and nonnegative")


@dataclass(frozen=True)
class ThermalState:
    tread_k: float
    carcass_k: float


@dataclass(frozen=True)
class HeatStep:
    state: ThermalState
    source_j: float
    road_j: float
    air_j: float
    stored_j: float
    balance_error_j: float


@lru_cache(maxsize=128)
def _transition(parameters: ThermalParameters, duration_s: float) -> np.ndarray:
    p = parameters
    ct, cc, coupling = p.tread_capacity_j_k, p.carcass_capacity_j_k, p.coupling_w_k
    # Augment [temperature, integrated temperature, constant forcing].
    generator = np.zeros((6, 6))
    generator[:2, :2] = [
        [-(coupling + p.road_w_k) / ct, coupling / ct],
        [coupling / cc, -(coupling + p.air_w_k) / cc],
    ]
    generator[:2, 4:] = np.eye(2)
    generator[2:4, :2] = np.eye(2)
    return expm(generator * duration_s)


DEFAULT_PARAMETERS = ThermalParameters()


def heat_step(state: ThermalState, duration_s: float, *, tread_w: float, carcass_w: float,
              road_k: float, air_k: float, parameters: ThermalParameters = DEFAULT_PARAMETERS) -> HeatStep:
    """Integrate constant inputs over one interval. Positive exchanges enter the tyre."""
    values = (state.tread_k, state.carcass_k, road_k, air_k, duration_s, tread_w, carcass_w)
    if any(not isfinite(x) or x <= 0 for x in values[:5]):
        raise ValueError("Temperatures in kelvin and duration must be finite and positive")
    if any(not isfinite(x) or x < 0 for x in values[5:]):
        raise ValueError("Dissipative heat inputs must be finite and nonnegative")
    p = parameters
    # Shift by the initial tread temperature to reduce cancellation in energy accounting.
    reference = state.tread_k
    road_delta, air_delta = road_k - reference, air_k - reference
    forcing = (
        (tread_w + p.road_w_k * road_delta) / p.tread_capacity_j_k,
        (carcass_w + p.air_w_k * air_delta) / p.carcass_capacity_j_k,
    )
    end = _transition(p, duration_s) @ [0.0, state.carcass_k - reference, 0.0, 0.0, *forcing]
    if not np.isfinite(end).all() or min(end[:2] + reference) <= 0:
        raise ValueError("Thermal integration left its finite positive domain")
    road_j = p.road_w_k * (road_delta * duration_s - end[2])
    air_j = p.air_w_k * (air_delta * duration_s - end[3])
    source_j = (tread_w + carcass_w) * duration_s
    stored_j = p.tread_capacity_j_k * end[0] + p.carcass_capacity_j_k * (end[1] - (state.carcass_k - reference))
    return HeatStep(ThermalState(*(float(t + reference) for t in end[:2])),
                    float(source_j), float(road_j), float(air_j), float(stored_j),
                    float(stored_j - source_j - road_j - air_j))
