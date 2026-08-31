from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from flask import Blueprint, jsonify, render_template, request

from games.calculatorx.engine import (
    ConfigError,
    DURATION_SECONDS,
    GameConfig,
    PROBLEM_COUNT,
    Problem,
    classic_config,
    constance_config,
    generate_problems,
    parse_config,
    reserve_count,
)
from games.calculatorx.leaderboard import LeaderboardClient, LeaderboardUnavailable
from games.calculatorx.statistics import ResponseSample, summarize
from games.calculatorx.storage import CalculatorStorage, SessionRecord, StorageError

BLUEPRINT_NAME = "calculatorx"
URL_PREFIX = "/games/calculatorx"
ProblemFactory = Callable[[GameConfig, int], list[Problem]]
VALID_MODES = ("classic", "custom", "constance")
VALID_ENDED_REASONS = ("timeout", "stopped", "exhausted")


class RequestError(ValueError):
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.field = field


def build_blueprint(
    storage: CalculatorStorage,
    problem_factory: ProblemFactory = generate_problems,
    leaderboard_client: LeaderboardClient | None = None,
) -> Blueprint:
    blueprint = Blueprint(BLUEPRINT_NAME, __name__, url_prefix=URL_PREFIX)
    leaderboard = leaderboard_client or LeaderboardClient("")

    @blueprint.get("/")
    def index():
        return render_template("calculatorx/index.html")

    @blueprint.post("/session")
    def session():
        try:
            config = _session_config()
        except (ConfigError, RequestError) as error:
            return _field_error(error)

        problems = problem_factory(config, reserve_count(config.duration_seconds))
        return jsonify(
            mode=config.mode,
            duration_seconds=config.duration_seconds,
            leaderboard_eligible=config.mode in ("classic", "constance"),
            problems=[problem.as_dict() for problem in problems],
        )

    @blueprint.post("/result")
    def result():
        try:
            result_data = _parse_result()
        except RequestError as error:
            return _field_error(error)

        statistics = summarize(result_data.samples)
        eligible = _is_leaderboard_eligible(
            result_data.mode, result_data.duration_seconds, result_data.ended_reason
        )
        submission_status = "pending" if eligible else "not_applicable"
        try:
            session_record = storage.record_session(
                mode=result_data.mode,
                duration_seconds=result_data.duration_seconds,
                score=result_data.score,
                ended_reason=result_data.ended_reason,
                submission_status=submission_status,
            )
        except StorageError:
            return _storage_error()
        return jsonify(
            leaderboard_eligible=eligible,
            session=asdict(session_record),
            statistics={operator: asdict(summary) for operator, summary in statistics.items()},
        )

    @blueprint.get("/history")
    def history():
        try:
            sessions = storage.list_sessions()
        except StorageError:
            return _storage_error()
        return jsonify(sessions=[asdict(record) for record in sessions])

    @blueprint.delete("/history")
    def clear_history():
        try:
            storage.clear_sessions()
        except StorageError:
            return _storage_error()
        return ("", 204)

    @blueprint.get("/profiles")
    def profiles():
        try:
            records = storage.list_profiles()
        except StorageError:
            return _storage_error()
        return jsonify(profiles=[asdict(profile) for profile in records])

    @blueprint.post("/profiles")
    def create_profile():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) != {"nickname"}:
            return _field_error(RequestError("Le pseudo est invalide.", "nickname"))
        try:
            profile = storage.create_profile(payload["nickname"])
        except StorageError as error:
            if str(error) == "Pseudo invalide.":
                return _field_error(RequestError(str(error), "nickname"))
            return _storage_error()
        return jsonify(profile=asdict(profile))

    @blueprint.get("/leaderboards/<mode>")
    def leaderboard_scores(mode: str):
        if mode not in ("classic", "constance"):
            return jsonify(error="Classement inconnu."), 404
        try:
            scores = leaderboard.list_scores(mode)
        except LeaderboardUnavailable:
            return _leaderboard_error()
        return jsonify(scores=scores)

    @blueprint.post("/leaderboard/submit")
    def submit_leaderboard_score():
        try:
            session_id, profile_id = _submission_identifiers()
        except RequestError as error:
            return _field_error(error)
        try:
            session = storage.get_session(session_id)
            profile = storage.get_profile(profile_id)
        except StorageError as error:
            return _lookup_error(error)
        if not _session_is_pending_and_eligible(session):
            return jsonify(error="Cette séance ne peut pas être envoyée."), 409
        try:
            record = leaderboard.submit_score(session.mode, profile.nickname, session.score)
        except LeaderboardUnavailable:
            return _leaderboard_error()
        try:
            submitted = storage.mark_submitted(session.id, profile.nickname)
        except StorageError as error:
            if str(error) in {"Cette séance ne peut pas être envoyée.", "Profil introuvable."}:
                return jsonify(error="Cette séance ne peut pas être envoyée."), 409
            return _storage_error()
        return jsonify(score=record, session=asdict(submitted))

    return blueprint


class ResultData:
    __slots__ = ("mode", "duration_seconds", "score", "ended_reason", "samples")

    def __init__(
        self,
        mode: str,
        duration_seconds: int,
        score: int,
        ended_reason: str,
        samples: list[ResponseSample],
    ) -> None:
        self.mode = mode
        self.duration_seconds = duration_seconds
        self.score = score
        self.ended_reason = ended_reason
        self.samples = samples


def _session_config() -> GameConfig:
    if not request.get_data(cache=True):
        return classic_config()

    payload = request.get_json(silent=True)
    if payload is None:
        raise RequestError("Le corps doit contenir du JSON valide.", "config")
    if isinstance(payload, dict) and payload.get("mode") == "constance":
        return constance_config()
    return parse_config(payload)


def _parse_result() -> ResultData:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise RequestError("Le résultat doit être un objet JSON.", "result")

    mode = _required_choice(payload, "mode", VALID_MODES)
    duration_seconds = _required_integer(payload, "duration_seconds", minimum=1, maximum=3600)
    if mode in ("classic", "constance") and duration_seconds != DURATION_SECONDS:
        raise RequestError("Ce mode dure 120 secondes.", "duration_seconds")
    score = _required_integer(
        payload, "score", minimum=0, maximum=_score_limit(mode, duration_seconds)
    )
    ended_reason = _required_choice(payload, "ended_reason", VALID_ENDED_REASONS)
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list):
        raise RequestError("Les temps de réponse doivent être une liste.", "samples")
    if len(raw_samples) != score:
        raise RequestError("Le nombre de temps doit correspondre au score.", "samples")
    try:
        samples = [ResponseSample.from_dict(sample) for sample in raw_samples]
    except ValueError as error:
        raise RequestError(str(error), "samples") from error
    return ResultData(mode, duration_seconds, score, ended_reason, samples)


def _required_choice(payload: dict[str, object], field: str, choices: tuple[str, ...]) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or value not in choices:
        raise RequestError("Cette valeur est inconnue.", field)
    return value


def _required_integer(
    payload: dict[str, object], field: str, *, minimum: int, maximum: int | None = None
) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RequestError("Cette valeur doit être un entier.", field)
    if value < minimum or (maximum is not None and value > maximum):
        raise RequestError("Cette valeur est hors limites.", field)
    return value


def _is_leaderboard_eligible(mode: str, duration_seconds: int, ended_reason: str) -> bool:
    return (
        mode in ("classic", "constance")
        and duration_seconds == DURATION_SECONDS
        and ended_reason in ("timeout", "exhausted")
    )


def _score_limit(mode: str, duration_seconds: int) -> int:
    return 9999 if mode in ("classic", "constance") else reserve_count(duration_seconds)


def _submission_identifiers() -> tuple[int, str]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"session_id", "profile_id"}:
        raise RequestError("La demande d'envoi est invalide.", "submission")
    session_id = payload["session_id"]
    profile_id = payload["profile_id"]
    if isinstance(session_id, bool) or not isinstance(session_id, int) or session_id < 1:
        raise RequestError("La séance est invalide.", "session_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise RequestError("Le profil est invalide.", "profile_id")
    return session_id, profile_id


def _session_is_pending_and_eligible(session: SessionRecord) -> bool:
    return (
        session.submission_status == "pending"
        and session.mode in {"classic", "constance"}
        and session.duration_seconds == DURATION_SECONDS
        and session.ended_reason in {"timeout", "exhausted"}
    )


def _lookup_error(error: StorageError):
    if str(error) in {"Séance introuvable.", "Profil introuvable."}:
        return jsonify(error=str(error)), 404
    return _storage_error()


def _field_error(error: ConfigError | RequestError):
    return jsonify(error=str(error), field=error.field), 400


def _storage_error():
    return jsonify(error="Historique local indisponible."), 503


def _leaderboard_error():
    return jsonify(error="Classement indisponible."), 503
