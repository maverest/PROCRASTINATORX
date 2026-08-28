from flask import Flask
import pytest

from games.calculatorx.engine import GameConfig, Problem
from games.calculatorx.routes import build_blueprint
from games.calculatorx.storage import CalculatorStorage


def custom_session_payload():
    return {
        "mode": "custom",
        "duration_seconds": 45,
        "operations": ["+"],
        "addition": {
            "left": {"minimum": 7, "maximum": 7},
            "right": {"minimum": 9, "maximum": 9},
        },
        "multiplication": {
            "left": {"minimum": 2, "maximum": 12},
            "right": {"minimum": 2, "maximum": 100},
        },
    }


def result_payload(*, ended_reason="timeout", mode="classic"):
    return {
        "mode": mode,
        "duration_seconds": 120,
        "score": 2,
        "ended_reason": ended_reason,
        "samples": [
            {"operator": "+", "elapsed_ms": 1000},
            {"operator": "÷", "elapsed_ms": 2500},
        ],
    }


@pytest.fixture
def client(tmp_path):
    received_configs: list[GameConfig] = []

    def problems(config: GameConfig, count: int):
        received_configs.append(config)
        assert count == 512
        return [Problem(301, "÷", 7, 43) for _ in range(count)]

    app = Flask(__name__, template_folder="../../templates", static_folder="../../static")
    app.config["TESTING"] = True

    @app.get("/")
    def home():
        return "menu"

    app.register_blueprint(
        build_blueprint(
            storage=CalculatorStorage(tmp_path / "calculatorx.sqlite3"),
            problem_factory=problems,
        )
    )
    app.extensions["calculatorx_received_configs"] = received_configs
    return app.test_client()


def test_index_is_scoped_to_calculatorx_prefix(client):
    assert client.get("/games/calculatorx/").status_code == 200
    assert client.get("/calculatorx/").status_code == 404


def test_session_without_body_returns_classic_contract(client):
    response = client.post("/games/calculatorx/session")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["mode"] == "classic"
    assert payload["duration_seconds"] == 120
    assert payload["leaderboard_eligible"] is True
    assert len(payload["problems"]) == 512
    assert payload["problems"][0] == {
        "left": 301,
        "operator": "÷",
        "right": 7,
        "answer": 43,
    }


def test_custom_session_returns_validated_config(client):
    response = client.post("/games/calculatorx/session", json=custom_session_payload())

    assert response.status_code == 200
    assert response.get_json()["mode"] == "custom"
    assert response.get_json()["duration_seconds"] == 45


def test_constance_session_uses_its_fixed_configuration(client):
    response = client.post("/games/calculatorx/session", json={"mode": "constance"})

    assert response.status_code == 200
    assert response.get_json()["mode"] == "constance"
    assert response.get_json()["duration_seconds"] == 120
    assert response.get_json()["leaderboard_eligible"] is True


def test_invalid_config_returns_field_error(client):
    response = client.post("/games/calculatorx/session", json={"mode": "custom"})

    assert response.status_code == 400
    assert response.get_json()["field"]


def test_stopped_result_is_not_leaderboard_eligible(client):
    response = client.post(
        "/games/calculatorx/result", json=result_payload(ended_reason="stopped")
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["leaderboard_eligible"] is False
    assert payload["session"]["submission_status"] == "not_applicable"


def test_finished_classic_result_recalculates_statistics_and_persists_summary(client):
    response = client.post("/games/calculatorx/result", json=result_payload())
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["leaderboard_eligible"] is True
    assert payload["session"]["submission_status"] == "pending"
    assert payload["statistics"] == {
        "+": {"count": 1, "median_ms": 1000, "fastest_ms": 1000, "slowest_ms": 1000},
        "÷": {"count": 1, "median_ms": 2500, "fastest_ms": 2500, "slowest_ms": 2500},
    }


def test_custom_result_is_not_leaderboard_eligible(client):
    response = client.post(
        "/games/calculatorx/result", json=result_payload(mode="custom")
    )

    assert response.status_code == 200
    assert response.get_json()["leaderboard_eligible"] is False


def test_result_rejects_invalid_sample_with_field_error(client):
    payload = result_payload()
    payload["samples"] = [{"operator": "+", "elapsed_ms": -1}]

    response = client.post("/games/calculatorx/result", json=payload)

    assert response.status_code == 400
    assert response.get_json()["field"] == "samples"


def test_result_rejects_a_score_above_the_leaderboard_limit(client):
    payload = result_payload()
    payload["score"] = 10_000

    response = client.post("/games/calculatorx/result", json=payload)

    assert response.status_code == 400
    assert response.get_json()["field"] == "score"


def test_history_excludes_samples_and_can_be_cleared(client):
    client.post("/games/calculatorx/result", json=result_payload())

    listed = client.get("/games/calculatorx/history")

    assert listed.status_code == 200
    assert listed.get_json()["sessions"]
    assert "samples" not in listed.get_json()["sessions"][0]
    assert client.delete("/games/calculatorx/history").status_code == 204
    assert client.get("/games/calculatorx/history").get_json() == {"sessions": []}


def test_session_rejects_get(client):
    assert client.get("/games/calculatorx/session").status_code == 405
