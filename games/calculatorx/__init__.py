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
