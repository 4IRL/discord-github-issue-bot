"""File issues through the GitHub REST API, authenticated as a GitHub App.

This module never logs. Its errors carry the request stage and HTTP status only,
never GitHub's response text, tokens or the App private key; callers log them
by type, stage and status.
"""

import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from issue_bot.config import TargetConfig

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
USER_AGENT = "discord-github-issue-bot"
TOKEN_REFRESH_MARGIN = 300  # seconds before expires_at
JWT_LIFETIME = 540  # GitHub rejects exp > 10 minutes ahead
REQUEST_TIMEOUT = 30  # seconds
LABEL_COLOR = "c5def5"  # the colour new labels get; any later colour change happens on GitHub

Transport = Callable[[str, str, Mapping[str, str], object], Awaitable[tuple[int, Any]]]


async def aiohttp_transport(
    method: str, url: str, headers: Mapping[str, str], payload: object
) -> tuple[int, Any]:
    """Send one JSON request in its own session; return the status and parsed JSON (or None)."""
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    ) as session:
        async with session.request(method, url, headers=headers, json=payload) as resp:
            try:
                data = await resp.json(content_type=None)
            except ValueError:
                data = None
            return resp.status, data


@dataclass(frozen=True)
class FiledIssue:
    """The issue GitHub created."""

    number: int
    html_url: str
    node_id: str  # the GraphQL id a Project item is added by


class GitHubError(Exception):
    """A GitHub request failed; carries the stage and HTTP status only, never response text.

    ``stage`` is ``"token"``, ``"label"`` or ``"issue"``; ``status`` is None for a transport failure.
    """

    def __init__(self, stage: str, status: int | None) -> None:
        super().__init__(f"{stage} request failed status={status}")
        self.stage = stage
        self.status = status


def app_jwt(app_id: int, private_key: RSAPrivateKey, now: float) -> str:
    """Return the App's RS256 JWT, backdated 60 s against clock drift."""
    return jwt.encode(
        {"iat": int(now) - 60, "exp": int(now) + JWT_LIFETIME, "iss": str(app_id)},
        private_key,
        algorithm="RS256",
    )


def _parse_token_response(data: Any) -> tuple[str, float] | None:
    """Return (token, expires_at epoch) from an access-token response, or None if malformed."""
    if not isinstance(data, dict):
        return None
    token = data.get("token")
    expires_at = data.get("expires_at")
    if not isinstance(token, str) or not isinstance(expires_at, str):
        return None
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return None
    if expiry.tzinfo is None:
        return None
    return token, expiry.timestamp()


class GitHubClient:
    """Creates issues, and the labels they need, as a GitHub App installation.

    Caches a repo-scoped token per repo and Project need.
    """

    def __init__(
        self,
        app_id: int,
        installation_id: int,
        private_key: RSAPrivateKey,
        *,
        transport: Transport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._app_id = app_id
        self._installation_id = installation_id
        self._private_key = private_key
        self._transport = transport or aiohttp_transport
        self._clock = clock
        self._tokens: dict[tuple[int, bool], tuple[str, float]] = {}
        self._labels: set[tuple[int, str]] = set()

    def __repr__(self) -> str:
        return f"GitHubClient(app_id={self._app_id}, installation_id={self._installation_id})"

    @staticmethod
    def _headers(bearer: str) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {bearer}",
        }

    async def _request(
        self, stage: str, url: str, headers: Mapping[str, str], payload: object
    ) -> tuple[int, Any]:
        try:
            return await self._transport("POST", url, headers, payload)
        except (aiohttp.ClientError, TimeoutError):
            pass
        # Raised outside the handler so __context__ is None: the transport error's
        # traceback frames hold the request headers, including the bearer token.
        raise GitHubError(stage, None) from None

    @staticmethod
    def _token_key(target: TargetConfig) -> tuple[int, bool]:
        return target.github_repo_id, target.project is not None

    async def _installation_token(self, target: TargetConfig) -> str:
        key = self._token_key(target)
        cached = self._tokens.get(key)
        if cached is not None and self._clock() < cached[1] - TOKEN_REFRESH_MARGIN:
            return cached[0]
        permissions = {"issues": "write"}
        # Least privilege: only a route with a Project asks for the Projects permission.
        if target.project is not None:
            permissions["organization_projects"] = "write"
        status, data = await self._request(
            "token",
            f"{API_URL}/app/installations/{self._installation_id}/access_tokens",
            self._headers(app_jwt(self._app_id, self._private_key, self._clock())),
            {"repository_ids": [target.github_repo_id], "permissions": permissions},
        )
        parsed = _parse_token_response(data) if status == 201 else None
        if parsed is None:
            raise GitHubError("token", status) from None
        self._tokens[key] = parsed
        return parsed[0]

    async def check_access(self, target: TargetConfig) -> None:
        """Confirm a repo-scoped installation token can be had for the target; raise GitHubError otherwise."""
        await self._installation_token(target)

    async def ensure_label(self, target: TargetConfig, name: str) -> None:
        """Create the label in the target repo unless it exists; raise GitHubError otherwise."""
        key = (target.github_repo_id, name)
        if key in self._labels:
            return
        token = await self._installation_token(target)
        status, _data = await self._request(
            "label",
            f"{API_URL}/repos/{target.github_repo}/labels",
            self._headers(token),
            {"name": name, "color": LABEL_COLOR},
        )
        if status == 401:
            # Never a keyed del: a concurrent filing may already have dropped it.
            self._tokens.pop(self._token_key(target), None)
            raise GitHubError("label", status) from None
        # Every 422 is taken as "already exists": GitHub also uses 422 for other
        # validation errors, unlikely with a fixed name and colour. Labels stay cached
        # for the process, so one deleted on GitHub is re-created only after a restart.
        if status not in (201, 422):
            raise GitHubError("label", status) from None
        self._labels.add(key)

    async def create_issue(
        self, target: TargetConfig, title: str, body: str, labels: list[str]
    ) -> FiledIssue:
        """Create an issue in the target repo; raise GitHubError on any failure."""
        token = await self._installation_token(target)
        status, data = await self._request(
            "issue",
            f"{API_URL}/repos/{target.github_repo}/issues",
            self._headers(token),
            {"title": title, "body": body, "labels": labels},
        )
        if status == 401:
            # Never a keyed del: a concurrent filing may already have dropped it.
            self._tokens.pop(self._token_key(target), None)
            raise GitHubError("issue", status) from None
        if (
            status != 201
            or not isinstance(data, dict)
            or type(data.get("number")) is not int
            or not isinstance(data.get("html_url"), str)
            or not isinstance(data.get("node_id"), str)
        ):
            raise GitHubError("issue", status) from None
        return FiledIssue(data["number"], data["html_url"], data["node_id"])
