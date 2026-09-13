"""Interface HTTP du mini-jeu Mapix."""

from flask import Blueprint, jsonify, render_template, request

from .engine import GameRuleError
from .state import MapixState, NoActiveGame, StaleGame, StaleQuestion

BLUEPRINT_NAME = "mapix"
URL_PREFIX = "/games/mapix"
RULE_MESSAGES = {
    "invalid mode": "Mode inconnu.",
    "invalid region": "Zone inconnue.",
    "invalid action": "Action invalide pour ce mode.",
    "invalid country": "Pays inconnu.",
    "game is finished": "La partie est terminée.",
}


class RequestError(ValueError):
    """Un corps ou un champ ne respecte pas le contrat HTTP."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


def build_blueprint(state: MapixState) -> Blueprint:
    blueprint = Blueprint(BLUEPRINT_NAME, __name__, url_prefix=URL_PREFIX)

    @blueprint.errorhandler(RequestError)
    def malformed_request(error):
        return jsonify(error=str(error), field=error.field), 400

    @blueprint.errorhandler(GameRuleError)
    def invalid_action(error):
        message = RULE_MESSAGES.get(str(error), "Cette action est impossible.")
        return jsonify(error=message, field=error.field), 400

    @blueprint.errorhandler(NoActiveGame)
    def no_active_game(error):
        return jsonify(error="Aucune partie en cours.", field=None), 404

    @blueprint.errorhandler(StaleGame)
    def stale_game(error):
        return jsonify(error="Cette partie n’est plus active.", field="token"), 409

    @blueprint.errorhandler(StaleQuestion)
    def stale_question(error):
        return jsonify(error="Cette question n’est plus active.", field="question_index"), 409

    @blueprint.get("/")
    def index():
        return render_template("mapix/index.html")

    @blueprint.post("/session")
    def start_session():
        payload = _require_payload()
        return jsonify(state.start(
            _require_string(payload, "mode"), _require_string(payload, "region")
        ))

    @blueprint.get("/session")
    def get_session():
        return jsonify(state.snapshot())

    @blueprint.post("/answer")
    def answer():
        payload = _require_payload()
        return jsonify(state.answer(
            _require_string(payload, "token"),
            _require_integer(payload, "question_index"),
            _require_string(payload, "action"),
            _require_string(payload, "value"),
        ))

    @blueprint.post("/quit")
    def quit_session():
        payload = _require_payload()
        state.quit(_require_string(payload, "token"))
        return "", 204

    return blueprint


def _require_payload() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise RequestError("Le corps doit être un objet JSON valide.")
    return payload


def _require_string(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RequestError("Ce champ doit être un texte non vide.", field)
    return value


def _require_integer(payload: dict, field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RequestError("Ce champ doit être un entier.", field)
    return value
