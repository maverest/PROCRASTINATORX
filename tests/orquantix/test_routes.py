import threading

import pytest
from flask import Flask

from games.orquantix.engine import get_neighbours, rank_map
from games.orquantix.routes import build_blueprint
from games.orquantix.state import OrquantixState
from games.orquantix.vocabulary import Pools, build_norm_map
from tests.conftest import make_mock_model

VOCAB = ["chien", "chat", "maison", "arbre", "fleur"]


@pytest.fixture
def state():
    model = make_mock_model(VOCAB)
    s = OrquantixState()
    s.phase = "ready"
    s.model = model
    s.pools = Pools(
        mystery_words=VOCAB,
        mystery_freq={w: 50.0 for w in VOCAB},
        hint_words=frozenset(VOCAB),
    )
    s.norm_to_model = build_norm_map(VOCAB)
    s.neighbours = get_neighbours(model, "chien", topn=4)
    s.top1000 = rank_map(s.neighbours)
    s.mystery_word = "chien"
    s.difficulty = 2
    s.littre = None
    return s


@pytest.fixture
def client(state):
    app = Flask(__name__, template_folder="../../templates")

    @app.get("/")
    def home():
        return "menu"

    app.register_blueprint(build_blueprint(state))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index_links_back_to_games(client):
    page = client.get("/games/orquantix/").data.decode()

    assert 'class="back-to-games"' in page
    assert 'href="/"' in page
    assert "Retour aux jeux" in page


def test_index_separates_controls_from_guess_history(client):
    page = client.get("/games/orquantix/").data.decode()

    assert 'class="game-workspace"' in page
    assert 'class="game-controls"' in page
    assert 'class="guess-history-panel"' in page
    assert page.index('class="game-controls"') < page.index(
        'class="guess-history-panel"'
    )
    history = page[page.index('class="guess-history-panel"') :]
    assert 'id="guessTable"' in history


def test_index_groups_primary_actions_in_one_toolbar(client):
    page = client.get("/games/orquantix/").data.decode()

    assert 'class="game-actions"' in page
    actions = page[
        page.index('class="game-actions"') : page.index(
            "</div>", page.index('class="game-actions"')
        )
    ]
    for button_id in ("giveUpBtn", "timerBtn", "hintToggleBtn", "dyslexicToggle"):
        assert f'id="{button_id}"' in actions


def test_routes_are_namespaced_under_the_game(client):
    # Le préfixe évite la collision quand un quiz voudra son propre /guess.
    assert client.post("/games/orquantix/guess", json={"word": "chat"}).status_code == 200
    assert client.post("/guess", json={"word": "chat"}).status_code == 404


def test_guess_returns_progress_and_rank(client):
    data = client.post("/games/orquantix/guess", json={"word": "chat"}).get_json()

    assert "progress" in data
    assert "rank" in data
    assert "mood" in data
    assert data["win"] is False


def test_guess_the_mystery_word_wins_at_100_degrees(client):
    data = client.post("/games/orquantix/guess", json={"word": "chien"}).get_json()

    assert data["win"] is True
    assert data["progress"] == 100.0
    assert data["mood"] == "found"


def test_guess_is_accent_and_case_insensitive(client):
    data = client.post("/games/orquantix/guess", json={"word": "CHIEN"}).get_json()

    assert data["win"] is True


def test_unknown_word_is_rejected(client):
    data = client.post("/games/orquantix/guess", json={"word": "zzzzz"}).get_json()

    assert data["error"] == "inconnu"


def test_give_up_reveals_the_word(client):
    data = client.post("/games/orquantix/give-up").get_json()

    assert data["word"] == "chien"
    assert data["gave_up"] is True
    assert data["progress"] == 100.0


def test_state_survives_between_requests(client):
    client.post("/games/orquantix/guess", json={"word": "chat"})
    data = client.get("/games/orquantix/session").get_json()

    # C'est ce qui rend la navigation par pages viable.
    assert len(data["guesses"]) == 1
    assert data["guesses"][0]["word"] == "chat"


def test_new_game_resets_the_guesses(client):
    client.post("/games/orquantix/guess", json={"word": "chat"})
    client.post("/games/orquantix/new-game")
    data = client.get("/games/orquantix/session").get_json()

    assert data["guesses"] == []


def test_routes_refuse_when_not_ready(state):
    state.phase = "loading"
    app = Flask(__name__)
    app.register_blueprint(build_blueprint(state))
    app.config["TESTING"] = True

    with app.test_client() as c:
        assert c.post("/games/orquantix/guess", json={"word": "chat"}).status_code == 503


# Le reste ci-dessous restitue de la couverture perdue avec la suppression de
# tests/test_app.py : /suggest, /hint et /status n'étaient pas dans la liste
# donnée par le brief mais existaient dans l'ancienne suite.


def test_guess_missing_word_is_rejected(client):
    assert client.post("/games/orquantix/guess", json={}).status_code == 400


def test_status_reports_the_phase(client):
    data = client.get("/games/orquantix/status").get_json()
    assert data["phase"] == "ready"


def test_suggest_finds_close_word(client):
    data = client.post("/games/orquantix/suggest", json={"word": "chein"}).get_json()
    assert data["suggestion"] == "chien"


def test_suggest_missing_word_is_rejected(client):
    assert client.post("/games/orquantix/suggest", json={}).status_code == 400


def test_hint_first_letter(client):
    data = client.post("/games/orquantix/hint", json={"type": "first-letter"}).get_json()
    assert data["value"] == "c"


def test_hint_word_length(client):
    data = client.post("/games/orquantix/hint", json={"type": "word-length"}).get_json()
    assert data["value"] == 5


def test_hint_better_word_offers_a_pool_word_by_default(client, state):
    data = client.post("/games/orquantix/hint", json={"type": "better-word"}).get_json()
    assert data["value"] in state.pools.hint_words


def test_hint_better_word_never_crosses_the_hint_pool(client, state):
    # Régression pour l'obligation 1 : app.py passait frozenset(top1000), pas
    # le vrai pool d'indices. Un pool vide doit donc rendre value=None — s'il
    # retombait sur top1000 au lieu du pool, ce test échouerait.
    state.pools = Pools(
        mystery_words=state.pools.mystery_words,
        mystery_freq=state.pools.mystery_freq,
        hint_words=frozenset(),
    )
    data = client.post("/games/orquantix/hint", json={"type": "better-word"}).get_json()
    assert data["value"] is None


def test_hint_golden_fish_never_crosses_the_hint_pool(client, state):
    # Même régression que ci-dessus, pour le poisson doré (obligations 1 et 4).
    # littre est None dans la fixture, donc golden_fish retombe sur
    # strong_hint_word, qui doit lui aussi respecter le pool vide.
    state.pools = Pools(
        mystery_words=state.pools.mystery_words,
        mystery_freq=state.pools.mystery_freq,
        hint_words=frozenset(),
    )
    data = client.post("/games/orquantix/hint", json={"type": "golden-fish"}).get_json()
    assert data["value"] is None
    assert data["kind"] == "none"


def test_new_game_increments_the_game_index(client, state):
    assert state.game_index == 0
    client.post("/games/orquantix/new-game")
    assert state.game_index == 1


def test_new_game_response_has_difficulty_and_word_length(client):
    data = client.post("/games/orquantix/new-game").get_json()
    assert 1 <= data["difficulty"] <= 5
    assert data["word_length"] > 0


# Fix pass — concurrence (review findings 1, 2, 3).
#
# Findings 1 et 2 dénoncent des mutations qui contournent state._lock :
# state.guesses.append() en dehors du verrou, et state.game_index += 1
# séparé de la mise à jour du reste de la manche. Les tests ci-dessous
# pilotent directement OrquantixState (pas seulement les routes HTTP) pour
# vérifier le contrat des nouvelles méthodes atomiques.


def test_session_refuses_when_not_ready(state):
    # Le seul frère sans garde de phase (finding 3) — le frontend distingue
    # "pas encore prêt" de "partie vide" via ce statut.
    state.phase = "loading"
    app = Flask(__name__)
    app.register_blueprint(build_blueprint(state))
    app.config["TESTING"] = True

    with app.test_client() as c:
        resp = c.get("/games/orquantix/session")
        assert resp.status_code == 503
        assert resp.get_json() == {"error": "not ready"}


def test_session_returns_payload_when_ready(client):
    data = client.get("/games/orquantix/session").get_json()
    assert data["difficulty"] == 2
    assert data["word_length"] == 5
    assert data["guesses"] == []
    assert data["resolved"] is False


def test_record_guess_against_stale_round_is_rejected(state):
    # Reproduction structurelle du finding 1 : une réponse calculée pour
    # l'ancienne manche (round_index capturé avant la transition) ne doit
    # jamais apparaître dans la liste de la nouvelle manche, ni avoir été
    # ajoutée à un objet que l'état a déjà abandonné. Une vraie course sur le
    # découpage exact "lecture de l'attribut, puis .append()" n'est pas
    # reproductible de façon fiable sans forcer artificiellement
    # l'ordonnancement des threads (il faudrait un sleep entre les deux
    # bytecodes) — on vérifie donc directement le contrat de la méthode.
    stale_round = state.game_index
    state.start_new_round(
        mystery_word="fleur",
        neighbours=state.neighbours,
        top1000=state.top1000,
        difficulty=1,
    )

    recorded = state.record_guess(stale_round, {"word": "chien", "win": False, "gave_up": False})

    assert recorded is False
    assert state.guesses == []


def test_record_guess_for_the_current_round_still_works(state):
    current_round = state.game_index
    recorded = state.record_guess(current_round, {"word": "chat", "win": False, "gave_up": False})

    assert recorded is True
    assert state.guesses == [{"word": "chat", "win": False, "gave_up": False}]


def test_start_new_round_bundles_index_and_round_fields(state):
    # Finding 2 : game_index et les champs de la manche doivent changer
    # comme un seul geste — on vérifie qu'un unique appel les met tous à
    # jour ensemble, et que la valeur renvoyée est le nouvel index.
    before_index = state.game_index
    new_index = state.start_new_round(
        mystery_word="fleur",
        neighbours=[("arbre", 0.5)],
        top1000={"arbre": 1},
        difficulty=4,
    )

    assert new_index == before_index + 1
    assert state.game_index == new_index
    assert state.mystery_word == "fleur"
    assert state.neighbours == [("arbre", 0.5)]
    assert state.top1000 == {"arbre": 1}
    assert state.difficulty == 4
    assert state.guesses == []


def test_start_new_round_increments_are_never_lost_under_concurrency(state):
    # Vraie course, reproductible de façon fiable : sans un verrou qui
    # couvre tout l'incrément, "x += 1" lu-modifié-écrit par de nombreux
    # threads perd des incréments sous contention (le GIL peut changer de
    # thread entre le LOAD et le STORE du bytecode). Le barrier aligne le
    # départ des threads pour maximiser la contention.
    threads_n = 25
    barrier = threading.Barrier(threads_n)

    def bump():
        barrier.wait()
        state.start_new_round(
            mystery_word="chat",
            neighbours=[],
            top1000={},
            difficulty=1,
        )

    threads = [threading.Thread(target=bump) for _ in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert state.game_index == threads_n
