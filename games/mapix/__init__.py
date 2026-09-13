"""Le mini-jeu de géographie Mapix."""

from __future__ import annotations

import os
from pathlib import Path

from games.registration import GameMetadata, MountedGame
from .countries import CountryCatalog
from .routes import build_blueprint
from .state import MapixState

GAME_ID = "mapix"
GAME_NAME = "Mapix"


def build_game(data_dir: Path) -> MountedGame:
    default_static_root = Path(__file__).resolve().parents[2] / "static"
    static_root = Path(os.environ.get("PROCRASTINATOR_STATIC", default_static_root))
    catalog = CountryCatalog.from_json(static_root / "mapix/countries.json")
    return MountedGame(
        metadata=GameMetadata(
            id=GAME_ID,
            name=GAME_NAME,
            description="Quiz des pays du monde.",
            icon="⌖",
            theme="mapix",
            endpoint="mapix.index",
        ),
        blueprint=build_blueprint(MapixState(catalog)),
    )


__all__ = ["GAME_ID", "GAME_NAME", "build_game"]
