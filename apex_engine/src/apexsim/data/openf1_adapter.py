"""Migration boundary for the retired public dense CSV converter (P1-07)."""
from __future__ import annotations

from pathlib import Path
from typing import NoReturn

from apexsim.contracts import PUBLIC_CSV_MIGRATION_MESSAGE


def ingest_openf1_session(
    session_key: int,
    driver_number: int,
    output_path: str | Path,
    sample_hz: int = 4,
    manifest_path: str | Path | None = None,
) -> NoReturn:
    """Reject dense conversion before downloads or filesystem changes."""
    raise ValueError(PUBLIC_CSV_MIGRATION_MESSAGE)
