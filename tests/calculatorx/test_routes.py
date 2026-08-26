from flask import Flask

from games.calculatorx.engine import Problem
from games.calculatorx.routes import build_blueprint


def make_client():
    def problems(count):
        assert count == 512
        return [Problem(301, "÷", 7, 43) for _ in range(count)]

    app = Flask(__name__, template_folder="../../templates", static_folder="../../static")
    app.config["TESTING"] = True

    @app.get("/")
    def home():
        return "menu"

    app.register_blueprint(build_blueprint(problem_factory=problems))
    return app.test_client()


def test_index_is_scoped_to_calculatorx_prefix():
    client = make_client()

    assert client.get("/games/calculatorx/").status_code == 200
    assert client.get("/calculatorx/").status_code == 404


def test_session_returns_fixed_classic_contract():
    client = make_client()

    response = client.post("/games/calculatorx/session")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["duration_seconds"] == 120
    assert len(payload["problems"]) == 512
    assert payload["problems"][0] == {
        "left": 301,
        "operator": "÷",
        "right": 7,
        "answer": 43,
    }


def test_session_rejects_get():
    assert make_client().get("/games/calculatorx/session").status_code == 405
