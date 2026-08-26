from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, redirect, url_for

from games.orquantix import GAME_ID, build_blueprint
from games.orquantix.runtime import OrquantixRuntime

APP_NAME = "PROCRASTINATOR"


class Shell:
    """L'application. Ne connaît aucune règle de mini-jeu."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.orquantix_runtime = OrquantixRuntime(data_dir)
        self.orquantix = self.orquantix_runtime.state

    def ensure_loaded(self, game_id: str) -> None:
        """Déclenche le chargement d'un jeu, une seule fois."""
        if game_id != GAME_ID:
            raise KeyError(game_id)
        self.orquantix_runtime.ensure_loaded()


def create_app(shell: Shell) -> Flask:
    templates_dir = os.environ.get("PROCRASTINATOR_TEMPLATES", "templates")
    static_dir = os.environ.get("PROCRASTINATOR_STATIC", "static")
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    app.register_blueprint(
        build_blueprint(shell.orquantix, on_load=lambda: shell.ensure_loaded(GAME_ID))
    )

    @app.route("/")
    def home():
        # Phase 2 : le menu de PROCRASTINATOR. En attendant, on entre dans le jeu.
        # Le chargement paresseux se déclenche sur l'index du jeu lui-même
        # (routes.py), pas ici : cette redirection l'atteint de toute façon,
        # et un accès direct à /games/orquantix/ le déclenche aussi.
        return redirect(url_for("orquantix.index"))

    @app.route("/status")
    def status():
        return jsonify(shell.orquantix.snapshot())

    return app
