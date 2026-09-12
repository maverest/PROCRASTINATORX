# Mapix — spécification de conception

Date : 12 septembre 2026
Statut : conception validée

## Objectif

Ajouter à PROCRASTINATORX un troisième mini-jeu, **Mapix**, consacré aux pays du monde. Le jeu doit fonctionner entièrement hors ligne dans l'application macOS, rester rapide et épuré, et respecter la frontière existante entre la coquille et les règles propres à chaque jeu.

Mapix utilise une liste fermée de **195 États** : les 193 membres de l'ONU, plus le Vatican et la Palestine. Les territoires dépendants ne sont pas jouables dans cette première version.

## Périmètre de la première version

La première version comprend :

- quatre modes de jeu ;
- sept zones géographiques ;
- une carte interactive locale ;
- les drapeaux et noms français des 195 pays ;
- les statistiques de la partie qui vient de se terminer ;
- l'intégration de Mapix au menu de PROCRASTINATORX.

Elle ne comprend pas :

- de classement local ou en ligne ;
- d'historique des parties ;
- de sauvegarde ou de reprise d'une partie ;
- de compte joueur ;
- de dépendance à une connexion Internet.

Quitter, recharger ou recommencer abandonne donc la partie en cours. Le bouton de sortie demande confirmation pendant une partie active.

## Zones géographiques

Les zones proposées sont :

1. Monde
2. Afrique
3. Europe
4. Asie
5. Amérique du Nord
6. Amérique du Sud
7. Océanie

Chaque pays appartient à un seul continent, selon le classement géographique principal de l'ONU. Cette règle garantit que les listes continentales sont disjointes et que leur union contient exactement les 195 pays.

Répartition attendue :

- Afrique : 54 ;
- Europe : 44 ;
- Asie : 48 ;
- Amérique du Nord : 23 ;
- Amérique du Sud : 12 ;
- Océanie : 14.

Les cas transcontinentaux suivent ce classement : la Russie est en Europe ; la Turquie, Chypre, la Géorgie, l'Arménie, l'Azerbaïdjan et le Kazakhstan sont en Asie ; l'Égypte est en Afrique.

## Écran d'accueil de Mapix

L'écran est volontairement court. Il contient :

- un retour au menu des jeux ;
- une ligne de sélection du mode : **Territoire**, **Drapeau**, **Drapeau seul**, **Tous** ;
- une ligne de sélection de la zone ;
- un bouton principal **Jouer**.

Après un abandon ou une fin de partie, le joueur peut revenir à cet écran ou relancer avec les mêmes paramètres.

## Règles communes

Pour les trois modes à questions successives, les pays de la zone choisie sont mélangés au début de la partie et présentés une fois chacun. Le nom français du pays courant est toujours affiché clairement.

Une mauvaise sélection clignote brièvement en rouge, incrémente le compteur d'erreurs et laisse le joueur réessayer. Une bonne sélection reste visuellement validée. Le pays suivant n'apparaît que lorsque toutes les actions attendues pour le pays courant ont été réussies.

Le chrono démarre lorsque la première question est affichée. Il monte sans imposer de limite. La partie s'achève lorsque tous les pays de la zone ont été trouvés.

## Mode Territoire

Le nom d'un pays apparaît. Le joueur doit cliquer sur son territoire.

- Un clic incorrect compte comme une erreur et fait clignoter le territoire choisi en rouge.
- Un clic correct colore le territoire et passe au pays suivant.
- Les pays déjà trouvés restent colorés pour rendre la progression visible.

## Mode Drapeau

Le nom d'un pays apparaît. Le joueur doit accomplir deux actions :

1. choisir son drapeau dans le panneau droit ;
2. choisir son territoire sur la carte à gauche.

Les deux actions peuvent être réalisées dans n'importe quel ordre. Une action correcte est verrouillée visuellement et ne peut plus devenir incorrecte. Le pays suivant n'apparaît qu'après les deux bonnes réponses.

Le panneau droit est une grille défilante contenant les drapeaux de tous les pays de la zone qui ne sont pas encore entièrement validés. Les drapeaux restent assez grands pour être reconnus sans agrandir la fenêtre. Le drapeau du pays courant ne disparaît qu'après validation complète du drapeau et du territoire.

## Mode Drapeau seul

Le nom d'un pays apparaît et le joueur choisit uniquement son drapeau.

La carte est masquée afin de laisser la place à une grande grille défilante. Cette grille contient tous les drapeaux des pays restant à trouver. Une bonne réponse retire le drapeau de la grille et affiche le pays suivant.

## Mode Tous

La carte est muette et un champ unique permet de saisir les pays de la zone dans n'importe quel ordre.

- Une réponse correcte colore immédiatement le territoire et augmente le compteur.
- Un pays déjà trouvé est ignoré sans pénalité.
- Une réponse inconnue ou incorrecte validée compte comme une erreur.
- Le compteur affiche la progression sous la forme `42/195` ou l'équivalent pour le continent choisi.
- La liste des pays trouvés reste secondaire par rapport à la carte et au champ de saisie.

Les noms sont normalisés avant comparaison : casse ignorée, accents ignorés, apostrophes, traits d'union et espaces harmonisés. Des alias français usuels sont acceptés lorsqu'ils sont non ambigus, par exemple `USA`, `États-Unis` et `Etats Unis`. Chaque alias normalisé doit désigner un seul pays.

## Carte et navigation

Mapix utilise une carte SVG embarquée et interactive, dérivée des données vectorielles Natural Earth. Les données Natural Earth sont dans le domaine public et peuvent être adaptées et distribuées avec l'application : <https://www.naturalearthdata.com/about/terms-of-use/>.

La source retenue est la carte administrative mondiale Natural Earth au 1:10m, transformée en un SVG optimisé et limité aux besoins de Mapix. L'application n'effectue aucun téléchargement de carte.

Comportement :

- cadrage automatique sur la zone sélectionnée ;
- zoom à la molette et par boutons `+` et `−` ;
- déplacement de la carte par glisser ;
- couleurs distinctes pour un territoire neutre, trouvé, correctement sélectionné et incorrectement sélectionné ;
- aucune infobulle donnant le nom d'un pays pendant une question.

Les micro-États et petites îles disposent d'une cible interactive agrandie ou d'un marqueur discret. La géométrie réelle reste affichée lorsqu'elle est lisible. Ces cibles font partie des données testées et non d'exceptions écrites directement dans l'interface.

La sélection des 195 États est explicitement organisée par Mapix au-dessus des entités Natural Earth, qui contiennent aussi des territoires et reflètent des frontières de fait. La Palestine fait partie de la liste jouable conformément à la définition des 195 États retenue pour le jeu. Les zones disputées ne deviennent pas des réponses supplémentaires.

Les drapeaux sont stockés dans le catalogue sous forme de séquences Unicode régionales et rendus par macOS. Ils restent donc disponibles hors ligne sans ajouter 195 fichiers d'images ni une nouvelle licence d'actifs.

## Identité visuelle et disposition

Mapix possède une identité claire, cartographique et sobre, distincte des autres jeux mais compatible avec le menu général : fond clair, encre sombre, eau douce et accent chaud.

La disposition validée est la variante **Carte dominante** :

- grande carte à gauche ;
- panneau compact et défilant de drapeaux à droite ;
- nom du pays et progression au-dessus de la zone de jeu ;
- commandes secondaires discrètes.

En mode Territoire, la carte récupère l'espace du panneau inutile. En mode Drapeau seul, la grille récupère tout l'espace. Sur une fenêtre étroite, le panneau passe sous la carte sans réduire les drapeaux à une taille illisible.

## Résultats

À la fin d'une partie, l'écran affiche uniquement :

- **Temps** : durée totale ;
- **Sans faute** : nombre de pays terminés sans aucune mauvaise action, sauf dans le mode Tous où cette donnée est masquée ;
- **Erreurs** : nombre total de mauvaises actions validées ;
- **Précision** : part des actions correctes parmi toutes les actions validées.

Le nombre d'actions correctes attendu vaut :

- une par pays en mode Territoire ;
- deux par pays en mode Drapeau ;
- une par pays en mode Drapeau seul ;
- une par pays en mode Tous.

La précision est calculée ainsi :

`actions correctes / (actions correctes + erreurs) × 100`

Dans le mode Drapeau, une erreur de drapeau et une erreur de territoire sont donc comptées séparément. Dans le mode Tous, la statistique Sans faute est masquée car une saisie inconnue ne peut pas être attribuée de manière fiable à un pays particulier.

## Architecture

Mapix respecte le contrat `MountedGame` existant :

```text
games/mapix/
  __init__.py       métadonnées et construction du jeu
  countries.py      catalogue validé, normalisation et alias
  engine.py         modes, ordre, validation et statistiques
  routes.py         blueprint sous /games/mapix
  state.py          partie en mémoire, verrou et jeton de partie
templates/mapix/
  index.html        structure sans script en ligne
static/mapix/
  game.js           interactions et rendu de l'état
  map.js            zoom, déplacement et sélection SVG
  style.css         identité visuelle et disposition
  countries.json    données publiques nécessaires au navigateur
  world.svg         géométries et cibles cliquables
```

`games/catalog.py` importe uniquement le constructeur public de Mapix et l'ajoute après CalculatorX. `app.py` ne connaît aucune règle géographique.

Le serveur garde la partie courante en mémoire afin que les règles, les alias et le score soient testables indépendamment de l'interface. Chaque démarrage produit un jeton de partie ; toute réponse porte ce jeton afin qu'une réponse retardée d'une ancienne partie ne modifie pas la nouvelle. Les mutations passent par les méthodes verrouillées de l'état.

Le navigateur reçoit seulement les informations nécessaires à l'affichage. Il envoie une action typée (`territory`, `flag` ou `name`) et rend la réponse du serveur. La géométrie SVG reste un actif statique et le serveur valide les identifiants de pays, jamais des coordonnées.

## Routes prévues

- `GET /games/mapix/` : interface ;
- `POST /games/mapix/session` : démarre une partie avec un mode et une zone ;
- `GET /games/mapix/session` : état affichable de la partie courante ;
- `POST /games/mapix/answer` : valide une action ;
- `POST /games/mapix/quit` : abandonne la partie en mémoire.

Les modes internes sont `territory`, `flag-territory`, `flag-only` et `all`. Les zones internes sont `world`, `africa`, `europe`, `asia`, `north-america`, `south-america` et `oceania`.

Les données reçues sont validées strictement. Un mode, une zone, un type d'action, un identifiant ou un jeton inconnu renvoie une erreur JSON explicite sans modifier l'état.

## Gestion des défaillances

Tous les actifs étant embarqués, une absence de carte ou de catalogue est une erreur de paquetage, pas une situation réseau normale. L'interface affiche alors un message bref invitant à relancer l'application, tandis que les tests empêchent normalement la création d'un paquet incomplet.

Une requête arrivée après un abandon, une nouvelle partie ou un changement de pays ne peut pas être appliquée grâce au jeton et à l'index de question. Une double soumission d'une réponse correcte est idempotente et ne fausse ni le score ni les erreurs.

## Tests et critères d'acceptation

Les tests automatisés doivent vérifier :

- présence de Mapix en troisième position dans le menu ;
- montage exclusif sous `/games/mapix` ;
- exactement 195 pays et la répartition continentale attendue ;
- absence de doublon ou de pays sans continent ;
- unicité des identifiants et des alias normalisés ;
- correspondance entre les pays, les drapeaux, les formes SVG et les cibles des petits États ;
- fonctionnement des quatre modes et des sept zones ;
- ordre aléatoire sans répétition ;
- drapeau et territoire validables dans les deux ordres ;
- disparition des drapeaux au moment prévu dans les deux modes concernés ;
- répétition d'une erreur possible jusqu'à la bonne réponse ;
- calcul exact de Temps, Sans faute, Erreurs et Précision ;
- absence de pénalité pour un pays déjà trouvé dans le mode Tous ;
- rejet sans mutation des requêtes invalides ou périmées ;
- absence de scripts en ligne dans le template ;
- inclusion des actifs Mapix dans le paquet PyInstaller ;
- exécution complète de `pytest -rs` avec zéro test ignoré.

L'acceptation manuelle vérifie également que la carte reste fluide, que les drapeaux sont lisibles, que tous les petits États sont sélectionnables, que le panneau défile sans déplacer toute la page et que le jeu reste entièrement utilisable sans réseau.
