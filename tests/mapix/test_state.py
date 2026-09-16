from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import random
import threading

import pytest

from games.mapix.countries import CountryCatalog
from games.mapix.engine import GameRuleError
from games.mapix.state import MapixState, NoActiveGame, StaleGame, StaleQuestion


@pytest.fixture(scope="module")
def catalog():
    return CountryCatalog.from_json(
        Path(__file__).parents[2] / "static/mapix/countries.json"
    )


@pytest.fixture
def clock():
    return [10.0]


@pytest.fixture
def state(catalog, clock):
    return MapixState(catalog, clock=lambda: clock[0], rng=random.Random(7))


@pytest.fixture
def target():
    """Seul accès des tests à la cible privée, sous le verrou de l'état."""
    def read(state):
        with state._lock:
            return state._game.current_country_id
    return read


@pytest.mark.parametrize("operation", ["snapshot", "answer", "solution", "quit"])
def test_empty_state_rejects_operations(state, operation):
    with pytest.raises(NoActiveGame):
        if operation == "answer":
            state.answer("missing", 0, "territory", "CH")
        elif operation == "solution":
            state.solution("missing", 0)
        elif operation == "quit":
            state.quit("missing")
        else:
            state.snapshot()


def test_start_replaces_game_and_invalidates_old_token(state, target):
    first = state.start("territory", "europe")
    old_target = target(state)
    second = state.start("flag-only", "asia")
    assert first["token"] != second["token"]
    with pytest.raises(StaleGame):
        state.answer(first["token"], 0, "territory", old_target)
    assert state.snapshot() == second


@pytest.mark.parametrize("mode, region", [("bad", "europe"), ("territory", "bad")])
def test_invalid_start_preserves_active_game_and_token(state, mode, region):
    before = state.start("territory", "europe")
    with pytest.raises(GameRuleError):
        state.start(mode, region)
    assert state.snapshot() == before


def test_stale_question_cannot_mutate_next_question(state, target):
    session = state.start("territory", "south-america")
    country_id = target(state)
    state.answer(session["token"], 0, "territory", country_id)
    before = state.snapshot()
    with pytest.raises(StaleQuestion):
        state.answer(session["token"], 0, "territory", country_id)
    assert state.snapshot() == before


def test_future_question_cannot_mutate_state(state):
    before = state.start("territory", "europe")
    with pytest.raises(StaleQuestion):
        state.answer(before["token"], 1, "territory", "CH")
    assert state.snapshot() == before


def test_quit_requires_current_token_and_clears_state(state):
    old = state.start("territory", "oceania")
    current = state.start("territory", "oceania")
    with pytest.raises(StaleGame):
        state.quit(old["token"])
    assert state.snapshot() == current
    assert state.quit(current["token"]) is True
    with pytest.raises(NoActiveGame):
        state.snapshot()


@pytest.mark.parametrize("mode", ["territory", "flag-territory", "flag-only", "all"])
def test_public_payload_does_not_expose_target_or_question_order(state, catalog, target, mode):
    session = state.start(mode, "south-america")
    assert session["mode"] == mode
    assert session["region"] == "south-america"
    assert session["total"] == 12
    assert session["question_index"] == 0
    assert session["errors"] == 0
    assert session["found"] == []
    assert session["result"] is None
    assert session["finished"] is False
    assert session["flag_done"] is False
    assert session["territory_done"] is False
    assert session["current_errors"] == 0
    assert session["revealed_actions"] == []
    assert session["imperfect"] == []
    # Les choix suivent un ordre public stable, jamais l'ordre privé du tirage.
    assert session["remaining_flags"] == sorted(
        country.id for country in catalog.for_region("south-america")
    )
    assert session["current"] == (
        None if mode == "all" else {"name": catalog.by_id[target(state)].name}
    )
    assert set(session) == {
        "mode", "region", "token", "total", "question_index", "errors", "found",
        "remaining_flags", "current", "flag_done", "territory_done", "result",
        "finished", "elapsed_seconds", "current_errors", "revealed_actions",
        "imperfect",
    }


def test_combined_mode_retains_flag_until_both_actions_are_correct(state, target):
    session = state.start("flag-territory", "europe")
    country_id = target(state)
    first = state.answer(session["token"], 0, "flag", country_id)
    assert first["flag_done"] is True
    assert first["territory_done"] is False
    assert first["question_index"] == 0
    assert country_id in first["remaining_flags"]
    assert first["found"] == []
    duplicate = state.answer(session["token"], 0, "flag", country_id)
    assert duplicate["outcome"]["duplicate"] is True
    second = state.answer(session["token"], 0, "territory", country_id)
    assert country_id not in second["remaining_flags"]
    assert second["found"] == [country_id]
    assert second["question_index"] == 1
    assert second["flag_done"] is False
    assert second["territory_done"] is False


def test_wrong_answer_feedback_identifies_only_selected_country(state, target):
    session = state.start("territory", "europe")
    selected = "FR" if target(state) != "FR" else "CH"
    response = state.answer(session["token"], 0, "territory", selected)
    assert response["errors"] == 1
    assert response["found"] == []
    assert response["outcome"] == {
        "correct": False, "duplicate": False, "advanced": False,
        "finished": False, "selected_country_id": selected,
    }
    assert response["current"] == session["current"]
    assert "outcome" not in state.snapshot()


def test_payload_collections_cannot_mutate_server_state(state):
    before = state.start("territory", "europe")
    response = state.snapshot()
    response["found"].append("CH")
    response["remaining_flags"].clear()
    response["current"]["name"] = "Atlantide"
    assert state.snapshot() == before


@pytest.mark.parametrize("mode, action", [("flag-only", "flag"), ("all", "name")])
def test_completion_returns_engine_result_and_freezes_elapsed_time(state, clock, catalog, target, mode, action):
    session = state.start(mode, "south-america")
    clock[0] = 12.5
    assert state.snapshot()["elapsed_seconds"] == 2.5
    while not session["finished"]:
        country_id = target(state)
        value = catalog.by_id[country_id].name if action == "name" else country_id
        clock[0] = 35.0
        session = state.answer(session["token"], session["question_index"], action, value)
    assert session["result"] == {
        "elapsed_seconds": 25.0, "perfect_countries": None if mode == "all" else 12,
        "errors": 0, "accuracy_percent": 100.0,
    }
    assert session["current"] is None
    assert session["remaining_flags"] == []
    assert len(session["found"]) == 12
    assert session["outcome"]["finished"] is True
    clock[0] = 100.0
    assert state.snapshot()["elapsed_seconds"] == 25.0
    assert state.snapshot()["result"] == session["result"]


def test_two_simultaneous_correct_answers_advance_exactly_once(state, target):
    session = state.start("territory", "europe")
    country_id = target(state)
    barrier = threading.Barrier(2)

    def submit():
        barrier.wait(timeout=5)
        try:
            return state.answer(session["token"], 0, "territory", country_id)
        except StaleQuestion as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(submit) for _ in range(2)]
        responses = [future.result(timeout=5) for future in futures]

    accepted = [response for response in responses if isinstance(response, dict)]
    assert len(accepted) == 1
    assert sum(isinstance(response, StaleQuestion) for response in responses) == 1
    assert accepted[0]["outcome"]["advanced"] is True
    after = state.snapshot()
    assert after["found"] == [country_id]
    assert after["question_index"] == 1
    assert after["errors"] == 0


def test_solution_reveals_current_target_without_advancing(state, target):
    session = state.start("flag-territory", "europe")
    country_id = target(state)

    response = state.solution(session["token"], 0)

    assert response["errors"] == 1
    assert response["current_errors"] == 1
    assert response["revealed_actions"] == ["flag", "territory"]
    assert response["imperfect"] == [country_id]
    assert response["question_index"] == 0
    assert response["found"] == []
    assert response["flag_done"] is False
    assert response["territory_done"] is False


def test_combined_solution_reveals_only_action_still_missing(state, target):
    session = state.start("flag-territory", "europe")
    country_id = target(state)
    after_flag = state.answer(session["token"], 0, "flag", country_id)

    response = state.solution(after_flag["token"], 0)

    assert response["revealed_actions"] == ["territory"]
    assert response["flag_done"] is True


def test_stale_solution_cannot_mutate_next_question(state, target):
    session = state.start("territory", "europe")
    state.answer(session["token"], 0, "territory", target(state))
    before = state.snapshot()

    with pytest.raises(StaleQuestion):
        state.solution(session["token"], 0)

    assert state.snapshot() == before


def test_solution_rejects_all_mode_without_mutation(state):
    before = state.start("all", "europe")

    with pytest.raises(GameRuleError, match="solution"):
        state.solution(before["token"], 0)

    assert state.snapshot() == before
