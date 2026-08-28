from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median

from games.calculatorx.engine import OPERATIONS

MAX_ELAPSED_MS = 3_600_000


@dataclass(frozen=True, slots=True)
class ResponseSample:
    operator: str
    elapsed_ms: int

    def __post_init__(self) -> None:
        if self.operator not in OPERATIONS:
            raise ValueError("Opération inconnue.")
        if isinstance(self.elapsed_ms, bool) or not isinstance(self.elapsed_ms, int):
            raise ValueError("La durée doit être un entier.")
        if not 0 <= self.elapsed_ms <= MAX_ELAPSED_MS:
            raise ValueError("La durée doit être comprise entre 0 et 3600000 ms.")

    @classmethod
    def from_dict(cls, value: object) -> ResponseSample:
        if not isinstance(value, Mapping):
            raise ValueError("Un échantillon doit être un objet.")

        operator = value.get("operator")
        elapsed_ms = value.get("elapsed_ms")
        if isinstance(operator, bool) or not isinstance(operator, str):
            raise ValueError("L’opération doit être une chaîne.")
        if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, int):
            raise ValueError("La durée doit être un entier.")
        return cls(operator, elapsed_ms)


@dataclass(frozen=True, slots=True)
class OperationSummary:
    count: int
    median_ms: int
    fastest_ms: int
    slowest_ms: int


def summarize(samples: Sequence[ResponseSample]) -> dict[str, OperationSummary]:
    grouped = {operation: [] for operation in OPERATIONS}
    for sample in samples:
        grouped[sample.operator].append(sample.elapsed_ms)

    return {
        operation: OperationSummary(
            count=len(elapsed_times),
            median_ms=_round_half_up(median(elapsed_times)),
            fastest_ms=min(elapsed_times),
            slowest_ms=max(elapsed_times),
        )
        for operation in OPERATIONS
        if (elapsed_times := grouped[operation])
    }


def project_score(score: int, elapsed_ms: int, duration_seconds: int) -> int | None:
    if (
        isinstance(score, bool)
        or not isinstance(score, int)
        or score < 3
        or isinstance(elapsed_ms, bool)
        or not isinstance(elapsed_ms, int)
        or elapsed_ms <= 0
        or isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, int)
        or duration_seconds <= 0
    ):
        return None

    numerator = score * duration_seconds * 1_000
    return (2 * numerator + elapsed_ms) // (2 * elapsed_ms)


def _round_half_up(value: int | float) -> int:
    return int(value + 0.5)
