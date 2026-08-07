from __future__ import annotations

from dataclasses import replace

import numpy as np

from apexsim.sim_core.types import EnvironmentState, FlagState, RaceControlEvent, WeatherKeyframe


class WeatherSchedule:
    def __init__(self, keyframes: list[WeatherKeyframe] | None = None):
        self.keyframes = sorted(keyframes or [WeatherKeyframe(0.0)], key=lambda item: item.time_s)

    def at(self, time_s: float, flag: FlagState = FlagState.GREEN) -> EnvironmentState:
        if len(self.keyframes) == 1:
            key = self.keyframes[0]
            return EnvironmentState(
                air_temp_c=key.air_temp_c,
                track_temp_c=key.track_temp_c,
                rain_intensity=key.rain_intensity,
                standing_water=key.standing_water,
                wind_speed_mps=key.wind_speed_mps,
                wind_direction_rad=key.wind_direction_rad,
                surface_grip=key.surface_grip,
                flag=flag,
            )
        times = np.array([k.time_s for k in self.keyframes], dtype=float)
        i = int(np.searchsorted(times, time_s, side="right") - 1)
        i = max(0, min(i, len(self.keyframes) - 1))
        if i == len(self.keyframes) - 1:
            left = right = self.keyframes[i]
            alpha = 0.0
        else:
            left, right = self.keyframes[i], self.keyframes[i + 1]
            alpha = (time_s - left.time_s) / max(right.time_s - left.time_s, 1e-6)
            alpha = float(np.clip(alpha, 0.0, 1.0))

        def lerp(name: str) -> float:
            return float((1.0 - alpha) * getattr(left, name) + alpha * getattr(right, name))

        return EnvironmentState(
            air_temp_c=lerp("air_temp_c"),
            track_temp_c=lerp("track_temp_c"),
            rain_intensity=lerp("rain_intensity"),
            standing_water=lerp("standing_water"),
            wind_speed_mps=lerp("wind_speed_mps"),
            wind_direction_rad=lerp("wind_direction_rad"),
            surface_grip=lerp("surface_grip"),
            flag=flag,
        )


class RaceControlSchedule:
    def __init__(self, events: list[RaceControlEvent] | None = None):
        self.events = sorted(events or [], key=lambda item: item.start_s)

    def flag_at(self, time_s: float) -> FlagState:
        active = [event for event in self.events if event.start_s <= time_s < event.end_s]
        if not active:
            return FlagState.GREEN
        priority = {
            FlagState.GREEN: 0,
            FlagState.YELLOW: 1,
            FlagState.VSC: 2,
            FlagState.SAFETY_CAR: 3,
            FlagState.RED: 4,
        }
        return max((event.flag for event in active), key=lambda flag: priority[flag])
