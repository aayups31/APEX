from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.provenance import build_run_manifest, write_manifest
from apexsim.sim_core.driver import ReferenceDriverPolicy
from apexsim.sim_core.track import TrackMap
from apexsim.sim_core.types import (
    CarState,
    FlagState,
    PaceMode,
    RaceControlEvent,
    RaceEntry,
    SimulationConfig,
    WeatherKeyframe,
)
from apexsim.sim_core.validation import (
    assert_simulation_quality,
    derive_lap_table,
    derive_stint_table,
    validate_simulation_telemetry,
)
from apexsim.sim_core.vehicle import VehicleDynamics
from apexsim.sim_core.weather import RaceControlSchedule, WeatherSchedule


@dataclass
class RaceResult:
    telemetry: pd.DataFrame
    standings: pd.DataFrame
    events: pd.DataFrame
    laps: pd.DataFrame
    stints: pd.DataFrame
    quality_report: dict
    config: SimulationConfig
    track_id: str
    track: pd.DataFrame

    def save(self, output_dir: str | Path) -> None:
        root = Path(output_dir)
        if root.exists() and any(root.iterdir()):
            raise FileExistsError(f"Race artifact directory is not empty: {root}")
        root.mkdir(parents=True, exist_ok=True)
        self.telemetry.to_csv(root / "telemetry.csv", index=False)
        self.standings.to_csv(root / "standings.csv", index=False)
        self.events.to_csv(root / "events.csv", index=False)
        self.laps.to_csv(root / "laps.csv", index=False)
        self.stints.to_csv(root / "stints.csv", index=False)
        self.track.to_csv(root / "track.csv", index=False)
        import json

        (root / "quality_report.json").write_text(json.dumps(self.quality_report, indent=2), encoding="utf-8")
        (root / "summary.json").write_text(
            json.dumps({"track_id": self.track_id, "standings": self.standings.to_dict(orient="records"), "quality": self.quality_report}, indent=2),
            encoding="utf-8",
        )
        artifact_paths = [
            root / "telemetry.csv",
            root / "standings.csv",
            root / "events.csv",
            root / "laps.csv",
            root / "stints.csv",
            root / "track.csv",
            root / "quality_report.json",
            root / "summary.json",
        ]
        repository_root = Path(__file__).resolve().parents[4]
        write_manifest(
            root / "manifest.json",
            build_run_manifest(
                run_id=root.name,
                run_type="race_simulation",
                config=self.config,
                seed=self.config.random_seed,
                repository_root=repository_root,
                artifacts=artifact_paths,
                truth_labels={
                    "telemetry": "SIMULATED",
                    "tyre_temperature": "SIMULATED_PROXY",
                    "tyre_health": "SIMULATED_PROXY",
                    "battery": "SIMULATED_PROXY",
                },
                notes=["V0 deterministic race-simulation vertical slice"],
            ),
        )


class RaceSimulator:
    def __init__(
        self,
        track: TrackMap,
        entries: list[RaceEntry],
        config: SimulationConfig | None = None,
        weather: list[WeatherKeyframe] | None = None,
        race_control: list[RaceControlEvent] | None = None,
        dynamics: VehicleDynamics | None = None,
        policy_factory: Callable[[RaceEntry], ReferenceDriverPolicy] | None = None,
    ):
        if not entries:
            raise ValueError("At least one race entry is required")
        self.track = track
        self.entries = sorted(entries, key=lambda entry: entry.grid_position)
        self.config = config or SimulationConfig()
        self.weather = WeatherSchedule(weather)
        self.race_control = RaceControlSchedule(race_control)
        self.dynamics = dynamics or VehicleDynamics()
        self.policy_factory = policy_factory or (lambda entry: ReferenceDriverPolicy(entry.driver))
        self.rng = np.random.default_rng(self.config.random_seed)

    def _initial_states(self) -> dict[str, CarState]:
        states: dict[str, CarState] = {}
        for entry in self.entries:
            grid_offset = max(entry.grid_position - 1, 0) * 8.5
            # Every car starts before completing lap 1. Grid spacing affects race distance/order,
            # but does not grant the rear rows an immediate lap crossing.
            s = 0.0
            total_distance = -grid_offset
            states[entry.car_id] = CarState(
                car_id=entry.car_id,
                driver_id=entry.driver.name,
                lap=1,
                s_m=s,
                speed_mps=0.0,
                fuel_kg=min(entry.car.fuel_capacity_kg, entry.car.fuel_capacity_kg * 0.93),
                battery_mj=entry.car.ers_capacity_mj,
                tyre_compound=entry.initial_compound,
                tyre_temp_c=82.0,
                total_distance_m=total_distance,
                position=entry.grid_position,
                metadata={"completed_pit_plans": [], "overtake_boost_until": -1.0},
            )
        return states

    @staticmethod
    def _running_order(states: dict[str, CarState]) -> list[CarState]:
        finished = sorted(
            (state for state in states.values() if state.finished),
            key=lambda state: float(state.metadata.get("finish_time_s", float("inf"))),
        )
        active = sorted(
            (state for state in states.values() if not state.finished and not state.retired),
            key=lambda state: state.total_distance_m,
            reverse=True,
        )
        retired = sorted(
            (state for state in states.values() if state.retired and not state.finished),
            key=lambda state: state.total_distance_m,
            reverse=True,
        )
        return finished + active + retired

    def _gap_map(self, order: list[CarState]) -> dict[str, tuple[float | None, float | None]]:
        gaps: dict[str, tuple[float | None, float | None]] = {}
        if not order:
            return gaps
        leader = order[0]
        for index, state in enumerate(order):
            if index == 0:
                gaps[state.car_id] = (None, 0.0)
                continue
            ahead = order[index - 1]
            gap_m = max(ahead.total_distance_m - state.total_distance_m, 0.0)
            gap_leader_m = max(leader.total_distance_m - state.total_distance_m, 0.0)
            reference_speed = max(state.speed_mps, 12.0)
            gaps[state.car_id] = (gap_m, gap_leader_m / reference_speed)
        return gaps

    def _pit_plan_for_state(self, entry: RaceEntry, state: CarState):
        completed = set(state.metadata.get("completed_pit_plans", []))
        for index, plan in enumerate(entry.strategy):
            if index not in completed and plan.should_trigger(state.lap):
                return index, plan
        return None

    def run(self) -> RaceResult:
        states = self._initial_states()
        entries = {entry.car_id: entry for entry in self.entries}
        policies = {entry.car_id: self.policy_factory(entry) for entry in self.entries}
        rows: list[dict] = []
        events: list[dict] = []
        step_index = 0

        while True:
            active = [state for state in states.values() if not state.finished and not state.retired]
            if not active:
                break
            current_time = max(state.time_s for state in states.values())
            if current_time >= self.config.max_simulation_time_s:
                events.append({"time_s": current_time, "type": "TIME_LIMIT", "car_id": "", "detail": "Simulation time limit reached"})
                break

            order = self._running_order(states)
            gaps = self._gap_map(order)
            for position, state in enumerate(order, start=1):
                state.position = position
                state.gap_ahead_m, state.gap_to_leader_s = gaps.get(state.car_id, (None, None))

            flag = self.race_control.flag_at(current_time)
            environment = self.weather.at(current_time, flag)

            next_states: dict[str, CarState] = {}
            for state in order:
                entry = entries[state.car_id]
                if state.finished or state.retired:
                    next_states[state.car_id] = state
                    continue

                # Pit loss is modeled as one transparent time block in V1. The track/pit-lane
                # path is a later acceptance gate, not hidden inside an opaque correction.
                if state.in_pit:
                    remaining = max(0.0, state.pit_timer_s - self.config.dt_s)
                    if remaining <= 0.0:
                        compound = state.pending_compound or state.tyre_compound
                        events.append({
                            "time_s": current_time,
                            "type": "PIT_EXIT",
                            "car_id": state.car_id,
                            "detail": f"{compound.value}",
                        })
                        next_states[state.car_id] = state.clone(
                            time_s=current_time + self.config.dt_s,
                            in_pit=False,
                            pit_timer_s=0.0,
                            pending_compound=None,
                            tyre_compound=compound,
                            tyre_age_laps=0.0,
                            tyre_health=1.0,
                            tyre_temp_c=68.0,
                            speed_mps=min(entry.car.pit_speed_limit_mps, 18.0),
                        )
                    else:
                        next_states[state.car_id] = state.clone(
                            time_s=current_time + self.config.dt_s,
                            pit_timer_s=remaining,
                            speed_mps=0.0,
                        )
                    continue

                pending = self._pit_plan_for_state(entry, state)
                near_pit_entry = state.s_m >= self.track.length_m - self.config.pit_entry_window_m
                if pending and near_pit_entry:
                    plan_index, plan = pending
                    completed = list(state.metadata.get("completed_pit_plans", []))
                    completed.append(plan_index)
                    metadata = dict(state.metadata)
                    metadata["completed_pit_plans"] = completed
                    pit_loss = self.config.pit_lane_time_loss_s + entry.car.pit_stationary_time_s
                    events.append({
                        "time_s": current_time,
                        "type": "PIT_ENTRY",
                        "car_id": state.car_id,
                        "detail": f"lap={state.lap}, compound={plan.compound.value}",
                    })
                    next_states[state.car_id] = state.clone(
                        time_s=current_time + self.config.dt_s,
                        in_pit=True,
                        pit_timer_s=pit_loss,
                        pending_compound=plan.compound,
                        speed_mps=0.0,
                        metadata=metadata,
                    )
                    continue

                gap_ahead = state.gap_ahead_m
                gap_seconds = None if gap_ahead is None else gap_ahead / max(state.speed_mps, 12.0)
                drs_eligible = bool(
                    state.lap >= self.config.drs_enabled_from_lap
                    and gap_seconds is not None
                    and gap_seconds <= self.config.drs_detection_gap_s
                    and flag == FlagState.GREEN
                )
                track_sample = self.track.sample(state.s_m)
                boost_until = float(state.metadata.get("overtake_boost_until", -1.0))
                if (
                    drs_eligible
                    and track_sample.drs_allowed
                    and gap_ahead is not None
                    and gap_ahead < 22.0
                    and current_time >= boost_until
                ):
                    probability = entry.driver.overtaking * entry.driver.aggression * self.config.dt_s * 0.45
                    if self.rng.random() < probability:
                        boost_until = current_time + 4.0
                        state.metadata["overtake_boost_until"] = boost_until
                        events.append({
                            "time_s": current_time,
                            "type": "OVERTAKE_ATTEMPT",
                            "car_id": state.car_id,
                            "detail": f"gap_m={gap_ahead:.1f}",
                        })
                passing = current_time < boost_until
                policy_gap = None if passing else gap_ahead
                pace_mode = PaceMode.ATTACK if passing else entry.pace_mode
                control = policies[state.car_id].act(
                    state,
                    entry.car,
                    self.track,
                    environment,
                    pace_mode,
                    policy_gap,
                    drs_eligible,
                )
                next_state, diagnostics = self.dynamics.step(
                    state,
                    control,
                    entry.car,
                    entry.driver,
                    self.track,
                    environment,
                    self.config.dt_s,
                    gap_ahead,
                    drs_eligible,
                )
                if next_state.lap > self.config.total_laps:
                    next_state.finished = True
                    next_state.speed_mps = 0.0
                    next_state.metadata["finish_time_s"] = next_state.time_s
                    events.append({
                        "time_s": next_state.time_s,
                        "type": "FINISH",
                        "car_id": state.car_id,
                        "detail": f"race_time_s={next_state.time_s:.3f}",
                    })
                if next_state.retired and not state.retired:
                    events.append({
                        "time_s": next_state.time_s,
                        "type": "RETIREMENT",
                        "car_id": state.car_id,
                        "detail": "reliability_or_damage",
                    })
                next_states[state.car_id] = next_state

                if step_index % self.config.telemetry_stride == 0:
                    rows.append(
                        {
                            "time_s": next_state.time_s,
                            "car_id": next_state.car_id,
                            "driver_id": next_state.driver_id,
                            "position": next_state.position,
                            "lap": next_state.lap,
                            "s_m": next_state.s_m,
                            "total_distance_m": next_state.total_distance_m,
                            "speed_mps": next_state.speed_mps,
                            "throttle": control.throttle,
                            "brake": control.brake,
                            "ers_deploy": control.ers_deploy,
                            "drs": int(diagnostics.drs_active),
                            "fuel_kg": next_state.fuel_kg,
                            "battery_mj": next_state.battery_mj,
                            "tyre_compound": next_state.tyre_compound.value,
                            "tyre_age_laps": next_state.tyre_age_laps,
                            "tyre_health": next_state.tyre_health,
                            "tyre_temp_c": next_state.tyre_temp_c,
                            "effective_grip": diagnostics.effective_grip,
                            "curvature_1pm": track_sample.curvature_1pm,
                            "speed_limit_mps": diagnostics.speed_limit_mps,
                            "acceleration_mps2": diagnostics.acceleration_mps2,
                            "downforce_n": diagnostics.downforce_n,
                            "drag_n": diagnostics.drag_n,
                            "dirty_air_factor": diagnostics.dirty_air_factor,
                            "gap_ahead_m": next_state.gap_ahead_m,
                            "gap_to_leader_s": next_state.gap_to_leader_s,
                            "rain_intensity": environment.rain_intensity,
                            "track_temp_c": environment.track_temp_c,
                            "flag": environment.flag.value,
                            "in_pit": int(next_state.in_pit),
                            "retired": int(next_state.retired),
                            "finished": int(next_state.finished),
                        }
                    )

            states = next_states
            step_index += 1

        final_order = self._running_order(states)
        standings_rows = []
        for position, state in enumerate(final_order, start=1):
            status = "FINISHED" if state.finished else "RETIRED" if state.retired else "STOPPED"
            standings_rows.append(
                {
                    "position": position,
                    "car_id": state.car_id,
                    "driver_id": state.driver_id,
                    "status": status,
                    "race_time_s": float(state.metadata.get("finish_time_s", state.time_s)) if state.finished else np.nan,
                    "laps_completed": min(state.lap - 1, self.config.total_laps),
                    "total_distance_m": state.total_distance_m,
                    "final_compound": state.tyre_compound.value,
                    "pit_stops": len(state.metadata.get("completed_pit_plans", [])),
                    "fuel_remaining_kg": state.fuel_kg,
                    "tyre_health": state.tyre_health,
                }
            )
        telemetry = pd.DataFrame(rows)
        if not telemetry.empty:
            # Recompute position per timestamp after all cars have moved.
            telemetry["position"] = telemetry.groupby("time_s")["total_distance_m"].rank(
                method="first", ascending=False
            ).astype(int)
        laps = derive_lap_table(telemetry, self.config.total_laps)
        stints = derive_stint_table(telemetry)
        quality_report = validate_simulation_telemetry(
            telemetry,
            expected_cars=len(self.entries),
            battery_capacity_mj=max(entry.car.ers_capacity_mj for entry in self.entries),
        )
        assert_simulation_quality(quality_report)
        quality = quality_report.to_dict()
        return RaceResult(
            telemetry=telemetry,
            standings=pd.DataFrame(standings_rows),
            events=pd.DataFrame(events, columns=["time_s", "type", "car_id", "detail"]),
            laps=laps,
            stints=stints,
            quality_report=quality,
            config=self.config,
            track_id=self.track.track_id,
            track=self.track.to_frame(),
        )
