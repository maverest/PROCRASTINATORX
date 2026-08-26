# Menu PROCRASTINATOR et CalculatorX — conception

**Date :** 26 août 2026  
**Statut :** conception validée, en attente de plan d’implémentation

## Objectif

PROCRASTINATOR devient une véritable coquille de mini-jeux. Au lancement, l’application affiche un menu permettant de choisir un jeu au lieu de rediriger directement vers Orquantix.

Cette première évolution ajoute **CalculatorX**, un sprint de calcul mental reprenant les règles du mode classique de Zetamac pendant 120 secondes, mais avec une identité visuelle originale. La structure doit pouvoir accueillir trois ou quatre mini-jeux supplémentaires sans faire remonter leurs règles dans `app.py`.

Le parcours utilisateur est linéaire :

```text
Lancement → Menu → Accueil du jeu → Partie → Résultat
                                      ↓          ↓
                                    Menu     Rejouer ou Menu
```

## Périmètre

### Inclus

- Un menu à la route `/`, listant Orquantix et CalculatorX.
- Un catalogue explicite de mini-jeux, conçu pour cinq ou six entrées.
- Une carte de menu par jeu avec nom, description, identité visuelle et lien.
- Un lien de retour au menu depuis Orquantix.
- CalculatorX sous le préfixe `/games/calculatorx`.
- Un écran d’accueil CalculatorX avec lancement explicite de la partie.
- Une partie fixe de 120 secondes avec addition, soustraction, multiplication et division.
- Un écran final avec le score, « Rejouer » et « Retour au menu ».
- Une navigation et une saisie utilisables au clavier.
- Le respect de `prefers-reduced-motion`.

### Exclus de cette version

- Réglage de la durée, des opérations ou des plages numériques.
- Historique des parties, meilleur score ou statistiques détaillées.
- Comptes, classement, synchronisation ou multijoueur.
- Niveaux, bonus, pénalités ou progression.
- Menu de plugins dynamique ou découverte automatique de modules.
- Modification des règles ou de la courbe de progression d’Orquantix.

Ces éléments pourront faire l’objet d’améliorations ultérieures après validation du jeu classique.

## Architecture de la coquille

### Catalogue explicite

La coquille consomme un catalogue construit par le paquet `games`, sans importer les règles internes de chaque jeu. Chaque mini-jeu fournit une inscription contenant uniquement ce qui est nécessaire à la coquille :

- identifiant stable ;
- nom affiché ;
- courte description ;
- icône ou monogramme ;
- classe de thème pour sa carte ;
- point d’entrée Flask ;
- blueprint à monter.

Le catalogue reste explicite : aucun balayage du système de fichiers ni import magique. Ajouter un jeu signifie créer son paquet puis ajouter son inscription à la liste centrale. Cette solution garde l’ordre du menu déterministe et rend les erreurs d’import visibles au démarrage.

La coquille itère sur ce catalogue pour monter les blueprints et rendre les cartes. `app.py` ne contient aucune règle de jeu.

### Encapsulation des jeux

La structure visée est :

```text
games/
  catalog.py                 inscription commune et ordre du menu
  orquantix/                 jeu existant, règles inchangées
  calculatorx/
    __init__.py              métadonnées et construction du jeu
    engine.py                génération pure des calculs
    routes.py                blueprint et API de session
templates/
  index.html                 menu PROCRASTINATOR
  calculatorx/index.html     accueil, partie et résultat
static/
  shell.css                  identité de la coquille et du menu
  calculatorx/style.css
  calculatorx/game.js
tests/
  calculatorx/
    test_engine.py
    test_routes.py
```

Le code de chargement et l’état d’Orquantix restent isolés du nouveau jeu. La visite du menu ou de CalculatorX ne déclenche ni téléchargement ni chargement des quelque 180 Mo de ressources d’Orquantix. Un accès direct à `/games/orquantix/` conserve le chargement paresseux actuel.

La route historique `/status` est conservée pour compatibilité et continue de refléter l’état d’Orquantix. Sa présence ne déclenche pas le chargement du jeu.

## Règles de CalculatorX

La référence fonctionnelle est le [mode classique de Zetamac](https://arithmetic.zetamac.com/). La durée et les plages sont fixes dans cette version.

### Durée et score

- Une partie dure exactement 120 secondes.
- Le chrono démarre uniquement après activation de « C’est parti ! ».
- Le score commence à zéro.
- Chaque bonne réponse ajoute un point.
- Une réponse incorrecte ne retire aucun point.
- À l’échéance, la saisie est désactivée et aucune réponse tardive n’est comptée.

### Génération des opérations

Pour chaque nouveau calcul, l’une des quatre opérations est tirée uniformément et indépendamment.

| Opération | Génération | Exemple | Propriété garantie |
|---|---|---|---|
| Addition | `a, b ∈ [2, 100]` | `37 + 58` | résultat entier positif |
| Soustraction | renversement de `a + b`, avec `a, b ∈ [2, 100]` | `95 − 37` | résultat entier strictement positif |
| Multiplication | `a ∈ [2, 12]`, `b ∈ [2, 100]` | `7 × 43` | résultat entier positif |
| Division | renversement de `a × b`, affiché `(a × b) ÷ a` | `301 ÷ 7` | quotient entier et diviseur dans `[2, 12]` |

Les bornes sont inclusives. Les opérations successives peuvent se répéter ; aucune logique anti-répétition n’est ajoutée.

### Réserve de calculs

Le serveur crée au lancement de chaque partie une réserve de 512 calculs et l’envoie en une seule réponse. Ce volume couvre largement une partie humaine de 120 secondes et évite toute attente réseau entre deux réponses. Il n’existe aucun enjeu de sécurité ou d’anti-triche : PROCRASTINATOR est une application locale personnelle.

Le moteur est une fonction Python pure. Il accepte une source aléatoire injectable afin que les tests puissent forcer chaque opération et chaque borne sans dépendre du hasard.

### Saisie

- Le champ de réponse reçoit le focus au début de la partie et après chaque bonne réponse.
- À chaque modification, la valeur entière complète est comparée à la réponse attendue.
- Une bonne réponse efface le champ et affiche immédiatement le calcul suivant.
- Une réponse incorrecte reste visible afin que le joueur puisse la corriger.
- `Entrée` lance une partie depuis l’accueil et permet de rejouer depuis le résultat.
- Les contrôles restent activables à la souris et exposent des libellés accessibles.

## Chronométrage et concurrence côté navigateur

Le navigateur calcule une échéance absolue avec `performance.now()` au démarrage. L’affichage du temps restant est dérivé de cette échéance ; il ne repose pas sur un simple compteur décrémenté par `setInterval`. Une fenêtre ralentie, suspendue ou passée en arrière-plan ne prolonge donc pas la partie.

Chaque partie reçoit un jeton local unique. Tous les gestionnaires asynchrones vérifient ce jeton avant de modifier l’interface ou le score. Un retour tardif de la préparation d’une ancienne partie, un ancien minuteur ou une saisie arrivée à l’échéance ne peut pas affecter la partie suivante.

Le serveur ne conserve aucun score ni état de partie CalculatorX.

## Routes et flux de données

### `GET /`

Rend le menu avec les inscriptions ordonnées du catalogue. Cette route ne charge aucune ressource de jeu.

### `GET /games/calculatorx/`

Rend l’unique page CalculatorX dans son état d’accueil.

### `POST /games/calculatorx/session`

Crée une nouvelle réserve et renvoie :

```json
{
  "duration_seconds": 120,
  "problems": [
    {"left": 301, "operator": "÷", "right": 7, "answer": 43}
  ]
}
```

La route n’accepte aucun réglage client dans cette version. La durée, les opérations, les plages et la taille de la réserve sont des constantes du jeu.

### Flux d’une partie

1. L’utilisateur ouvre CalculatorX : seule la page d’accueil est rendue.
2. Il active « C’est parti ! ».
3. Le bouton passe temporairement en état de préparation et la session est demandée.
4. À réception d’une session valide, le chrono et la première question apparaissent simultanément.
5. Les réponses sont évaluées localement sans requête intermédiaire.
6. À l’échéance, l’écran de résultat remplace la partie.
7. « Rejouer » demande une nouvelle réserve ; « Retour au menu » navigue vers `/`.

## Gestion des erreurs

- Si la création de session échoue, le chrono ne démarre pas.
- L’accueil reste affiché avec un message compréhensible et une action « Réessayer ».
- Une réponse de session mal formée est traitée comme un échec de préparation.
- Un épuisement inattendu de la réserve termine proprement la partie et affiche le score, sans exception visible ni calcul `undefined`.
- Les erreurs de CalculatorX ne modifient pas l’état d’Orquantix et réciproquement.

## Direction visuelle

### Menu : atelier rétro

Le menu utilise une ambiance chaude et éditoriale : fond papier, typographie expressive, bordures tactiles et cartes légèrement décalées. La grille est responsive et accepte naturellement cinq ou six mini-jeux.

Chaque carte peut avoir sa propre couleur ou texture, mais conserve la même structure afin que l’ajout de jeux ne transforme pas la page en assemblage incohérent. Orquantix garde une évocation aquatique ; CalculatorX emploie son monogramme arithmétique.

### CalculatorX : carnet quadrillé

CalculatorX utilise un fond crème quadrillé, une encre sombre et un accent terre cuite. L’interface privilégie la lisibilité :

- accueil centré avec durée et opérations annoncées ;
- calcul très grand au centre pendant la partie ;
- chrono et score visibles sans concurrencer le calcul ;
- champ de réponse large et immédiatement identifiable ;
- résultat dans la même composition pour éviter une rupture visuelle.

Les animations sont courtes et décoratives. Sous `prefers-reduced-motion`, elles sont supprimées sans masquer de contenu ni changer l’ordre de navigation.

### Retour au menu depuis Orquantix

Un lien « Jeux » ou « Retour aux jeux » est ajouté dans la zone d’interface d’Orquantix, au-dessus des couches décoratives et sans intercepter les contrôles existants. Il ne modifie ni la scène de l’Abysse, ni son cycle de neuf secondes, ni ses easter eggs.

## Tests et vérification

### Tests du moteur

- Les quatre opérations peuvent être produites.
- Toutes les bornes minimales et maximales sont incluses.
- Une soustraction a toujours un résultat strictement positif.
- Une division a toujours un quotient entier.
- Le diviseur d’une division appartient toujours à `[2, 12]`.
- Le nombre de problèmes demandé est respecté.
- Une source aléatoire injectée rend les cas déterministes.

Les tests ne tentent pas de prouver statistiquement l’uniformité par échantillonnage aléatoire ; ils vérifient que le choix uniforme est correctement délégué à la source injectable.

### Tests des routes et de la coquille

- `/` répond `200` et affiche les deux jeux dans l’ordre du catalogue.
- Les cartes pointent vers leurs préfixes respectifs.
- Le menu ne déclenche pas le chargement d’Orquantix.
- L’accès direct à Orquantix déclenche toujours son chargement paresseux.
- La route de session CalculatorX renvoie 120 secondes et 512 problèmes valides.
- CalculatorX ne répond pas sous une route globale sans préfixe.
- Les templates ne contiennent aucun script inline.
- `/status` conserve son comportement historique.

### Vérification finale

1. Lancer la suite complète avec `python -m pytest -rs`.
2. Exiger `0 skipped`, notamment pour les trois tests utilisant les données réelles.
3. Lancer `python main.py --design`.
4. Vérifier le parcours complet au clavier et à la souris : menu, accueil CalculatorX, partie, échéance, rejeu, retour au menu, entrée et sortie d’Orquantix.
5. Vérifier visuellement les tailles de fenêtre prises en charge par l’application.
6. Vérifier le repli `prefers-reduced-motion`.

## Critères d’acceptation

- L’application s’ouvre sur un menu fonctionnel.
- Orquantix et CalculatorX sont accessibles depuis ce menu.
- Le retour au menu est possible depuis chaque jeu.
- CalculatorX respecte exactement la durée, les quatre familles d’opérations et les plages définies ci-dessus.
- La saisie reste continue et sans attente entre deux calculs.
- La fin de partie ne peut ni être retardée par une suspension de fenêtre ni compter une réponse tardive.
- Aucune règle de CalculatorX ou d’Orquantix n’est placée dans `app.py`.
- Ajouter un futur mini-jeu ne demande pas de modifier les jeux existants.
- La suite complète passe avec `0 skipped` sur les données réelles.
