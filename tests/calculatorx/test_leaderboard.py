from __future__ import annotations

import pytest
import requests

from games.calculatorx.leaderboard import LeaderboardClient, LeaderboardUnavailable


class FakeResponse:
    def __init__(self, payload=None, *, error: Exception | None = None, json_error: Exception | None = None):
        self.payload = payload
        self.error = error
        self.json_error = json_error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeHttp:
    def __init__(self):
        self.responses: list[FakeResponse] = []
        self.calls: list[tuple[str, str, float, dict | None]] = []
        self.error: Exception | None = None

    def queue_json(self, payload):
        self.responses.append(FakeResponse(payload))

    def queue_response(self, response: FakeResponse):
        self.responses.append(response)

    def get(self, url, *, timeout):
        self.calls.append(("get", url, timeout, None))
        if self.error:
            raise self.error
        return self.responses.pop(0)

    def post(self, url, *, json, timeout):
        self.calls.append(("post", url, timeout, json))
        if self.error:
            raise self.error
        return self.responses.pop(0)


@pytest.fixture
def fake_http():
    return FakeHttp()


def score_record(*, score=73):
    return {
        "rank": 1,
        "nickname": "Ada",
        "score": score,
        "achieved_at": "2026-08-31T10:00:00Z",
    }


def test_client_strips_trailing_slash_uses_timeout_and_validates_list_response(fake_http):
    fake_http.queue_json({"scores": [score_record()]})

    assert LeaderboardClient("https://scores.example///", http=fake_http).list_scores("classic") == [
        score_record()
    ]
    assert fake_http.calls == [
        ("get", "https://scores.example/leaderboards/classic", 3.0, None)
    ]


def test_client_posts_only_worker_score_payload_and_returns_validated_record(fake_http):
    fake_http.queue_json(score_record(score=74))

    record = LeaderboardClient("https://scores.example", http=fake_http).submit_score(
        "constance", "Ada", 74
    )

    assert record == score_record(score=74)
    assert fake_http.calls == [
        (
            "post",
            "https://scores.example/scores",
            3.0,
            {"mode": "constance", "nickname": "Ada", "score": 74},
        )
    ]


def test_disabled_client_makes_no_http_call(fake_http):
    client = LeaderboardClient("   ", http=fake_http)

    with pytest.raises(LeaderboardUnavailable):
        client.list_scores("classic")

    assert fake_http.calls == []


@pytest.mark.parametrize("method", ["list", "submit"])
def test_client_wraps_timeout_as_unavailable(fake_http, method):
    fake_http.error = requests.Timeout("offline")
    client = LeaderboardClient("https://scores.example", http=fake_http)

    with pytest.raises(LeaderboardUnavailable):
        (client.list_scores("classic") if method == "list" else client.submit_score("classic", "Ada", 1))


def test_client_wraps_http_error_and_bad_json_as_unavailable(fake_http):
    client = LeaderboardClient("https://scores.example", http=fake_http)
    fake_http.queue_response(FakeResponse(error=requests.HTTPError("bad gateway")))

    with pytest.raises(LeaderboardUnavailable):
        client.list_scores("classic")

    fake_http.queue_response(FakeResponse(json_error=ValueError("not json")))
    with pytest.raises(LeaderboardUnavailable):
        client.list_scores("classic")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"scores": {}},
        {"scores": [score_record(), score_record()] * 51},
        {"scores": [{**score_record(), "rank": True}]},
        {"scores": [{**score_record(), "score": True}]},
        {"scores": [{**score_record(), "rank": 0}]},
        {"scores": [{**score_record(), "score": 10_000}]},
        {"scores": [{**score_record(), "nickname": ""}]},
        {"scores": [{**score_record(), "achieved_at": 7}]},
        {"scores": [{**score_record(), "achieved_at": "2026-08-31"}]},
        {"scores": [score_record()], "unexpected": True},
    ],
)
def test_client_rejects_malformed_list_shapes(fake_http, payload):
    fake_http.queue_json(payload)

    with pytest.raises(LeaderboardUnavailable):
        LeaderboardClient("https://scores.example", http=fake_http).list_scores("classic")


@pytest.mark.parametrize("mode", ["custom", "CLASSIC", True, None])
def test_client_rejects_invalid_mode_without_http_call(fake_http, mode):
    client = LeaderboardClient("https://scores.example", http=fake_http)

    with pytest.raises(LeaderboardUnavailable):
        client.list_scores(mode)

    assert fake_http.calls == []


@pytest.mark.parametrize(
    "nickname, score",
    [("", 1), ("Ada", True), ("Ada", -1), ("Ada", 10_000), (7, 1)],
)
def test_client_rejects_invalid_submission_before_http_call(fake_http, nickname, score):
    client = LeaderboardClient("https://scores.example", http=fake_http)

    with pytest.raises(LeaderboardUnavailable):
        client.submit_score("classic", nickname, score)

    assert fake_http.calls == []
