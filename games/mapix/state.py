"""État transactionnel d'une partie Mapix et représentation publique."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
import random
import secrets
import threading
import time

from .countries import CountryCatalog
from .engine import (
    AnswerOutcome,
    Game,
    apply_answer,
    apply_solution,
    new_game,
    result_for,
    revealed_actions,
    solution_available,
)


class NoActiveGame(Exception):
    """Aucune partie n'est en cours."""


class StaleGame(Exception):
    """Le jeton appartient à une partie remplacée."""


class StaleQuestion(Exception):
    """La réponse ne concerne pas la question courante."""


class MapixState:
    """Sérialise les lectures et transitions sous un verrou unique."""

    def __init__(
        self,
        catalog: CountryCatalog,
        *,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self._catalog = catalog
        self._clock = clock
        self._rng = rng if rng is not None else random.SystemRandom()
        self._game: Game | None = None
        self._token: str | None = None
        self._lock = threading.Lock()

    def start(self, mode: str, region: str) -> dict:
        """Remplace la partie seulement après validation par le moteur."""
        with self._lock:
            now = self._clock()
            game = new_game(self._catalog, mode, region, self._rng, now)
            token = secrets.token_urlsafe(18)
            self._game = game
            self._token = token
            return self._payload(now)

    def answer(
        self, token: str, question_index: int, action: str, value: str
    ) -> dict:
        """Vérifie les jetons et applique la réponse dans la même transaction."""
        with self._lock:
            game = self._require_token(token)
            if question_index != game.current_index:
                raise StaleQuestion
            now = self._clock()
            outcome = apply_answer(game, self._catalog, action, value, now)
            return self._payload(now, outcome=outcome)

    def snapshot(self) -> dict:
        """Retourne une copie cohérente de l'état public."""
        with self._lock:
            self._require_game()
            return self._payload(self._clock())

    def solution(self, token: str, question_index: int) -> dict:
        """Révèle la cible courante sans la valider, sous le verrou du tour."""
        with self._lock:
            game = self._require_token(token)
            if question_index != game.current_index:
                raise StaleQuestion
            apply_solution(game)
            return self._payload(self._clock())

    def quit(self, token: str) -> bool:
        """Efface la partie uniquement si le jeton est encore valide."""
        with self._lock:
            self._require_token(token)
            self._game = None
            self._token = None
            return True

    def _require_game(self) -> Game:
        """À appeler uniquement sous le verrou."""
        if self._game is None:
            raise NoActiveGame
        return self._game

    def _require_token(self, token: str) -> Game:
        """À appeler uniquement sous le verrou."""
        game = self._require_game()
        if token != self._token:
            raise StaleGame
        return game

    def _payload(self, now: float, *, outcome: AnswerOutcome | None = None) -> dict:
        """Sérialise sous le verrou sans publier la cible ni l'ordre des questions."""
        game = self._require_game()
        finished = game.finished_at is not None
        current = None
        if not finished and game.mode != "all":
            current = {"name": self._catalog.by_id[game.current_country_id].name}
        elapsed_until = game.finished_at if finished else now
        payload = {
            "mode": game.mode,
            "region": game.region,
            "token": self._token,
            "total": len(game.order),
            "question_index": game.current_index,
            "elapsed_seconds": elapsed_until - game.started_at,
            "errors": game.errors,
            "found": sorted(game.found),
            "remaining_flags": sorted(set(game.order) - game.found),
            "current": current,
            "flag_done": game.flag_done,
            "territory_done": game.territory_done,
            "current_errors": game.current_errors,
            "revealed_actions": list(revealed_actions(game)),
            "solution_available": solution_available(game),
            "imperfect": sorted(game.imperfect),
            "finished": finished,
            "result": asdict(result_for(game)) if finished else None,
        }
        if outcome is not None:
            payload["outcome"] = asdict(outcome)
        return payload
