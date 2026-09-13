"""Tests de la coquille (Shell) elle-même.

Distinct de tests/orquantix/test_routes.py : ici on vérifie que app.py sait
démarrer un jeu paresseusement, une seule fois, et remonter une erreur —
sans rien connaître des règles d'Orquantix. Aucun de ces cas n'existait dans
l'ancien tests/test_app.py (qui testait AppState, supprimé avec ce refactor).
"""

import pytest

import games.orquantix.runtime as runtime_module
from app import Shell, create_app
from games.orquantix.runtime import OrquantixRuntime


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


def test_home_renders_catalog_without_starting_orquantix(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"PROCRASTINATOR" in response.data
    assert b"Orquantix" in response.data
    assert b'href="/games/orquantix/"' in response.data
    assert client.get("/status").get_json()["phase"] == "idle"


def test_home_lists_orquantix_then_calculatorx_then_mapix(client):
    page = client.get("/").data.decode()

    assert page.index("Orquantix") < page.index("CalculatorX") < page.index("Mapix")
    assert 'href="/games/calculatorx/"' in page
    assert 'href="/games/mapix/"' in page
    assert client.get("/games/mapix/").status_code == 200


def test_home_only_displays_game_titles_and_actions(client):
    page = client.get("/").data.decode()

    assert 'class="shell-eyebrow"' not in page
    assert 'class="shell-tagline"' not in page
    assert "Trouve le mot secret par proximité sémantique." not in page
    assert "120 secondes de calcul mental." not in page
    assert "PROCRASTINATORX" in page
    assert "Orquantix" in page
    assert "CalculatorX" in page
    assert "Mapix" in page
    assert page.count("Ouvrir") == 3


def test_legacy_status_still_reports_orquantix_idle(client):
    response = client.get("/status")

    assert response.status_code == 200
    assert response.get_json()["phase"] == "idle"


def test_direct_orquantix_entry_still_starts_loading(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(OrquantixRuntime, "ensure_loaded", lambda self: calls.append("load"))
    shell = Shell(tmp_path)
    flask_app = create_app(shell)
    flask_app.config["TESTING"] = True

    with flask_app.test_client() as direct_client:
        response = direct_client.get("/games/orquantix/")

    assert response.status_code == 200
    assert calls == ["load"]
