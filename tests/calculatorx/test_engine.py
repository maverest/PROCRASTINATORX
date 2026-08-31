import random

import pytest

from games.calculatorx.engine import (
    ConfigError,
    GameConfig,
    NumberRange,
    PROBLEM_COUNT,
    Problem,
    classic_config,
    constance_config,
    generate_constance_problem,
    generate_problem,
    generate_problems,
    parse_config,
    reserve_count,
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


class ConstanceRandom:
    def __init__(self, operation: str, template: str, integers: list[int]):
        self.choices = iter((operation, template))
        self.integers = iter(integers)

    def choice(self, values):
        value = next(self.choices)
        assert value in values
        return value

    def randint(self, minimum: int, maximum: int) -> int:
        value = next(self.integers)
        assert minimum <= value <= maximum
        return value


def valid_custom_payload(**overrides):
    payload = {
        "mode": "custom",
        "duration_seconds": 45,
        "operations": ["+", "−", "×", "÷"],
        "addition": {
            "left": {"minimum": 2, "maximum": 100},
            "right": {"minimum": 2, "maximum": 100},
        },
        "multiplication": {
            "left": {"minimum": 2, "maximum": 12},
            "right": {"minimum": 2, "maximum": 100},
        },
    }
    payload.update(overrides)
    return payload


def custom_config(
    *,
    operations,
    addition_left=(2, 100),
    addition_right=(2, 100),
    multiplication_left=(2, 12),
    multiplication_right=(2, 100),
):
    return parse_config(
        valid_custom_payload(
            operations=list(operations),
            addition={
                "left": {
                    "minimum": addition_left[0],
                    "maximum": addition_left[1],
                },
                "right": {
                    "minimum": addition_right[0],
                    "maximum": addition_right[1],
                },
            },
            multiplication={
                "left": {
                    "minimum": multiplication_left[0],
                    "maximum": multiplication_left[1],
                },
                "right": {
                    "minimum": multiplication_right[0],
                    "maximum": multiplication_right[1],
                },
            },
        )
    )


def test_classic_config_matches_zetamac():
    config = classic_config()

    assert config.duration_seconds == 120
    assert config.operations == ("+", "−", "×", "÷")
    assert config.addition_left == NumberRange(2, 100)
    assert config.multiplication_left == NumberRange(2, 12)


@pytest.mark.parametrize("duration", [0, 3601, 1.5, "120"])
def test_custom_duration_is_bounded_integer(duration):
    payload = valid_custom_payload(duration_seconds=duration)

    with pytest.raises(ConfigError) as error:
        parse_config(payload)

    assert error.value.field == "duration_seconds"


def test_custom_requires_one_operation():
    with pytest.raises(ConfigError) as error:
        parse_config(valid_custom_payload(operations=[]))

    assert error.value.field == "operations"


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
    assert generate_problem(classic_config(), StubRandom(operation, integers)) == expected


def test_problem_serializes_to_session_contract():
    problem = Problem(301, "÷", 7, 43)

    assert problem.as_dict() == {
        "left": 301,
        "operator": "÷",
        "right": 7,
        "answer": 43,
    }


def test_generate_problems_uses_fixed_default_size():
    problems = generate_problems(classic_config())

    assert len(problems) == PROBLEM_COUNT == 512


@pytest.mark.parametrize(
    ("duration_seconds", "expected"),
    [(1, 512), (120, 512), (121, 517), (3600, 15_360)],
)
def test_reserve_count_scales_custom_sessions_without_shrinking_the_minimum(
    duration_seconds, expected
):
    assert reserve_count(duration_seconds) == expected


def test_generated_divisions_are_always_exact():
    problems = generate_problems(classic_config(), count=2_000, rng=random.Random(42))
    divisions = [problem for problem in problems if problem.operator == "÷"]

    assert divisions
    assert all(problem.left % problem.right == 0 for problem in divisions)
    assert all(2 <= problem.right <= 12 for problem in divisions)


def test_generated_subtractions_are_strictly_positive():
    problems = generate_problems(classic_config(), count=2_000, rng=random.Random(42))
    subtractions = [problem for problem in problems if problem.operator == "−"]

    assert subtractions
    assert all(problem.answer > 0 for problem in subtractions)


def test_custom_addition_uses_both_operand_ranges():
    config = custom_config(
        operations=("+",), addition_left=(7, 7), addition_right=(90, 90)
    )

    assert generate_problem(config, random.Random(1)) == Problem(7, "+", 90, 97)


def test_custom_division_never_uses_zero_divisor():
    config = custom_config(
        operations=("÷",),
        multiplication_left=(0, 2),
        multiplication_right=(8, 8),
    )
    problems = generate_problems(config, count=200, rng=random.Random(4))

    assert all(problem.operator == "÷" and problem.right != 0 for problem in problems)
    assert all(problem.left % problem.right == 0 for problem in problems)


@pytest.mark.parametrize(
    ("operation", "template", "integers", "expected"),
    [
        ("+", "small-small", [3, 2], Problem(3, "+", 2, 5)),
        ("−", "same", [5], Problem(5, "−", 5, 0)),
        ("×", "identity", [32], Problem(1, "×", 32, 32)),
        ("÷", "zero", [9], Problem(0, "÷", 9, 0)),
    ],
)
def test_constance_generates_trivial_families(operation, template, integers, expected):
    rng = ConstanceRandom(operation, template, integers)

    assert generate_constance_problem(rng) == expected


def test_constance_division_is_always_defined_and_exact():
    problems = generate_problems(constance_config(), 2_000, random.Random(42))
    divisions = [problem for problem in problems if problem.operator == "÷"]

    assert divisions
    assert all(problem.right != 0 and problem.left % problem.right == 0 for problem in divisions)
