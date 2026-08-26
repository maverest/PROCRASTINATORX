from __future__ import annotations

from pathlib import Path

from games.orquantix import build_game as build_orquantix_game
from games.registration import MountedGame


def build_catalog(data_dir: Path) -> tuple[MountedGame, ...]:
    return (build_orquantix_game(data_dir),)
