"""Règles pures des parties Mapix."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

from .countries import CatalogError, CountryCatalog, normalize_name


VALID_MODES = ("territory", "flag-territory", "flag-only", "all")
VALID_ACTIONS = {
    "territory": frozenset({"territory"}),
    "flag-territory": frozenset({"flag", "territory"}),
    "flag-only": frozenset({"flag"}),
    "all": frozenset({"name"}),
}
ACTION_ORDER = ("flag", "territory", "name")


class GameRuleError(ValueError):
    """Une action ne respecte pas les règles d'une partie."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


@dataclass(frozen=True, slots=True)
class AnswerOutcome:
    correct: bool
    duplicate: bool
    advanced: bool
    finished: bool
    selected_country_id: str | None


@dataclass(frozen=True, slots=True)
class GameResult:
    elapsed_seconds: float
    perfect_countries: int | None
    errors: int
    accuracy_percent: float


@dataclass(slots=True)
class Game:
    mode: str
    region: str
    order: tuple[str, ...]
    current_index: int
    found: set[str]
    flag_done: bool
    territory_done: bool
    errors: int
    perfect: int
    started_at: float
    finished_at: float | None
    current_is_perfect: bool = field(default=True, init=False)
    current_errors: int = field(default=0, init=False)
    current_revealed: bool = field(default=False, init=False)
    imperfect: set[str] = field(default_factory=set, init=False)

    @property
    def current_country_id(self) -> str | None:
        """Retourne une cible restante pour l'usage interne du serveur."""
        if self.mode == "all":
            return next(
                (country_id for country_id in self.order if country_id not in self.found),
                None,
            )
        if self.current_index >= len(self.order):
            return None
        return self.order[self.current_index]


def new_game(
    catalog: CountryCatalog,
    mode: str,
    region: str,
    rng: random.Random,
    now: float,
) -> Game:
    """Crée une partie dont chaque pays de la région apparaît une fois."""
    if mode not in VALID_MODES:
        raise GameRuleError("invalid mode", "mode")
    try:
        countries = catalog.for_region(region)
    except CatalogError as error:
        raise GameRuleError("invalid region", "region") from error
    order = [country.id for country in countries]
    rng.shuffle(order)
    return Game(
        mode=mode,
        region=region,
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


def apply_answer(
    game: Game,
    catalog: CountryCatalog,
    action: str,
    value: str,
    now: float,
) -> AnswerOutcome:
    """Applique une réponse et retourne ses effets observables."""
    allowed_actions = VALID_ACTIONS.get(game.mode)
    if allowed_actions is None:
        raise GameRuleError("invalid mode", "mode")
    if action not in allowed_actions:
        raise GameRuleError("invalid action", "action")
    if game.finished_at is not None:
        raise GameRuleError("game is finished")
    if game.mode == "all":
        return _apply_name(game, catalog, value, now)
    if value not in catalog.by_id:
        raise GameRuleError("invalid country", "value")
    return _apply_sequential(game, action, value, now)


def apply_solution(game: Game) -> None:
    """Révèle la réponse courante sans la valider."""
    if game.mode == "all":
        raise GameRuleError("solution unavailable")
    if game.finished_at is not None:
        raise GameRuleError("game is finished")
    if not solution_available(game):
        return
    _record_current_error(game)
    game.current_revealed = True


def solution_available(game: Game) -> bool:
    """Indique si Solution peut encore révéler une action manquante."""
    if game.mode == "all" or game.finished_at is not None:
        return False
    missing = {
        action
        for action in VALID_ACTIONS[game.mode]
        if not getattr(game, f"{action}_done")
    }
    return bool(missing - set(revealed_actions(game)))


def revealed_actions(game: Game) -> tuple[str, ...]:
    """Retourne les actions encore attendues dont la solution est visible."""
    if (
        game.mode == "all"
        or game.finished_at is not None
        or not (game.current_revealed or game.current_errors >= 3)
    ):
        return ()
    required = VALID_ACTIONS[game.mode]
    return tuple(
        action
        for action in ACTION_ORDER
        if action in required and not getattr(game, f"{action}_done")
    )


def _apply_name(
    game: Game, catalog: CountryCatalog, value: str, now: float
) -> AnswerOutcome:
    country = catalog.by_normalized_name.get(normalize_name(value))
    selected_country_id = country.id if country is not None else None
    if country is None or country.id not in game.order:
        game.errors += 1
        return _outcome(False, selected_country_id=selected_country_id)
    if country.id in game.found:
        return _outcome(True, duplicate=True, selected_country_id=country.id)

    game.found.add(country.id)
    game.current_index += 1
    finished = game.current_index == len(game.order)
    if finished:
        game.finished_at = now
    return _outcome(
        True,
        advanced=True,
        finished=finished,
        selected_country_id=country.id,
    )


def _apply_sequential(
    game: Game, action: str, value: str, now: float
) -> AnswerOutcome:
    target = game.current_country_id
    if value != target:
        _record_current_error(game)
        return _outcome(False, selected_country_id=value)

    done_attribute = f"{action}_done"
    if getattr(game, done_attribute):
        return _outcome(True, duplicate=True, selected_country_id=value)
    setattr(game, done_attribute, True)

    if not all(getattr(game, f"{required}_done") for required in VALID_ACTIONS[game.mode]):
        return _outcome(True, selected_country_id=value)

    game.found.add(target)
    if game.current_is_perfect:
        game.perfect += 1
    game.current_index += 1
    game.flag_done = False
    game.territory_done = False
    game.current_is_perfect = True
    game.current_errors = 0
    game.current_revealed = False
    finished = game.current_index == len(game.order)
    if finished:
        game.finished_at = now
    return _outcome(
        True,
        advanced=True,
        finished=finished,
        selected_country_id=value,
    )


def _record_current_error(game: Game) -> None:
    target = game.current_country_id
    game.errors += 1
    game.current_errors += 1
    game.current_is_perfect = False
    if target is not None:
        game.imperfect.add(target)


def _outcome(
    correct: bool,
    *,
    duplicate: bool = False,
    advanced: bool = False,
    finished: bool = False,
    selected_country_id: str | None,
) -> AnswerOutcome:
    return AnswerOutcome(correct, duplicate, advanced, finished, selected_country_id)


def result_for(game: Game) -> GameResult:
    """Calcule les statistiques finales d'une partie terminée."""
    if game.finished_at is None:
        raise GameRuleError("game is not finished")
    correct_actions = len(game.order) * len(VALID_ACTIONS[game.mode])
    return GameResult(
        elapsed_seconds=game.finished_at - game.started_at,
        perfect_countries=None if game.mode == "all" else game.perfect,
        errors=game.errors,
        accuracy_percent=correct_actions / (correct_actions + game.errors) * 100,
    )
