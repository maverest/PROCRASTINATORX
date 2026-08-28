# CalculatorX V2 et classements amicaux — conception

**Date :** 28 août 2026  
**Statut :** conception validée, en attente du plan d’implémentation

## Objectif

Faire évoluer CalculatorX d’une reproduction du mode classique de Zetamac vers un jeu de calcul mental rapide, configurable et mesurable, tout en conservant une interface sobre. Cette version ajoute :

- un mode personnalisé ;
- un mode humoristique Constance ;
- des mesures de vitesse en direct et en fin de partie ;
- un historique local léger ;
- deux classements amicaux hébergés sur Cloudflare.

Le jeu doit rester pleinement utilisable hors ligne. Le réseau ne sert qu’à consulter ou alimenter les classements.

## Principes d’interface

CalculatorX privilégie la vitesse et retire tout texte qui ne sert pas immédiatement l’action :

- police sans serif normale pour tous les nombres ;
- chiffres tabulaires pour le chrono, le score et la projection ;
- aucune animation ou variation de mise en page pendant la saisie ;
- calcul et champ de réponse au centre ;
- libellés raccourcis ou remplacés par des signes compréhensibles ;
- actions secondaires discrètes, mais accessibles au clavier et aux technologies d’assistance.

Le repli `prefers-reduced-motion` reste obligatoire.

## Parcours utilisateur

### Accueil

L’accueil CalculatorX expose quatre entrées compactes :

1. **Classique** ;
2. **Personnalisé** ;
3. **Constance** ;
4. **Scores**.

Aucun pseudonyme n’est demandé avant une partie. Le dernier mode et les derniers réglages personnalisés sont mémorisés localement.

### Partie

La partie affiche uniquement :

- `CALCULATORX` et le mode en cours ;
- le temps restant ;
- le score actuel ;
- une projection discrète, sous la forme `≈28` ;
- un petit bouton Stop rouge, représenté par `■` et doté d’un libellé accessible ;
- le calcul et le champ de réponse ;
- un graphique chronologique en bas de page.

Le graphique reçoit un point après chaque bonne réponse :

- l’abscisse représente l’ordre des calculs ;
- l’ordonnée représente le temps de réponse ;
- la couleur représente l’opération ;
- une ligne discrète relie les points ;
- une ligne horizontale représente la médiane de la séance ;
- la légende ne contient que les signes colorés `+ − × ÷`.

Pendant la partie, le graphique montre une fenêtre glissante des 30 derniers calculs. Le résultat final montre toute la séance, comprimée à la largeur disponible. Le graphique ne prend jamais le focus et ne provoque aucun défilement automatique.

### Résultat

L’écran final conserve le graphique et affiche :

- le score réel ;
- pour chaque opération activée : quantité résolue, temps médian, meilleur temps et temps le plus lent ;
- les actions Rejouer, Modifier et Retour ;
- l’action Ajouter au classement pour une partie Classique ou Constance terminée normalement.

Une séance arrêtée manuellement affiche ses résultats et est enregistrée localement, mais elle ne peut pas être envoyée au classement.

### Choix du pseudonyme

Le joueur ne choisit une identité qu’après avoir activé Ajouter au classement :

- les pseudonymes déjà créés sur ce Mac sont proposés ;
- `+` crée un nouveau pseudonyme ;
- le dernier profil utilisé est présélectionné ;
- le profil choisi est associé à l’envoi, pas au déroulement de la partie.

Il n’existe ni mot de passe, ni compte distant, ni récupération sur un autre Mac. Plusieurs profils locaux permettent à plusieurs amis d’utiliser la même machine.

## Modes de jeu

### Classique

Le mode Classique reste la référence Zetamac de 120 secondes :

| Opération | Génération |
|---|---|
| Addition | `a, b ∈ [2, 100]`, affiche `a + b` |
| Soustraction | `a, b ∈ [2, 100]`, affiche `(a + b) − a` |
| Multiplication | `a ∈ [2, 12]`, `b ∈ [2, 100]`, affiche `a × b` |
| Division | mêmes facteurs, affiche `(a × b) ÷ a` |

Les bornes sont inclusives. Les quatre opérations sont choisies uniformément et indépendamment.

### Personnalisé

Le formulaire personnalisé permet de régler :

- une durée entière de 1 à 3 600 secondes ;
- les opérations actives, avec au moins une opération cochée ;
- les bornes minimale et maximale du premier et du second opérande pour l’addition ;
- les bornes minimale et maximale du premier et du second facteur pour la multiplication.

Chaque borne est un entier compris entre 0 et 9 999 et le minimum ne peut pas dépasser le maximum.

La soustraction renverse les additions configurées pour garantir un résultat positif ou nul. La division renverse les multiplications configurées pour garantir un quotient entier. Quand la division est active, la plage servant de diviseur doit contenir au moins une valeur non nulle ; les tirages nuls à cette position sont exclus.

Le bouton Reset classique restaure :

- 120 secondes ;
- les quatre opérations ;
- addition `2–100` par `2–100` ;
- multiplication `2–12` par `2–100`.

Une partie personnalisée n’est jamais admissible à un classement.

### Constance

Constance dure toujours 120 secondes et choisit uniformément parmi les quatre opérations. Son générateur produit uniquement des calculs volontairement faciles ou absurdes :

- additions entre deux valeurs de `0` à `5`, ou `0/1 + n` avec `n ∈ [0, 100]` ;
- soustractions inversées donnant notamment `n − 0`, `n − n` ou une différence très petite ;
- multiplications dont au moins un facteur vaut `0` ou `1`, l’autre appartenant à `[0, 100]` ;
- divisions des formes `0 ÷ n`, `n ÷ 1` ou `n ÷ n`, avec `n ∈ [1, 100]`.

Ce générateur couvre notamment l’esprit de `1 × 32`, `3 + 2` et `0 + 0`, sans liste figée. Une partie Constance terminée normalement alimente son propre classement, distinct du Classique.

## Saisie, chronométrage et mesures

La bonne réponse est reconnue dès que sa représentation entière complète est saisie. Entrée n’est pas requise. Une valeur incorrecte reste dans le champ afin d’être corrigée.

Le navigateur utilise `performance.now()` pour :

- calculer l’échéance absolue de la séance ;
- mesurer le temps entre l’affichage d’un calcul et sa bonne réponse ;
- empêcher une suspension de fenêtre de prolonger le chrono.

Le score augmente d’un point par calcul résolu. Le temps de réponse inclut tout le temps nécessaire pour corriger une saisie incorrecte ; cette version ne calcule donc pas de taux d’erreur séparé.

Après trois bonnes réponses, la projection est recalculée à chaque réponse :

```text
projection = arrondi(score × durée totale / temps écoulé)
```

La projection disparaît quand la séance se termine. Les statistiques par opération utilisent les temps de réponse individuels et calculent quantité, médiane, minimum et maximum. La médiane, plus robuste qu’une moyenne face à une interruption ponctuelle, est la mesure principale.

## Architecture locale

Les règles restent strictement dans `games/calculatorx`. `app.py` monte le jeu par son inscription et ne connaît aucune règle de génération, de score ou de classement.

La structure visée sépare :

- `engine.py` : configuration validée et générateurs purs Classique, Personnalisé et Constance ;
- `statistics.py` : calculs purs de médiane, agrégats et projection ;
- `storage.py` : profils et historique SQLite local ;
- `leaderboard.py` : client réseau vers l’API distante ;
- `routes.py` : endpoints Flask et adaptation HTTP ;
- JavaScript : chrono, saisie, rendu du graphique et orchestration de l’interface.

Le serveur continue de fournir une réserve de calculs afin qu’aucune requête réseau n’interrompe la saisie. La requête de session contient le mode et, pour Personnalisé, sa configuration. Python valide toutes les valeurs avant de générer la réserve.

Le navigateur collecte les temps individuels. À la fin, il les transmet à une route locale qui recalcule les agrégats en Python, enregistre le résumé de la séance et renvoie les statistiques finales. Le graphique utilise directement les mesures brutes déjà présentes en mémoire.

## Données locales

Une base SQLite est créée dans le dossier de données de PROCRASTINATOR. Les tests reçoivent toujours un chemin temporaire injecté et n’appellent jamais `main.get_data_dir()` sans avoir isolé `Path.home()`.

### Profils

Un profil contient :

- un identifiant UUID local ;
- un pseudonyme affiché ;
- une forme normalisée pour empêcher les doublons locaux ;
- la date de création et la date de dernière utilisation.

Le pseudonyme est normalisé en Unicode NFKC, débarrassé des espaces périphériques et limité à 24 caractères visibles. Les caractères de contrôle sont refusés.

### Historique

Chaque séance conserve seulement :

- date ;
- mode ;
- durée ;
- score ;
- état terminé ou arrêté ;
- état envoyé ou non ;
- pseudonyme utilisé pour l’envoi, le cas échéant.

Les temps individuels et statistiques détaillées ne sont pas persistés. Ils restent disponibles uniquement jusqu’au lancement de la séance suivante ou à la fermeture de l’application. L’utilisateur peut vider l’historique local.

Un score Classique ou Constance terminé mais non envoyé peut être soumis plus tard depuis l’historique.

## Classements distants

### Périmètre

Il existe exactement deux classements :

- `classic` pour le Classique 120 secondes ;
- `constance` pour Constance 120 secondes.

Le classement conserve uniquement le meilleur score de chaque pseudonyme dans chaque mode. Une valeur inférieure ou égale ne remplace pas le record existant. En cas d’égalité entre joueurs, la date d’obtention la plus ancienne passe devant.

Le système est volontairement amical : aucune authentification, signature de séance ou protection anti-triche avancée n’est ajoutée.

### Hébergement

Un Cloudflare Worker expose une API JSON et utilise une base D1. Cette solution ne nécessite aucun serveur permanent et reste dans l’offre gratuite au volume prévu pour un groupe d’amis.

Le Worker et son schéma vivent dans un dossier autonome du dépôt avec leur configuration de déploiement. Le déploiement nécessite une connexion au compte Cloudflare du propriétaire ; les tests et le fonctionnement local ne nécessitent pas cette connexion.

### API

```text
GET  /leaderboards/classic
GET  /leaderboards/constance
POST /scores
```

Les lectures renvoient les 100 premiers résultats, triés par score décroissant puis date croissante.

L’envoi accepte uniquement :

```json
{
  "mode": "classic",
  "nickname": "Ada",
  "score": 73
}
```

Le Worker :

- valide `classic` ou `constance` ;
- normalise et valide le pseudonyme ;
- exige un score entier entre 0 et 9 999 ;
- insère le score ou remplace l’ancien uniquement s’il est supérieur ;
- renvoie le record retenu et sa position actuelle.

La clé logique distante est `(mode, pseudonyme_normalisé)`. Deux machines utilisant le même pseudonyme alimentent donc le même record, ce qui est acceptable dans ce contexte amical.

### Accès depuis l’application

Le navigateur appelle uniquement les routes Flask locales. Le client Python contacte le Worker avec un délai court et une URL configurable en développement, puis intégrée à l’application lors de la distribution. Cela évite les problèmes CORS liés au port local dynamique de pywebview et centralise la gestion des erreurs réseau.

Aucun secret d’administration Cloudflare n’est embarqué dans l’application. Seuls le pseudonyme, le mode, le score et l’horodatage du record sont stockés à distance.

## Gestion des erreurs

- Une configuration invalide empêche le démarrage et indique brièvement le champ concerné.
- Une création de session défaillante ne démarre ni chrono ni mesure.
- Un épuisement imprévu de la réserve termine proprement la séance.
- Une fermeture, un rejeu ou une réponse asynchrone tardive ne peut pas modifier une nouvelle séance grâce à un jeton de manche.
- Une erreur de stockage local n’empêche pas de jouer, mais l’interface signale que l’historique n’a pas été enregistré.
- Une indisponibilité Cloudflare n’affecte jamais une partie. Le score reste non envoyé et peut être réessayé.
- Un double clic d’envoi est idempotent : D1 conserve toujours un seul record par mode et pseudonyme.

## Tests

### Python

- validation complète des configurations et des bornes ;
- reproduction exacte des règles classiques ;
- couverture déterministe de chaque famille Constance ;
- propriétés des soustractions et divisions ;
- génération des réserves pour toute combinaison valide ;
- calcul de la médiane, des agrégats et de la projection ;
- échéance, arrêt manuel et admissibilité au classement ;
- création, sélection et normalisation des profils ;
- historique local, effacement et migrations SQLite ;
- client distant simulé : succès, record inférieur, délai dépassé et erreur réseau ;
- routes Flask et absence de dépendance envers Orquantix.

### JavaScript et interface

- maintien du focus et validation automatique ;
- protection contre les callbacks d’une ancienne séance ;
- mise à jour du graphique et de la projection sans déplacement de page ;
- arrêt manuel ;
- parcours complet au clavier ;
- libellé accessible du bouton Stop malgré son affichage `■` ;
- mise en page aux tailles de fenêtre prises en charge ;
- absence d’animations sous `prefers-reduced-motion`.

La logique statistique de référence est testée en Python. Les contrats HTML/JavaScript existants sont étendus, puis le parcours réel est vérifié dans le navigateur et dans la fenêtre pywebview.

### Worker Cloudflare

- validation des entrées ;
- normalisation des pseudonymes ;
- insertion initiale ;
- remplacement par un meilleur score ;
- refus de remplacer par un score inférieur ou égal ;
- séparation stricte des deux modes ;
- ordre des résultats et limite à 100.

### Vérification finale

1. Exécuter `python -m pytest -rs` et exiger `0 skipped`.
2. Exécuter les tests autonomes du Worker.
3. Vérifier le parcours complet avec `python main.py --design`.
4. Vérifier une partie hors ligne et la reprise d’un envoi.
5. Construire l’application PyInstaller et tester la version macOS packagée.

## Critères d’acceptation

- Les trois modes respectent exactement leurs règles et le Reset restaure le Classique.
- La saisie ne nécessite jamais Entrée et reste fluide pendant tout le chrono.
- Le graphique, la projection et les statistiques utilisent les temps réels de chaque réponse.
- L’interface de partie reste épurée et stable.
- L’arrêt manuel fonctionne et interdit l’envoi du score.
- L’historique local conserve les scores, sans persister les mesures détaillées.
- Un profil n’est demandé qu’au moment d’ajouter un score au classement.
- Seuls Classique et Constance possèdent un classement.
- Chaque classement conserve le meilleur score par pseudonyme.
- L’absence de réseau n’empêche aucune fonction locale.
- `app.py` ne contient aucune règle CalculatorX.
- La suite complète passe avec `0 skipped`.

## Hors périmètre conservé pour la suite

### Orquantix

- séparer une température sémantique pouvant devenir négative de la progression par rang existante ;
- placer `I give up`, Timer, Indice et Mode dyslexique sur une même ligne responsive ;
- préparer de futurs easter eggs avec variantes orthographiques pour Nimègue, Sierre-Zinal/Trail, mille-feuille, brownie/`brwonie`, taboulé et éclipse ;
- les images de ces easter eggs seront fournies ultérieurement.

### Mapix

- nom du pays vers territoire à cliquer ;
- drapeau vers territoire puis nom ;
- mode exhaustif pour nommer tous les pays ;
- carte et drapeaux disponibles hors ligne.

Ces éléments feront chacun l’objet d’une conception et d’un plan séparés.
