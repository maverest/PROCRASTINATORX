"""Contrat HTTP Mapix, exercé avec le vrai état et le vrai moteur."""

from pathlib import Path
import random

from flask import Flask
import pytest

from games.mapix.countries import Country, CountryCatalog
from games.mapix.state import MapixState


@pytest.fixture
def state():
    catalog = CountryCatalog((
        Country("CH", "Suisse", "europe", "flags/CH.svg", ()),
        Country("FR", "France", "europe", "flags/FR.svg", ()),
    ))
    return MapixState(catalog, clock=lambda: 10.0, rng=random.Random(7))


@pytest.fixture
def client(state):
    from games.mapix.routes import build_blueprint

    app = Flask(__name__, template_folder=str(Path(__file__).parents[2] / "templates"))
    app.config["TESTING"] = True
    app.register_blueprint(build_blueprint(state))
    with app.test_client() as client:
        yield client


def start(client, mode="territory"):
    response = client.post("/games/mapix/session", json={"mode": mode, "region": "europe"})
    assert response.status_code == 200
    return response.get_json()


def answer_payload(session, **overrides):
    return {
        "token": session["token"], "question_index": session["question_index"],
        "action": "territory", "value": "CH", **overrides,
    }


def target(state):
    with state._lock:
        return state._game.current_country_id


def test_index_is_scoped_to_mapix_prefix(client):
    response = client.get("/games/mapix/")
    assert response.status_code == 200
    assert b"<title>Mapix</title>" in response.data
    assert client.get("/mapix/").status_code == 404


@pytest.mark.parametrize("field,value,message", [
    ("mode", "bad", "Mode inconnu."),
    ("region", "bad", "Zone inconnue."),
])
def test_invalid_start_preserves_session(client, state, field, value, message):
    before = start(client)
    payload = {"mode": "territory", "region": "europe", field: value}
    response = client.post("/games/mapix/session", json=payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": message, "field": field}
    assert state.snapshot() == before


@pytest.mark.parametrize("endpoint,field", [
    ("session", "mode"), ("answer", "token"), ("solution", "token"),
    ("quit", "token"),
])
def test_empty_object_reports_first_missing_field(client, endpoint, field):
    response = client.post(f"/games/mapix/{endpoint}", json={})
    assert response.status_code == 400
    assert response.get_json()["field"] == field


@pytest.mark.parametrize("endpoint", ["session", "answer", "solution", "quit"])
@pytest.mark.parametrize("body", [None, "{", "null", "[]", '"text"', "true", "3"])
def test_missing_or_non_object_json_is_rejected_without_mutation(client, state, endpoint, body):
    before = start(client)
    response = client.post(f"/games/mapix/{endpoint}", data=body, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Le corps doit être un objet JSON valide.", "field": None}
    assert state.snapshot() == before


@pytest.mark.parametrize("field", ["mode", "region"])
@pytest.mark.parametrize("value", [None, True, 3, [], {}, "", "  "])
def test_start_requires_nonempty_strings(client, state, field, value):
    before = start(client)
    payload = {"mode": "territory", "region": "europe", field: value}
    response = client.post("/games/mapix/session", json=payload)
    assert response.status_code == 400
    assert response.get_json()["field"] == field
    assert state.snapshot() == before


@pytest.mark.parametrize("field", ["token", "question_index", "action", "value"])
def test_answer_requires_every_field(client, state, field):
    before = start(client)
    payload = answer_payload(before)
    del payload[field]
    response = client.post("/games/mapix/answer", json=payload)
    assert response.status_code == 400
    assert response.get_json()["field"] == field
    assert state.snapshot() == before


@pytest.mark.parametrize("field", ["token", "action", "value"])
@pytest.mark.parametrize("value", [None, True, 3, [], {}, "", "  "])
def test_answer_requires_nonempty_strings(client, state, field, value):
    before = start(client)
    response = client.post("/games/mapix/answer", json=answer_payload(before, **{field: value}))
    assert response.status_code == 400
    assert response.get_json()["field"] == field
    assert state.snapshot() == before


@pytest.mark.parametrize("value", [None, False, True, 0.0, "0", [], {}])
def test_question_index_requires_integer_excluding_boolean(client, state, value):
    before = start(client)
    response = client.post("/games/mapix/answer", json=answer_payload(before, question_index=value))
    assert response.status_code == 400
    assert response.get_json()["field"] == "question_index"
    assert state.snapshot() == before


@pytest.mark.parametrize("value", [None, True, 3, [], {}, "", "  "])
def test_quit_requires_nonempty_token(client, state, value):
    before = start(client)
    response = client.post("/games/mapix/quit", json={"token": value})
    assert response.status_code == 400
    assert response.get_json()["field"] == "token"
    assert state.snapshot() == before


@pytest.mark.parametrize("endpoint", ["session", "answer", "solution", "quit"])
def test_missing_session_returns_json_404(client, endpoint):
    if endpoint == "session":
        response = client.get("/games/mapix/session")
    else:
        response = client.post(f"/games/mapix/{endpoint}", json=answer_payload({"token": "absent", "question_index": 0}))
    assert response.status_code == 404
    assert response.get_json() == {"error": "Aucune partie en cours.", "field": None}


@pytest.mark.parametrize("endpoint", ["answer", "solution", "quit"])
def test_stale_token_returns_conflict_without_mutation(client, state, endpoint):
    old = start(client)
    before = start(client)
    response = client.post(f"/games/mapix/{endpoint}", json=answer_payload(old))
    assert response.status_code == 409
    assert response.get_json() == {"error": "Cette partie n’est plus active.", "field": "token"}
    assert state.snapshot() == before


@pytest.mark.parametrize("index", [-1, 0, 2])
def test_stale_or_future_question_returns_conflict_without_mutation(client, state, index):
    session = start(client)
    accepted = client.post("/games/mapix/answer", json=answer_payload(session, value=target(state)))
    assert accepted.status_code == 200
    before = state.snapshot()
    response = client.post("/games/mapix/answer", json=answer_payload(session, question_index=index))
    assert response.status_code == 409
    assert response.get_json() == {"error": "Cette question n’est plus active.", "field": "question_index"}
    assert state.snapshot() == before


@pytest.mark.parametrize("field,value,message", [
    ("action", "flag", "Action invalide pour ce mode."),
    ("value", "XX", "Pays inconnu."),
])
def test_rule_errors_are_translated_without_mutation(client, state, field, value, message):
    before = start(client)
    response = client.post("/games/mapix/answer", json=answer_payload(before, **{field: value}))
    assert response.status_code == 400
    assert response.get_json() == {"error": message, "field": field}
    assert state.snapshot() == before


def test_snapshot_answer_and_quit(client, state):
    session = start(client)
    assert client.get("/games/mapix/session").get_json() == session
    response = client.post("/games/mapix/answer", json=answer_payload(session, value=target(state)))
    assert response.status_code == 200
    assert response.get_json()["outcome"]["correct"] is True
    assert response.get_json()["question_index"] == 1
    response = client.post("/games/mapix/quit", json={"token": session["token"]})
    assert response.status_code == 204
    assert response.data == b""
    assert client.get("/games/mapix/session").status_code == 404


@pytest.mark.parametrize("mode,actions", [
    ("territory", ("territory",)), ("flag-only", ("flag",)),
    ("flag-territory", ("flag", "territory")), ("all", ("name",)),
])
def test_each_mode_can_finish_through_http(client, state, mode, actions):
    session = start(client, mode)
    for _ in range(2):
        country_id = target(state)
        for action in actions:
            value = {"CH": "Suisse", "FR": "France"}[country_id] if action == "name" else country_id
            response = client.post("/games/mapix/answer", json=answer_payload(session, action=action, value=value))
            assert response.status_code == 200
            session = response.get_json()
    assert session["finished"] is True
    assert session["result"] == {
        "elapsed_seconds": 0.0, "perfect_countries": None if mode == "all" else 2,
        "errors": 0, "accuracy_percent": 100.0,
    }
    response = client.post("/games/mapix/answer", json=answer_payload(session, action=actions[0]))
    assert response.status_code == 400
    assert response.get_json() == {"error": "La partie est terminée.", "field": None}


def test_combined_flag_stays_until_territory_is_also_correct(client, state):
    session = start(client, "flag-territory")
    country_id = target(state)

    response = client.post(
        "/games/mapix/answer",
        json=answer_payload(session, action="flag", value=country_id),
    )
    after_flag = response.get_json()
    assert response.status_code == 200
    assert after_flag["flag_done"] is True
    assert after_flag["territory_done"] is False
    assert country_id in after_flag["remaining_flags"]

    response = client.post(
        "/games/mapix/answer",
        json=answer_payload(after_flag, action="territory", value=country_id),
    )
    after_territory = response.get_json()
    assert response.status_code == 200
    assert country_id not in after_territory["remaining_flags"]


def test_solution_endpoint_counts_error_and_reveals_without_advancing(client, state):
    session = start(client, "flag-territory")
    response = client.post(
        "/games/mapix/solution",
        json={"token": session["token"], "question_index": 0},
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["errors"] == 1
    assert payload["current_errors"] == 1
    assert payload["revealed_actions"] == ["flag", "territory"]
    assert payload["question_index"] == 0
    assert payload["found"] == []


def test_solution_endpoint_rejects_all_mode_without_mutation(client, state):
    session = start(client, "all")
    response = client.post(
        "/games/mapix/solution",
        json={"token": session["token"], "question_index": 0},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Solution indisponible pour ce mode.", "field": None,
    }
    assert state.snapshot() == session


def test_solution_endpoint_rejects_stale_question_without_mutation(client, state):
    session = start(client)
    client.post(
        "/games/mapix/answer",
        json=answer_payload(session, value=target(state)),
    )
    before = state.snapshot()

    response = client.post(
        "/games/mapix/solution",
        json={"token": session["token"], "question_index": 0},
    )

    assert response.status_code == 409
    assert response.get_json()["field"] == "question_index"
    assert state.snapshot() == before


def test_flag_only_removes_flag_immediately(client, state):
    session = start(client, "flag-only")
    country_id = target(state)
    response = client.post(
        "/games/mapix/answer",
        json=answer_payload(session, action="flag", value=country_id),
    )
    updated = response.get_json()
    assert response.status_code == 200
    assert country_id not in updated["remaining_flags"]


def test_all_mode_has_no_prompt_and_no_perfect_result(client, state):
    session = start(client, "all")
    assert session["current"] is None
    while session["result"] is None:
        country_id = target(state)
        session = client.post(
            "/games/mapix/answer",
            json=answer_payload(
                session,
                action="name",
                value=state._catalog.by_id[country_id].name,
            ),
        ).get_json()
    assert session["result"]["perfect_countries"] is None


def test_build_game_uses_configured_static_root(tmp_path, monkeypatch):
    from games.mapix import build_game

    static_root = tmp_path / "assets"
    (static_root / "mapix").mkdir(parents=True)
    (static_root / "mapix/countries.json").write_text(
        '[{"id":"CH","name":"Suisse","continent":"europe","flag":"flags/CH.svg","aliases":[]}]',
        encoding="utf-8",
    )
    monkeypatch.setenv("PROCRASTINATOR_STATIC", str(static_root))
    mounted = build_game(tmp_path)
    app = Flask(__name__)
    app.register_blueprint(mounted.blueprint)
    session = start(app.test_client())
    assert session["total"] == 1
    assert session["remaining_flags"] == ["CH"]


def test_build_game_finds_real_catalog_from_another_working_directory(tmp_path, monkeypatch):
    from games.mapix import build_game

    monkeypatch.delenv("PROCRASTINATOR_STATIC", raising=False)
    monkeypatch.chdir(tmp_path)
    mounted = build_game(tmp_path)
    app = Flask(__name__)
    app.register_blueprint(mounted.blueprint)
    response = app.test_client().post(
        "/games/mapix/session", json={"mode": "territory", "region": "world"}
    )
    assert response.status_code == 200
    session = response.get_json()
    assert session["total"] == 195
    assert len(session["remaining_flags"]) == 195
    assert {"CH", "FR", "JP", "US"} <= set(session["remaining_flags"])
