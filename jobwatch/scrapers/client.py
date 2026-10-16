"""Shared HTTP client for scraper requests."""

import shlex
import time
from typing import Any

import requests


MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = 1


class HTTPResponseError(ValueError):
    """An unsuccessful HTTP response with its status code preserved."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def _curl_command(request: requests.PreparedRequest) -> str:
    args = ["curl", "--request", request.method or "GET", request.url or ""]
    for name, value in request.headers.items():
        args.extend(("--header", f"{name}: {value}"))

    if request.body is not None:
        body = request.body
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="surrogateescape")
        args.extend(("--data-binary", body))
    return shlex.join(args)


def _error_message(response: requests.Response | None, message: str) -> str:
    if response is None:
        return f"Error no response: {message}"
    response_message = response.text or message
    return f"Error {response.status_code}: {response_message}"


class _CurlSession(requests.Session):
    """Print every prepared request, including requests followed by redirects."""

    def send(self, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        print(_curl_command(request))
        return super().send(request, **kwargs)


def request_json(method: str, url: str, **kwargs: Any) -> Any:
    """Send a JSON request, logging cURL and retrying timeouts only.

    Timeout failures receive up to four total attempts with 1, 2, and 4 second
    exponential backoff. Other request failures, unsuccessful HTTP responses,
    and JSON parsing errors are raised immediately with their response details.
    """
    timeout = kwargs.pop("timeout", 10)
    with _CurlSession() as session:
        prepared = session.prepare_request(requests.Request(method, url, **kwargs))
        settings = session.merge_environment_settings(prepared.url, {}, None, None, None)

        for attempt in range(MAX_ATTEMPTS):
            try:
                response = session.send(
                    prepared,
                    timeout=timeout,
                    allow_redirects=True,
                    **settings,
                )
            except requests.Timeout as exc:
                if attempt + 1 == MAX_ATTEMPTS:
                    raise ValueError(_error_message(None, str(exc))) from exc
                time.sleep(RETRY_BACKOFF_SECONDS * (2 ** attempt))
                continue
            except requests.RequestException as exc:
                raise ValueError(
                    _error_message(getattr(exc, "response", None), str(exc))
                ) from exc

            if not response.ok:
                raise HTTPResponseError(
                    _error_message(response, response.reason or "HTTP request failed"),
                    response.status_code,
                )

            try:
                return response.json()
            except (requests.exceptions.JSONDecodeError, ValueError) as exc:
                raise ValueError(_error_message(response, str(exc))) from exc

    raise AssertionError("unreachable")
