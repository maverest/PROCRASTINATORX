import random

import pytest

from games.calculatorx.engine import (
    PROBLEM_COUNT,
    Problem,
    generate_problem,
    generate_problems,
)


class StubRandom:
    def __init__(self, operation: str, integers: list[int]):
        self.operation = operation
        self.integers = iter(integers)

    def choice(self, values):
        assert tuple(values) == ("+", "−", "×", "÷")
        return self.operation

    def randint(self, minimum: int, maximum: int) -> int:
        value = next(self.integers)
        assert minimum <= value <= maximum
        return value


@pytest.mark.parametrize(
    ("operation", "integers", "expected"),
    [
        ("+", [2, 100], Problem(2, "+", 100, 102)),
        ("−", [37, 58], Problem(95, "−", 37, 58)),
        ("×", [12, 100], Problem(12, "×", 100, 1200)),
        ("÷", [7, 43], Problem(301, "÷", 7, 43)),
    ],
)
def test_generate_problem_matches_classic_rules(operation, integers, expected):
    assert generate_problem(StubRandom(operation, integers)) == expected


def test_problem_serializes_to_session_contract():
    problem = Problem(301, "÷", 7, 43)

    assert problem.as_dict() == {
        "left": 301,
        "operator": "÷",
        "right": 7,
        "answer": 43,
    }


def test_generate_problems_uses_fixed_default_size():
    problems = generate_problems()

    assert len(problems) == PROBLEM_COUNT == 512


def test_generated_divisions_are_always_exact():
    problems = generate_problems(count=2_000, rng=random.Random(42))
    divisions = [problem for problem in problems if problem.operator == "÷"]

    assert divisions
    assert all(problem.left % problem.right == 0 for problem in divisions)
    assert all(2 <= problem.right <= 12 for problem in divisions)


def test_generated_subtractions_are_strictly_positive():
    problems = generate_problems(count=2_000, rng=random.Random(42))
    subtractions = [problem for problem in problems if problem.operator == "−"]

    assert subtractions
    assert all(problem.answer > 0 for problem in subtractions)
