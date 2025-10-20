"""Thin Spotify Web API client with retry-aware GET operations."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

try:
    from .utils.retry import retry_with_backoff
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils.retry import retry_with_backoff  # type: ignore[no-redef]


class SpotifyClientError(RuntimeError):
    """Base error for Spotify client issues."""


class SpotifyRateLimit(SpotifyClientError):
    """Raised when Spotify responds with HTTP 429."""

    def __init__(self, retry_after: float):
        super().__init__(f"Rate limited for {retry_after} seconds")
        self.retry_after = retry_after


class SpotifyTransientError(SpotifyClientError):
    """Raised for retryable Spotify API failures."""

    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message or f"Spotify transient error: {status_code}")
        self.status_code = status_code


@dataclass
class RetryConfig:
    max_tries: int = 5
    base: float = 0.5
    cap: float = 30.0


class SpotifyClient:
    """Minimal Spotify Web API client with client credentials flow."""

    token_url = "https://accounts.spotify.com/api/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 30.0,
        retry: Optional[RetryConfig] = None,
    ) -> None:
        if not client_id or not client_secret:
            raise SpotifyClientError("missing Spotify credentials")
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retry = retry or RetryConfig()
        self._token: Optional[str] = None

    @classmethod
    def from_env(cls) -> "SpotifyClient":
        client_id = os.getenv("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIPY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise SpotifyClientError("SPOTIFY_CLIENT_ID/SECRET not configured")
        return cls(client_id, client_secret)

    def authenticate(self) -> None:
        response = self.session.post(
            self.token_url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise SpotifyClientError("no access_token in response")
        self._token = token

    def _request_headers(self) -> Dict[str, str]:
        if not self._token:
            self.authenticate()
        assert self._token is not None
        return {"Authorization": f"Bearer {self._token}"}

    def get(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        sleep_between = max(0.0, float(os.getenv("SPOTIFY_REQ_SLEEP", "0.35") or 0.35))

        def _call() -> Dict[str, Any]:
            headers = self._request_headers()
            response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)

            if response.status_code == 401:
                # Token expired or revoked. Force re-authentication and retry.
                self._token = None
                raise SpotifyTransientError(401, "unauthorized")

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    retry_seconds = float(retry_after) if retry_after is not None else 1.0
                except ValueError:
                    retry_seconds = 1.0
                raise SpotifyRateLimit(max(0.0, retry_seconds))

            if 500 <= response.status_code < 600:
                raise SpotifyTransientError(response.status_code, "server error")

            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:  # JSON decode issues are transient.
                raise SpotifyTransientError(response.status_code, "invalid JSON") from exc

            if sleep_between:
                time.sleep(sleep_between)
            return payload

        def _on_retry(exc: BaseException, _attempt: int) -> Optional[float]:
            if isinstance(exc, SpotifyRateLimit):
                return exc.retry_after
            return None

        return retry_with_backoff(
            _call,
            max_tries=self.retry.max_tries,
            base=self.retry.base,
            cap=self.retry.cap,
            jitter=True,
            retry_exceptions=(
                SpotifyRateLimit,
                SpotifyTransientError,
                requests.RequestException,
            ),
            on_retry=_on_retry,
        )


__all__ = [
    "SpotifyClient",
    "SpotifyClientError",
    "SpotifyRateLimit",
    "SpotifyTransientError",
    "RetryConfig",
]
