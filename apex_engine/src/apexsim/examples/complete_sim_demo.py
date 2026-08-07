from __future__ import annotations

import argparse
import json
from pathlib import Path

from apexsim.sim_core.race import RaceSimulator
from apexsim.sim_core.track import TrackMap
from apexsim.sim_core.types import (
    CarParameters,
    DriverParameters,
    PaceMode,
    PitStopPlan,
    RaceControlEvent,
    RaceEntry,
    SimulationConfig,
    TyreCompound,
    WeatherKeyframe,
    FlagState,
)


def build_demo(seed: int = 42, total_laps: int = 6) -> RaceSimulator:
    track = TrackMap.synthetic(length_m=3600.0, points=900, seed=seed)
    base_car = CarParameters(reliability_per_hour=1.0, fuel_burn_kg_per_km=0.020)
    names = ["Apex", "Orion", "Nova", "Vector", "Pulse", "Zenith"]
    entries: list[RaceEntry] = []
    for index, name in enumerate(names):
        driver = DriverParameters(
            name=name,
            aggression=0.58 + 0.06 * (index % 3),
            consistency=0.95 - 0.015 * index,
            tyre_management=0.62 + 0.05 * ((index + 1) % 3),
            wet_skill=0.62 + 0.04 * (index % 4),
            overtaking=0.58 + 0.05 * (index % 4),
            pace_offset=0.035 - 0.012 * index,
            seed=seed + index * 17,
        )
        if index == 0:
            strategy = [PitStopPlan(max(3, total_laps // 2), TyreCompound.HARD)]
            initial = TyreCompound.MEDIUM
            mode = PaceMode.PUSH
        elif index % 2 == 0:
            strategy = [PitStopPlan(max(2, total_laps // 2 - 1), TyreCompound.MEDIUM)]
            initial = TyreCompound.SOFT
            mode = PaceMode.ATTACK
        else:
            strategy = [PitStopPlan(max(3, total_laps // 2 + 1), TyreCompound.HARD)]
            initial = TyreCompound.MEDIUM
            mode = PaceMode.HOLD
        entries.append(
            RaceEntry(
                car_id=f"CAR_{index + 1:02d}",
                driver=driver,
                car=base_car,
                initial_compound=initial,
                strategy=strategy,
                pace_mode=mode,
                grid_position=index + 1,
            )
        )
    weather = [
        WeatherKeyframe(0.0, track_temp_c=36.0, rain_intensity=0.0, surface_grip=1.0),
        WeatherKeyframe(260.0, track_temp_c=31.0, rain_intensity=0.12, standing_water=0.02, surface_grip=0.95),
        WeatherKeyframe(520.0, track_temp_c=28.0, rain_intensity=0.32, standing_water=0.14, surface_grip=0.88),
        WeatherKeyframe(780.0, track_temp_c=30.0, rain_intensity=0.04, standing_water=0.03, surface_grip=0.94),
    ]
    race_control = [
        RaceControlEvent(390.0, 420.0, FlagState.VSC, "Demo VSC window"),
    ]
    config = SimulationConfig(
        dt_s=0.25,
        total_laps=total_laps,
        random_seed=seed,
        telemetry_stride=2,
        max_simulation_time_s=2400.0,
    )
    return RaceSimulator(track, entries, config, weather, race_control)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the APEX complete-simulation vertical slice")
    parser.add_argument("--output", type=Path, default=Path("artifacts/complete_sim_demo"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--laps", type=int, default=6)
    args = parser.parse_args()
    simulator = build_demo(args.seed, args.laps)
    result = simulator.run()
    result.save(args.output)
    simulator.track.save_csv(args.output / "track.csv")
    payload = {
        "output": str(args.output),
        "track": result.track_id,
        "telemetry_rows": len(result.telemetry),
        "events": len(result.events),
        "winner": result.standings.iloc[0].to_dict() if not result.standings.empty else None,
    }
    (args.output / "run_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
