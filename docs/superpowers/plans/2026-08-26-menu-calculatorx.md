# Menu PROCRASTINATOR and CalculatorX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ouvrir PROCRASTINATOR sur un menu extensible, conserver le chargement paresseux d’Orquantix et ajouter CalculatorX, un sprint de calcul mental classique de 120 secondes.

**Architecture:** Le paquet `games` construit un catalogue explicite de jeux montés ; `app.py` ne fait qu’enregistrer leurs blueprints et rendre leurs métadonnées. Orquantix encapsule son état et son chargement dans un runtime propre. CalculatorX produit côté serveur une réserve testable de 512 calculs, puis le navigateur gère sans latence la saisie, le score et une échéance absolue basée sur `performance.now()`.

**Tech Stack:** Python 3.12, Flask 3, dataclasses, JavaScript sans framework, HTML/Jinja, CSS, pytest 8.

**Spec:** `docs/superpowers/specs/2026-08-26-menu-calculatorx-design.md`

## Global Constraints

- Ne jamais placer une règle de mini-jeu dans `app.py` et ne jamais importer `app.py` depuis `games/`.
- Conserver `engine.progress(rank) == ((1001 - rank) / 1000) ** 3.4 * 100` dans le top 1000 et `0` hors top 1000.
- Conserver les humeurs de l’orque indexées sur le rang, pas sur la progression.
- Ne modifier aucun chemin d’indice qui contournerait `hints._eligible()` et `hint_words`.
- Ne modifier ni le nettoyage Littré ni ses invariants de non-fuite.
- Ne jamais recalculer une statistique sur les 31 548 mots à chaque proposition.
- Ne jamais muter directement `OrquantixState.guesses` ou `OrquantixState.game_index`.
- Le menu et CalculatorX ne doivent déclencher ni téléchargement ni chargement des ressources Orquantix.
- CalculatorX utilise exactement 120 secondes et 512 problèmes par session.
- Les plages CalculatorX sont inclusives : addition `2–100 + 2–100`, soustraction inverse, multiplication `2–12 × 2–100`, division inverse avec diviseur `2–12`.
- Aucun historique, réglage, classement, niveau, bonus ou compte dans cette version.
- Aucun `<script>` inline dans les nouveaux templates.
- Toute animation respecte `prefers-reduced-motion`; toute couche décorative non interactive utilise `pointer-events: none`.
- La vérification finale obligatoire est `python -m pytest -rs` avec `0 skipped`.
- Messages de commit et documentation en français ; code et identifiants en anglais.

---

## File Map

### Files created

- `games/registration.py` — types communs `GameMetadata` et `MountedGame`, sans règle de jeu.
- `games/catalog.py` — ordre explicite des jeux et construction du catalogue.
- `games/orquantix/runtime.py` — état, verrou et chargement paresseux d’Orquantix extraits de la coquille.
- `games/calculatorx/__init__.py` — métadonnées CalculatorX et construction de son inscription.
- `games/calculatorx/engine.py` — génération pure et sérialisation des calculs.
- `games/calculatorx/routes.py` — blueprint et création d’une session.
- `templates/index.html` — menu PROCRASTINATOR.
- `templates/calculatorx/index.html` — trois états accessibles : accueil, partie, résultat.
- `static/calculatorx/style.css` — identité « carnet quadrillé ».
- `static/calculatorx/game.js` — préparation, jeton de partie, saisie, score et chrono.
- `tests/orquantix/test_runtime.py` — transactions de chargement paresseux.
- `tests/calculatorx/__init__.py` — paquet de tests CalculatorX.
- `tests/calculatorx/test_engine.py` — règles arithmétiques déterministes.
- `tests/calculatorx/test_routes.py` — préfixe, template et contrat JSON.
- `tests/calculatorx/test_frontend.py` — contrat DOM, scripts externes et garde-fous du chrono.

### Files modified

- `app.py` — consomme le catalogue, monte les blueprints, rend le menu et préserve `/status`.
- `games/orquantix/__init__.py` — expose `build_game(data_dir)` en plus des symboles historiques utiles aux tests.
- `static/shell.css` — remplace la déclaration prospective par les styles réellement consommés du menu, tous préfixés par `.shell-menu`.
- `templates/orquantix/index.html` — ajoute « Retour aux jeux ».
- `static/orquantix/style.css` — style isolé du lien de retour, sans toucher aux filtres ni animations existants.
- `tests/test_app.py` — remplace l’attente de redirection par les assertions du menu/catalogue.
- `README.md` — documente le menu et CalculatorX.

---

### Task 1: Extraire le runtime paresseux d’Orquantix

**Files:**
- Create: `games/orquantix/runtime.py`
- Create: `tests/orquantix/test_runtime.py`
- Modify: `app.py`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: `OrquantixState`, `missing_files(data_dir)`, `download_all(state, data_dir)`, `load_resources(state, data_dir)`.
- Produces: `OrquantixRuntime(data_dir: Path)`, `.state`, `.started`, `.ensure_loaded() -> None`, `._load() -> None`.

- [ ] **Step 1: Vérifier la référence avant refactor**

Run: `python -m pytest -rs`

Expected: `117 passed`, `0 skipped`. Si les trois tests de données réelles sont ignorés, restaurer les ressources avant de modifier le code.

- [ ] **Step 2: Écrire les tests rouges du runtime**

Créer `tests/orquantix/test_runtime.py` :

```python
from pathlib import Path

import games.orquantix.runtime as runtime_module
from games.orquantix.runtime import OrquantixRuntime


class ImmediateThread:
    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


def test_ensure_loaded_runs_only_once(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr(runtime_module.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: [])
    monkeypatch.setattr(
        runtime_module,
        "load_resources",
        lambda state, data_dir: calls.append((state, data_dir)),
    )
    runtime = OrquantixRuntime(tmp_path)

    runtime.ensure_loaded()
    runtime.ensure_loaded()

    assert runtime.started is True
    assert calls == [(runtime.state, tmp_path)]


def test_load_downloads_before_loading_when_files_are_missing(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: ["Lexique383.tsv"])
    monkeypatch.setattr(
        runtime_module,
        "download_all",
        lambda state, data_dir: calls.append("download"),
    )
    monkeypatch.setattr(
        runtime_module,
        "load_resources",
        lambda state, data_dir: calls.append("load"),
    )

    OrquantixRuntime(tmp_path)._load()

    assert calls == ["download", "load"]


def test_load_failure_is_published_on_state(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: [])

    def fail(state, data_dir):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(runtime_module, "load_resources", fail)
    runtime = OrquantixRuntime(tmp_path)

    runtime._load()

    assert runtime.state.phase == "error"
    assert "kaboom" in runtime.state.detail
```

- [ ] **Step 3: Vérifier l’échec attendu**

Run: `python -m pytest tests/orquantix/test_runtime.py -v`

Expected: FAIL pendant la collecte avec `ModuleNotFoundError: No module named 'games.orquantix.runtime'`.

- [ ] **Step 4: Implémenter le runtime minimal**

Créer `games/orquantix/runtime.py` avec cette interface :

```python
from __future__ import annotations

import threading
from pathlib import Path

from downloader import download_all, missing_files
from games.orquantix import load_resources
from games.orquantix.state import OrquantixState


class OrquantixRuntime:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.state = OrquantixState()
        self._started = False
        self._lock = threading.Lock()

    @property
    def started(self) -> bool:
        with self._lock:
            return self._started

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self) -> None:
        try:
            if missing_files(self.data_dir):
                self.state.update(
                    phase="downloading",
                    progress=0,
                    detail="Téléchargement…",
                )
                download_all(self.state, self.data_dir)
            load_resources(self.state, self.data_dir)
        except Exception as exc:  # noqa: BLE001 — remonté à l’interface
            self.state.update(phase="error", detail=f"Erreur : {exc}")
```

Adapter provisoirement `Shell` dans `app.py` pour déléguer au runtime sans changer les routes :

```python
class Shell:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.orquantix_runtime = OrquantixRuntime(data_dir)
        self.orquantix = self.orquantix_runtime.state

    def ensure_loaded(self, game_id: str) -> None:
        if game_id != GAME_ID:
            raise KeyError(game_id)
        self.orquantix_runtime.ensure_loaded()
```

Supprimer de `app.py` les imports et méthodes désormais dupliqués : `threading`, `download_all`, `missing_files`, `load_resources`, `_started`, `_lock` et `_load`.

Dans `tests/test_app.py`, remplacer les tests unitaires de `_load` et `_started` par une assertion de délégation :

```python
import games.orquantix.runtime as runtime_module


@pytest.fixture
def shell(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: [])
    monkeypatch.setattr(runtime_module, "load_resources", lambda state, data_dir: None)
    return Shell(tmp_path)


def test_direct_orquantix_entry_starts_runtime(client, shell, monkeypatch):
    calls = []
    monkeypatch.setattr(shell.orquantix_runtime, "ensure_loaded", lambda: calls.append("load"))

    response = client.get("/games/orquantix/")

    assert response.status_code == 200
    assert calls == ["load"]
```

- [ ] **Step 5: Vérifier le runtime et la coquille**

Run: `python -m pytest tests/orquantix/test_runtime.py tests/test_app.py -v`

Expected: PASS.

- [ ] **Step 6: Committer l’extraction**

```bash
git add games/orquantix/runtime.py tests/orquantix/test_runtime.py app.py tests/test_app.py
git commit -m "refactor: isoler le chargement paresseux d’Orquantix"
```

---

### Task 2: Construire le catalogue et le menu extensible

**Files:**
- Create: `games/registration.py`
- Create: `games/catalog.py`
- Create: `templates/index.html`
- Modify: `games/orquantix/__init__.py`
- Modify: `app.py`
- Modify: `static/shell.css`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: `OrquantixRuntime(data_dir)` de Task 1.
- Produces: `GameMetadata`, `MountedGame`, `build_game(data_dir)`, `build_catalog(data_dir) -> tuple[MountedGame, ...]`, `Shell.get_game(game_id) -> MountedGame`.

- [ ] **Step 1: Écrire les tests rouges du catalogue et du menu**

Remplacer le test de redirection dans `tests/test_app.py` et ajouter les tests suivants :

```python
from games.orquantix.runtime import OrquantixRuntime


def test_home_renders_catalog_without_starting_orquantix(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"PROCRASTINATOR" in response.data
    assert b"Orquantix" in response.data
    assert b'href="/games/orquantix/"' in response.data
    assert client.get("/status").get_json()["phase"] == "idle"


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


def test_legacy_status_still_reports_orquantix_idle(client):
    response = client.get("/status")

    assert response.status_code == 200
    assert response.get_json()["phase"] == "idle"
```

- [ ] **Step 2: Vérifier l’échec attendu**

Run: `python -m pytest tests/test_app.py -v`

Expected: FAIL car `/` renvoie encore `302` et `templates/index.html` n’existe pas.

- [ ] **Step 3: Créer les types communs et l’inscription Orquantix**

Créer `games/registration.py` :

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from flask import Blueprint


@dataclass(frozen=True, slots=True)
class GameMetadata:
    id: str
    name: str
    description: str
    icon: str
    theme: str
    endpoint: str


@dataclass(frozen=True, slots=True)
class MountedGame:
    metadata: GameMetadata
    blueprint: Blueprint
    status: Callable[[], dict] | None = None
```

Ajouter à `games/orquantix/__init__.py` :

```python
def build_game(data_dir: Path) -> MountedGame:
    from games.orquantix.runtime import OrquantixRuntime
    from games.registration import GameMetadata, MountedGame

    runtime = OrquantixRuntime(data_dir)
    metadata = GameMetadata(
        id=GAME_ID,
        name=GAME_NAME,
        description="Trouve le mot secret par proximité sémantique.",
        icon="≋",
        theme="orquantix",
        endpoint="orquantix.index",
    )
    return MountedGame(
        metadata=metadata,
        blueprint=build_blueprint(runtime.state, on_load=runtime.ensure_loaded),
        status=runtime.state.snapshot,
    )
```

Ajouter `build_game` à `__all__` sans retirer les exports existants.

Créer `games/catalog.py` :

```python
from __future__ import annotations

from pathlib import Path

from games.orquantix import build_game as build_orquantix_game
from games.registration import MountedGame


def build_catalog(data_dir: Path) -> tuple[MountedGame, ...]:
    return (build_orquantix_game(data_dir),)
```

- [ ] **Step 4: Faire consommer le catalogue par la coquille**

Remplacer l’état spécifique de `Shell` et l’enregistrement direct dans `app.py` par :

```python
from games.catalog import build_catalog
from games.registration import MountedGame


class Shell:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.games = build_catalog(data_dir)
        self._games_by_id = {game.metadata.id: game for game in self.games}

    def get_game(self, game_id: str) -> MountedGame:
        return self._games_by_id[game_id]
```

Dans `create_app(shell)` :

```python
for game in shell.games:
    app.register_blueprint(game.blueprint)

@app.route("/")
def home():
    return render_template("index.html", games=shell.games)

@app.route("/status")
def status():
    game = shell.get_game("orquantix")
    if game.status is None:
        return jsonify({"error": "status unavailable"}), 404
    return jsonify(game.status())
```

Importer `render_template` et supprimer les imports Orquantix désormais inutiles de `app.py`.
Supprimer également `redirect` et `url_for` de l’import Flask puisqu’ils ne sont plus utilisés par la coquille.

- [ ] **Step 5: Créer le template du menu**

Créer `templates/index.html` sans gestionnaire inline :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PROCRASTINATOR</title>
  <link rel="stylesheet" href="/static/shell.css">
</head>
<body class="shell-menu">
  <main class="shell-main">
    <header class="shell-header">
      <p class="shell-eyebrow">La petite salle des jeux</p>
      <h1>PROCRASTINATOR</h1>
      <p class="shell-tagline">Des détours inutiles et indispensables.</p>
    </header>
    <section class="game-grid" aria-label="Mini-jeux disponibles">
      {% for game in games %}
      <a class="game-card game-card--{{ game.metadata.theme }}"
         href="{{ url_for(game.metadata.endpoint) }}">
        <span class="game-card-icon" aria-hidden="true">{{ game.metadata.icon }}</span>
        <span class="game-card-copy">
          <strong>{{ game.metadata.name }}</strong>
          <span>{{ game.metadata.description }}</span>
        </span>
        <span class="game-card-action">Ouvrir <span aria-hidden="true">→</span></span>
      </a>
      {% endfor %}
    </section>
  </main>
</body>
</html>
```

- [ ] **Step 6: Activer l’identité « atelier rétro » dans `static/shell.css`**

Conserver les tokens généraux utiles, supprimer le commentaire « NON CONSOMMÉ », et préfixer toutes les règles de menu pour qu’Orquantix garde son propre `body` :

```css
:root {
  --shell-paper: #f2eadc;
  --shell-paper-light: #fffaf0;
  --shell-ink: #27231d;
  --shell-muted: #756b5e;
  --shell-line: #c9bba5;
  --shell-rust: #c34b2b;
  --shell-sea: #173e48;
}

* { box-sizing: border-box; }

.shell-menu {
  margin: 0;
  min-height: 100vh;
  padding: clamp(24px, 6vw, 64px);
  color: var(--shell-ink);
  background:
    radial-gradient(circle at 12% 10%, rgba(195, 75, 43, .10), transparent 28%),
    var(--shell-paper);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.shell-main { width: min(980px, 100%); margin: 0 auto; }
.shell-eyebrow { color: var(--shell-rust); font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
.shell-header h1 { margin: 8px 0; font: 800 clamp(2.4rem, 8vw, 5.4rem)/.9 Georgia, serif; letter-spacing: -.055em; }
.shell-tagline { color: var(--shell-muted); font-size: 1.05rem; }
.game-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-top: 48px; }
.game-card { min-height: 220px; padding: 24px; display: flex; flex-direction: column; color: inherit; background: var(--shell-paper-light); border: 1px solid var(--shell-line); border-radius: 16px; box-shadow: 5px 6px 0 #d2c1a5; text-decoration: none; transition: transform .16s ease, box-shadow .16s ease; }
.game-card:hover, .game-card:focus-visible { transform: translate(-2px, -2px); box-shadow: 8px 9px 0 #d2c1a5; outline: 3px solid var(--shell-rust); outline-offset: 4px; }
.game-card-icon { font: 800 2.4rem/1 Georgia, serif; }
.game-card-copy { display: grid; gap: 7px; margin-top: 32px; }
.game-card-copy strong { font: 800 1.55rem/1 Georgia, serif; }
.game-card-copy span { color: var(--shell-muted); line-height: 1.45; }
.game-card-action { margin-top: auto; padding-top: 20px; color: var(--shell-rust); font-weight: 800; }
.game-card--orquantix { border-bottom: 5px solid var(--shell-sea); }

@media (prefers-reduced-motion: reduce) {
  .game-card { transition: none; }
}
```

- [ ] **Step 7: Vérifier le menu et les régressions de routes**

Run: `python -m pytest tests/test_app.py tests/orquantix/test_routes.py -v`

Expected: PASS, avec `/` à `200`, `/status` inchangé et Orquantix toujours sous son préfixe.

- [ ] **Step 8: Committer le catalogue et le menu**

```bash
git add games/registration.py games/catalog.py games/orquantix/__init__.py app.py templates/index.html static/shell.css tests/test_app.py
git commit -m "feat: ajouter le menu extensible des mini-jeux"
```

---

### Task 3: Implémenter le moteur pur de CalculatorX

**Files:**
- Create: `games/calculatorx/__init__.py`
- Create: `games/calculatorx/engine.py`
- Create: `tests/calculatorx/__init__.py`
- Create: `tests/calculatorx/test_engine.py`

**Interfaces:**
- Consumes: une source aléatoire fournissant `choice(sequence)` et `randint(minimum, maximum)`.
- Produces: `Problem`, `generate_problem(rng) -> Problem`, `generate_problems(count=512, rng=None) -> list[Problem]`, `DURATION_SECONDS`, `PROBLEM_COUNT`.

- [ ] **Step 1: Écrire les tests rouges des quatre opérations**

Créer `tests/calculatorx/__init__.py` vide et `tests/calculatorx/test_engine.py` :

```python
import random

import pytest

from games.calculatorx.engine import (
    PROBLEM_COUNT,
    Problem,
    generate_problem,
    generate_problems,
)


class StubRandom:
    def __init__(self, operation: str, integers: list[int]):
        self.operation = operation
        self.integers = iter(integers)

    def choice(self, values):
        assert tuple(values) == ("+", "−", "×", "÷")
        return self.operation

    def randint(self, minimum: int, maximum: int) -> int:
        value = next(self.integers)
        assert minimum <= value <= maximum
        return value


@pytest.mark.parametrize(
    ("operation", "integers", "expected"),
    [
        ("+", [2, 100], Problem(2, "+", 100, 102)),
        ("−", [37, 58], Problem(95, "−", 37, 58)),
        ("×", [12, 100], Problem(12, "×", 100, 1200)),
        ("÷", [7, 43], Problem(301, "÷", 7, 43)),
    ],
)
def test_generate_problem_matches_classic_rules(operation, integers, expected):
    assert generate_problem(StubRandom(operation, integers)) == expected


def test_problem_serializes_to_session_contract():
    problem = Problem(301, "÷", 7, 43)

    assert problem.as_dict() == {
        "left": 301,
        "operator": "÷",
        "right": 7,
        "answer": 43,
    }


def test_generate_problems_uses_fixed_default_size():
    problems = generate_problems()

    assert len(problems) == PROBLEM_COUNT == 512


def test_generated_divisions_are_always_exact():
    problems = generate_problems(count=2_000, rng=random.Random(42))
    divisions = [problem for problem in problems if problem.operator == "÷"]

    assert divisions
    assert all(problem.left % problem.right == 0 for problem in divisions)
    assert all(2 <= problem.right <= 12 for problem in divisions)


def test_generated_subtractions_are_strictly_positive():
    problems = generate_problems(count=2_000, rng=random.Random(42))
    subtractions = [problem for problem in problems if problem.operator == "−"]

    assert subtractions
    assert all(problem.answer > 0 for problem in subtractions)
```

- [ ] **Step 2: Vérifier l’échec attendu**

Run: `python -m pytest tests/calculatorx/test_engine.py -v`

Expected: FAIL pendant la collecte avec `ModuleNotFoundError: No module named 'games.calculatorx'`.

- [ ] **Step 3: Implémenter le moteur minimal**

Créer `games/calculatorx/__init__.py` vide et `games/calculatorx/engine.py` :

```python
from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Protocol, TypeVar

DURATION_SECONDS = 120
PROBLEM_COUNT = 512
OPERATIONS = ("+", "−", "×", "÷")
T = TypeVar("T")


class RandomSource(Protocol):
    def choice(self, values: tuple[T, ...]) -> T:
        raise NotImplementedError

    def randint(self, minimum: int, maximum: int) -> int:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Problem:
    left: int
    operator: str
    right: int
    answer: int

    def as_dict(self) -> dict[str, int | str]:
        return asdict(self)


def generate_problem(rng: RandomSource) -> Problem:
    operation = rng.choice(OPERATIONS)
    if operation in ("+", "−"):
        first = rng.randint(2, 100)
        second = rng.randint(2, 100)
        if operation == "+":
            return Problem(first, operation, second, first + second)
        return Problem(first + second, operation, first, second)

    small = rng.randint(2, 12)
    large = rng.randint(2, 100)
    if operation == "×":
        return Problem(small, operation, large, small * large)
    return Problem(small * large, operation, small, large)


def generate_problems(
    count: int = PROBLEM_COUNT,
    rng: RandomSource | None = None,
) -> list[Problem]:
    source = rng if rng is not None else random.SystemRandom()
    return [generate_problem(source) for _ in range(count)]
```

- [ ] **Step 4: Vérifier le moteur**

Run: `python -m pytest tests/calculatorx/test_engine.py -v`

Expected: PASS.

- [ ] **Step 5: Committer le moteur**

```bash
git add games/calculatorx/__init__.py games/calculatorx/engine.py tests/calculatorx/__init__.py tests/calculatorx/test_engine.py
git commit -m "feat: ajouter le moteur classique de CalculatorX"
```

---

### Task 4: Ajouter le blueprint et le contrat de session CalculatorX

**Files:**
- Modify: `games/calculatorx/__init__.py`
- Create: `games/calculatorx/routes.py`
- Create: `tests/calculatorx/test_routes.py`
- Modify: `games/catalog.py`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: `GameMetadata`, `MountedGame`, `Problem.as_dict()`, `generate_problems(count)`.
- Produces: `build_blueprint(problem_factory=generate_problems)`, `build_game(data_dir)`, `POST /games/calculatorx/session`.

- [ ] **Step 1: Écrire les tests rouges du blueprint**

Créer `tests/calculatorx/test_routes.py` :

```python
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
```

Ajouter dans `tests/test_app.py` :

```python
def test_home_lists_orquantix_then_calculatorx(client):
    page = client.get("/").data.decode()

    assert page.index("Orquantix") < page.index("CalculatorX")
    assert 'href="/games/calculatorx/"' in page
```

- [ ] **Step 2: Vérifier les échecs attendus**

Run: `python -m pytest tests/calculatorx/test_routes.py tests/test_app.py -v`

Expected: FAIL pendant l’import de `games.calculatorx.routes` et FAIL car CalculatorX n’est pas encore au catalogue.

- [ ] **Step 3: Implémenter le blueprint**

Créer `games/calculatorx/routes.py` :

```python
from __future__ import annotations

from collections.abc import Callable

from flask import Blueprint, jsonify, render_template

from games.calculatorx.engine import (
    DURATION_SECONDS,
    PROBLEM_COUNT,
    Problem,
    generate_problems,
)

BLUEPRINT_NAME = "calculatorx"
URL_PREFIX = "/games/calculatorx"
ProblemFactory = Callable[[int], list[Problem]]


def build_blueprint(problem_factory: ProblemFactory = generate_problems) -> Blueprint:
    blueprint = Blueprint(BLUEPRINT_NAME, __name__, url_prefix=URL_PREFIX)

    @blueprint.get("/")
    def index():
        return render_template("calculatorx/index.html")

    @blueprint.post("/session")
    def session():
        problems = problem_factory(PROBLEM_COUNT)
        return jsonify(
            duration_seconds=DURATION_SECONDS,
            problems=[problem.as_dict() for problem in problems],
        )

    return blueprint
```

- [ ] **Step 4: Inscrire CalculatorX dans le catalogue**

Remplir `games/calculatorx/__init__.py` :

```python
from __future__ import annotations

from pathlib import Path

from games.calculatorx.routes import build_blueprint
from games.registration import GameMetadata, MountedGame

GAME_ID = "calculatorx"
GAME_NAME = "CalculatorX"


def build_game(data_dir: Path) -> MountedGame:
    del data_dir
    return MountedGame(
        metadata=GameMetadata(
            id=GAME_ID,
            name=GAME_NAME,
            description="120 secondes de calcul mental.",
            icon="±",
            theme="calculatorx",
            endpoint="calculatorx.index",
        ),
        blueprint=build_blueprint(),
    )


__all__ = ["GAME_ID", "GAME_NAME", "build_game"]
```

Modifier `games/catalog.py` :

```python
from games.calculatorx import build_game as build_calculatorx_game


def build_catalog(data_dir: Path) -> tuple[MountedGame, ...]:
    return (
        build_orquantix_game(data_dir),
        build_calculatorx_game(data_dir),
    )
```

Ajouter dans `static/shell.css` l’accent de carte :

```css
.game-card--calculatorx { border-bottom: 5px solid var(--shell-rust); }
```

- [ ] **Step 5: Créer un template minimal pour rendre la route testable**

Créer `templates/calculatorx/index.html` dans une version minimale sans asset ; Task 5 remplacera cette page par l’interface complète et créera ses assets :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CalculatorX</title>
</head>
<body>
  <main id="calculatorxApp"><h1>CalculatorX</h1></main>
</body>
</html>
```

- [ ] **Step 6: Vérifier les routes et le catalogue**

Run: `python -m pytest tests/calculatorx/test_engine.py tests/calculatorx/test_routes.py tests/test_app.py -v`

Expected: PASS.

- [ ] **Step 7: Committer l’API et l’inscription**

```bash
git add games/calculatorx games/catalog.py templates/calculatorx/index.html tests/calculatorx/test_routes.py tests/test_app.py static/shell.css
git commit -m "feat: exposer les sessions de CalculatorX"
```

---

### Task 5: Construire l’interface jouable CalculatorX

**Files:**
- Create: `tests/calculatorx/test_frontend.py`
- Create: `static/calculatorx/style.css`
- Create: `static/calculatorx/game.js`
- Modify: `templates/calculatorx/index.html`

**Interfaces:**
- Consumes: `POST /games/calculatorx/session` avec `duration_seconds` et `problems`.
- Produces: IDs DOM `welcomePanel`, `gamePanel`, `resultPanel`, `startButton`, `retryButton`, `answerInput`, `problemText`, `timerValue`, `scoreValue`, `finalScore`, `errorMessage`.

- [ ] **Step 1: Écrire les tests rouges du contrat frontend**

Créer `tests/calculatorx/test_frontend.py` :

```python
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_template_exposes_three_panels_and_external_script():
    html = (ROOT / "templates/calculatorx/index.html").read_text()

    for element_id in (
        "welcomePanel",
        "gamePanel",
        "resultPanel",
        "startButton",
        "retryButton",
        "answerInput",
        "problemText",
        "timerValue",
        "scoreValue",
        "finalScore",
        "errorMessage",
    ):
        assert f'id="{element_id}"' in html
    assert '<script src="/static/calculatorx/game.js"></script>' in html
    assert "<script>" not in html


def test_game_script_uses_absolute_deadline_and_round_token():
    script = (ROOT / "static/calculatorx/game.js").read_text()

    assert "performance.now()" in script
    assert "deadline" in script
    assert "roundToken" in script
    assert "requestAnimationFrame" in script
    assert "fetch('/games/calculatorx/session'" in script


def test_styles_include_reduced_motion_fallback():
    css = (ROOT / "static/calculatorx/style.css").read_text()

    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation: none" in css
```

- [ ] **Step 2: Vérifier l’échec attendu**

Run: `python -m pytest tests/calculatorx/test_frontend.py -v`

Expected: FAIL car le template minimal ne contient pas les panneaux et les assets sont vides.

- [ ] **Step 3: Écrire le template accessible définitif**

Remplacer `templates/calculatorx/index.html` par une page sans gestionnaire inline contenant exactement :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CalculatorX</title>
  <link rel="stylesheet" href="/static/calculatorx/style.css">
</head>
<body>
  <main class="calculatorx-shell" id="calculatorxApp">
    <nav class="calculatorx-nav" aria-label="Navigation du jeu">
      <a href="{{ url_for('home') }}">← Retour aux jeux</a>
      <span>Calcul mental</span>
    </nav>

    <section class="panel welcome-panel" id="welcomePanel" aria-labelledby="welcomeTitle">
      <div class="calculatorx-mark" aria-hidden="true">×÷</div>
      <p class="eyebrow">Sprint arithmétique</p>
      <h1 id="welcomeTitle">CalculatorX</h1>
      <p>Deux minutes. Une réponse après l’autre.</p>
      <div class="rule-chips" aria-label="Règles de la partie">
        <span>120 secondes</span><span>+ − × ÷</span>
      </div>
      <button class="primary-button" id="startButton" type="button">C’est parti !</button>
      <p class="error-message" id="errorMessage" role="alert" hidden></p>
    </section>

    <section class="panel game-panel" id="gamePanel" aria-label="Partie en cours" hidden>
      <header class="game-stats">
        <p>Temps <strong id="timerValue">120</strong></p>
        <p>Score <strong id="scoreValue">0</strong></p>
      </header>
      <p class="problem-text" id="problemText" aria-live="polite"></p>
      <label class="answer-label" for="answerInput">Ta réponse</label>
      <input id="answerInput" inputmode="numeric" autocomplete="off" pattern="[0-9]*" disabled>
    </section>

    <section class="panel result-panel" id="resultPanel" aria-labelledby="resultTitle" hidden>
      <p class="eyebrow">Temps écoulé</p>
      <h2 id="resultTitle">Score : <strong id="finalScore">0</strong></h2>
      <button class="primary-button" id="retryButton" type="button">Rejouer</button>
      <a class="secondary-link" href="{{ url_for('home') }}">Retour au menu</a>
    </section>
  </main>
  <script src="/static/calculatorx/game.js"></script>
</body>
</html>
```

- [ ] **Step 4: Implémenter le contrôleur de partie**

Remplir `static/calculatorx/game.js` avec une IIFE sans variable globale. Les fonctions et gardes doivent suivre ce corps :

```javascript
(() => {
  'use strict';

  const ui = {
    welcome: document.getElementById('welcomePanel'),
    game: document.getElementById('gamePanel'),
    result: document.getElementById('resultPanel'),
    start: document.getElementById('startButton'),
    retry: document.getElementById('retryButton'),
    input: document.getElementById('answerInput'),
    problem: document.getElementById('problemText'),
    timer: document.getElementById('timerValue'),
    score: document.getElementById('scoreValue'),
    finalScore: document.getElementById('finalScore'),
    error: document.getElementById('errorMessage'),
  };

  const state = {
    roundToken: 0,
    preparing: false,
    problems: [],
    problemIndex: 0,
    score: 0,
    deadline: 0,
    frameId: 0,
    playing: false,
  };

  function showPanel(panel) {
    ui.welcome.hidden = panel !== ui.welcome;
    ui.game.hidden = panel !== ui.game;
    ui.result.hidden = panel !== ui.result;
  }

  function setPreparing(preparing) {
    state.preparing = preparing;
    ui.start.disabled = preparing;
    ui.retry.disabled = preparing;
    ui.start.textContent = preparing ? 'Préparation…' : 'C’est parti !';
    ui.retry.textContent = preparing ? 'Préparation…' : 'Rejouer';
  }

  function isProblem(problem) {
    return Number.isInteger(problem.left)
      && ['+', '−', '×', '÷'].includes(problem.operator)
      && Number.isInteger(problem.right)
      && Number.isInteger(problem.answer);
  }

  function isSession(payload) {
    return payload
      && payload.duration_seconds === 120
      && Array.isArray(payload.problems)
      && payload.problems.length > 0
      && payload.problems.every(isProblem);
  }

  function renderProblem() {
    const problem = state.problems[state.problemIndex];
    ui.problem.textContent = `${problem.left} ${problem.operator} ${problem.right} =`;
    ui.input.value = '';
    ui.input.focus();
  }

  function finishRound(token) {
    if (token !== state.roundToken || !state.playing) return;
    state.playing = false;
    cancelAnimationFrame(state.frameId);
    ui.input.disabled = true;
    ui.timer.textContent = '0';
    ui.finalScore.textContent = String(state.score);
    showPanel(ui.result);
    ui.retry.focus();
  }

  function updateClock(token) {
    if (token !== state.roundToken || !state.playing) return;
    const remaining = Math.max(0, state.deadline - performance.now());
    ui.timer.textContent = String(Math.ceil(remaining / 1000));
    if (remaining <= 0) {
      finishRound(token);
      return;
    }
    state.frameId = requestAnimationFrame(() => updateClock(token));
  }

  function beginRound(payload, token) {
    if (token !== state.roundToken) return;
    state.problems = payload.problems;
    state.problemIndex = 0;
    state.score = 0;
    state.deadline = performance.now() + payload.duration_seconds * 1000;
    state.playing = true;
    ui.score.textContent = '0';
    ui.timer.textContent = String(payload.duration_seconds);
    ui.input.disabled = false;
    setPreparing(false);
    showPanel(ui.game);
    renderProblem();
    updateClock(token);
  }

  function showPreparationError(token) {
    if (token !== state.roundToken) return;
    setPreparing(false);
    showPanel(ui.welcome);
    ui.error.textContent = 'Impossible de préparer la partie. Réessaie.';
    ui.error.hidden = false;
    ui.start.focus();
  }

  function prepareRound() {
    if (state.preparing) return;
    const token = ++state.roundToken;
    state.playing = false;
    cancelAnimationFrame(state.frameId);
    ui.error.hidden = true;
    setPreparing(true);
    fetch('/games/calculatorx/session', {method: 'POST'})
      .then((response) => {
        if (!response.ok) throw new Error('session unavailable');
        return response.json();
      })
      .then((payload) => {
        if (!isSession(payload)) throw new Error('invalid session');
        beginRound(payload, token);
      })
      .catch(() => showPreparationError(token));
  }

  function handleAnswer() {
    if (!state.playing) return;
    const token = state.roundToken;
    if (performance.now() >= state.deadline) {
      finishRound(token);
      return;
    }
    if (!/^\d+$/.test(ui.input.value)) return;
    const current = state.problems[state.problemIndex];
    if (Number(ui.input.value) !== current.answer) return;
    state.score += 1;
    state.problemIndex += 1;
    ui.score.textContent = String(state.score);
    if (state.problemIndex >= state.problems.length) {
      finishRound(token);
      return;
    }
    renderProblem();
  }

  ui.start.addEventListener('click', prepareRound);
  ui.retry.addEventListener('click', prepareRound);
  ui.input.addEventListener('input', handleAnswer);
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || state.playing || state.preparing) return;
    if (ui.welcome.hidden && ui.result.hidden) return;
    event.preventDefault();
    prepareRound();
  });
})();
```

- [ ] **Step 5: Appliquer le style carnet quadrillé**

Utiliser le CSS complet suivant pour la maquette C :

```css
:root {
  --paper: #f4eddd;
  --paper-light: #fffaf0;
  --ink: #27231d;
  --muted: #756b5e;
  --grid-blue: rgba(49, 113, 139, .12);
  --rust: #c64d2d;
  --rust-dark: #85321e;
  --slate: #29343b;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  background-color: var(--paper);
  background-image:
    linear-gradient(var(--grid-blue) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-blue) 1px, transparent 1px);
  background-size: 24px 24px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

button, input { font: inherit; }
.calculatorx-shell { width: min(720px, calc(100% - 32px)); min-height: 100vh; margin: 0 auto; padding: 24px 0 48px; }
.calculatorx-nav { display: flex; justify-content: space-between; gap: 16px; font-size: .84rem; font-weight: 800; text-transform: uppercase; letter-spacing: .09em; }
.calculatorx-nav a { color: var(--rust); }
.panel { margin-top: clamp(48px, 12vh, 120px); text-align: center; }
.calculatorx-mark { width: 76px; height: 76px; margin: 0 auto 24px; display: grid; place-items: center; color: var(--paper-light); background: var(--slate); border-radius: 14px; box-shadow: 5px 5px 0 var(--rust); font: 800 1.8rem/1 Georgia, serif; transform: rotate(2deg); }
.eyebrow { color: var(--rust); font-weight: 850; letter-spacing: .13em; text-transform: uppercase; }
h1, h2 { margin: 10px 0; font: 800 clamp(2.8rem, 10vw, 5.6rem)/.92 Georgia, serif; letter-spacing: -.055em; }
.rule-chips { display: flex; justify-content: center; flex-wrap: wrap; gap: 8px; margin: 28px 0; }
.rule-chips span { padding: 7px 12px; background: rgba(255, 250, 240, .75); border: 1px solid #cbbca4; border-radius: 999px; font-weight: 750; }
.primary-button { padding: 13px 24px; color: var(--paper-light); background: var(--rust); border: 0; border-radius: 999px; box-shadow: 0 5px 0 var(--rust-dark); cursor: pointer; font-weight: 850; transition: transform .15s ease, box-shadow .15s ease; }
.primary-button:hover { transform: translateY(-1px); box-shadow: 0 6px 0 var(--rust-dark); }
.primary-button:focus-visible { outline: 3px solid var(--slate); outline-offset: 4px; }
.primary-button:disabled { opacity: .58; cursor: wait; }
.error-message { color: #9f2417; font-weight: 700; }
.game-stats { display: flex; justify-content: space-between; padding: 16px 20px; background: rgba(255, 250, 240, .78); border: 1px solid #cbbca4; border-radius: 14px; }
.game-stats p { margin: 0; }
.game-stats strong { font-variant-numeric: tabular-nums; }
.problem-text { margin: clamp(54px, 12vh, 96px) 0 30px; font: 800 clamp(3.2rem, 15vw, 7rem)/1 Georgia, serif; }
.answer-label { display: block; margin-bottom: 9px; color: var(--muted); font-weight: 750; }
#answerInput { width: min(320px, 100%); padding: 12px 18px; color: var(--ink); background: var(--paper-light); border: 2px solid var(--slate); border-radius: 10px; outline: 0; text-align: center; font-size: 2rem; font-variant-numeric: tabular-nums; }
#answerInput:focus { border-color: var(--rust); box-shadow: 0 0 0 4px rgba(198, 77, 45, .18); }
.secondary-link { display: block; width: max-content; margin: 22px auto 0; color: var(--rust-dark); font-weight: 750; }
.secondary-link:focus-visible, .calculatorx-nav a:focus-visible { outline: 3px solid var(--rust); outline-offset: 4px; }

@media (max-width: 520px) {
  .calculatorx-shell { width: min(100% - 22px, 720px); }
  .calculatorx-nav { font-size: .7rem; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
}
```

Ne pas ajouter de couche décorative cliquable. Si une texture supplémentaire est ajoutée avec un pseudo-élément, lui imposer `pointer-events: none`.

- [ ] **Step 6: Vérifier le contrat frontend et toutes les routes CalculatorX**

Run: `python -m pytest tests/calculatorx -v`

Expected: PASS.

- [ ] **Step 7: Committer l’interface jouable**

```bash
git add templates/calculatorx/index.html static/calculatorx/style.css static/calculatorx/game.js tests/calculatorx/test_frontend.py
git commit -m "feat: rendre CalculatorX jouable au clavier"
```

---

### Task 6: Ajouter le retour au menu depuis Orquantix

**Files:**
- Modify: `templates/orquantix/index.html`
- Modify: `static/orquantix/style.css`
- Modify: `tests/orquantix/test_routes.py`

**Interfaces:**
- Consumes: endpoint Flask `home`.
- Produces: lien `.back-to-games` visible sur l’écran de chargement comme sur le plateau.

- [ ] **Step 1: Écrire le test rouge de navigation**

Ajouter à `tests/orquantix/test_routes.py` :

```python
@pytest.fixture
def client(state):
    app = Flask(__name__)

    @app.get("/")
    def home():
        return "menu"

    app.register_blueprint(build_blueprint(state))
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_index_links_back_to_games(client):
    page = client.get("/games/orquantix/").data.decode()

    assert 'class="back-to-games"' in page
    assert 'href="/"' in page
    assert "Retour aux jeux" in page
```

Cette fixture remplace la fixture `client` existante du fichier ; l’endpoint hôte `home` permet au blueprint isolé de résoudre `url_for('home')`, comme il le fera dans l’application réelle.

- [ ] **Step 2: Vérifier l’échec attendu**

Run: `python -m pytest tests/orquantix/test_routes.py::test_index_links_back_to_games -v`

Expected: FAIL car `.back-to-games` n’existe pas encore.

- [ ] **Step 3: Ajouter le lien hors des couches décoratives**

Dans `templates/orquantix/index.html`, immédiatement après `<body>` et avant `.scene-layer` :

```html
  <a class="back-to-games" href="{{ url_for('home') }}">← Retour aux jeux</a>
```

Dans `static/orquantix/style.css`, ajouter une règle sans `filter` et sans animation :

```css
.back-to-games {
  position: relative;
  z-index: 4;
  display: block;
  width: max-content;
  margin: 18px 0 0 20px;
  padding: .45rem .7rem;
  color: var(--abysse-cyan-dim);
  background: rgba(6, 13, 24, .72);
  border: 1px solid rgba(127, 227, 240, .24);
  border-radius: 999px;
  text-decoration: none;
  font-size: .8rem;
  font-weight: 700;
}

.back-to-games:hover,
.back-to-games:focus-visible {
  color: var(--abysse-cyan);
  border-color: var(--abysse-cyan);
  outline: none;
}
```

- [ ] **Step 4: Vérifier la navigation et les invariants front Orquantix**

Run: `python -m pytest tests/orquantix/test_routes.py tests/orquantix/test_orca.py -v`

Expected: PASS.

- [ ] **Step 5: Committer le retour au menu**

```bash
git add templates/orquantix/index.html static/orquantix/style.css tests/orquantix/test_routes.py
git commit -m "feat: relier Orquantix au menu des jeux"
```

---

### Task 7: Documenter et vérifier le parcours complet

**Files:**
- Modify: `README.md`
- Modify only if visual verification finds a defect: `static/shell.css`, `static/calculatorx/style.css`, `static/calculatorx/game.js`, `templates/index.html`, `templates/calculatorx/index.html`

**Interfaces:**
- Consumes: l’application complète des Tasks 1–6.
- Produces: documentation à jour et preuves de non-régression.

- [ ] **Step 1: Mettre à jour le README**

Remplacer la formulation indiquant que la fenêtre s’ouvre directement sur Orquantix et ajouter une section courte :

```markdown
Au lancement, PROCRASTINATOR ouvre son menu de mini-jeux. Orquantix ne charge
ses ressources qu’au moment où sa carte est ouverte.

## CalculatorX

Résoudre le plus de calculs possible en 120 secondes. Le mode classique
mélange additions, soustractions, multiplications et divisions exactes ;
la partie se joue entièrement au clavier après son lancement.
```

- [ ] **Step 2: Lancer les tests ciblés de la nouvelle architecture**

Run: `python -m pytest tests/test_app.py tests/calculatorx tests/orquantix/test_runtime.py tests/orquantix/test_routes.py -rs`

Expected: PASS, `0 skipped`.

- [ ] **Step 3: Lancer la suite complète sur les données réelles**

Run: `python -m pytest -rs`

Expected: tous les tests PASS et `0 skipped`. Ne pas accepter un résultat où les tests Littré ou vocabulaire réel sont ignorés.

- [ ] **Step 4: Vérifier les erreurs statiques**

Run: `git diff --check`

Expected: aucune sortie.

Run: `python -m compileall -q app.py games`

Expected: code de sortie `0`.

- [ ] **Step 5: Vérifier visuellement en mode design**

Run: `python main.py --design`

Vérifier dans la fenêtre navigateur, à 480×600 puis 720×900 :

1. `/` affiche l’atelier rétro avec Orquantix puis CalculatorX.
2. Cliquer CalculatorX ouvre son accueil sans démarrer le chrono.
3. `Entrée` prépare la partie, affiche `120`, focalise la saisie et mélange les quatre opérations.
4. Une réponse fausse reste dans le champ ; une réponse correcte incrémente le score et avance sans attente.
5. Une session dont l’échéance est dépassée affiche le résultat et refuse tout point tardif.
6. « Rejouer » crée une nouvelle session ; « Retour au menu » revient à `/`.
7. Ouvrir Orquantix déclenche son chargement, et son lien revient au menu.
8. Avec la réduction des animations simulée, aucun contenu ne disparaît et aucune animation ne continue.

Si une correction visuelle est nécessaire, ajouter d’abord une assertion à `tests/calculatorx/test_frontend.py` lorsqu’elle peut être exprimée de façon stable, appliquer le correctif minimal, puis relancer `python -m pytest tests/calculatorx -v`.

- [ ] **Step 6: Rejouer la suite complète après toute correction visuelle**

Run: `python -m pytest -rs`

Expected: tous les tests PASS, `0 skipped`.

- [ ] **Step 7: Committer la documentation et les éventuels ajustements vérifiés**

```bash
git add README.md static/shell.css static/calculatorx/style.css static/calculatorx/game.js templates/index.html templates/calculatorx/index.html tests/calculatorx/test_frontend.py
git commit -m "docs: présenter le menu et CalculatorX"
```

- [ ] **Step 8: Vérifier l’état final de la branche**

Run: `git status --short`

Expected: aucune sortie.

Run: `git log --oneline -7`

Expected: les commits des Tasks 1–7 sont présents dans l’ordre, sans fichier étranger au périmètre.
