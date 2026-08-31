from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from games.calculatorx.storage import CalculatorStorage, StorageError
from games.calculatorx import build_game


def test_storage_records_only_session_summary(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")

    session = storage.record_session(
        mode="classic",
        duration_seconds=120,
        score=42,
        ended_reason="timeout",
        submission_status="pending",
    )

    assert storage.list_sessions() == [session]
    assert not hasattr(session, "samples")
    assert session.mode == "classic"
    assert session.duration_seconds == 120
    assert session.score == 42
    assert session.ended_reason == "timeout"
    assert session.submission_status == "pending"
    assert session.nickname is None


def test_storage_lists_latest_session_first_when_timestamps_match(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")

    first = storage.record_session("classic", 120, 10, "timeout", "pending")
    second = storage.record_session("constance", 120, 11, "timeout", "pending")

    assert storage.list_sessions() == [second, first]


def test_storage_marks_session_submitted_with_nickname(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    session = storage.record_session("classic", 120, 42, "timeout", "pending")
    profile = storage.create_profile("Mila")

    submitted = storage.mark_submitted(session.id, profile.nickname)

    assert submitted == storage.list_sessions()[0]
    assert submitted.submission_status == "submitted"
    assert submitted.nickname == "Mila"


def test_profiles_reuse_normalized_nickname_and_keep_first_display_name(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")

    ada = storage.create_profile(" Ada ")
    same_profile = storage.create_profile("ADA")
    same_nfkc_profile = storage.create_profile("ＡＤＡ")

    assert ada.nickname == "Ada"
    assert same_profile.id == ada.id
    assert same_nfkc_profile.id == ada.id
    assert same_profile.nickname == "Ada"
    assert same_profile.normalized_nickname == "ada"


def test_reusing_a_profile_updates_its_last_use_and_recency(tmp_path, monkeypatch):
    timestamps = iter(
        [
            "2026-08-31T10:00:00.000+00:00",
            "2026-08-31T10:01:00.000+00:00",
            "2026-08-31T10:02:00.000+00:00",
        ]
    )
    monkeypatch.setattr(
        CalculatorStorage, "_timestamp", staticmethod(lambda: next(timestamps))
    )
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")

    first_ada = storage.create_profile("Ada")
    bob = storage.create_profile("Bob")
    reused_ada = storage.create_profile("ADA")

    assert reused_ada.id == first_ada.id
    assert reused_ada.last_used_at == "2026-08-31T10:02:00.000+00:00"
    assert [profile.id for profile in storage.list_profiles()] == [reused_ada.id, bob.id]


def test_profiles_are_listed_by_last_use_with_deterministic_tie_breaker(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    ada = storage.create_profile("Ada")
    bob = storage.create_profile("Bob")
    equal_time = datetime(2026, 8, 31, tzinfo=timezone.utc).isoformat()

    with sqlite3.connect(storage.database_path) as connection:
        connection.execute(
            "UPDATE calculator_profiles SET last_used_at = ?", (equal_time,)
        )

    profiles = storage.list_profiles()

    assert [profile.id for profile in profiles] == sorted(
        [ada.id, bob.id], reverse=True
    )


@pytest.mark.parametrize(
    "nickname",
    [None, 42, "", "   ", "a" * 25, "Ada\x00", "Ada\n"],
)
def test_create_profile_rejects_invalid_nicknames(tmp_path, nickname):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")

    with pytest.raises(StorageError, match="Pseudo invalide"):
        storage.create_profile(nickname)


def test_get_profile_returns_created_profile_and_rejects_unknown_identifier(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    profile = storage.create_profile("Mila")

    assert storage.get_profile(profile.id) == profile
    with pytest.raises(StorageError, match="Profil introuvable"):
        storage.get_profile("missing-profile")


def test_get_session_returns_summary_and_rejects_unknown_identifier(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    session = storage.record_session("classic", 120, 42, "timeout", "pending")

    assert storage.get_session(session.id) == session
    with pytest.raises(StorageError, match="Séance introuvable"):
        storage.get_session(999)


@pytest.mark.parametrize(
    ("mode", "duration_seconds"),
    [("classic", 120), ("constance", 120)],
)
def test_mark_submitted_accepts_pending_ranked_sessions(tmp_path, mode, duration_seconds):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    profile = storage.create_profile("Mila")
    session = storage.record_session(
        mode, duration_seconds, 42, "timeout", "pending"
    )

    submitted = storage.mark_submitted(session.id, "MILA")

    assert submitted.submission_status == "submitted"
    assert submitted.nickname == profile.nickname


@pytest.mark.parametrize(
    ("mode", "duration_seconds", "ended_reason", "submission_status"),
    [
        ("custom", 45, "timeout", "pending"),
        ("classic", 120, "stopped", "pending"),
        ("classic", 120, "timeout", "not_applicable"),
        ("classic", 120, "timeout", "submitted"),
    ],
)
def test_mark_submitted_rejects_ineligible_or_already_submitted_sessions(
    tmp_path, mode, duration_seconds, ended_reason, submission_status
):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    profile = storage.create_profile("Mila")
    session = storage.record_session(
        mode, duration_seconds, 42, ended_reason, submission_status
    )

    with pytest.raises(StorageError, match="ne peut pas être envoyé"):
        storage.mark_submitted(session.id, profile.nickname)

    assert storage.get_session(session.id).submission_status == submission_status


def test_mark_submitted_rejects_unknown_session_and_profile(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    pending = storage.record_session("classic", 120, 42, "timeout", "pending")

    with pytest.raises(StorageError, match="Séance introuvable"):
        storage.mark_submitted(999, "Mila")
    with pytest.raises(StorageError, match="Profil introuvable"):
        storage.mark_submitted(pending.id, "Mila")


def test_profiles_migration_preserves_preexisting_session_history(tmp_path):
    database_path = tmp_path / "calculatorx.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE calculator_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              played_at TEXT NOT NULL,
              mode TEXT NOT NULL,
              duration_seconds INTEGER NOT NULL,
              score INTEGER NOT NULL,
              ended_reason TEXT NOT NULL,
              submission_status TEXT NOT NULL,
              nickname TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO calculator_sessions (
              played_at, mode, duration_seconds, score, ended_reason,
              submission_status, nickname
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-08-31T10:00:00+00:00", "classic", 120, 42, "timeout", "pending", None),
        )

    storage = CalculatorStorage(database_path)

    assert storage.list_sessions()[0].score == 42
    assert storage.create_profile("Mila").nickname == "Mila"


def test_clear_history_keeps_database_usable(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")

    storage.record_session("custom", 45, 7, "stopped", "not_applicable")
    storage.clear_sessions()

    assert storage.list_sessions() == []
    recorded = storage.record_session("constance", 120, 8, "exhausted", "pending")
    assert storage.list_sessions() == [recorded]


def test_build_game_injects_storage_using_the_catalog_data_directory(tmp_path):
    build_game(tmp_path)

    assert not (tmp_path / "calculatorx.sqlite3").exists()


def test_storage_constructor_defers_all_database_io_until_a_public_operation(tmp_path):
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("This file deliberately blocks SQLite's parent directory.")

    storage = CalculatorStorage(blocked_parent / "calculatorx.sqlite3")

    with pytest.raises(StorageError):
        storage.list_sessions()


class TrackedConnection:
    def __init__(self, *, failing: bool = False):
        self.closed = False
        self.failing = failing

    def __enter__(self):
        return self

    def __exit__(self, *_details):
        return False

    def execute(self, _query):
        if self.failing:
            raise sqlite3.DatabaseError("test database failure")

    def close(self):
        self.closed = True


@pytest.mark.parametrize("failing", [False, True])
def test_storage_closes_each_connection_after_success_or_database_failure(tmp_path, monkeypatch, failing):
    connection = TrackedConnection(failing=failing)
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    monkeypatch.setattr(storage, "_connect", lambda: connection)

    if failing:
        with pytest.raises(StorageError):
            storage.clear_sessions()
    else:
        storage.clear_sessions()

    assert connection.closed is True
