# PROCRASTINATOR

<img width="712" height="939" alt="image" src="https://github.com/user-attachments/assets/ad6ef5d5-5446-4c57-abd5-4bd6d827d1cc" />

Une petite application macOS regroupant des mini-jeux. Le premier est
**Orquantix**, un jeu de proximité sémantique en français.

## Jouer depuis les sources

```bash
git clone https://github.com/maverest/PROCRASTINATORX.git
cd PROCRASTINATORX
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Au premier lancement, l'application télécharge ses ressources — Lexique383,
un modèle Word2Vec français et le dictionnaire Littré, environ 180 Mo au
total — dans `~/Library/Application Support/Procrastinator/`. Les lancements
suivants sont immédiats.

Au lancement, PROCRASTINATOR ouvre son menu de mini-jeux. Orquantix ne charge
ses ressources qu’au moment où sa carte est ouverte.

`python main.py --design` ouvre l'interface dans le navigateur par défaut
plutôt que dans la fenêtre native, ce qui donne accès aux outils de
développement.

Pour lancer directement le projet depuis le dossier local avec l'environnement
déjà installé :

```bash
cd /Users/mverest/Desktop/PROCRASTINATORX
.venv/bin/python main.py
```

## Construire l'application

```bash
cd /Users/mverest/Desktop/PROCRASTINATORX
./build.sh
open dist/PROCRASTINATOR.app
```

Le script crée son propre environnement virtuel (`.venv_build`), installe
les dépendances nécessaires et produit `dist/PROCRASTINATOR.app` avec
PyInstaller. L'application garde l'icône Orquantix existante
(`build_assets/Orquantix.icns`) : aucune icône PROCRASTINATOR n'a encore été
créée.

## Tests

```bash
source .venv/bin/activate
python -m pytest -rs
```

La suite doit se terminer avec **0 skipped** : un test ignoré signale que les
ressources réelles d’Orquantix ne sont pas disponibles et doit être résolu
avant de considérer la vérification comme réussie.

## Orquantix

Trouver le mot mystère — toujours un nom commun — en proposant des mots.
Chaque proposition reçoit une **température** de 0 à 100 : 50° signifie que
le mot fait partie des mille plus proches voisins du mot mystère, et son
**rang** apparaît alors. L'orque commente.

## CalculatorX

Résoudre le plus de calculs possible, entièrement au clavier après le
lancement :

- **Classique** : 120 secondes, avec les opérations et les bornes de Zetamac ;
- **Personnalisé** : durée, opérations et bornes configurables, avec un bouton
  Reset qui rétablit les réglages classiques ;
- **Constance** : 120 secondes de calculs faciles ou volontairement absurdes,
  construits autour de 0, 1 et de petits nombres.

Les scores des parties sont conservés dans un historique local sur le Mac.
Les statistiques détaillées affichées sont celles de la dernière séance. Il
n'y a pas encore de classement partagé entre plusieurs machines : son
hébergement distant fera l'objet d'une étape séparée.

## Ressources et attributions

Les ressources téléchargées au premier lancement viennent de trois sources :

- **Lexique383**, base de données lexicale du français —
  [lexique.org](http://www.lexique.org)
- un modèle de vecteurs de mots (Word2Vec, français)
- le **dictionnaire Littré** : texte d'Émile Littré, domaine public ;
  encodage XML par François Gannaz — [littre.org](https://littre.org),
  sous licence [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
