# CalculatorX Friendly Leaderboards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter deux classements amicaux gratuits, Classique et Constance, avec choix du profil uniquement après la partie et reprise des envois hors ligne.

**Architecture:** Un Cloudflare Worker expose trois endpoints et conserve les records dans D1. L’application macOS ne contacte jamais Cloudflare depuis le navigateur : des routes Flask locales relisent la séance et le profil SQLite, appellent le Worker avec un délai court, puis marquent le score envoyé. Sans URL distante ou sans réseau, toute la partie locale continue de fonctionner.

**Tech Stack:** Cloudflare Workers, D1, TypeScript, Wrangler/Vitest pour le service ; Python 3.12, Flask, requests, SQLite, JavaScript sans bundler et pytest pour l’application.

**Spec:** `docs/superpowers/specs/2026-08-28-calculatorx-v2-design.md`

**Depends on:** `docs/superpowers/plans/2026-08-28-calculatorx-v2-local.md` entièrement exécuté et vert.

## Global Constraints

- Exactement deux classements : `classic` et `constance`, tous deux réservés aux séances de 120 secondes terminées normalement.
- Un seul record par pseudonyme normalisé et par mode ; seul un score strictement supérieur remplace le record.
- Classement trié par score décroissant, puis date de record croissante, limité à 100 lignes.
- Profil demandé uniquement après la partie ou lors d’une reprise depuis l’historique.
- Aucun mot de passe, compte distant, récupération inter-Mac, signature ou anti-triche avancé.
- Seuls pseudonyme, mode, score et date sont stockés à distance.
- Aucune indisponibilité réseau ne peut empêcher une partie, un résultat ou l’écriture de l’historique local.
- Ne jamais embarquer de jeton d’administration Cloudflare dans l’application.
- Le déploiement distant demande l’autorisation explicite du propriétaire au moment de `wrangler login` et `wrangler deploy`.

## File Structure

- Create: `leaderboard/package.json`, `tsconfig.json`, `vitest.config.ts`, `wrangler.jsonc` — projet Worker autonome.
- Create: `leaderboard/migrations/0001_scores.sql` — schéma D1.
- Create: `leaderboard/src/normalize.ts` — normalisation/validation des pseudonymes.
- Create: `leaderboard/src/repository.ts` — requêtes D1 typées.
- Create: `leaderboard/src/index.ts` — routage HTTP JSON.
- Create: `leaderboard/test/normalize.test.ts`, `repository.test.ts`, `api.test.ts`.
- Modify: `games/calculatorx/storage.py` — profils et lecture d’une séance admissible.
- Create: `games/calculatorx/leaderboard.py` — client HTTP distant.
- Modify: `games/calculatorx/routes.py`, `__init__.py` — proxy local et injection.
- Modify: `templates/calculatorx/index.html`, `static/calculatorx/game.js`, `style.css` — profils, envoi et deux classements.
- Modify/Create: `tests/calculatorx/test_storage.py`, `test_leaderboard.py`, `test_routes.py`, `test_frontend.py`.
- Modify: `README.md` — configuration, déploiement et comportement hors ligne.

---

### Task 1: Projet Worker, normalisation et schéma D1

**Files:**
- Create: `leaderboard/package.json`
- Create: `leaderboard/tsconfig.json`
- Create: `leaderboard/vitest.config.ts`
- Create: `leaderboard/wrangler.jsonc`
- Create: `leaderboard/migrations/0001_scores.sql`
- Create: `leaderboard/src/normalize.ts`
- Create: `leaderboard/test/normalize.test.ts`

**Interfaces:**
- Produces: `normalizeNickname(value: unknown) -> {key: string, display: string}` ou lève `InputError`.
- D1 binding name: `DB`.
- D1 table: `leaderboard_scores(mode, nickname_key, nickname, score, achieved_at)`.

- [ ] **Step 1: Initialiser le projet et verrouiller les dépendances de développement**

```bash
mkdir -p leaderboard/src leaderboard/test leaderboard/migrations
cd leaderboard
npm init -y
npm install --save-dev wrangler@latest vitest@latest @cloudflare/vitest-plugin@latest @cloudflare/workers-types@latest typescript@latest
```

Modifier `package.json` pour avoir `"type": "module"` et les scripts :

```json
{
  "scripts": {
    "test": "vitest run",
    "dev": "wrangler dev",
    "deploy": "wrangler deploy"
  }
}
```

Créer `tsconfig.json` :

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["ES2022", "WebWorker"],
    "types": ["@cloudflare/workers-types", "vitest/globals"],
    "strict": true,
    "noEmit": true
  },
  "include": ["src", "test", "vitest.config.ts"]
}
```

- [ ] **Step 2: Créer la configuration locale du Worker**

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "procrastinatorx-leaderboard",
  "main": "src/index.ts",
  "compatibility_date": "2026-08-28",
  "d1_databases": [{
    "binding": "DB",
    "database_name": "procrastinatorx-leaderboard",
    "database_id": "local-development",
    "migrations_dir": "migrations"
  }]
}
```

`database_id = "local-development"` est réservé aux tests locaux ; Task 6 le remplace par l’identifiant réel retourné par Cloudflare.

- [ ] **Step 3: Écrire les tests de normalisation qui échouent**

```typescript
import {describe, expect, it} from 'vitest';
import {InputError, normalizeNickname} from '../src/normalize';

it('normalizes equivalent nicknames', () => {
  expect(normalizeNickname('  Ada  ')).toEqual({key: 'ada', display: 'Ada'});
  expect(normalizeNickname('Ａｄａ')).toEqual({key: 'ada', display: 'Ada'});
});

it.each(['', ' '.repeat(4), 'a'.repeat(25), 'A\u0000B'])(
  'rejects invalid nickname %j', value => expect(() => normalizeNickname(value)).toThrow(InputError)
);
```

- [ ] **Step 4: Vérifier l’échec**

Run: `cd leaderboard && npm test -- normalize.test.ts`

Expected: FAIL car `normalize.ts` n’existe pas.

- [ ] **Step 5: Implémenter la normalisation**

Définir `InputError extends Error` dans `normalize.ts`. `normalizeNickname` exige une chaîne, normalise avec `value.normalize('NFKC').trim()`, refuser les caractères Unicode de contrôle via `/\p{Cc}/u`, compter les points de code avec `[...display].length`, accepter de 1 à 24 caractères et calculer la clé avec `display.toLocaleLowerCase('fr-FR')`.

- [ ] **Step 6: Créer la migration D1**

```sql
CREATE TABLE leaderboard_scores (
  mode TEXT NOT NULL CHECK (mode IN ('classic', 'constance')),
  nickname_key TEXT NOT NULL,
  nickname TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 9999),
  achieved_at TEXT NOT NULL,
  PRIMARY KEY (mode, nickname_key)
);

CREATE INDEX leaderboard_rank
ON leaderboard_scores (mode, score DESC, achieved_at ASC);
```

- [ ] **Step 7: Exécuter les tests de normalisation**

Run: `cd leaderboard && npm test -- normalize.test.ts`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add leaderboard
git commit -m "feat: initialiser le service de classements"
```

---

### Task 2: Dépôt D1 et API Worker

**Files:**
- Create: `leaderboard/src/repository.ts`
- Create: `leaderboard/src/index.ts`
- Create: `leaderboard/test/repository.test.ts`
- Create: `leaderboard/test/api.test.ts`
- Create: `leaderboard/test/apply-migrations.ts`
- Modify: `leaderboard/vitest.config.ts`

**Interfaces:**
- Produces: `ScoreRepository.list(mode, limit=100)`.
- Produces: `ScoreRepository.submit(mode, nickname, score, now)`.
- Produces endpoints `GET /leaderboards/classic`, `GET /leaderboards/constance`, `POST /scores`.

- [ ] **Step 1: Configurer Vitest avec le Worker et les migrations D1**

```typescript
import path from 'node:path';
import {cloudflareTest, readD1Migrations} from '@cloudflare/vitest-plugin';
import {defineConfig} from 'vitest/config';

export default defineConfig({
  plugins: [cloudflareTest(async () => ({
    wrangler: {configPath: './wrangler.jsonc'},
    miniflare: {
      bindings: {
        TEST_MIGRATIONS: await readD1Migrations(path.join(process.cwd(), 'migrations'))
      }
    }
  }))],
  test: {setupFiles: ['./test/apply-migrations.ts']}
});
```

Créer le setup :

```typescript
import {beforeEach} from 'vitest';
import {env} from 'cloudflare:workers';
import {applyD1Migrations} from 'cloudflare:test';

declare module 'cloudflare:workers' {
  interface ProvidedEnv {
    DB: D1Database;
    TEST_MIGRATIONS: D1Migration[];
  }
}

beforeEach(async () => {
  await applyD1Migrations(env.DB, env.TEST_MIGRATIONS);
});
```

- [ ] **Step 2: Écrire les tests du dépôt qui échouent**

```typescript
import {beforeEach, expect, it} from 'vitest';
import {env} from 'cloudflare:workers';
import {ScoreRepository} from '../src/repository';

let repository: ScoreRepository;
beforeEach(() => { repository = new ScoreRepository(env.DB); });

it('keeps only a strictly better score', async () => {
  await repository.submit('classic', 'Ada', 40, '2026-08-28T10:00:00Z');
  await repository.submit('classic', 'ADA', 39, '2026-08-28T11:00:00Z');
  await repository.submit('classic', 'Ada', 52, '2026-08-28T12:00:00Z');
  expect(await repository.list('classic')).toEqual([
    {nickname: 'Ada', score: 52, achieved_at: '2026-08-28T12:00:00Z', rank: 1}
  ]);
});

it('keeps modes separate and breaks ties by oldest date', async () => {
  await repository.submit('classic', 'Bob', 50, '2026-08-28T12:00:00Z');
  await repository.submit('classic', 'Ada', 50, '2026-08-28T10:00:00Z');
  await repository.submit('constance', 'Bob', 99, '2026-08-28T09:00:00Z');
  expect((await repository.list('classic')).map(row => row.nickname)).toEqual(['Ada', 'Bob']);
});
```

- [ ] **Step 3: Implémenter l’upsert conditionnel et la lecture indexée**

```sql
INSERT INTO leaderboard_scores(mode, nickname_key, nickname, score, achieved_at)
VALUES (?1, ?2, ?3, ?4, ?5)
ON CONFLICT(mode, nickname_key) DO UPDATE SET
  nickname = excluded.nickname,
  score = excluded.score,
  achieved_at = excluded.achieved_at
WHERE excluded.score > leaderboard_scores.score;
```

La lecture utilise `WHERE mode = ? ORDER BY score DESC, achieved_at ASC LIMIT ?` et ajoute `rank` à partir de 1 dans la réponse.

- [ ] **Step 4: Écrire les tests HTTP qui échouent**

```typescript
import {expect, it} from 'vitest';
import {exports} from 'cloudflare:workers';

it('rejects unsupported mode and malformed scores', async () => {
  expect((await exports.default.fetch(new Request('https://x/scores', {
    method: 'POST', headers: {'content-type': 'application/json'},
    body: JSON.stringify({mode: 'custom', nickname: 'Ada', score: 12})
  }))).status).toBe(400);
});

it('submits then lists a classic record', async () => {
  const submitted = await exports.default.fetch(new Request('https://x/scores', {
    method: 'POST', headers: {'content-type': 'application/json'},
    body: JSON.stringify({mode: 'classic', nickname: 'Ada', score: 73})
  }));
  expect(submitted.status).toBe(200);
  const listed = await (await exports.default.fetch(
    new Request('https://x/leaderboards/classic')
  )).json();
  expect(listed.scores[0]).toMatchObject({nickname: 'Ada', score: 73, rank: 1});
});
```

- [ ] **Step 5: Implémenter le routeur JSON minimal**

Refuser les méthodes inconnues avec 405, les routes inconnues avec 404, les corps non JSON avec 400 et les modes/scores invalides avec 400. Générer `achieved_at` côté Worker avec `new Date().toISOString()`. Toutes les réponses, erreurs incluses, utilisent `application/json; charset=utf-8`.

- [ ] **Step 6: Exécuter la suite Worker**

Run: `cd leaderboard && npm test`

Expected: tous les tests passent.

- [ ] **Step 7: Commit**

```bash
git add leaderboard
git commit -m "feat: exposer les deux classements Cloudflare"
```

---

### Task 3: Profils locaux et admissibilité des séances

**Files:**
- Modify: `games/calculatorx/storage.py`
- Modify: `tests/calculatorx/test_storage.py`

**Interfaces:**
- Produces: `Profile(id, nickname, normalized_nickname, created_at, last_used_at)`.
- Produces methods: `create_profile`, `list_profiles`, `get_profile`, `get_session`, `mark_submitted`.
- `create_profile` réutilise le profil local existant si la forme normalisée est identique.

- [ ] **Step 1: Écrire les tests de profils qui échouent**

```python
@pytest.fixture
def storage(tmp_path):
    return CalculatorStorage(tmp_path / "calculatorx.sqlite3")


def record_classic_timeout(storage, score=42):
    return storage.record_session(
        mode="classic", duration_seconds=120, score=score,
        ended_reason="timeout", submission_status="pending",
    )


def test_profiles_are_local_deduplicated_and_recent_first(storage):
    ada = storage.create_profile(" Ada ")
    same = storage.create_profile("ADA")
    bob = storage.create_profile("Bob")
    assert same.id == ada.id
    assert [profile.nickname for profile in storage.list_profiles()] == ["Bob", "Ada"]


def test_only_pending_eligible_session_can_be_marked_submitted(storage):
    pending = record_classic_timeout(storage)
    profile = storage.create_profile("Ada")
    storage.mark_submitted(pending.id, profile.nickname)
    assert storage.get_session(pending.id).submission_status == "submitted"
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_storage.py -k "profile or submitted" -v`

Expected: FAIL sur les interfaces manquantes.

- [ ] **Step 3: Ajouter la table profils**

```sql
CREATE TABLE IF NOT EXISTS calculator_profiles (
  id TEXT PRIMARY KEY,
  nickname TEXT NOT NULL,
  normalized_nickname TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  last_used_at TEXT NOT NULL
);
```

Normaliser en NFKC, retirer les espaces périphériques, refuser les contrôles, limiter à 24 points de code et utiliser `casefold()` pour la clé locale. Les méthodes lèvent `StorageError` sur une séance absente ou non admissible.

- [ ] **Step 4: Exécuter les tests stockage**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_storage.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add games/calculatorx/storage.py tests/calculatorx/test_storage.py
git commit -m "feat: ajouter les profils CalculatorX"
```

---

### Task 4: Client Python et proxy Flask

**Files:**
- Create: `games/calculatorx/leaderboard.py`
- Modify: `games/calculatorx/routes.py`
- Modify: `games/calculatorx/__init__.py`
- Create: `tests/calculatorx/test_leaderboard.py`
- Modify: `tests/calculatorx/test_routes.py`

**Interfaces:**
- Produces: `LeaderboardClient(base_url: str, timeout_seconds: float = 3.0, http=requests)`.
- Produces: `list_scores(mode) -> list[dict]`, `submit_score(mode, nickname, score) -> dict`.
- Produces local routes `GET /games/calculatorx/profiles`, `POST /games/calculatorx/profiles`, `GET /games/calculatorx/leaderboards/<mode>`, `POST /games/calculatorx/leaderboard/submit`.
- `POST .../submit` accepte seulement `{session_id, profile_id}` ; Flask relit mode, score et admissibilité dans SQLite.

- [ ] **Step 1: Écrire les tests du client qui échouent**

```python
class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttp:
    def __init__(self):
        self.responses = []
        self.last_timeout = None
        self.error = None

    def queue_json(self, payload):
        self.responses.append(FakeResponse(payload))

    def raise_timeout(self):
        self.error = requests.Timeout("offline")

    def get(self, url, timeout):
        self.last_timeout = timeout
        if self.error:
            raise self.error
        return self.responses.pop(0)


@pytest.fixture
def fake_http():
    return FakeHttp()


def test_client_uses_short_timeout_and_validates_response(fake_http):
    client = LeaderboardClient("https://scores.example", http=fake_http)
    fake_http.queue_json({"scores": [{"rank": 1, "nickname": "Ada", "score": 73}]})
    assert client.list_scores("classic")[0]["score"] == 73
    assert fake_http.last_timeout == 3.0


def test_client_wraps_timeout_as_unavailable(fake_http):
    fake_http.raise_timeout()
    with pytest.raises(LeaderboardUnavailable):
        LeaderboardClient("https://scores.example", http=fake_http).list_scores("classic")
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_leaderboard.py -v`

Expected: FAIL avec `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter le client sans secret**

Utiliser `requests.get/post`, `timeout=3.0`, `raise_for_status()` et une validation stricte de la forme JSON. Une URL vide crée un client désactivé qui lève `LeaderboardUnavailable` sans tentative réseau. Aucun header secret n’est ajouté.

- [ ] **Step 4: Écrire les tests des routes proxy**

```python
def record_stopped_session(storage):
    return storage.record_session(
        mode="classic", duration_seconds=120, score=4,
        ended_reason="stopped", submission_status="not_applicable",
    )


def submit_session(client, storage, session):
    profile = storage.create_profile("Ada")
    return client.post("/games/calculatorx/leaderboard/submit", json={
        "session_id": session.id, "profile_id": profile.id,
    })


def test_submit_route_reads_score_from_storage(client, storage, remote):
    session = record_classic_timeout(storage, score=73)
    profile = storage.create_profile("Ada")
    response = client.post("/games/calculatorx/leaderboard/submit", json={
        "session_id": session.id, "profile_id": profile.id,
    })
    assert response.status_code == 200
    assert remote.submissions == [("classic", "Ada", 73)]
    assert storage.get_session(session.id).submission_status == "submitted"


def test_custom_or_stopped_session_cannot_be_submitted(client, storage, remote):
    session = record_stopped_session(storage)
    response = submit_session(client, storage, session)
    assert response.status_code == 409
    assert remote.submissions == []
```

- [ ] **Step 5: Implémenter les routes et l’injection**

`build_blueprint` reçoit `storage` et `leaderboard_client`. Définir d’abord `DEFAULT_BASE_URL = ""`; `build_game` choisit `os.environ.get("CALCULATORX_LEADERBOARD_URL", DEFAULT_BASE_URL)`. La chaîne vide désactive proprement le client avant Task 6. Les erreurs réseau deviennent un JSON 503 court ; les erreurs de profil/séance deviennent 404 ou 409. Marquer `submitted` uniquement après succès distant.

- [ ] **Step 6: Exécuter les tests Python ciblés**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_leaderboard.py tests/calculatorx/test_routes.py tests/calculatorx/test_storage.py -v`

Expected: PASS sans requête Internet réelle.

- [ ] **Step 7: Commit**

```bash
git add games/calculatorx/leaderboard.py games/calculatorx/routes.py games/calculatorx/__init__.py tests/calculatorx/test_leaderboard.py tests/calculatorx/test_routes.py
git commit -m "feat: relier CalculatorX aux classements"
```

---

### Task 5: Interface profils, envoi, classement et reprise

**Files:**
- Modify: `templates/calculatorx/index.html`
- Modify: `static/calculatorx/game.js`
- Modify: `static/calculatorx/style.css`
- Modify: `tests/calculatorx/test_frontend.py`

**Interfaces:**
- Produces nodes: `submitScoreButton`, `profilePicker`, `profileList`, `newProfileInput`, `createProfileButton`, `classicLeaderboard`, `constanceLeaderboard`.
- Consumes les routes locales de Task 4 ; aucune URL Cloudflare n’apparaît dans JavaScript.

- [ ] **Step 1: Écrire les tests de contrat UI qui échouent**

```python
def test_template_has_post_game_profile_picker_and_two_boards():
    html = TEMPLATE.read_text()
    for element_id in (
        "submitScoreButton", "profilePicker", "profileList", "newProfileInput",
        "classicLeaderboard", "constanceLeaderboard",
    ):
        assert f'id="{element_id}"' in html


def test_browser_uses_only_local_leaderboard_routes():
    script = GAME_SCRIPT.read_text()
    assert "/games/calculatorx/leaderboard/submit" in script
    assert "/games/calculatorx/leaderboards/" in script
    assert "workers.dev" not in script
```

- [ ] **Step 2: Vérifier l’échec**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx/test_frontend.py -v`

Expected: FAIL sur les nouveaux identifiants et routes.

- [ ] **Step 3: Ajouter le sélecteur de profil après la partie**

Masquer Ajouter au classement pour Personnalisé et Stop. Pour une séance admissible, le bouton ouvre un panneau compact avec profils récents et `+`. Créer un profil via POST, le sélectionner, puis envoyer `{session_id, profile_id}`. Désactiver l’action pendant l’envoi et empêcher le double clic.

- [ ] **Step 4: Ajouter les deux classements**

L’écran Scores possède deux bascules `120` et `C` ou les libellés accessibles équivalents. Chaque ligne montre rang, pseudonyme et score. Afficher au maximum 100 lignes et un message court si le réseau manque.

- [ ] **Step 5: Ajouter la reprise depuis l’historique**

Une séance locale `pending` Classique/Constance affiche une action d’envoi. Elle ouvre le même sélecteur de profil. Après succès, rafraîchir la ligne et le classement concerné sans dupliquer la séance.

- [ ] **Step 6: Préserver le clavier et l’épure**

Le panneau profil piège le focus tant qu’il est ouvert, Échap le ferme, et le focus revient au bouton déclencheur. Les libellés complets restent accessibles via `aria-label`; les textes visibles restent courts.

- [ ] **Step 7: Exécuter les tests CalculatorX**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest tests/calculatorx -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add templates/calculatorx/index.html static/calculatorx/game.js static/calculatorx/style.css tests/calculatorx/test_frontend.py
git commit -m "feat: envoyer les scores CalculatorX"
```

---

### Task 6: Déploiement Cloudflare, URL de production et vérification

**Files:**
- Modify: `leaderboard/wrangler.jsonc`
- Modify: `games/calculatorx/leaderboard.py`
- Modify: `README.md`
- Test: Worker, full pytest, build macOS.

**Interfaces:**
- Produces: Worker public déployé et URL par défaut intégrée à l’application.
- `CALCULATORX_LEADERBOARD_URL` continue de remplacer l’URL par défaut en développement/tests.

- [ ] **Step 1: Exécuter toutes les vérifications locales avant déploiement**

Run: `cd leaderboard && npm test`

Expected: PASS.

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python -m pytest -rs`

Expected: tous les tests passent avec `0 skipped`.

- [ ] **Step 2: Obtenir l’autorisation puis connecter Wrangler**

Run: `cd leaderboard && npx wrangler login`

Expected: le navigateur Cloudflare confirme le compte du propriétaire et Wrangler affiche une authentification réussie.

- [ ] **Step 3: Créer la base distante et enregistrer son identifiant réel**

Run: `cd leaderboard && npx wrangler d1 create procrastinatorx-leaderboard`

Copier exactement le `database_id` UUID renvoyé dans `leaderboard/wrangler.jsonc` à la place de `local-development`, sans modifier le binding `DB` ni le nom de base.

- [ ] **Step 4: Appliquer la migration distante**

Run: `cd leaderboard && npx wrangler d1 migrations apply procrastinatorx-leaderboard --remote`

Expected: `0001_scores.sql` est appliquée avec succès.

- [ ] **Step 5: Déployer et intégrer l’URL réelle**

Run: `cd leaderboard && npx wrangler deploy`

Copier exactement l’URL HTTPS affichée par Wrangler dans `DEFAULT_BASE_URL` de `games/calculatorx/leaderboard.py`. Conserver :

```python
base_url = os.environ.get("CALCULATORX_LEADERBOARD_URL", DEFAULT_BASE_URL)
```

- [ ] **Step 6: Vérifier l’API distante avec des données de fumée**

Définir la variable avec l’URL exacte imprimée à Step 5 :

```bash
read -r DEPLOYED_WORKER_URL
curl -fsS "$DEPLOYED_WORKER_URL/leaderboards/classic"
```

À l’invite silencieuse de `read`, coller l’URL exacte imprimée par Wrangler puis valider avec Entrée.

Expected: JSON `{"scores":[]}` avant le premier envoi.

Envoyer puis relire le record :

```bash
curl -fsS -X POST "$DEPLOYED_WORKER_URL/scores" \
  -H "content-type: application/json" \
  --data '{"mode":"classic","nickname":"SmokeTest","score":1}'
curl -fsS "$DEPLOYED_WORKER_URL/leaderboards/classic"
```

Vérifier que `SmokeTest` apparaît, puis supprimer cette ligne via D1 :

```bash
npx wrangler d1 execute procrastinatorx-leaderboard --remote \
  --command "DELETE FROM leaderboard_scores WHERE nickname_key = 'smoketest'"
```

- [ ] **Step 7: Vérifier l’application connectée et hors ligne**

Run: `/Users/mverest/Desktop/PROCRASTINATORX/.venv/bin/python main.py --design`

Vérifier lecture des deux tableaux, création/sélection d’un profil après une partie admissible, remplacement uniquement par un meilleur score, refus de Stop/Personnalisé, puis désactiver le réseau et vérifier que le score reste `pending` et peut être renvoyé au retour du réseau.

- [ ] **Step 8: Construire et tester l’application macOS**

Run: `./build.sh`

Expected: exit code 0 et `dist/PROCRASTINATOR.app`.

Run: `open dist/PROCRASTINATOR.app`

Vérifier que l’URL par défaut intégrée permet de lire et envoyer sans variable d’environnement.

- [ ] **Step 9: Documenter l’exploitation gratuite**

Dans README, documenter le dossier `leaderboard/`, `npm test`, la commande de déploiement, l’override `CALCULATORX_LEADERBOARD_URL`, les deux classements seulement et le fait que les quotas Cloudflare gratuits restent une dépendance externe susceptible d’évoluer.

- [ ] **Step 10: Commit**

```bash
git add leaderboard/wrangler.jsonc games/calculatorx/leaderboard.py README.md
git commit -m "deploy: publier les classements CalculatorX"
```

## Coverage Map

- Stockage D1 et meilleur score : Tasks 1–2.
- Deux modes strictement séparés : Tasks 1–2, 4–5.
- Profils demandés après la partie : Tasks 3, 5.
- Proxy Flask et aucun CORS navigateur : Task 4.
- Reprise hors ligne depuis l’historique : Tasks 4–5.
- Déploiement gratuit et URL packagée : Task 6.
- Absence d’authentification/anti-triche : contraintes globales et Tasks 2, 4.
