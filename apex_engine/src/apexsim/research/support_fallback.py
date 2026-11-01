"""R038 empirical support envelope and hysteretic transparent reversion.

This is finite empirical runtime supervision, not an invariant-set safety proof.
Untrusted pose/map/known vehicle assumptions require explicit abstention.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2

import numpy as np

from apexsim.research.bicycle import BicycleState
from apexsim.research.imitation_driver import (
    RESIDUAL_LIMIT_RAD,
    apply_steering,
    baseline_raw,
    predict_residual,
)
from apexsim.research.transparent_driver import CAR, command

FLOORS = np.array([.05, .02, .02, .005, .005, .02, .01, .01])


def fit_envelope(training: np.ndarray, validation: np.ndarray) -> dict:
    """Training-only robust coordinate ranges; cutoff calibrated on validation only."""
    if any(a.ndim != 2 or a.shape[1] != 8 or len(a) < 12 or not np.isfinite(a).all() for a in (training, validation)):
        raise ValueError("R038 requires finite separate training/validation feature matrices")
    low, high = np.quantile(training, [.005, .995], axis=0)
    center, width = (low+high)/2, np.maximum((high-low)/2, FLOORS)
    scores = np.max(abs((validation-center)/width), axis=1)
    cutoff = float(max(1.25, 1.1*np.quantile(scores, .995)))
    return {"schema_version": "apex-empirical-support-v1", "center": center.tolist(), "half_range": width.tolist(),
            "floors": FLOORS.tolist(), "cutoff": cutoff, "release_fraction": .8, "release_commands": 10,
            "training_rows": len(training), "validation_rows": len(validation),
            "validation_exceedance_fraction": float(np.mean(scores > cutoff)),
            "statistical_coverage_guarantee": False, "test_outcomes_used": False}


def support_score(envelope: dict, row: np.ndarray) -> float | None:
    center, width = np.asarray(envelope["center"]), np.asarray(envelope["half_range"])
    if (envelope.get("schema_version") != "apex-empirical-support-v1" or center.shape != (8,) or width.shape != (8,)
            or not np.isfinite([center, width]).all() or np.any(width <= 0)
            or not np.isfinite(envelope["cutoff"]) or envelope["cutoff"] < 1.25
            or envelope["release_fraction"] != .8 or envelope["release_commands"] != 10):
        raise ValueError("R038 invalid frozen detector parameters")
    if row.shape != (8,) or not np.isfinite(row).all():
        return None
    return float(np.max(abs((row-center)/width)))


@dataclass
class Supervisor:
    """Causal state machine; ten supported low-score commands before re-engagement."""

    envelope: dict
    mode: str = "learned"
    good_commands: int = 0

    def decide(self, state: BicycleState, lateral: float, row: np.ndarray, residual: float,
               *, map_valid: bool = True, state_trusted: bool = True, context_valid: bool = True) -> dict:
        finite = bool(np.isfinite(state.array()).all() and np.isfinite(lateral))
        hard = (not finite or not state_trusted or not map_valid or not context_valid
                or not CAR.min_vx_mps <= state.vx_mps <= CAR.max_vx_mps
                or (finite and (abs(atan2(state.vy_mps, state.vx_mps)) > CAR.max_sideslip_rad
                               or abs(state.yaw_rate_radps) > CAR.max_yaw_rate_radps or abs(lateral) > 2)))
        if hard or self.mode == "abstain":
            self.mode, self.good_commands = "abstain", 0
            return {"mode": self.mode, "score": None, "reason": "UNTRUSTED_STATE_MAP_OR_VEHICLE_SUPPORT", "triggered": True}
        score = support_score(self.envelope, row)
        valid = bool(np.isfinite(residual) and abs(residual) <= RESIDUAL_LIMIT_RAD)
        bad = score is None or score > self.envelope["cutoff"] or not valid
        if bad:
            self.mode, self.good_commands = "fallback", 0
            reason = "INVALID_LEARNER_FEATURES" if score is None else "FEATURE_OOD" if score > self.envelope["cutoff"] else "INVALID_LEARNED_ACTION"
        elif self.mode == "fallback":
            self.good_commands = self.good_commands+1 if score < .8*self.envelope["cutoff"] else 0
            if self.good_commands >= 10:
                self.mode, self.good_commands = "learned", 0
            reason = "RECOVERY_HYSTERESIS" if self.mode == "fallback" else None
        else:
            reason = None
        return {"mode": self.mode, "score": score, "reason": reason, "triggered": bool(bad)}


class RuntimeController:
    """Frozen test injection and deployment supervisor; no chassis-state mutation."""

    def __init__(self, actor: str, fault: str, envelope: dict, model: dict):
        if actor not in ("guarded", "unguarded", "transparent") or fault not in (
                "nominal", "feature_shift", "residual_bias", "nonfinite", "missing_map", "untrusted_state", "vehicle_mismatch"):
            raise ValueError("R038 unknown actor or frozen fault")
        self.actor, self.fault, self.envelope, self.model = actor, fault, envelope, model
        self.monitor = Supervisor(envelope)
        self.next_event, self.remaining = 0, 0

    def __call__(self, state, track, profile, station, lateral, previous, index, nominal, row, log):
        first = False
        if self.fault in ("feature_shift", "residual_bias", "nonfinite"):
            targets = (1.25, 2.60)
            if self.next_event < 2 and station >= targets[self.next_event]*track.length_m:
                self.next_event += 1
                self.remaining, first = 20, True
        active = self.remaining > 0
        self.remaining = max(0, self.remaining-1)
        learner_row = row.copy()
        if active and self.fault == "feature_shift":
            learner_row[2] += 10*self.envelope["half_range"][2]*self.envelope["cutoff"]
        residual = predict_residual(self.model, learner_row)
        if active and self.fault == "residual_bias":
            residual += .3
        if active and self.fault == "nonfinite":
            residual = float("nan")
        if self.actor == "guarded":
            decision = self.monitor.decide(state, lateral, learner_row, residual,
                                           map_valid=self.fault != "missing_map", state_trusted=self.fault != "untrusted_state",
                                           context_valid=self.fault != "vehicle_mismatch")
        else:
            decision = {"mode": "transparent" if self.actor == "transparent" else "learned", "score": support_score(self.envelope, learner_row),
                        "reason": None, "triggered": False}
        decision.update(fault_active=active, first_fault_command=first, learner_action_valid=bool(np.isfinite(residual) and abs(residual) <= .2))
        if decision["mode"] == "abstain":
            return None, decision
        if decision["mode"] in ("fallback", "transparent"):
            action, fallback_log = command(state, track, profile, station, lateral, previous)
            log.update(steering_projected=fallback_log["steering_projected"], force_projected=fallback_log["force_projected"], residual_projected=False)
            return action, decision
        if not np.isfinite(residual):
            return None, {**decision, "reason": "UNGUARDED_NONFINITE_ACTION"}
        bounded = float(np.clip(residual, -.2, .2))
        action, projections = apply_steering(baseline_raw(learner_row)+bounded, state, track, profile, station, previous)
        log.update(projections, residual_projected=abs(bounded-residual) > 1e-15)
        return action, decision
