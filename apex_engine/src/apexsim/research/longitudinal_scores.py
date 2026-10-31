"""R030 equal-driver/lap section errors and conditional paired lap bootstrap."""
from __future__ import annotations

import numpy as np

from apexsim.research.longitudinal_data import LongitudinalSection


def section_errors(section: LongitudinalSection, predicted: np.ndarray) -> dict:
    """Exclude observed initial speed; distance is speed integral, not surveyed GPS."""
    if (predicted.shape != section.speed_mps.shape or not np.isfinite(predicted).all()
            or not np.isclose(predicted[0], section.speed_mps[0], rtol=0, atol=1e-7)):
        raise ValueError("R030 finite matched speed prediction contract failed")
    error = predicted[1:]-section.speed_mps[1:]
    delta = np.diff(section.time_s)
    actual_distance = float(np.sum((section.speed_mps[:-1]+section.speed_mps[1:])*.5*delta))
    estimated_distance = float(np.sum((predicted[:-1]+predicted[1:])*.5*delta))
    return {"mse_m2ps2": float(np.mean(error**2)), "mae_mps": float(np.mean(abs(error))),
            "endpoint_error_mps": float(error[-1]), "absolute_endpoint_error_mps": float(abs(error[-1])),
            "speed_integral_distance_error_m": estimated_distance-actual_distance,
            "absolute_speed_integral_distance_error_m": abs(estimated_distance-actual_distance),
            "predicted_nodes": len(error), "sum_squared_error_m2ps2": float(error@error),
            "raw_out_of_physical_domain_nodes": int(np.sum((predicted <= 0) | (predicted > 120)))}


def aggregate_errors(sections: list[LongitudinalSection], predictions: list[np.ndarray]) -> dict:
    """Equal sections within lap, equal laps within driver, equal drivers."""
    if not sections or len(sections) != len(predictions):
        raise ValueError("R030 aggregate requires nonempty matched sections")
    records = [section_errors(s, p) for s, p in zip(sections, predictions, strict=True)]
    lap_indices: dict[str, list[int]] = {}
    driver_laps: dict[str, list[str]] = {}
    for i, section in enumerate(sections):
        lap = section.metadata["lap_id"]
        driver = section.metadata["driver_id"]
        if lap not in lap_indices:
            driver_laps.setdefault(driver, []).append(lap)
        lap_indices.setdefault(lap, []).append(i)
    fields = ("mse_m2ps2", "mae_mps", "absolute_endpoint_error_mps", "absolute_speed_integral_distance_error_m")
    laps = {lap: {key: float(np.mean([records[i][key] for i in indices])) for key in fields}
            for lap, indices in lap_indices.items()}
    drivers = {driver: {key: float(np.mean([laps[lap][key] for lap in ids])) for key in fields}
               for driver, ids in driver_laps.items()}
    result = {key: float(np.mean([d[key] for d in drivers.values()])) for key in fields}
    result.update(rmse_mps=float(np.sqrt(result["mse_m2ps2"])), sections=len(sections), laps=len(laps),
                  per_driver=drivers, per_lap=laps, section_errors=records,
                  frame_weighted_rmse_mps=float(np.sqrt(sum(r["sum_squared_error_m2ps2"] for r in records)/sum(r["predicted_nodes"] for r in records))),
                  raw_out_of_physical_domain_nodes=sum(r["raw_out_of_physical_domain_nodes"] for r in records))
    for values in drivers.values():
        values["rmse_mps"] = float(np.sqrt(values["mse_m2ps2"]))
    return result


def paired_lap_interval(selected: dict, baseline: dict, sections: list[LongitudinalSection], *,
                         resamples: int = 500) -> dict:
    """Fixed drivers/test event, resample whole laps; serial section dependence retained."""
    if set(selected["per_lap"]) != set(baseline["per_lap"]) or resamples < 20:
        raise ValueError("R030 paired bootstrap requires matched laps and>=20 resamples")
    driver_laps: dict[str, set[str]] = {}
    for section in sections:
        driver_laps.setdefault(section.metadata["driver_id"], set()).add(section.metadata["lap_id"])
    differences = {}
    for driver, ids in sorted(driver_laps.items()):
        differences[driver] = np.array([selected["per_lap"][lap]["mse_m2ps2"]-baseline["per_lap"][lap]["mse_m2ps2"] for lap in sorted(ids)])
    rng = np.random.default_rng(3030)
    values = [np.mean([d[rng.integers(0, len(d), len(d))].mean() for d in differences.values()]) for _ in range(resamples)]
    return {"seed": 3030, "resamples": resamples, "resampling_unit": "LAP_WITHIN_FIXED_DRIVER_AND_EVENT",
            "difference_mse_m2ps2": selected["mse_m2ps2"]-baseline["mse_m2ps2"],
            "interval_95_m2ps2": np.quantile(values, [.025, .975]).tolist()}


def error_breakdowns(sections: list[LongitudinalSection], predictions: list[np.ndarray]) -> dict:
    groups: dict[str, list[int]] = {}
    for i, s in enumerate(sections):
        speed = s.speed_mps[0]
        labels = ["drs_open" if s.drs_open[0] else "drs_closed",
                  "speed_40_60" if speed < 60 else "speed_60_80" if speed < 80 else "speed_80_105",
                  "duration_2_3s" if s.time_s[-1]-s.time_s[0] < 3 else "duration_3_3.5s"]
        for label in labels:
            groups.setdefault(label, []).append(i)
    return {label: {k: v for k, v in aggregate_errors([sections[i] for i in indices], [predictions[i] for i in indices]).items()
                    if k not in ("section_errors", "per_lap")} for label, indices in groups.items()}
