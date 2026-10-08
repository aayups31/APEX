"""Migration boundary for the retired public dense CSV converter (P1-07)."""
from __future__ import annotations

from pathlib import Path
from typing import NoReturn

from apexsim.contracts import PUBLIC_CSV_MIGRATION_MESSAGE


def ingest_fastf1_session(
    year: int,
    event: str,
    session_code: str,
    driver: str,
    output_path: str | Path,
    sample_hz: int = 5,
    manifest_path: str | Path | None = None,
) -> NoReturn:
    """Reject dense conversion before downloads or filesystem changes.

    Retain the former signature so callers receive actionable migration instructions.
    """
    raise ValueError(PUBLIC_CSV_MIGRATION_MESSAGE)
