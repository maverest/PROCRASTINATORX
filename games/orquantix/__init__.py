from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from games.orquantix import engine
from games.orquantix.dictionary import DICT_FILENAME, IDX_FILENAME, Littre
from games.orquantix.routes import build_blueprint
from games.orquantix.state import OrquantixState
from games.orquantix.vocabulary import (
    build_norm_map,
    build_pools,
    compute_difficulty_thresholds,
)

if TYPE_CHECKING:
    from games.registration import MountedGame

GAME_ID = "orquantix"
GAME_NAME = "Orquantix"
MODEL_FILENAME = "frWiki_no_phrase_no_postag_1000_skip_cut200.bin"
LEXIQUE_FILENAME = "Lexique383.tsv"

__all__ = ["GAME_ID", "GAME_NAME", "OrquantixState", "build_blueprint", "build_game", "load_resources"]


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


def load_resources(state: OrquantixState, data_dir: Path) -> None:
    """Charge le modèle, les pools et le dictionnaire.

    Déclenché à l'entrée dans le jeu, pas au démarrage de l'application :
    un quiz géographique n'a aucun usage d'un modèle Word2Vec de 126 Mo.
    """
    from gensim.models import KeyedVectors

    state.update(phase="loading", progress=0, detail="Chargement du modèle Word2Vec…")
    model = KeyedVectors.load_word2vec_format(str(data_dir / MODEL_FILENAME), binary=True)

    state.update(progress=60, detail="Filtrage du vocabulaire…")
    pools = build_pools(str(data_dir / LEXIQUE_FILENAME), set(model.key_to_index))
    if not pools.mystery_words:
        raise RuntimeError("Aucun mot éligible — vérifier Lexique383.tsv")

    state.update(progress=75, detail="Ouverture du dictionnaire…")
    try:
        littre = Littre(data_dir / IDX_FILENAME, data_dir / DICT_FILENAME)
    except (OSError, ValueError):
        littre = None  # le poisson doré retombera sur le voisin fort

    state.update(progress=85, detail="Tirage du mot mystère…")
    word = engine.get_daily_word(pools.mystery_words, state.game_index)
    neighbours = engine.get_neighbours(model, word)
    thresholds = compute_difficulty_thresholds(pools.mystery_words, pools.mystery_freq)

    state.update(
        model=model,
        littre=littre,
        pools=pools,
        norm_to_model=build_norm_map(list(model.key_to_index)),
        difficulty_thresholds=thresholds,
        mystery_word=word,
        neighbours=neighbours,
        top1000=engine.rank_map(neighbours),
        difficulty=engine.get_difficulty(word, pools.mystery_freq, thresholds),
        guesses=[],
        phase="ready",
        progress=100,
        detail="Prêt !",
    )
