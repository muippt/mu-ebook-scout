"""Tests for GitHub token support in the shared HTTP layer.

The token must come from the environment, be attached ONLY to
api.github.com requests, and never leak to any other host.
"""
import urllib.request

import pytest

from bookscout.core.model import SourceError
from bookscout.sources import _http


class TestGithubToken:
    def test_empty_when_no_env(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("BOOKSCOUT_GITHUB_TOKEN", raising=False)
        assert _http.github_token() == ""

    def test_project_env_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "generic-token")
        monkeypatch.setenv("BOOKSCOUT_GITHUB_TOKEN", "project-token")
        assert _http.github_token() == "project-token"

    def test_generic_env_used_when_project_unset(self, monkeypatch):
        monkeypatch.delenv("BOOKSCOUT_GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "generic-token")
        assert _http.github_token() == "generic-token"

    def test_token_attached_only_to_github_api(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")

        req = _http._build_request("https://api.github.com/repos/x/y")
        assert req.get_header("Authorization") == "Bearer secret-token"

        other = _http._build_request("https://gutendex.com/books")
        assert other.get_header("Authorization") is None

        raw = _http._build_request(
            "https://raw.githubusercontent.com/zhpelo/wenshuoge/HEAD/x.epub"
        )
        assert raw.get_header("Authorization") is None

    def test_no_token_no_header(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("BOOKSCOUT_GITHUB_TOKEN", raising=False)
        req = _http._build_request("https://api.github.com/repos/x/y")
        assert req.get_header("Authorization") is None

    def test_user_agent_always_present(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        req = _http._build_request("https://example.com")
        assert req.get_header("User-agent") == _http.USER_AGENT


class TestHttpRetries:
    def test_source_error_on_http_403_rate_limit(self, monkeypatch):
        """A 403 (rate limit) must surface as SourceError, not crash."""

        class Boom(urllib.request.OpenerDirector):
            def open(self, req, timeout=None):
                raise urllib.error.HTTPError(
                    req.full_url, 403, "rate limited", {}, None
                )

        monkeypatch.setattr(_http.urllib.request, "urlopen", Boom().open)
        with pytest.raises(SourceError):
            _http._open("https://api.github.com/x", timeout=1, max_retries=0)
