from __future__ import annotations

import os
from pathlib import Path

from games.calculatorx.leaderboard import LeaderboardClient
from games.calculatorx.routes import build_blueprint
from games.calculatorx.storage import CalculatorStorage
from games.registration import GameMetadata, MountedGame

GAME_ID = "calculatorx"
GAME_NAME = "CalculatorX"
DEFAULT_BASE_URL = ""


def build_game(data_dir: Path) -> MountedGame:
    storage = CalculatorStorage(data_dir / "calculatorx.sqlite3")
    leaderboard_client = LeaderboardClient(
        os.environ.get("CALCULATORX_LEADERBOARD_URL", DEFAULT_BASE_URL)
    )
    return MountedGame(
        metadata=GameMetadata(
            id=GAME_ID,
            name=GAME_NAME,
            description="120 secondes de calcul mental.",
            icon="±",
            theme="calculatorx",
            endpoint="calculatorx.index",
        ),
        blueprint=build_blueprint(storage=storage, leaderboard_client=leaderboard_client),
    )


__all__ = ["GAME_ID", "GAME_NAME", "build_game"]
