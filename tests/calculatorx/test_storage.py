from __future__ import annotations

import sqlite3

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

    submitted = storage.mark_submitted(session.id, "Mila")

    assert submitted == storage.list_sessions()[0]
    assert submitted.submission_status == "submitted"
    assert submitted.nickname == "Mila"


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
