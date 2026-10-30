"""R028 finite what-if scenarios, conditional on declared kinematic/proxy priors.

These are model-level counterfactuals. Actuator, friction-circle, complete path
and real-car feasibility are UNKNOWN; no causal or strategy recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np

from apexsim.research.forecast_benchmark import EVENTS, ForecastWindows
from apexsim.research.forecast_explanations import guard_origins
from apexsim.research.tyre_energy import TyreEnergyInputs, estimate_wheel_tyre_energy
from apexsim.research.tyre_energy_dataset import ProxyDatasetConfig

SPEED_FACTORS = (.8, .85, .9, .95, .975, 1., 1.025, 1.05, 1.1, 1.15, 1.2)
THROTTLE_OFFSETS = (-.2, -.1, 0., .1, .2)
SCENARIOS = tuple(product(SPEED_FACTORS, THROTTLE_OFFSETS))
IDENTITY_INDEX = SCENARIOS.index((1., 0.))
RTOL, ATOL = 5e-5, 5e-6  # Preregistered float32 source-equation tolerances.
PRIORS = ProxyDatasetConfig()


@dataclass(frozen=True)
class TrainingEnvelope:
    """Training-only marginal ranges, not a guarantee of joint physical support."""

    minimum: np.ndarray
    maximum: np.ndarray

    def __post_init__(self) -> None:
        if (self.minimum.shape != (14,) or self.maximum.shape != (14,)
                or not np.isfinite([self.minimum, self.maximum]).all()
                or np.any(self.minimum > self.maximum)):
            raise ValueError("Invalid finite training marginal envelope")

    @classmethod
    def fit(cls, training: ForecastWindows) -> TrainingEnvelope:
        guard_origins(training.metadata)
        if {m["event_id"] for m in training.metadata} != set(EVENTS[:2]):
            raise ValueError("Counterfactual support requires exactly frozen training events")
        return cls(training.dynamic.min(axis=(0, 1)).astype(float), training.dynamic.max(axis=(0, 1)).astype(float))

    def contains(self, history: np.ndarray) -> bool:
        return bool(np.all(history >= self.minimum-(ATOL+RTOL*abs(self.minimum)))
                    and np.all(history <= self.maximum+(ATOL+RTOL*abs(self.maximum))))


def unprojected_loads(history: np.ndarray) -> np.ndarray:
    """Four-wheel normal loads [N], before the shared proxy's 50N projection."""
    transfer = PRIORS.mass_kg*history[:, 3]*.32/PRIORS.wheelbase_m
    front = .46*PRIORS.mass_kg*9.81-transfer
    rear = .54*PRIORS.mass_kg*9.81+transfer
    lateral = PRIORS.mass_kg*history[:, 4]*.32/2.
    return np.column_stack((.5*front+.5*.46*lateral, .5*front-.5*.46*lateral,
                            .5*rear+.5*.54*lateral, .5*rear-.5*.54*lateral))


def proxy_energies(history: np.ndarray) -> np.ndarray:
    """Recompute all four past proxies from the shared scalar R024 equation [kJ]."""
    return np.array([estimate_wheel_tyre_energy(TyreEnergyInputs(
        speed_mps=float(row[0]), longitudinal_accel_mps2=float(row[3]),
        lateral_accel_mps2=float(row[4]), steering_rad=float(row[5]),
        throttle=float(row[1]), brake=float(row[2]), dt_s=float(row[8]),
        mass_kg=PRIORS.mass_kg, wheelbase_m=PRIORS.wheelbase_m,
    )).as_array() for row in history])


def history_violations(history: np.ndarray, envelope: TrainingEnvelope | None = None) -> list[str]:
    """Reject rather than repair unsupported bounds, coupled equations or proxies."""
    if history.shape != (8, 14) or not np.isfinite(history).all():
        return ["nonfinite_or_shape"]
    x = history.astype(float)
    errors = []
    bounds = (
        ("speed", (x[:, 0] >= PRIORS.min_speed_mps) & (x[:, 0] <= PRIORS.max_speed_mps)),
        ("throttle", (x[:, 1] >= 0) & (x[:, 1] <= 1)),
        ("brake_boolean", (x[:, 2] == 0) | (x[:, 2] == 1)),
        ("longitudinal_accel", abs(x[:, 3]) <= PRIORS.max_longitudinal_accel_mps2),
        ("lateral_accel", abs(x[:, 4]) <= PRIORS.max_lateral_accel_mps2),
        ("steering", abs(x[:, 5]) <= PRIORS.max_steering_rad),
        ("heading_rate", abs(x[:, 6]) <= PRIORS.max_heading_rate_rad_s),
        ("geometry_speed", x[:, 7] > 0),
        ("dt", (x[:, 8] > 0) & (x[:, 8] <= PRIORS.max_gap_s)),
        ("position_lag", (x[:, 9] >= 0) & (x[:, 9] <= PRIORS.max_position_lag_s)),
        ("negative_energy", x[:, 10:] >= 0),
    )
    errors.extend(name for name, valid in bounds if not valid.all())
    if np.all(x[:, 0] > 0) and np.all(x[:, 7] > 0):
        ratio = x[:, 7]/x[:, 0]
        if np.any((ratio < PRIORS.min_geometry_speed_ratio) | (ratio > PRIORS.max_geometry_speed_ratio)):
            errors.append("geometry_speed_ratio")
        if not np.allclose(x[:, 4], -x[:, 0]*x[:, 6], rtol=RTOL, atol=ATOL):
            errors.append("lateral_equation")
        steering = np.arctan(PRIORS.wheelbase_m*x[:, 6]/x[:, 7])
        if not np.allclose(x[:, 5], steering, rtol=RTOL, atol=ATOL):
            errors.append("steering_equation")
    if np.any(unprojected_loads(x) < PRIORS.min_wheel_normal_load_n):
        errors.append("unprojected_wheel_load")
    # Do not invoke a proxy that would clip invalid controls or sample duration.
    if (not set(errors) & {"throttle", "brake_boolean", "dt"}
            and not np.allclose(x[:, 10:], proxy_energies(x), rtol=RTOL, atol=ATOL)):
        errors.append("past_energy_equation")
    if envelope is not None and not envelope.contains(x):
        errors.append("training_marginal_support")
    return errors


def transform_history(history: np.ndarray, speed_factor: float, throttle_offset: float) -> np.ndarray:
    """Coupled hypothetical history; no clipping, changed timing or target inputs.

    Caller checks bounds. Uniform speed scaling preserves linear speed-derived
    acceleration and fixed curvature; lateral acceleration scales quadratically.
    """
    if (history.shape != (8, 14) or not np.isfinite(history).all()
            or not np.isfinite([speed_factor, throttle_offset]).all() or speed_factor <= 0):
        raise ValueError("Invalid finite counterfactual transformation")
    if speed_factor == 1. and throttle_offset == 0.:
        return history.copy()
    result = history.astype(float).copy()
    result[:, (0, 3, 6, 7)] *= speed_factor
    result[:, 4] *= speed_factor**2
    result[:, 1] += throttle_offset
    if np.any((result[:, 1] < 0) | (result[:, 1] > 1)):
        raise ValueError("Counterfactual throttle is outside [0,1]; no clipping")
    result[:, 10:] = proxy_energies(result)
    return result.astype(np.float32)


@dataclass(frozen=True)
class ScenarioCatalogue:
    """All55 histories with explicit rejection reasons and immutable origin."""

    histories: np.ndarray
    valid: np.ndarray
    reasons: list[list[str]]
    source_violations: list[str]


def build_catalogue(history: np.ndarray, envelope: TrainingEnvelope) -> ScenarioCatalogue:
    """Generate once, independently of any model, target or future observation."""
    source_errors = history_violations(history, envelope)
    values = np.repeat(history[None], len(SCENARIOS), axis=0)
    reasons = []
    for i, (factor, offset) in enumerate(SCENARIOS):
        if source_errors:
            reasons.append(["source_"+reason for reason in source_errors])
            continue
        try:
            values[i] = transform_history(history, factor, offset)
        except ValueError:
            reasons.append(["throttle"])
            continue
        reasons.append(history_violations(values[i], envelope))
    return ScenarioCatalogue(values, np.array([not r for r in reasons]), reasons, source_errors)


def scenario_cost(index: int) -> float:
    """Dimensionless L1 cost in two declared scenario parameters; not lap time."""
    factor, offset = SCENARIOS[index]
    return abs(factor-1)/.2+abs(offset)/.2


def counterfactual_result(catalogue: ScenarioCatalogue, raw_predictions: np.ndarray,
                          baseline_raw: np.ndarray) -> dict:
    """Exact finite-catalogue minimum with explicit impossible/support abstentions."""
    return robust_counterfactual_result(catalogue, raw_predictions[None], baseline_raw[None])


def robust_counterfactual_result(catalogue: ScenarioCatalogue, raw_predictions: np.ndarray,
                                 baseline_raw: np.ndarray) -> dict:
    """One candidate must cross each frozen seed's own goal, without averaging seeds."""
    seeds = len(baseline_raw)
    if (not seeds or raw_predictions.shape != (seeds, len(SCENARIOS), 3, 4)
            or baseline_raw.shape != (seeds, 3, 4)
            or not np.isfinite(raw_predictions).all() or not np.isfinite(baseline_raw).all()):
        raise ValueError("Invalid finite counterfactual forecast shape")
    baseline = np.maximum(baseline_raw, 0).mean(axis=(1, 2))
    targets = baseline-np.maximum(.1*baseline, .01)
    scores = np.maximum(raw_predictions, 0).mean(axis=(2, 3))
    crossing = catalogue.valid & np.all(scores <= targets[:, None], axis=0)

    def best(mask: np.ndarray) -> int | None:
        candidates = np.flatnonzero(crossing & mask)
        return int(min(candidates, key=lambda i: (scenario_cost(i), *SCENARIOS[i]))) if len(candidates) else None

    selected = best(np.ones(len(SCENARIOS), dtype=bool))
    single_speed = best(np.array([offset == 0 for _, offset in SCENARIOS]))
    single_throttle = best(np.array([factor == 1 for factor, _ in SCENARIOS]))
    result = {
        "status": "SUCCESS_CONDITIONAL_SCENARIO" if selected is not None else
                  "ABSTAIN_SOURCE_CONSTRAINT_OR_SUPPORT" if catalogue.source_violations else "ABSTAIN_NO_FEASIBLE_CROSSING",
        "selected_index": selected, "baseline_mean_kj_by_seed": baseline.tolist(),
        "target_maximum_mean_kj_by_seed": targets.tolist(),
        "valid_candidates": int(catalogue.valid.sum()), "crossing_candidates": int(crossing.sum()),
        "source_violations": catalogue.source_violations,
        "speed_only_index": single_speed, "throttle_only_index": single_throttle,
        "cost": scenario_cost(selected) if selected is not None else None,
        "selected_parameters": list(SCENARIOS[selected]) if selected is not None else None,
        "crossing_margin_kj_by_seed": (targets-scores[:, selected]).tolist() if selected is not None else None,
        "optimality_scope": "EXHAUSTIVE_55_CANDIDATES_ONLY", "physical_realizability": "UNKNOWN",
    }
    if selected is not None:
        audit_counterfactual(catalogue, raw_predictions, baseline_raw, selected)
    return result


def audit_counterfactual(catalogue: ScenarioCatalogue, raw_predictions: np.ndarray,
                         baseline_raw: np.ndarray, selected: int) -> None:
    """Independently scan the entire finite catalogue for crossing and minimality.

    The study verifier additionally regenerates histories and repeats checkpoint
    inference. This audit uses scalar loops, not the vectorized selection mask.
    """
    feasible = []
    for i, valid in enumerate(catalogue.valid):
        if not valid:
            continue
        passed = True
        for seed in range(len(baseline_raw)):
            base = sum(max(float(v), 0.) for v in baseline_raw[seed].ravel())/12
            value = sum(max(float(v), 0.) for v in raw_predictions[seed, i].ravel())/12
            if value > base-max(.1*base, .01)+1e-12:
                passed = False
        if passed:
            feasible.append(i)
    if not feasible or selected != min(feasible, key=lambda i: (scenario_cost(i), *SCENARIOS[i])):
        raise ValueError("Counterfactual independent crossing/optimality audit failed")
