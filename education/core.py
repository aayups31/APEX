from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class CarState:
    time_s: float
    position_m: float
    speed_mps: float

def step_car(state: CarState, throttle: float, brake: float, dt: float, *, mass_kg: float=800.0, engine_force_n: float=12000.0, brake_force_n: float=18000.0, drag_coeff: float=0.45) -> CarState:
    if dt <= 0:
        raise ValueError("dt must be positive")
    throttle = float(np.clip(throttle, 0.0, 1.0))
    brake = float(np.clip(brake, 0.0, 1.0))
    drive = throttle * engine_force_n
    braking = brake * brake_force_n
    drag = drag_coeff * state.speed_mps ** 2
    acceleration = (drive - braking - drag) / mass_kg
    next_speed = max(0.0, state.speed_mps + acceleration * dt)
    next_position = state.position_m + next_speed * dt
    return CarState(state.time_s + dt, next_position, next_speed)

def cyclic_delta(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    raw = a - b
    return (raw + 0.5) % 1.0 - 0.5

def sliding_windows(values: np.ndarray, history: int, horizon: int):
    if values.ndim != 2:
        raise ValueError("values must have shape [time, features]")
    if history <= 0 or horizon <= 0:
        raise ValueError("history and horizon must be positive")
    xs, ys = [], []
    for start in range(0, len(values) - history - horizon + 1):
        xs.append(values[start:start+history])
        ys.append(values[start+history:start+history+horizon])
    return np.asarray(xs), np.asarray(ys)
