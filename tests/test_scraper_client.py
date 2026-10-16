import requests
import pytest

from jobwatch.scrapers import client


class JsonResponse:
    def __init__(self, status_code=200, payload=None, text="", reason=""):
        self.status_code = status_code
        self.payload = payload
        self.text = text
        self.reason = reason
        self.ok = 200 <= status_code < 400

    def json(self):
        return self.payload


class MalformedJsonResponse(JsonResponse):
    def json(self):
        raise ValueError("invalid JSON")


@pytest.mark.parametrize(
    "timeout_error",
    [requests.ConnectTimeout("connect timed out"), requests.ReadTimeout("read timed out")],
)
def test_request_json_retries_timeouts_and_returns_success(
    monkeypatch, timeout_error
):
    outcomes = [timeout_error, JsonResponse(payload={"ok": True})]
    sleeps = []

    def send(self, request, **kwargs):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(client._CurlSession, "send", send)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    assert client.request_json("GET", "https://example.test/jobs") == {"ok": True}
    assert sleeps == [1]


def test_request_json_exhausts_timeout_retries_with_useful_error(monkeypatch):
    attempts = []
    sleeps = []

    def send(self, request, **kwargs):
        attempts.append(request)
        raise requests.ReadTimeout("read timed out")

    monkeypatch.setattr(client._CurlSession, "send", send)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    with pytest.raises(ValueError, match="Error no response: read timed out"):
        client.request_json("GET", "https://example.test/jobs")

    assert len(attempts) == client.MAX_ATTEMPTS
    assert sleeps == [1, 2, 4]


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (JsonResponse(404, text="not found", reason="Not Found"), "Error 404: not found"),
        (JsonResponse(403, text="forbidden", reason="Forbidden"), "Error 403: forbidden"),
        (JsonResponse(401, text="unauthorized", reason="Unauthorized"), "Error 401: unauthorized"),
        (JsonResponse(429, text="too many requests", reason="Too Many Requests"), "Error 429: too many requests"),
        (JsonResponse(500, text="server error", reason="Internal Server Error"), "Error 500: server error"),
        (requests.ConnectionError("connection refused"), "Error no response: connection refused"),
        (requests.exceptions.ContentDecodingError("invalid response encoding"), "invalid response encoding"),
        (MalformedJsonResponse(text="{"), r"Error 200: \{"),
    ],
)
def test_request_json_does_not_retry_non_timeout_failures(
    monkeypatch, failure, message
):
    attempts = []
    sleeps = []

    def send(self, request, **kwargs):
        attempts.append(request)
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(client._CurlSession, "send", send)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    with pytest.raises(ValueError, match=message):
        client.request_json("GET", "https://example.test/jobs")

    assert len(attempts) == 1
    assert sleeps == []
