"""R034 matched horizon errors; unsupported continuous lap/stint scopes stay explicit."""
from __future__ import annotations

import numpy as np

from apexsim.research.longitudinal_calibration import SpecificPowerDrag, integrate_speed, physical_prior
from apexsim.research.longitudinal_data import LongitudinalSection

HORIZONS = (.5, 1., 2., 3.)
METHODS = ("shared_drag", "physical_prior", "legacy_huber", "constant_speed", "constant_acceleration")


def horizon_grid(section: LongitudinalSection, horizon_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Insert exact endpoint; hold controls backward, interpolate evaluation target only."""
    duration = float(section.time_s[-1]-section.time_s[0])
    if not np.isfinite(horizon_s) or horizon_s <= 0 or horizon_s > duration+1e-9:
        raise ValueError("R034 HORIZON_OUTSIDE_FROZEN_SECTION")
    relative = section.time_s-section.time_s[0]
    t = np.r_[0., relative[(relative > 0) & (relative < horizon_s-1e-9)], horizon_s]
    parent = np.searchsorted(relative, t+1e-10, side="right")-1
    return t, section.throttle[parent], section.drs_open[parent], np.interp(t, relative, section.speed_mps)


def predict_horizon(section: LongitudinalSection, horizon_s: float, method: str, models: dict) -> np.ndarray:
    """Use only initial speed, causal past slope and supplied recorded controls."""
    t, throttle, drs, _ = horizon_grid(section, horizon_s)
    initial = float(section.speed_mps[0])
    if method == "constant_speed":
        return np.full(len(t), initial)
    if method == "constant_acceleration":
        return initial+section.initial_acceleration_mps2*t
    if method == "shared_drag":
        law = SpecificPowerDrag(**models["candidates"]["shared_drag"]["cells"][section.cell]["parameters"]).acceleration
    elif method == "physical_prior":
        law = physical_prior().acceleration
    elif method == "legacy_huber":
        fit = models["legacy"][section.cell]

        def law(v, u, z):
            return -fit["rolling_accel"]+fit["throttle_accel_gain"]*u-fit["drag_accel_coeff"]*v*v
    else:
        raise ValueError("R034 unknown frozen method")
    return integrate_speed(initial, t, throttle, drs, law, max_step_s=.05)


def error_record(t: np.ndarray, observed: np.ndarray, predicted: np.ndarray) -> dict:
    """Matched future nodes only; distance is a reconstructed speed integral."""
    if (t.ndim != 1 or len(t) < 2 or observed.shape != t.shape or predicted.shape != t.shape
            or not np.isfinite([t, observed, predicted]).all() or np.any(np.diff(t) <= 0)
            or not np.isclose(observed[0], predicted[0], rtol=0, atol=1e-7)):
        raise ValueError("R034 invalid matched time/target/prediction contract")
    delta = predicted[1:]-observed[1:]
    signed_distance = float(np.sum((predicted[:-1]+predicted[1:]-observed[:-1]-observed[1:])*.5*np.diff(t)))
    return {"mse_m2ps2": float(np.mean(delta**2)), "mae_mps": float(np.mean(abs(delta))),
            "absolute_endpoint_error_mps": float(abs(delta[-1])), "absolute_speed_integral_error_m": abs(signed_distance),
            "endpoint_error_mps": float(delta[-1]), "speed_integral_error_m": signed_distance,
            "future_nodes": len(delta), "raw_nonphysical_nodes": int(np.sum((predicted <= 0) | (predicted > 120)))}


def hierarchical_scores(records: list[dict]) -> dict | None:
    """Equal sections/lap, laps/driver, drivers/event, events; never mix horizons."""
    if not records:
        return None
    if len({r["horizon_s"] for r in records}) != 1:
        raise ValueError("R034 cannot pool different forecast horizons")
    fields = ("mse_m2ps2", "mae_mps", "absolute_endpoint_error_mps", "absolute_speed_integral_error_m")
    laps = {}
    for r in records:
        laps.setdefault((r["event_id"], r["driver_id"], r["lap_id"]), []).append(r)
    lap_values = {key: {f: float(np.mean([r[f] for r in rows])) for f in fields} for key, rows in laps.items()}
    drivers = {}
    for (event, driver, _), values in lap_values.items():
        drivers.setdefault((event, driver), []).append(values)
    driver_values = {key: {f: float(np.mean([v[f] for v in values])) for f in fields} for key, values in drivers.items()}
    events = {}
    for (event, _), values in driver_values.items():
        events.setdefault(event, []).append(values)
    event_values = {key: {f: float(np.mean([v[f] for v in values])) for f in fields} for key, values in events.items()}
    result = {f: float(np.mean([v[f] for v in event_values.values()])) for f in fields}
    result.update(rmse_mps=float(np.sqrt(result["mse_m2ps2"])), sections=len(records), laps=len(laps),
                  events=len(events), drivers=len(drivers), raw_nonphysical_nodes=sum(r["raw_nonphysical_nodes"] for r in records))
    return result


def regime_labels(section: LongitudinalSection) -> list[str]:
    v = section.speed_mps[0]
    return [section.metadata["track_id"], "drs_open" if section.drs_open[0] else "drs_closed",
            "speed_40_60" if v < 60 else "speed_60_80" if v < 80 else "speed_80_105"]
