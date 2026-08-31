from __future__ import annotations

import sqlite3
import unicodedata
from uuid import uuid4
from contextlib import closing
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


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    nickname: str
    normalized_nickname: str
    created_at: str
    last_used_at: str


class StorageError(RuntimeError):
    """A local SQLite operation could not be completed."""


class CalculatorStorage:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def record_session(
        self,
        mode: str,
        duration_seconds: int,
        score: int,
        ended_reason: str,
        submission_status: str,
    ) -> SessionRecord:
        played_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        def record(connection: sqlite3.Connection) -> SessionRecord:
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

        return self._run(record)

    def list_sessions(self) -> list[SessionRecord]:
        def list_records(connection: sqlite3.Connection) -> list[SessionRecord]:
            rows = connection.execute(
                "SELECT * FROM calculator_sessions ORDER BY played_at DESC, id DESC"
            ).fetchall()
            return [self._record_from_row(row) for row in rows]

        return self._run(list_records)

    def get_session(self, session_id: int) -> SessionRecord:
        def get(connection: sqlite3.Connection) -> SessionRecord:
            row = connection.execute(
                "SELECT * FROM calculator_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise StorageError("Séance introuvable.")
            return self._record_from_row(row)

        return self._run(get)

    def create_profile(self, nickname: str) -> Profile:
        display_name, normalized_name = self._normalize_nickname(nickname)
        used_at = self._timestamp()

        def create(connection: sqlite3.Connection) -> Profile:
            row = connection.execute(
                "SELECT * FROM calculator_profiles WHERE normalized_nickname = ?",
                (normalized_name,),
            ).fetchone()
            if row is None:
                profile_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO calculator_profiles (
                      id, nickname, normalized_nickname, created_at, last_used_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (profile_id, display_name, normalized_name, used_at, used_at),
                )
                row = connection.execute(
                    "SELECT * FROM calculator_profiles WHERE id = ?", (profile_id,)
                ).fetchone()
            else:
                connection.execute(
                    "UPDATE calculator_profiles SET last_used_at = ? WHERE id = ?",
                    (used_at, row["id"]),
                )
                row = connection.execute(
                    "SELECT * FROM calculator_profiles WHERE id = ?", (row["id"],)
                ).fetchone()
            return self._profile_from_row(row)

        return self._run(create)

    def list_profiles(self) -> list[Profile]:
        def list_records(connection: sqlite3.Connection) -> list[Profile]:
            rows = connection.execute(
                """
                SELECT * FROM calculator_profiles
                ORDER BY last_used_at DESC, id DESC
                """
            ).fetchall()
            return [self._profile_from_row(row) for row in rows]

        return self._run(list_records)

    def get_profile(self, profile_id: str) -> Profile:
        def get(connection: sqlite3.Connection) -> Profile:
            row = connection.execute(
                "SELECT * FROM calculator_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
            if row is None:
                raise StorageError("Profil introuvable.")
            return self._profile_from_row(row)

        return self._run(get)

    def mark_submitted(self, session_id: int, nickname: str) -> SessionRecord:
        _display_name, normalized_name = self._normalize_nickname(nickname)
        used_at = self._timestamp()

        def mark(connection: sqlite3.Connection) -> SessionRecord:
            session_row = connection.execute(
                "SELECT * FROM calculator_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if session_row is None:
                raise StorageError("Séance introuvable.")
            session = self._record_from_row(session_row)
            if not self._is_submission_eligible(session):
                raise StorageError("Cette séance ne peut pas être envoyée.")

            profile_row = connection.execute(
                "SELECT * FROM calculator_profiles WHERE normalized_nickname = ?",
                (normalized_name,),
            ).fetchone()
            if profile_row is None:
                raise StorageError("Profil introuvable.")

            connection.execute(
                """
                UPDATE calculator_sessions
                SET submission_status = 'submitted', nickname = ?
                WHERE id = ?
                """,
                (profile_row["nickname"], session_id),
            )
            connection.execute(
                "UPDATE calculator_profiles SET last_used_at = ? WHERE id = ?",
                (used_at, profile_row["id"]),
            )
            row = connection.execute(
                "SELECT * FROM calculator_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return self._record_from_row(row)

        return self._run(mark)

    def clear_sessions(self) -> None:
        def clear(connection: sqlite3.Connection) -> None:
            connection.execute("DELETE FROM calculator_sessions")
        self._run(clear)

    def _run(self, operation):
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with closing(self._connect()) as connection, connection:
                self._initialize(connection)
                return operation(connection)
        except (OSError, sqlite3.Error) as error:
            raise StorageError("Historique local indisponible.") from error

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS calculator_profiles (
              id TEXT PRIMARY KEY,
              nickname TEXT NOT NULL,
              normalized_nickname TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL,
              last_used_at TEXT NOT NULL
            )
            """
        )

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

    @staticmethod
    def _profile_from_row(row: sqlite3.Row) -> Profile:
        return Profile(
            id=row["id"],
            nickname=row["nickname"],
            normalized_nickname=row["normalized_nickname"],
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
        )

    @staticmethod
    def _normalize_nickname(nickname: str) -> tuple[str, str]:
        if not isinstance(nickname, str):
            raise StorageError("Pseudo invalide.")
        normalized_display = unicodedata.normalize("NFKC", nickname)
        if any(unicodedata.category(character) == "Cc" for character in normalized_display):
            raise StorageError("Pseudo invalide.")
        display_name = normalized_display.strip()
        if not 1 <= len(display_name) <= 24:
            raise StorageError("Pseudo invalide.")
        return display_name, display_name.casefold()

    @staticmethod
    def _is_submission_eligible(session: SessionRecord) -> bool:
        return (
            session.submission_status == "pending"
            and session.mode in {"classic", "constance"}
            and session.duration_seconds == 120
            and session.ended_reason == "timeout"
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
