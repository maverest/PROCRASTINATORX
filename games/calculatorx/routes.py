from __future__ import annotations

from collections.abc import Callable

from flask import Blueprint, jsonify, render_template

from games.calculatorx.engine import (
    DURATION_SECONDS,
    PROBLEM_COUNT,
    Problem,
    generate_problems,
)
from games.calculatorx.storage import CalculatorStorage

BLUEPRINT_NAME = "calculatorx"
URL_PREFIX = "/games/calculatorx"
ProblemFactory = Callable[[int], list[Problem]]


def build_blueprint(
    problem_factory: ProblemFactory = generate_problems,
    storage: CalculatorStorage | None = None,
) -> Blueprint:
    del storage
    blueprint = Blueprint(BLUEPRINT_NAME, __name__, url_prefix=URL_PREFIX)

    @blueprint.get("/")
    def index():
        return render_template("calculatorx/index.html")

    @blueprint.post("/session")
    def session():
        problems = problem_factory(PROBLEM_COUNT)
        return jsonify(
            duration_seconds=DURATION_SECONDS,
            problems=[problem.as_dict() for problem in problems],
        )

    return blueprint
