from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class RunRegistry:
    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    model_kind TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    run_dir TEXT NOT NULL,
                    metrics_json TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def start(self, run_id: str, model_kind: str, run_dir: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, "running", model_kind, now, None, run_dir, None),
            )

    def finish(self, run_id: str, status: str, metrics: dict | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status=?, finished_at=?, metrics_json=? WHERE run_id=?",
                (status, now, json.dumps(metrics) if metrics else None, run_id),
            )

    def list_runs(self) -> list[dict]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM runs ORDER BY started_at DESC").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["metrics"] = json.loads(item.pop("metrics_json")) if item.get("metrics_json") else None
            result.append(item)
        return result
