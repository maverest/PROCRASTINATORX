from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from flask import Blueprint


@dataclass(frozen=True, slots=True)
class GameMetadata:
    id: str
    name: str
    description: str
    icon: str
    theme: str
    endpoint: str


@dataclass(frozen=True, slots=True)
class MountedGame:
    metadata: GameMetadata
    blueprint: Blueprint
    status: Callable[[], dict] | None = None
