"""Private process boundary for FastF1's global cache and offline network guard."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from apexsim.data.fastf1_archive import (
    REQUIRED_TABLES,
    SNAPSHOT_VERSION,
    FastF1Query,
    environment_versions,
    validate_identity,
)
from apexsim.provenance import file_sha256, write_manifest


def snapshot_session(session, root: Path, query: FastF1Query, *, network_attempts: int) -> dict:
    """Preserve native source frames and nanosecond timestamps without interpolation."""
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    frames = {name: pd.DataFrame(getattr(session, name)) for name in sorted(REQUIRED_TABLES)}
    cars, positions = session.car_data, session.pos_data
    if set(cars) != set(positions):
        raise ValueError("FastF1 car/location driver inventories disagree")
    lap_drivers = set(frames["laps"]["DriverNumber"].dropna().astype(str))
    if not lap_drivers or not lap_drivers.issubset(cars) or not lap_drivers.issubset(positions):
        raise ValueError("FastF1 session is missing lap-driver car/location streams")
    for category, streams in (("car_data", cars), ("pos_data", positions)):
        for driver, frame in sorted(streams.items()):
            if not re.fullmatch(r"[0-9]+", driver):
                raise ValueError("Invalid FastF1 driver identifier")
            frames[f"{category}/{driver}"] = pd.DataFrame(frame)
    empty = [name for name, frame in frames.items() if frame.empty]
    if empty:
        raise ValueError(f"FastF1 required source streams are empty: {empty}")
    tables = {}
    for name, frame in sorted(frames.items()):
        path = root / "tables" / f"{name}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        with path.open("xb") as handle:
            pq.write_table(table, handle, compression="zstd", version="2.6")
        tables[name] = {"rows": len(frame), "sha256": file_sha256(path),
                        "columns": list(frame.columns),
                        "null_counts": {column: table[column].null_count for column in table.column_names}}
    event = session.event
    if int(event["RoundNumber"]) != query.round_number or int(event.year) != query.year:
        raise ValueError("FastF1 resolved a different season/round")
    identity = {"year": query.year, "round_number": query.round_number,
                "event_name": str(event["EventName"]), "session_name": session.name,
                "api_path": session.api_path, "drivers": sorted(cars),
                "t0_date": session.t0_date.isoformat(),
                "session_start_time_s": session.session_start_time.total_seconds()}
    validate_identity(query, identity)
    snapshot = {"schema_version": SNAPSHOT_VERSION, "identity": identity,
                "environment": environment_versions(), "complete": True,
                "network_attempts": network_attempts, "tables": tables,
                "truth": "FASTF1_PARSED_SOURCE; contains upstream reconstructed and generated values"}
    write_manifest(root / "snapshot.json", snapshot)
    return snapshot


def install_network_guard() -> list[str]:
    """Permanently deny Python DNS and socket connection/send attempts in this worker."""
    attempts = []

    def audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "socket.sendmsg"}:
            attempts.append(event)
            raise RuntimeError("Network access forbidden during FastF1 offline replay")

    sys.addaudithook(audit)
    return attempts


def run_worker(root: Path, query: FastF1Query, *, offline: bool) -> None:
    attempts = install_network_guard() if offline else []
    import fastf1

    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(offline)
    session = fastf1.get_session(query.year, query.round_number, query.session, backend="fastf1")
    session.load(laps=True, telemetry=True, weather=True, messages=True)
    # Upstream soft exceptions can swallow failures, so inspect completeness and
    # network attempts explicitly instead of relying only on Session.load returning.
    if attempts:
        raise RuntimeError(f"Offline replay attempted {len(attempts)} network operations")
    snapshot_session(session, root, query, network_attempts=len(attempts))


if __name__ == "__main__":
    root = Path(sys.argv[1])
    query = FastF1Query(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    run_worker(root, query, offline="--offline" in sys.argv[5:])
    print(json.dumps({"snapshot": str(root / "snapshot.json"), "status": "completed"}))
