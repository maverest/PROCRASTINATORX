import copy
from pathlib import Path
import random

import pytest

from games.mapix.countries import CountryCatalog
from games.mapix.engine import (
    Game,
    GameResult,
    GameRuleError,
    apply_answer,
    new_game,
    result_for,
)


ROOT = Path(__file__).parents[2]
CATALOG_PATH = ROOT / "static/mapix/countries.json"


@pytest.fixture(scope="module")
def catalog():
    return CountryCatalog.from_json(CATALOG_PATH)


def game_with_order(catalog, mode, order, now=0.0):
    assert set(order) <= set(catalog.by_id)
    return Game(
        mode=mode,
        region="world",
        order=tuple(order),
        current_index=0,
        found=set(),
        flag_done=False,
        territory_done=False,
        errors=0,
        perfect=0,
        started_at=now,
        finished_at=None,
    )


def completed_game(*, mode, countries, errors, perfect, elapsed):
    order = tuple(f"C{index}" for index in range(countries))
    return Game(
        mode=mode,
        region="world",
        order=order,
        current_index=countries,
        found=set(order),
        flag_done=False,
        territory_done=False,
        errors=errors,
        perfect=perfect,
        started_at=10.0,
        finished_at=10.0 + elapsed,
    )


def test_new_game_shuffles_every_country_once(catalog):
    countries = catalog.for_region("south-america")
    game = new_game(catalog, "territory", "south-america", random.Random(7), 10.0)

    assert len(game.order) == 12
    assert len(set(game.order)) == 12
    assert set(game.order) == {country.id for country in countries}
    assert game.order != tuple(country.id for country in countries)


@pytest.mark.parametrize(
    "actions", [("territory", "flag"), ("flag", "territory")]
)
def test_flag_territory_accepts_both_orders(catalog, actions):
    game = game_with_order(catalog, "flag-territory", ["CH", "FR"], now=10.0)

    first = apply_answer(game, catalog, actions[0], "CH", now=11.0)
    assert first.correct and not first.advanced
    second = apply_answer(game, catalog, actions[1], "CH", now=12.0)

    assert second.correct and second.advanced
    assert game.current_country_id == "FR"


def test_wrong_action_increments_error_and_removes_perfect_status(catalog):
    game = game_with_order(catalog, "territory", ["CH"], now=10.0)

    outcome = apply_answer(game, catalog, "territory", "FR", now=11.0)

    assert not outcome.correct
    assert game.errors == 1
    assert game.current_is_perfect is False


def test_all_mode_normalizes_alias_and_ignores_duplicate(catalog):
    game = game_with_order(catalog, "all", ["US", "CH"], now=10.0)

    assert apply_answer(game, catalog, "name", "Etats Unis", 11.0).correct
    before = copy.deepcopy(game)
    duplicate = apply_answer(game, catalog, "name", "USA", 12.0)

    assert duplicate.duplicate
    assert game == before


def test_result_uses_two_expected_actions_for_combined_mode():
    game = completed_game(
        mode="flag-territory", countries=3, errors=2, perfect=2, elapsed=25.0
    )

    assert result_for(game) == GameResult(
        elapsed_seconds=25.0,
        perfect_countries=2,
        errors=2,
        accuracy_percent=75.0,
    )


@pytest.mark.parametrize("mode", ["", "flags", "unknown"])
def test_new_game_rejects_invalid_mode(catalog, mode):
    with pytest.raises(GameRuleError, match="mode"):
        new_game(catalog, mode, "world", random.Random(1), 0.0)


def test_all_mode_counts_unknown_and_out_of_region_names_as_errors(catalog):
    game = game_with_order(catalog, "all", ["CH", "FR"], now=0.0)

    assert not apply_answer(game, catalog, "name", "Atlantide", 1.0).correct
    assert not apply_answer(game, catalog, "name", "Japon", 2.0).correct

    assert game.errors == 2


@pytest.mark.parametrize(
    ("mode", "action"),
    [("territory", "territory"), ("flag-only", "flag")],
)
def test_single_action_modes_finish_after_last_country(catalog, mode, action):
    game = game_with_order(catalog, mode, ["CH"], now=5.0)

    outcome = apply_answer(game, catalog, action, "CH", now=9.0)

    assert outcome.finished
    assert result_for(game).accuracy_percent == 100.0


def test_action_not_allowed_by_mode_does_not_mutate(catalog):
    game = game_with_order(catalog, "territory", ["CH"], now=0.0)
    before = copy.deepcopy(game)

    with pytest.raises(GameRuleError, match="action"):
        apply_answer(game, catalog, "flag", "CH", now=1.0)

    assert game == before


def test_new_game_translates_unknown_region_to_rule_error(catalog):
    with pytest.raises(GameRuleError, match="region") as error:
        new_game(catalog, "territory", "atlantis", random.Random(1), 0.0)

    assert error.value.field == "region"


def test_unknown_country_id_does_not_mutate_sequential_game(catalog):
    game = game_with_order(catalog, "territory", ["CH"], now=0.0)
    before = copy.deepcopy(game)

    with pytest.raises(GameRuleError, match="country") as error:
        apply_answer(game, catalog, "territory", "XX", now=1.0)

    assert error.value.field == "value"
    assert game == before


def test_finished_game_rejects_answers_without_mutating(catalog):
    game = game_with_order(catalog, "flag-only", ["CH"], now=0.0)
    apply_answer(game, catalog, "flag", "CH", now=1.0)
    before = copy.deepcopy(game)

    with pytest.raises(GameRuleError, match="finished"):
        apply_answer(game, catalog, "flag", "CH", now=2.0)

    assert game == before
