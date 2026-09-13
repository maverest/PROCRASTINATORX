from __future__ import annotations

from pathlib import Path

from games.calculatorx import build_game as build_calculatorx_game
from games.mapix import build_game as build_mapix_game
from games.orquantix import build_game as build_orquantix_game
from games.registration import MountedGame


def build_catalog(data_dir: Path) -> tuple[MountedGame, ...]:
    return (
        build_orquantix_game(data_dir),
        build_calculatorx_game(data_dir),
        build_mapix_game(data_dir),
    )
