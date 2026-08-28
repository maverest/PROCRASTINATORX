# CalculatorX V2 Local Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer les modes Classique, Personnalisé et Constance avec interface de vitesse, chronométrage par réponse, graphique, statistiques finales et historique local, sans dépendance réseau.

**Architecture:** Python reste la source de vérité pour les configurations, la génération, les agrégats et SQLite. Le navigateur conserve le chemin critique de saisie et de chronométrage avec `performance.now()`, puis transmet le résumé de fin à Flask. Les composants du futur classement sont préparés dans le schéma local, mais aucun appel distant n’est ajouté dans ce plan.

**Tech Stack:** Python 3.12, Flask, SQLite standard library, JavaScript sans bundler, HTML/CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-08-28-calculatorx-v2-design.md`

## Global Constraints

- Préserver les règles exactes du Classique : 120 s, addition `2–100 × 2–100`, multiplication `2–12 × 2–100`, soustraction et division inversées.
- Personnalisé : durée entière `1–3600`, bornes entières `0–9999`, au moins une opération, minimum inférieur ou égal au maximum.
- Constance : 120 s fixes, quatre opérations uniformes, calculs triviaux définis par la spécification, aucune division par zéro.
- La saisie correcte avance automatiquement sans Entrée ; le focus ne quitte jamais le champ pendant la partie.
- L’interface de partie contient le minimum de texte, une projection discrète `≈N`, un bouton Stop rouge `■` et une légende graphique `+ − × ÷`.
- Les statistiques détaillées ne survivent pas à la séance suivante ; SQLite conserve seulement le résumé de chaque séance.
- `app.py` ne reçoit aucune règle CalculatorX et Orquantix n’est pas modifié.
- Tous les tests finaux s’exécutent avec `python -m pytest -rs` et doivent afficher `0 skipped`.

## File Structure

- Modify: `games/calculatorx/engine.py` — configurations et trois générateurs purs.
- Create: `games/calculatorx/statistics.py` — projection et agrégats par opération.
- Create: `games/calculatorx/storage.py` — schéma SQLite et historique local.
- Modify: `games/calculatorx/routes.py` — sessions configurées, résultats et historique.
- Modify: `games/calculatorx/__init__.py` — injection du chemin de données dans le jeu.
- Modify: `templates/calculatorx/index.html` — accueil, réglages, partie, résultat et historique.
- Create: `static/calculatorx/chart.js` — rendu SVG du graphique chronologique.
- Modify: `static/calculatorx/game.js` — machine d’état, saisie, chrono, Stop et navigation locale.
- Modify: `static/calculatorx/style.css` — identité sombre, compacte, responsive et accessible.
- Modify/Create: `tests/calculatorx/test_engine.py`, `test_statistics.py`, `test_storage.py`, `test_routes.py`, `test_frontend.py`.
- Modify: `README.md` — commandes de lancement et description des trois modes, après conservation des changements déjà présents.

---

### Task 1: Configuration et moteur Classique/Personnalisé

**Files:**
- Modify: `games/calculatorx/engine.py`
- Modify: `tests/calculatorx/test_engine.py`

**Interfaces:**
- Produces: `NumberRange(minimum: int, maximum: int)`.
- Produces: `GameConfig(mode, duration_seconds, operations, addition_left, addition_right, multiplication_left, multiplication_right)`.
- Produces: `classic_config() -> GameConfig`.
- Produces: `parse_config(payload: object) -> GameConfig`, levant `ConfigError(message, field)`.
- Produces: `generate_problem(config: GameConfig, rng: RandomSource) -> Problem`.
- Produces: `generate_problems(config: GameConfig, count: int = 512, rng: RandomSource | None = None) -> list[Problem]`.

- [ ] **Step 1: Écrire les tests de configuration qui échouent**

```python
def valid_custom_payload(**overrides):
    payload = {
        "mode": "custom",
        "duration_seconds": 45,
        "operations": ["+", "−", "×", "÷"],
        "addition": {
            "left": {"minimum": 2, "maximum": 100},
            "right": {"minimum": 2, "maximum": 100},
        },
        "multiplication": {
            "left": {"minimum": 2, "maximum": 12},
            "right": {"minimum": 2, "maximum": 100},
        },
    }
    payload.update(overrides)
    return payload


def test_classic_config_matches_zetamac():
    config = classic_config()
    assert config.duration_seconds == 120
    assert config.operations == ("+", "−", "×", "÷")
    assert config.addition_left == NumberRange(2, 100)
    assert config.multiplication_left == NumberRange(2, 12)


@pytest.mark.parametrize("duration", [0, 3601, 1.5, "120"])
def test_custom_duration_is_bounded_integer(duration):
    payload = valid_custom_payload(duration_seconds=duration)
    with pytest.raises(ConfigError) as error:
        parse_config(payload)
    assert error.value.field == "duration_seconds"


def test_custom_requires_one_operation():
    with pytest.raises(ConfigError) as error:
        parse_config(valid_custom_payload(operations=[]))
    assert error.value.field == "operations"
```

- [ ] **Step 2: Vérifier l’échec des nouveaux tests**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_engine.py -v`

Expected: FAIL sur les imports `NumberRange`, `GameConfig`, `ConfigError`, `classic_config` et `parse_config`.

- [ ] **Step 3: Implémenter les types et la validation minimale**

```python
@dataclass(frozen=True, slots=True)
class NumberRange:
    minimum: int
    maximum: int


@dataclass(frozen=True, slots=True)
class GameConfig:
    mode: str
    duration_seconds: int
    operations: tuple[str, ...]
    addition_left: NumberRange
    addition_right: NumberRange
    multiplication_left: NumberRange
    multiplication_right: NumberRange


class ConfigError(ValueError):
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.field = field
```

`parse_config` accepte `{"mode": "classic"}` ou le contrat personnalisé de la spec. Il refuse les booléens comme entiers, les clés manquantes, les opérations inconnues, les bornes hors `0–9999`, les minima supérieurs aux maxima et une plage de diviseur réduite à zéro.

- [ ] **Step 4: Écrire les tests de génération personnalisée qui échouent**

```python
def custom_config(*, operations, addition_left=(2, 100), addition_right=(2, 100),
                  multiplication_left=(2, 12), multiplication_right=(2, 100)):
    return parse_config(valid_custom_payload(
        operations=list(operations),
        addition={
            "left": {"minimum": addition_left[0], "maximum": addition_left[1]},
            "right": {"minimum": addition_right[0], "maximum": addition_right[1]},
        },
        multiplication={
            "left": {"minimum": multiplication_left[0], "maximum": multiplication_left[1]},
            "right": {"minimum": multiplication_right[0], "maximum": multiplication_right[1]},
        },
    ))


def test_custom_addition_uses_both_operand_ranges():
    config = custom_config(operations=("+",), addition_left=(7, 7), addition_right=(90, 90))
    assert generate_problem(config, random.Random(1)) == Problem(7, "+", 90, 97)


def test_custom_division_never_uses_zero_divisor():
    config = custom_config(
        operations=("÷",),
        multiplication_left=(0, 2),
        multiplication_right=(8, 8),
    )
    problems = generate_problems(config, count=200, rng=random.Random(4))
    assert all(p.operator == "÷" and p.right != 0 for p in problems)
    assert all(p.left % p.right == 0 for p in problems)
```

- [ ] **Step 5: Adapter le générateur aux configurations**

Utiliser `rng.choice(config.operations)` puis les quatre plages de `GameConfig`. Pour `−`, afficher `(a + b) − a`; pour `÷`, tirer un premier facteur non nul et afficher `(a × b) ÷ a`. Conserver `Problem.as_dict()` inchangé.

- [ ] **Step 6: Exécuter les tests du moteur**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_engine.py -v`

Expected: PASS pour les anciens tests classiques et les nouveaux tests personnalisés.

- [ ] **Step 7: Commit**

```bash
git add games/calculatorx/engine.py tests/calculatorx/test_engine.py
git commit -m "feat: configurer les règles de CalculatorX"
```

---

### Task 2: Générateur Constance

**Files:**
- Modify: `games/calculatorx/engine.py`
- Modify: `tests/calculatorx/test_engine.py`

**Interfaces:**
- Consumes: `GameConfig`, `Problem`, `RandomSource` de Task 1.
- Produces: `constance_config() -> GameConfig`.
- Produces: `generate_constance_problem(rng: RandomSource) -> Problem`.
- `generate_problem` délègue à ce générateur quand `config.mode == "constance"`.

- [ ] **Step 1: Écrire les tests déterministes des quatre familles**

```python
class ConstanceRandom:
    def __init__(self, operation, template, integers):
        self.choices = iter((operation, template))
        self.integers = iter(integers)

    def choice(self, values):
        value = next(self.choices)
        assert value in values
        return value

    def randint(self, minimum, maximum):
        value = next(self.integers)
        assert minimum <= value <= maximum
        return value


@pytest.mark.parametrize(
    ("operation", "template", "integers", "expected"),
    [
        ("+", "small-small", [3, 2], Problem(3, "+", 2, 5)),
        ("−", "same", [5], Problem(5, "−", 5, 0)),
        ("×", "identity", [32], Problem(1, "×", 32, 32)),
        ("÷", "zero", [9], Problem(0, "÷", 9, 0)),
    ],
)
def test_constance_generates_trivial_families(operation, template, integers, expected):
    rng = ConstanceRandom(operation, template, integers)
    assert generate_constance_problem(rng) == expected


def test_constance_division_is_always_defined_and_exact():
    problems = generate_problems(constance_config(), 2_000, random.Random(42))
    divisions = [problem for problem in problems if problem.operator == "÷"]
    assert divisions
    assert all(p.right != 0 and p.left % p.right == 0 for p in divisions)
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_engine.py -k constance -v`

Expected: FAIL car les interfaces Constance n’existent pas.

- [ ] **Step 3: Implémenter les gabarits Constance**

Le choix d’opération est uniforme. Les gabarits autorisés sont exactement :

```python
CONSTANCE_OPERATIONS = ("+", "−", "×", "÷")
# + : petit+petit ou 0/1+n
# − : n−0, n−n, ou (a+b)−a avec a,b dans 0..5
# × : 0/1 × n, avec n dans 0..100
# ÷ : 0÷n, n÷1, n÷n, avec n dans 1..100
```

Le générateur sélectionne d’abord l’opération, puis un gabarit de cette famille, sans liste de problèmes figée.

- [ ] **Step 4: Exécuter les tests du moteur complet**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_engine.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add games/calculatorx/engine.py tests/calculatorx/test_engine.py
git commit -m "feat: ajouter le mode Constance"
```

---

### Task 3: Statistiques pures et projection

**Files:**
- Create: `games/calculatorx/statistics.py`
- Create: `tests/calculatorx/test_statistics.py`

**Interfaces:**
- Produces: `ResponseSample(operator: str, elapsed_ms: int)` avec `from_dict` strict.
- Produces: `OperationSummary(count, median_ms, fastest_ms, slowest_ms)`.
- Produces: `summarize(samples: Sequence[ResponseSample]) -> dict[str, OperationSummary]`.
- Produces: `project_score(score: int, elapsed_ms: int, duration_seconds: int) -> int | None`.

- [ ] **Step 1: Écrire les tests d’agrégation et projection**

```python
def test_summary_groups_and_uses_true_median():
    samples = [
        ResponseSample("+", 1000), ResponseSample("+", 3000),
        ResponseSample("+", 2000), ResponseSample("÷", 4500),
    ]
    summary = summarize(samples)
    assert summary["+"] == OperationSummary(3, 2000, 1000, 3000)
    assert summary["÷"] == OperationSummary(1, 4500, 4500, 4500)


def test_projection_starts_after_three_answers():
    assert project_score(2, 10_000, 120) is None
    assert project_score(3, 12_000, 120) == 30
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_statistics.py -v`

Expected: FAIL avec `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter les fonctions pures**

Utiliser `statistics.median`, conserver les millisecondes entières dans le contrat JSON et trier la sortie selon `("+", "−", "×", "÷")`. `ResponseSample.from_dict` refuse une opération inconnue, les booléens et les durées négatives ou supérieures à 3 600 000 ms.

- [ ] **Step 4: Exécuter les tests**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_statistics.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add games/calculatorx/statistics.py tests/calculatorx/test_statistics.py
git commit -m "feat: calculer les statistiques de vitesse"
```

---

### Task 4: Historique SQLite local

**Files:**
- Create: `games/calculatorx/storage.py`
- Create: `tests/calculatorx/test_storage.py`
- Modify: `games/calculatorx/__init__.py`

**Interfaces:**
- Produces: `SessionRecord(id, played_at, mode, duration_seconds, score, ended_reason, submission_status, nickname)`.
- Produces: `CalculatorStorage(database_path: Path)`.
- Produces methods: `record_session(...)`, `list_sessions()`, `mark_submitted(session_id, nickname)`, `clear_sessions()`.
- `build_game(data_dir)` instancie `CalculatorStorage(data_dir / "calculatorx.sqlite3")` et l’injecte au blueprint.

- [ ] **Step 1: Écrire les tests de persistance**

```python
def test_storage_records_only_session_summary(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    session = storage.record_session(
        mode="classic", duration_seconds=120, score=42,
        ended_reason="timeout", submission_status="pending",
    )
    assert storage.list_sessions() == [session]
    assert not hasattr(session, "samples")


def test_clear_history_keeps_database_usable(tmp_path):
    storage = CalculatorStorage(tmp_path / "calculatorx.sqlite3")
    storage.record_session("custom", 45, 7, "stopped", "not_applicable")
    storage.clear_sessions()
    assert storage.list_sessions() == []
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_storage.py -v`

Expected: FAIL avec `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter le schéma et les transactions**

```sql
CREATE TABLE IF NOT EXISTS calculator_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  played_at TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('classic','custom','constance')),
  duration_seconds INTEGER NOT NULL,
  score INTEGER NOT NULL,
  ended_reason TEXT NOT NULL CHECK (ended_reason IN ('timeout','stopped','exhausted')),
  submission_status TEXT NOT NULL CHECK (submission_status IN ('not_applicable','pending','submitted')),
  nickname TEXT
);
```

Ouvrir une connexion courte par opération, activer `PRAGMA foreign_keys = ON`, utiliser des paramètres SQL et retourner les lignes en ordre `played_at DESC, id DESC`.

- [ ] **Step 4: Injecter le stockage depuis le catalogue**

Remplacer `del data_dir` dans `build_game` par la création du stockage et appeler `build_blueprint(storage=storage)`. Les tests de catalogue continuent d’injecter un `tmp_path`; aucun test ne doit appeler `get_data_dir()`.

- [ ] **Step 5: Exécuter les tests ciblés**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_storage.py tests/test_app.py -v`

Expected: PASS et aucun chargement Orquantix depuis le menu.

- [ ] **Step 6: Commit**

```bash
git add games/calculatorx/storage.py games/calculatorx/__init__.py tests/calculatorx/test_storage.py
git commit -m "feat: conserver l’historique CalculatorX"
```

---

### Task 5: API locale de session, résultat et historique

**Files:**
- Modify: `games/calculatorx/routes.py`
- Modify: `tests/calculatorx/test_routes.py`

**Interfaces:**
- Consumes: `parse_config`, `generate_problems`, `ResponseSample`, `summarize`, `CalculatorStorage`.
- Produces: `POST /games/calculatorx/session` avec contrat configuré.
- Produces: `POST /games/calculatorx/result`.
- Produces: `GET /games/calculatorx/history` et `DELETE /games/calculatorx/history`.

- [ ] **Step 1: Écrire les tests de route qui échouent**

```python
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


def result_payload(*, ended_reason="timeout"):
    return {
        "mode": "classic",
        "duration_seconds": 120,
        "score": 2,
        "ended_reason": ended_reason,
        "samples": [
            {"operator": "+", "elapsed_ms": 1000},
            {"operator": "÷", "elapsed_ms": 2500},
        ],
    }


def test_custom_session_returns_validated_config(client):
    response = client.post("/games/calculatorx/session", json=custom_session_payload())
    assert response.status_code == 200
    assert response.get_json()["mode"] == "custom"
    assert response.get_json()["duration_seconds"] == 45


def test_invalid_config_returns_field_error(client):
    response = client.post("/games/calculatorx/session", json={"mode": "custom"})
    assert response.status_code == 400
    assert response.get_json()["field"]


def test_stopped_result_is_not_leaderboard_eligible(client):
    response = client.post("/games/calculatorx/result", json=result_payload(ended_reason="stopped"))
    payload = response.get_json()
    assert payload["leaderboard_eligible"] is False
    assert payload["session"]["submission_status"] == "not_applicable"
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_routes.py -v`

Expected: FAIL sur les nouveaux contrats.

- [ ] **Step 3: Adapter `build_blueprint` et `/session`**

La signature devient :

```python
def build_blueprint(
    storage: CalculatorStorage,
    problem_factory: ProblemFactory = generate_problems,
) -> Blueprint:
```

Définir `ProblemFactory = Callable[[GameConfig, int], list[Problem]]` et l’appeler avec `(config, PROBLEM_COUNT)`. `/session` lit un objet JSON, utilise Classique quand le corps est absent pour préserver la compatibilité, valide la configuration et renvoie `mode`, `duration_seconds`, `leaderboard_eligible` et 512 problèmes.

- [ ] **Step 4: Implémenter `/result` et `/history`**

`/result` valide `mode`, `duration_seconds`, `score`, `ended_reason` et la liste `samples`. Il recalcule les agrégats, détermine `pending` uniquement pour Classique/Constance terminés par `timeout` ou `exhausted`, enregistre le résumé et renvoie les statistiques. Les routes d’historique ne renvoient jamais les samples.

- [ ] **Step 5: Exécuter les tests routes et stockage**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_routes.py tests/calculatorx/test_storage.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add games/calculatorx/routes.py tests/calculatorx/test_routes.py
git commit -m "feat: exposer les séances CalculatorX V2"
```

---

### Task 6: Structure HTML et direction visuelle épurée

**Files:**
- Modify: `templates/calculatorx/index.html`
- Modify: `static/calculatorx/style.css`
- Modify: `tests/calculatorx/test_frontend.py`

**Interfaces:**
- Produces panels: `modePanel`, `settingsPanel`, `gamePanel`, `resultPanel`, `scoresPanel`.
- Produces controls: `classicButton`, `customButton`, `constanceButton`, `scoresButton`, `resetClassicButton`, `startCustomButton`, `stopButton`, `retryButton`, `clearHistoryButton`.
- Produces display nodes: `timerValue`, `scoreValue`, `projectedScore`, `problemText`, `answerInput`, `responseChart`, `operationSummaries`, `historyList`.

- [ ] **Step 1: Remplacer les contrats front-end attendus**

```python
def test_template_exposes_v2_panels_and_controls():
    html = TEMPLATE.read_text()
    for element_id in (
        "modePanel", "settingsPanel", "gamePanel", "resultPanel", "scoresPanel",
        "classicButton", "customButton", "constanceButton", "scoresButton",
        "stopButton", "projectedScore", "responseChart", "historyList",
    ):
        assert f'id="{element_id}"' in html
    assert 'aria-label="Arrêter la séance"' in html
    assert ">■<" in html
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_frontend.py::test_template_exposes_v2_panels_and_controls -v`

Expected: FAIL sur les nouveaux identifiants.

- [ ] **Step 3: Réécrire le template sans script inline**

Utiliser des sections cachées avec titres accessibles, mais limiter le texte visible. Le formulaire personnalisé contient durée, quatre bascules d’opération et huit champs de bornes. Charger `chart.js` avant `game.js`, tous deux avec `defer`.

- [ ] **Step 4: Réécrire le CSS à partir de la maquette validée**

Fond sombre sobre, calcul en sans serif de poids moyen, grille supérieure compacte, projection en couleur atténuée, Stop rouge de 28 px minimum visuel avec cible interactive de 44 px, graphique sous le calcul. Les signes `+ − × ÷` servent de légende colorée. Aucun `Georgia` sur les nombres.

- [ ] **Step 5: Ajouter les assertions CSS essentielles**

```python
def test_game_style_is_speed_oriented_and_reduced_motion_safe():
    css = STYLE.read_text()
    assert "font-variant-numeric: tabular-nums" in css
    assert "#stopButton" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation: none" in css
```

- [ ] **Step 6: Exécuter les tests front-end**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_frontend.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add templates/calculatorx/index.html static/calculatorx/style.css tests/calculatorx/test_frontend.py
git commit -m "style: épurer l’interface de CalculatorX"
```

---

### Task 7: Contrôleur navigateur, Stop, projection et graphique

**Files:**
- Create: `static/calculatorx/chart.js`
- Modify: `static/calculatorx/game.js`
- Modify: `tests/calculatorx/test_frontend.py`

**Interfaces:**
- Produces: `window.CalculatorXChart.render(svg, samples, {limit})` et `.clear(svg)`.
- `game.js` envoie `{mode, duration_seconds, score, ended_reason, samples}` à `/games/calculatorx/result`.
- Un sample navigateur a la forme `{operator: "+", elapsed_ms: 1234}`.

- [ ] **Step 1: Écrire les contrats source du graphique et de la machine d’état**

```python
def test_script_tracks_per_problem_time_and_manual_stop():
    script = GAME_SCRIPT.read_text()
    assert "problemStartedAt" in script
    assert "elapsed_ms" in script
    assert "projectedScore" in script
    assert "stopButton.addEventListener" in script
    assert "ended_reason" in script


def test_chart_has_sliding_live_window_and_operation_palette():
    script = CHART_SCRIPT.read_text()
    assert "samples.slice(-limit)" in script
    for operator in ("+", "−", "×", "÷"):
        assert repr(operator) in script or f"'{operator}'" in script
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_frontend.py -v`

Expected: FAIL car `chart.js` et les contrats V2 manquent.

- [ ] **Step 3: Implémenter le rendu SVG sans dépendance**

`render` vide le SVG, sélectionne les 30 derniers samples en direct ou tous les samples au résultat, calcule une échelle de 0 au maximum observé avec minimum visuel de 4 s, trace grille, médiane, polyline et cercles colorés. Utiliser `createElementNS`; ne jamais utiliser `innerHTML` avec des données utilisateur.

- [ ] **Step 4: Refondre la machine d’état de `game.js`**

Ajouter `mode`, `config`, `samples`, `problemStartedAt`, `endedReason` et `lastResult`. Au rendu d’un problème, mémoriser `performance.now()`. À la bonne réponse, pousser le sample, mettre à jour score, projection après trois réponses et graphique, puis afficher immédiatement le suivant. Enregistrer le dernier mode et la configuration personnalisée validée dans `localStorage`, avec repli vers Classique si les données locales sont absentes ou mal formées.

- [ ] **Step 5: Implémenter une seule terminaison idempotente**

`finishRound(token, reason)` doit : vérifier le jeton et `playing`, désactiver l’input, annuler l’animation frame, envoyer le résultat une seule fois, afficher les agrégats renvoyés puis transférer le focus vers Rejouer. Stop appelle `finishRound(token, 'stopped')`; l’échéance appelle `finishRound(token, 'timeout')`.

- [ ] **Step 6: Conserver les protections clavier**

Entrée démarre ou rejoue uniquement hors partie et hors cible interactive. La saisie reste automatique. Les boutons, liens, champs et bascules conservent leur comportement natif.

- [ ] **Step 7: Exécuter les tests CalculatorX**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add static/calculatorx/chart.js static/calculatorx/game.js tests/calculatorx/test_frontend.py
git commit -m "feat: mesurer la vitesse dans CalculatorX"
```

---

### Task 8: Écran Scores et historique local

**Files:**
- Modify: `static/calculatorx/game.js`
- Modify: `templates/calculatorx/index.html`
- Modify: `static/calculatorx/style.css`
- Modify: `tests/calculatorx/test_frontend.py`
- Modify: `tests/calculatorx/test_routes.py`

**Interfaces:**
- Consumes: `GET/DELETE /games/calculatorx/history` de Task 5.
- Produces: rendu local de date, mode, durée, score et état arrêté.
- Les sessions `pending` affichent une marque discrète réservée au futur bouton d’envoi, sans action réseau dans ce plan.

- [ ] **Step 1: Écrire les tests de contrat historique**

```python
def test_history_endpoint_never_returns_detailed_samples(client):
    client.post("/games/calculatorx/result", json=result_payload())
    payload = client.get("/games/calculatorx/history").get_json()
    assert payload["sessions"]
    assert "samples" not in payload["sessions"][0]


def test_frontend_loads_and_clears_local_history():
    script = GAME_SCRIPT.read_text()
    assert "fetch('/games/calculatorx/history')" in script
    assert "method: 'DELETE'" in script
```

- [ ] **Step 2: Vérifier l’échec ciblé**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_routes.py tests/calculatorx/test_frontend.py -v`

Expected: FAIL avant le câblage complet.

- [ ] **Step 3: Implémenter le rendu compact**

Chaque ligne affiche `date · mode · durée · score`, plus `■` pour une séance arrêtée. Trier du plus récent au plus ancien. Afficher un état vide court. Demander confirmation avant DELETE, puis rafraîchir la liste.

- [ ] **Step 4: Exécuter les tests ciblés**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add static/calculatorx/game.js templates/calculatorx/index.html static/calculatorx/style.css tests/calculatorx/test_frontend.py tests/calculatorx/test_routes.py
git commit -m "feat: afficher l’historique CalculatorX"
```

---

### Task 9: Vérification locale, documentation et build macOS

**Files:**
- Modify: `README.md`
- Verify: `build.sh`, `Procrastinator.spec`
- Test: full `tests/`

**Interfaces:**
- Produces: CalculatorX V2 local jouable dans le navigateur, pywebview et l’application packagée.
- Le README décrit les commandes depuis la worktree et les trois modes.

- [ ] **Step 1: Examiner puis compléter le README sans écraser les changements présents**

Documenter exactement :

```bash
cd /Users/mverest/Desktop/PROCRASTINATORX/.worktrees/menu-calculatorx
/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python main.py --design
./build.sh
open dist/PROCRASTINATOR.app
```

Décrire Classique, Personnalisé, Constance, historique local et absence de classement tant que le plan distant n’est pas exécuté.

- [ ] **Step 2: Exécuter la suite complète avec les ressources réelles**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest -rs`

Expected: tous les tests passent et le résumé ne contient aucune ligne `SKIPPED`.

- [ ] **Step 3: Vérifier le parcours dans le navigateur**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python main.py --design`

Vérifier Classique, réglages invalides/valides, Reset, Constance, saisie sans Entrée, projection au troisième point, graphique, Stop, résultat, historique, clavier, fenêtre étroite et mode réduction des animations.

- [ ] **Step 4: Construire l’application**

Run: `./build.sh`

Expected: exit code 0 et présence de `dist/PROCRASTINATOR.app`.

- [ ] **Step 5: Tester la version packagée**

Run: `open dist/PROCRASTINATOR.app`

Vérifier le menu, une courte partie personnalisée, Stop, historique après relance et l’accès intact à Orquantix.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: expliquer CalculatorX V2"
```

## Coverage Map

- Modes et réglages : Tasks 1–2, 5–7.
- Statistiques, projection et graphique : Tasks 3, 5–7.
- Stop et admissibilité : Tasks 5, 7.
- Historique local : Tasks 4–5, 8.
- Interface épurée et accessibilité : Tasks 6–7.
- Hors ligne : toutes les Tasks 1–9 n’utilisent aucun service distant.
- Tests réels, pywebview et build : Task 9.
