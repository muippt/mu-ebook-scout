"""Shared HTTP helpers for source adapters (stdlib urllib only).

Every adapter goes through `http_get_json` / `http_get_text` so that tests
can monkeypatch a single seam instead of hitting the real network.

GitHub API rate limits are 60 requests/hour for anonymous callers and
5,000/hour with a personal access token. Users can raise the limit by
setting ``GITHUB_TOKEN`` (or ``BOOKSCOUT_GITHUB_TOKEN``) in their
environment — see README "GitHub API token" section. The token is read
from the environment only, never stored, logged, or hard-coded, and is
attached exclusively to ``api.github.com`` requests.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from bookscout.core.model import SourceError

#: Project user agent — no cookies, tokens or keys are ever attached.
USER_AGENT = "mu-ebook-scout/1.4 (+https://github.com/muippt/mu-ebook-scout)"

#: Hosts that receive the user's GitHub token when one is configured.
_GITHUB_HOSTS = {"api.github.com"}

#: Fixed backoff schedule for retries (seconds), len == max extra attempts.
_BACKOFF = (0.5, 1.0, 2.0)


def github_token() -> str:
    """Return the configured GitHub token, or an empty string.

    Checked in order: ``BOOKSCOUT_GITHUB_TOKEN`` (project-specific,
    takes precedence) then ``GITHUB_TOKEN`` (the ecosystem-wide
    convention shared by gh, git-credential and many tools).
    """
    return (os.environ.get("BOOKSCOUT_GITHUB_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
            or "").strip()


def _build_request(url: str, user_agent: str = "") -> urllib.request.Request:
    """Build a GET request, attaching the GitHub token if applicable.

    ``user_agent`` overrides the project UA for hosts that reject
    non-browser clients (e.g. librivox.org returns 404 for tool UAs).
    """
    headers = {"User-Agent": user_agent or USER_AGENT}
    host = urllib.parse.urlparse(url).hostname or ""
    if host in _GITHUB_HOSTS:
        token = github_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def _open(url: str, timeout: float, max_retries: int, user_agent: str = "") -> bytes:
    """GET `url` and return the raw body, retrying with backoff.

    Raises SourceError on network errors, HTTP error statuses and after
    exhausting the retry budget. Credentials (when configured) are only
    sent to GitHub API hosts, never to any book source.
    """
    req = _build_request(url, user_agent)
    body: bytes | None = None
    last_err: Exception | None = None
    attempts = max(1, max_retries + 1)
    for attempt in range(attempts):
        if attempt:
            time.sleep(_BACKOFF[min(attempt - 1, len(_BACKOFF) - 1)])
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
            return body
        except urllib.error.HTTPError as exc:
            # A definitive server answer: do not retry 4xx (except 429).
            if exc.code == 429 and attempt < attempts - 1:
                last_err = exc
                continue
            exc.read()
            raise SourceError(f"HTTP {exc.code} for {url}") from exc
        except Exception as exc:  # URLError, timeout, ConnectionError...
            last_err = exc
    raise SourceError(f"request failed for {url}: {last_err}") from last_err


def http_get_json(
    url: str, timeout: float = 15.0, max_retries: int = 2, user_agent: str = ""
) -> Any:
    """GET `url` and parse a JSON document.

    Non-JSON payloads raise SourceError (treated as a parse failure).
    """
    body = _open(url, timeout, max_retries, user_agent)
    try:
        return json.loads(body.decode("utf-8", errors="strict"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SourceError(f"invalid JSON from {url}: {exc}") from exc


def http_get_text(
    url: str, timeout: float = 15.0, max_retries: int = 2, user_agent: str = ""
) -> str:
    """GET `url` and return the body as text (UTF-8 with fallback)."""
    body = _open(url, timeout, max_retries, user_agent)
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("utf-8", errors="replace")


def quote_path(value: str) -> str:
    """URL-encode a path segment (safe for CJK titles)."""
    return urllib.parse.quote(value, safe="")
