from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Protocol, TypeVar

DURATION_SECONDS = 120
PROBLEM_COUNT = 512
OPERATIONS = ("+", "−", "×", "÷")
T = TypeVar("T")


class RandomSource(Protocol):
    def choice(self, values: tuple[T, ...]) -> T:
        raise NotImplementedError

    def randint(self, minimum: int, maximum: int) -> int:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Problem:
    left: int
    operator: str
    right: int
    answer: int

    def as_dict(self) -> dict[str, int | str]:
        return asdict(self)


def generate_problem(rng: RandomSource) -> Problem:
    operation = rng.choice(OPERATIONS)
    if operation in ("+", "−"):
        first = rng.randint(2, 100)
        second = rng.randint(2, 100)
        if operation == "+":
            return Problem(first, operation, second, first + second)
        return Problem(first + second, operation, first, second)

    small = rng.randint(2, 12)
    large = rng.randint(2, 100)
    if operation == "×":
        return Problem(small, operation, large, small * large)
    return Problem(small * large, operation, small, large)


def generate_problems(
    count: int = PROBLEM_COUNT,
    rng: RandomSource | None = None,
) -> list[Problem]:
    source = rng if rng is not None else random.SystemRandom()
    return [generate_problem(source) for _ in range(count)]
