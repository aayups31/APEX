"""End-to-end, no-game research demo for the APEX paper layer."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.research.fienia_strategy import DiscreteStrategyOracle, PaperStrategyModel, PaperStrategyParameters
from apexsim.research.registry import registry_frame
from apexsim.research.state_space_tyre import LatentTyreDegradationFilter
from apexsim.research.tyre_energy import TyreEnergyInputs, estimate_wheel_tyre_energy
from apexsim.research.tyre_forecasting import (
    RidgeTyreEnergyForecaster,
    TrackStateEncoding,
    build_tyre_energy_windows,
    make_event_split,
    rmse,
    subset_by_events,
)
from apexsim.sim_core.types import TyreCompound


def _synthetic_tyre_energy_frame(events: int = 5, samples: int = 160, dt_s: float = 0.1) -> pd.DataFrame:
    rows = []
    for event_i in range(events):
        for t in range(samples):
            phase = 2 * np.pi * t / 50.0
            speed = 58.0 + 15.0 * np.sin(phase) + event_i
            steering = 0.09 * np.sin(phase + 0.4)
            throttle = float(np.clip(0.55 + 0.45 * np.sin(phase - 1.0), 0.0, 1.0))
            brake = float(np.clip(-0.9 * np.sin(phase - 1.0), 0.0, 1.0))
            ax = 4.0 * throttle - 7.0 * brake
            ay = speed**2 * steering / 45.0
            energy = estimate_wheel_tyre_energy(
                TyreEnergyInputs(speed, ax, ay, steering, throttle, brake, dt_s)
            ).as_array()
            noise = np.random.default_rng(1000 + event_i * samples + t).normal(0.0, 0.015, 4)
            rows.append(
                {
                    "event_id": f"SYNTH_{event_i}",
                    "time_s": t * dt_s,
                    "speed_mps": speed,
                    "steering": steering,
                    "throttle": throttle,
                    "brake": brake,
                    "track_state": "YELLOW" if 90 <= t < 100 else "GREEN",
                    "tyre_energy_front_left_kj": max(energy[0] + noise[0], 0.0),
                    "tyre_energy_front_right_kj": max(energy[1] + noise[1], 0.0),
                    "tyre_energy_rear_left_kj": max(energy[2] + noise[2], 0.0),
                    "tyre_energy_rear_right_kj": max(energy[3] + noise[3], 0.0),
                }
            )
    return pd.DataFrame(rows)


def run_research_demo(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    registry = registry_frame()
    registry.to_csv(output / "paper_registry.csv", index=False)

    model = PaperStrategyModel(PaperStrategyParameters(total_laps=8, initial_fuel_kg=16.0))
    oracle = DiscreteStrategyOracle(model, beam_width=128, pit_window=(2, 6))
    solution = oracle.solve(TyreCompound.MEDIUM)
    strategy_rows = []
    state = model.initial_state(TyreCompound.MEDIUM)
    for action in solution.actions:
        state, info = model.transition(state, action)
        strategy_rows.append(
            {
                "lap": state.lap,
                "lap_time_s": info.lap_time_s,
                "race_time_s": state.race_time_s,
                "fuel_energy_mj": state.fuel_energy_mj,
                "battery_mj": state.battery_mj,
                "compound": state.compound.value,
                "tyre_wear": state.tyre_wear,
                "pit": info.applied_action.pit_compound.value if info.applied_action.pit_compound else "",
            }
        )
    pd.DataFrame(strategy_rows).to_csv(output / "fieni_strategy_rollout.csv", index=False)

    tyre_frame = _synthetic_tyre_energy_frame()
    tyre_frame.to_csv(output / "synthetic_tyre_energy.csv", index=False)
    windows = build_tyre_energy_windows(
        tyre_frame,
        feature_columns=["speed_mps", "steering", "throttle", "brake", "track_state"],
        window=20,
        encoding=TrackStateEncoding.ONE_HOT,
    )
    split = make_event_split(windows.event_ids, seed=42)
    train = subset_by_events(windows, split.train_events)
    test = subset_by_events(windows, split.test_events)
    ridge = RidgeTyreEnergyForecaster(alpha=0.1).fit(train.x, train.y)
    test_prediction = ridge.predict(test.x)
    prediction_frame = pd.DataFrame(test_prediction, columns=[f"pred_{c}" for c in ("fl", "fr", "rl", "rr")])
    for idx, name in enumerate(("true_fl", "true_fr", "true_rl", "true_rr")):
        prediction_frame[name] = test.y[:, idx]
    prediction_frame.to_csv(output / "tyre_energy_predictions.csv", index=False)

    laps = np.arange(20)
    fuel = 40.0 - 1.7 * laps
    pit_reset = laps == 11
    latent = np.where(laps < 11, 0.07 * laps, 0.04 * (laps - 11))
    lap_times = 91.0 + 0.03 * fuel + latent
    compounds = np.where(laps < 11, "MEDIUM", "HARD")
    tyre_state = LatentTyreDegradationFilter().filter(lap_times, fuel, compounds, pit_reset)
    tyre_state.to_csv(output / "latent_tyre_degradation.csv", index=False)

    summary = {
        "paper_count": int(len(registry)),
        "strategy": {
            "race_time_s": float(solution.state.race_time_s),
            "compound_changed": bool(solution.state.compound_changed),
            "residual_fuel_energy_mj": float(solution.state.fuel_energy_mj),
            "residual_battery_mj": float(solution.state.battery_mj),
        },
        "tyre_energy": {
            "train_windows": int(len(train.x)),
            "test_windows": int(len(test.x)),
            "ridge_test_rmse": rmse(test.y, test_prediction),
            "target_quality": "synthetic proxy, not proprietary measured tyre energy",
        },
        "state_space": {
            "rows": int(len(tyre_state)),
            "pit_reset_lap": 11,
            "final_latent_degradation_s": float(tyre_state.iloc[-1].latent_tyre_pace_s),
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
