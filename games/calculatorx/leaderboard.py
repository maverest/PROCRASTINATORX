from __future__ import annotations

from datetime import datetime
from typing import Any
import unicodedata

import requests


VALID_MODES = frozenset(("classic", "constance"))
MAX_SCORES = 100
MAX_SCORE = 9999


class LeaderboardUnavailable(RuntimeError):
    """The remote friendly leaderboard cannot safely be used right now."""


class LeaderboardClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 3.0,
        http: Any = requests,
    ) -> None:
        self.base_url = base_url.strip().rstrip("/") if isinstance(base_url, str) else ""
        self.timeout_seconds = timeout_seconds
        self.http = http

    def list_scores(self, mode: str) -> list[dict[str, object]]:
        self._require_mode(mode)
        response = self._request("get", f"/leaderboards/{mode}")
        payload = self._json(response)
        if not isinstance(payload, dict) or set(payload) != {"scores"}:
            raise LeaderboardUnavailable("Réponse du classement invalide.")
        scores = payload["scores"]
        if not isinstance(scores, list) or len(scores) > MAX_SCORES:
            raise LeaderboardUnavailable("Réponse du classement invalide.")
        return [self._validate_record(record) for record in scores]

    def submit_score(self, mode: str, nickname: str, score: int) -> dict[str, object]:
        self._require_mode(mode)
        self._require_nickname(nickname)
        self._require_score(score)
        response = self._request(
            "post",
            "/scores",
            json={"mode": mode, "nickname": nickname, "score": score},
        )
        return self._validate_record(self._json(response))

    def _request(self, method: str, path: str, json: dict[str, object] | None = None):
        if not self.base_url:
            raise LeaderboardUnavailable("Classement indisponible.")
        try:
            if method == "get":
                response = self.http.get(f"{self.base_url}{path}", timeout=self.timeout_seconds)
            else:
                response = self.http.post(
                    f"{self.base_url}{path}", json=json, timeout=self.timeout_seconds
                )
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            raise LeaderboardUnavailable("Classement indisponible.") from error

    @staticmethod
    def _json(response) -> object:
        try:
            return response.json()
        except (TypeError, ValueError) as error:
            raise LeaderboardUnavailable("Réponse du classement invalide.") from error

    @staticmethod
    def _require_mode(mode: object) -> None:
        if not isinstance(mode, str) or mode not in VALID_MODES:
            raise LeaderboardUnavailable("Mode de classement invalide.")

    @staticmethod
    def _require_nickname(nickname: object) -> None:
        if not isinstance(nickname, str):
            raise LeaderboardUnavailable("Pseudo invalide.")
        display = unicodedata.normalize("NFKC", nickname).strip()
        if (
            not 1 <= len(display) <= 24
            or any(unicodedata.category(character) == "Cc" for character in display)
        ):
            raise LeaderboardUnavailable("Pseudo invalide.")

    @staticmethod
    def _require_score(score: object) -> None:
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= MAX_SCORE:
            raise LeaderboardUnavailable("Score invalide.")

    @classmethod
    def _validate_record(cls, value: object) -> dict[str, object]:
        if not isinstance(value, dict) or set(value) != {
            "rank", "nickname", "score", "achieved_at"
        }:
            raise LeaderboardUnavailable("Réponse du classement invalide.")
        rank = value["rank"]
        nickname = value["nickname"]
        score = value["score"]
        achieved_at = value["achieved_at"]
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
            raise LeaderboardUnavailable("Réponse du classement invalide.")
        try:
            cls._require_nickname(nickname)
            cls._require_score(score)
        except LeaderboardUnavailable as error:
            raise LeaderboardUnavailable("Réponse du classement invalide.") from error
        if not isinstance(achieved_at, str) or not cls._is_iso_datetime(achieved_at):
            raise LeaderboardUnavailable("Réponse du classement invalide.")
        return {
            "rank": rank,
            "nickname": nickname,
            "score": score,
            "achieved_at": achieved_at,
        }

    @staticmethod
    def _is_iso_datetime(value: str) -> bool:
        if "T" not in value:
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return True
