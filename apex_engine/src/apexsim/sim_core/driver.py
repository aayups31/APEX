from __future__ import annotations

import math

import numpy as np

from apexsim.sim_core.track import TrackMap
from apexsim.sim_core.types import (
    CarParameters,
    CarState,
    Control,
    DriverParameters,
    EnvironmentState,
    FlagState,
    PaceMode,
)
from apexsim.sim_core.tyres import effective_tyre_grip

PACE_FACTORS = {
    PaceMode.CONSERVE: 0.91,
    PaceMode.HOLD: 0.96,
    PaceMode.PUSH: 1.00,
    PaceMode.ATTACK: 1.025,
    PaceMode.QUALIFY: 1.045,
}


class ReferenceDriverPolicy:
    """Transparent baseline driver used before imitation/RL policies.

    It follows a curvature-derived target speed with configurable pace, noise,
    tyre management, traffic, weather and flag behavior.
    """

    def __init__(self, parameters: DriverParameters):
        self.parameters = parameters
        self.rng = np.random.default_rng(parameters.seed)

    def target_speed(
        self,
        state: CarState,
        car: CarParameters,
        track: TrackMap,
        environment: EnvironmentState,
        pace_mode: PaceMode,
    ) -> float:
        grip = effective_tyre_grip(
            state.tyre_compound,
            state.tyre_temp_c,
            state.tyre_health,
            environment,
        )
        lookahead = 130.0 + 1.3 * state.speed_mps
        curvature = max(track.lookahead_curvature(state.s_m, lookahead), 1e-5)
        lateral_limit = grip * 9.81 * (1.0 + 0.0014 * state.speed_mps**2)
        corner_speed = math.sqrt(max(lateral_limit / curvature, 1.0))
        straight_speed = 95.0 + 6.0 * max(self.parameters.pace_offset, -0.5)
        target = min(corner_speed, straight_speed)
        target *= PACE_FACTORS[pace_mode]
        if environment.rain_intensity > 0.05:
            target *= 0.94 + 0.06 * self.parameters.wet_skill
        if environment.flag == FlagState.YELLOW:
            target *= 0.72
        elif environment.flag == FlagState.VSC:
            target *= 0.62
        elif environment.flag == FlagState.SAFETY_CAR:
            target *= 0.46
        elif environment.flag == FlagState.RED:
            target = 0.0
        return max(target, 0.0)

    def act(
        self,
        state: CarState,
        car: CarParameters,
        track: TrackMap,
        environment: EnvironmentState,
        pace_mode: PaceMode,
        gap_ahead_m: float | None,
        drs_eligible: bool,
    ) -> Control:
        if state.retired or state.finished:
            return Control()
        target = self.target_speed(state, car, track, environment, pace_mode)
        if gap_ahead_m is not None and 0.0 < gap_ahead_m < 22.0:
            follow_target = max(8.0, state.speed_mps * (0.72 + 0.012 * gap_ahead_m))
            target = min(target, follow_target)
        error = target - state.speed_mps
        response = 0.16 + 0.18 * self.parameters.aggression
        throttle = float(np.clip(error * response, 0.0, 1.0))
        brake = float(np.clip(-error * (0.10 + 0.12 * self.parameters.aggression), 0.0, 1.0))
        # Avoid simultaneous throttle and brake in the transparent baseline.
        if throttle > brake:
            brake = 0.0
        else:
            throttle = 0.0
        noise_scale = (1.0 - self.parameters.consistency) * 0.08
        throttle = float(np.clip(throttle + self.rng.normal(0.0, noise_scale), 0.0, 1.0))
        brake = float(np.clip(brake + self.rng.normal(0.0, noise_scale * 0.7), 0.0, 1.0))
        curvature = track.sample(state.s_m).curvature_1pm
        steering = float(np.clip(curvature * 95.0, -1.0, 1.0))
        ers = 0.15 + 0.65 * throttle
        if pace_mode in {PaceMode.ATTACK, PaceMode.QUALIFY}:
            ers = min(1.0, ers + 0.20)
        drs = bool(drs_eligible and throttle > 0.65 and brake < 0.05)
        return Control(throttle, brake, steering, ers, drs).clipped()
