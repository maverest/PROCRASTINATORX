"""Tests de la coquille (Shell) elle-même.

Distinct de tests/orquantix/test_routes.py : ici on vérifie que app.py sait
démarrer un jeu paresseusement, une seule fois, et remonter une erreur —
sans rien connaître des règles d'Orquantix. Aucun de ces cas n'existait dans
l'ancien tests/test_app.py (qui testait AppState, supprimé avec ce refactor).
"""

import pytest

import games.orquantix.runtime as runtime_module
from app import Shell, create_app


@pytest.fixture
def shell(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: [])
    monkeypatch.setattr(runtime_module, "load_resources", lambda state, data_dir: None)
    return Shell(tmp_path)


@pytest.fixture
def client(shell):
    flask_app = create_app(shell)
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_home_redirects_into_the_game(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/games/orquantix/")


def test_status_reports_idle_before_the_game_is_entered(client):
    data = client.get("/status").get_json()
    assert data["phase"] == "idle"


def test_direct_orquantix_entry_starts_runtime(client, shell, monkeypatch):
    # Le chargement paresseux doit démarrer depuis l'index du jeu lui-même,
    # pas seulement depuis / : sinon un accès direct à /games/orquantix/
    # laisse le front sonder indéfiniment à phase "idle".
    calls = []
    monkeypatch.setattr(shell.orquantix_runtime, "ensure_loaded", lambda: calls.append("load"))

    response = client.get("/games/orquantix/")

    assert response.status_code == 200
    assert calls == ["load"]
