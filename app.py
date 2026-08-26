from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template

from games.catalog import build_catalog
from games.registration import MountedGame

APP_NAME = "PROCRASTINATOR"


class Shell:
    """L'application. Ne connaît aucune règle de mini-jeu."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.games = build_catalog(data_dir)
        self._games_by_id = {game.metadata.id: game for game in self.games}

    def get_game(self, game_id: str) -> MountedGame:
        return self._games_by_id[game_id]


def create_app(shell: Shell) -> Flask:
    templates_dir = os.environ.get("PROCRASTINATOR_TEMPLATES", "templates")
    static_dir = os.environ.get("PROCRASTINATOR_STATIC", "static")
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    for game in shell.games:
        app.register_blueprint(game.blueprint)

    @app.route("/")
    def home():
        return render_template("index.html", games=shell.games)

    @app.route("/status")
    def status():
        game = shell.get_game("orquantix")
        if game.status is None:
            return jsonify({"error": "status unavailable"}), 404
        return jsonify(game.status())

    return app
