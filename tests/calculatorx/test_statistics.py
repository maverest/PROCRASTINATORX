import pytest

from games.calculatorx.statistics import (
    OperationSummary,
    ResponseSample,
    project_score,
    summarize,
)


def test_summary_groups_and_uses_true_median():
    samples = [
        ResponseSample("+", 1000),
        ResponseSample("+", 3000),
        ResponseSample("+", 2000),
        ResponseSample("÷", 4500),
    ]

    summary = summarize(samples)

    assert summary["+"] == OperationSummary(3, 2000, 1000, 3000)
    assert summary["÷"] == OperationSummary(1, 4500, 4500, 4500)


def test_summary_uses_the_median_instead_of_the_average():
    summary = summarize(
        [
            ResponseSample("+", 1000),
            ResponseSample("+", 3000),
            ResponseSample("+", 10_000),
        ]
    )

    assert summary["+"] == OperationSummary(3, 3000, 1000, 10_000)


def test_summary_rounds_half_milliseconds_up():
    summary = summarize([ResponseSample("+", 1000), ResponseSample("+", 1001)])

    assert summary["+"] == OperationSummary(2, 1001, 1000, 1001)


def test_summary_orders_operations_for_a_stable_json_contract():
    summary = summarize(
        [
            ResponseSample("÷", 2000),
            ResponseSample("×", 1000),
            ResponseSample("−", 3000),
            ResponseSample("+", 4000),
        ]
    )

    assert list(summary) == ["+", "−", "×", "÷"]


@pytest.mark.parametrize(
    "payload",
    [
        {"operator": "?", "elapsed_ms": 1000},
        {"operator": "+", "elapsed_ms": True},
        {"operator": "+", "elapsed_ms": -1},
        {"operator": "+", "elapsed_ms": 3_600_001},
        {"operator": "+", "elapsed_ms": 1.5},
        {"operator": True, "elapsed_ms": 1000},
    ],
)
def test_response_sample_from_dict_rejects_invalid_json_values(payload):
    with pytest.raises(ValueError):
        ResponseSample.from_dict(payload)


def test_response_sample_from_dict_keeps_integer_milliseconds():
    sample = ResponseSample.from_dict({"operator": "×", "elapsed_ms": 3_600_000})

    assert sample == ResponseSample("×", 3_600_000)


def test_projection_starts_after_three_answers():
    assert project_score(2, 10_000, 120) is None
    assert project_score(3, 12_000, 120) == 30


def test_projection_handles_a_zero_elapsed_time_without_dividing_by_zero():
    assert project_score(3, 0, 120) is None


def test_projection_rounds_half_scores_up():
    assert project_score(3, 16_000, 120) == 23
