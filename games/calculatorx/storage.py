from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: int
    played_at: str
    mode: str
    duration_seconds: int
    score: int
    ended_reason: str
    submission_status: str
    nickname: str | None


class CalculatorStorage:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS calculator_sessions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  played_at TEXT NOT NULL,
                  mode TEXT NOT NULL CHECK (mode IN ('classic','custom','constance')),
                  duration_seconds INTEGER NOT NULL,
                  score INTEGER NOT NULL,
                  ended_reason TEXT NOT NULL CHECK (ended_reason IN ('timeout','stopped','exhausted')),
                  submission_status TEXT NOT NULL CHECK (submission_status IN ('not_applicable','pending','submitted')),
                  nickname TEXT
                )
                """
            )

    def record_session(
        self,
        mode: str,
        duration_seconds: int,
        score: int,
        ended_reason: str,
        submission_status: str,
    ) -> SessionRecord:
        played_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO calculator_sessions (
                    played_at, mode, duration_seconds, score, ended_reason,
                    submission_status, nickname
                ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    played_at,
                    mode,
                    duration_seconds,
                    score,
                    ended_reason,
                    submission_status,
                ),
            )
            row = connection.execute(
                "SELECT * FROM calculator_sessions WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._record_from_row(row)

    def list_sessions(self) -> list[SessionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM calculator_sessions ORDER BY played_at DESC, id DESC"
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def mark_submitted(self, session_id: int, nickname: str) -> SessionRecord:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE calculator_sessions
                SET submission_status = 'submitted', nickname = ?
                WHERE id = ?
                """,
                (nickname, session_id),
            )
            row = connection.execute(
                "SELECT * FROM calculator_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise KeyError(session_id)
        return self._record_from_row(row)

    def clear_sessions(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM calculator_sessions")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            played_at=row["played_at"],
            mode=row["mode"],
            duration_seconds=row["duration_seconds"],
            score=row["score"],
            ended_reason=row["ended_reason"],
            submission_status=row["submission_status"],
            nickname=row["nickname"],
        )
