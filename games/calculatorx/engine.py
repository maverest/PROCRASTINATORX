from __future__ import annotations

import random
from math import ceil
from dataclasses import asdict, dataclass
from typing import Protocol, TypeVar

DURATION_SECONDS = 120
PROBLEM_COUNT = 512
OPERATIONS = ("+", "−", "×", "÷")
CONSTANCE_OPERATIONS = OPERATIONS
T = TypeVar("T")


class RandomSource(Protocol):
    def choice(self, values: tuple[T, ...]) -> T:
        raise NotImplementedError

    def randint(self, minimum: int, maximum: int) -> int:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class NumberRange:
    minimum: int
    maximum: int


@dataclass(frozen=True, slots=True)
class GameConfig:
    mode: str
    duration_seconds: int
    operations: tuple[str, ...]
    addition_left: NumberRange
    addition_right: NumberRange
    multiplication_left: NumberRange
    multiplication_right: NumberRange


class ConfigError(ValueError):
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.field = field


@dataclass(frozen=True, slots=True)
class Problem:
    left: int
    operator: str
    right: int
    answer: int

    def as_dict(self) -> dict[str, int | str]:
        return asdict(self)


def classic_config() -> GameConfig:
    return GameConfig(
        mode="classic",
        duration_seconds=DURATION_SECONDS,
        operations=OPERATIONS,
        addition_left=NumberRange(2, 100),
        addition_right=NumberRange(2, 100),
        multiplication_left=NumberRange(2, 12),
        multiplication_right=NumberRange(2, 100),
    )


def constance_config() -> GameConfig:
    return GameConfig(
        mode="constance",
        duration_seconds=DURATION_SECONDS,
        operations=CONSTANCE_OPERATIONS,
        addition_left=NumberRange(0, 5),
        addition_right=NumberRange(0, 5),
        multiplication_left=NumberRange(0, 100),
        multiplication_right=NumberRange(0, 100),
    )


def parse_config(payload: object) -> GameConfig:
    if not isinstance(payload, dict):
        raise ConfigError("La configuration doit être un objet.", "config")

    mode = payload.get("mode")
    if mode == "classic":
        return classic_config()
    if mode != "custom":
        raise ConfigError("Mode inconnu.", "mode")

    duration_seconds = _integer(payload.get("duration_seconds"), "duration_seconds")
    if not 1 <= duration_seconds <= 3600:
        raise ConfigError("La durée doit être comprise entre 1 et 3600.", "duration_seconds")

    raw_operations = payload.get("operations")
    if not isinstance(raw_operations, (list, tuple)) or not raw_operations:
        raise ConfigError("Choisis au moins une opération.", "operations")
    if any(operation not in OPERATIONS for operation in raw_operations):
        raise ConfigError("Opération inconnue.", "operations")
    if len(set(raw_operations)) != len(raw_operations):
        raise ConfigError("Chaque opération ne peut être choisie qu'une fois.", "operations")
    operations = tuple(raw_operations)

    addition = _mapping(payload.get("addition"), "addition")
    multiplication = _mapping(payload.get("multiplication"), "multiplication")
    addition_left = _parse_range(addition.get("left"), "addition.left")
    addition_right = _parse_range(addition.get("right"), "addition.right")
    multiplication_left = _parse_range(multiplication.get("left"), "multiplication.left")
    multiplication_right = _parse_range(multiplication.get("right"), "multiplication.right")

    if "÷" in operations and multiplication_left.maximum == 0:
        raise ConfigError(
            "Le diviseur doit pouvoir être différent de zéro.", "multiplication.left"
        )

    return GameConfig(
        mode="custom",
        duration_seconds=duration_seconds,
        operations=operations,
        addition_left=addition_left,
        addition_right=addition_right,
        multiplication_left=multiplication_left,
        multiplication_right=multiplication_right,
    )


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigError("Cette valeur doit être un objet.", field)
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError("Cette valeur doit être un entier.", field)
    return value


def _parse_range(value: object, field: str) -> NumberRange:
    range_payload = _mapping(value, field)
    minimum = _integer(range_payload.get("minimum"), f"{field}.minimum")
    maximum = _integer(range_payload.get("maximum"), f"{field}.maximum")
    if not 0 <= minimum <= 9999:
        raise ConfigError("Le minimum doit être compris entre 0 et 9999.", f"{field}.minimum")
    if not 0 <= maximum <= 9999:
        raise ConfigError("Le maximum doit être compris entre 0 et 9999.", f"{field}.maximum")
    if minimum > maximum:
        raise ConfigError("Le minimum ne peut pas dépasser le maximum.", field)
    return NumberRange(minimum, maximum)


def generate_problem(config: GameConfig, rng: RandomSource) -> Problem:
    if config.mode == "constance":
        return generate_constance_problem(rng)

    operation = rng.choice(config.operations)
    if operation in ("+", "−"):
        first = _draw(config.addition_left, rng)
        second = _draw(config.addition_right, rng)
        if operation == "+":
            return Problem(first, operation, second, first + second)
        return Problem(first + second, operation, first, second)

    first = _draw(config.multiplication_left, rng, nonzero=operation == "÷")
    second = _draw(config.multiplication_right, rng)
    if operation == "×":
        return Problem(first, operation, second, first * second)
    return Problem(first * second, operation, first, second)


def generate_constance_problem(rng: RandomSource) -> Problem:
    operation = rng.choice(CONSTANCE_OPERATIONS)
    if operation == "+":
        return _generate_constance_addition(rng)
    if operation == "−":
        return _generate_constance_subtraction(rng)
    if operation == "×":
        return _generate_constance_multiplication(rng)
    return _generate_constance_division(rng)


def _generate_constance_addition(rng: RandomSource) -> Problem:
    template = rng.choice(("small-small", "identity"))
    if template == "small-small":
        left = rng.randint(0, 5)
        right = rng.randint(0, 5)
    else:
        left = rng.choice((0, 1))
        right = rng.randint(0, 100)
    return Problem(left, "+", right, left + right)


def _generate_constance_subtraction(rng: RandomSource) -> Problem:
    template = rng.choice(("zero", "same", "sum-minus-first"))
    if template == "zero":
        left = rng.randint(0, 100)
        right = 0
    elif template == "same":
        left = rng.randint(0, 100)
        right = left
    else:
        first = rng.randint(0, 5)
        answer = rng.randint(0, 5)
        left = first + answer
        right = first
    return Problem(left, "−", right, left - right)


def _generate_constance_multiplication(rng: RandomSource) -> Problem:
    template = rng.choice(("zero", "identity"))
    left = 0 if template == "zero" else 1
    right = rng.randint(0, 100)
    return Problem(left, "×", right, left * right)


def _generate_constance_division(rng: RandomSource) -> Problem:
    template = rng.choice(("zero", "one", "same"))
    value = rng.randint(1, 100)
    if template == "zero":
        return Problem(0, "÷", value, 0)
    if template == "one":
        return Problem(value, "÷", 1, value)
    return Problem(value, "÷", value, 1)


def _draw(number_range: NumberRange, rng: RandomSource, *, nonzero: bool = False) -> int:
    minimum = max(1, number_range.minimum) if nonzero else number_range.minimum
    return rng.randint(minimum, number_range.maximum)


def generate_problems(
    config: GameConfig,
    count: int = PROBLEM_COUNT,
    rng: RandomSource | None = None,
) -> list[Problem]:
    source = rng if rng is not None else random.SystemRandom()
    return [generate_problem(config, source) for _ in range(count)]


def reserve_count(duration_seconds: int) -> int:
    """Return enough locally generated problems for the configured session."""
    return max(PROBLEM_COUNT, ceil(PROBLEM_COUNT * duration_seconds / DURATION_SECONDS))
