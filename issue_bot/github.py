"""File issues through the GitHub REST and GraphQL APIs, authenticated as a GitHub App.

This module never logs. Its errors carry the request stage and HTTP status only,
never GitHub's response text, tokens or the App private key; callers log them
by type, stage and status.
"""

import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

import aiohttp
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from issue_bot.complexity import Complexity
from issue_bot.config import ProjectConfig, TargetConfig

API_URL = "https://api.github.com"
GRAPHQL_URL = f"{API_URL}/graphql"
API_VERSION = "2022-11-28"
USER_AGENT = "discord-github-issue-bot"
TOKEN_REFRESH_MARGIN = 300  # seconds before expires_at
JWT_LIFETIME = 540  # GitHub rejects exp > 10 minutes ahead
REQUEST_TIMEOUT = 30  # seconds
LABEL_COLOR = "c5def5"  # the colour new labels get; any later colour change happens on GitHub

# Option ids are GraphQL String, not ID: a String! variable is accepted for the nullable
# singleSelectOptionId, while an ID! declaration fails with variableMismatch.
PROJECT_FIELDS_QUERY = (
    "query($org: String!, $number: Int!) { organization(login: $org) {"
    " projectV2(number: $number) { id fields(first: 100) { nodes { ... on"
    " ProjectV2SingleSelectField { id name options { id name } } } } } } }"
)
ADD_ITEM_MUTATION = (
    "mutation($project: ID!, $content: ID!) { addProjectV2ItemById(input:"
    " {projectId: $project, contentId: $content}) { item { id } } }"
)
SET_FIELDS_MUTATION = (
    "mutation($project: ID!, $item: ID!, $statusField: ID!, $status: String!,"
    " $effortField: ID!, $effort: String!) {"
    " status: updateProjectV2ItemFieldValue(input: {projectId: $project, itemId: $item,"
    " fieldId: $statusField, value: {singleSelectOptionId: $status}}) { projectV2Item { id } }"
    " effort: updateProjectV2ItemFieldValue(input: {projectId: $project, itemId: $item,"
    " fieldId: $effortField, value: {singleSelectOptionId: $effort}}) { projectV2Item { id } } }"
)

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


@dataclass(frozen=True)
class ProjectFields:
    """A route's Project ids, looked up by name: the item's Status option and Effort options."""

    project_id: str
    status_field_id: str
    status_option_id: str
    effort_field_id: str
    effort_option_ids: Mapping[str, str]  # complexity band name -> option id

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "effort_option_ids", MappingProxyType(dict(self.effort_option_ids))
        )


class GitHubError(Exception):
    """A GitHub request failed; carries the stage and HTTP status only, never response text.

    ``stage`` is ``"token"``, ``"label"``, ``"issue"``, ``"project"``, ``"project-item"`` or
    ``"project-field"``; ``status`` is None for a transport failure.
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


def _single_select_options(
    nodes: list[Any], name: str
) -> tuple[str, dict[str, str]] | None:
    """Return (field id, option name -> id) of the single-select field named ``name``, or None."""
    for node in nodes:
        # The schema allows null nodes, and non-single-select fields come back as {}.
        if not isinstance(node, dict) or node.get("name") != name:
            continue
        field_id = node.get("id")
        raw_options = node.get("options")
        if not isinstance(field_id, str) or not isinstance(raw_options, list):
            return None
        options: dict[str, str] = {}
        for option in raw_options:
            if not isinstance(option, dict):
                return None
            option_id = option.get("id")
            option_name = option.get("name")
            if not isinstance(option_id, str) or not isinstance(option_name, str):
                return None
            options[option_name] = option_id
        return field_id, options
    return None


def _parse_project_fields(data: dict[str, Any], project: ProjectConfig) -> ProjectFields | None:
    """Return the Project's ids from a PROJECT_FIELDS_QUERY result, or None on any mismatch."""
    organization = data.get("organization")
    if not isinstance(organization, dict):
        return None
    project_node = organization.get("projectV2")
    if not isinstance(project_node, dict):
        return None
    project_id = project_node.get("id")
    fields = project_node.get("fields")
    if not isinstance(project_id, str) or not isinstance(fields, dict):
        return None
    nodes = fields.get("nodes")
    if not isinstance(nodes, list):
        return None
    status = _single_select_options(nodes, project.status_field)
    if status is None or project.status not in status[1]:
        return None
    effort = _single_select_options(nodes, project.effort_field)
    if effort is None:
        return None
    effort_field_id, options = effort
    if not all(str(band) in options for band in Complexity):
        return None
    return ProjectFields(
        project_id=project_id,
        status_field_id=status[0],
        status_option_id=status[1][project.status],
        effort_field_id=effort_field_id,
        effort_option_ids={str(band): options[str(band)] for band in Complexity},
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
    """Creates issues and their labels, and adds them to a route's Project, as an App installation.

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
        # A concurrent first miss looks up twice, harmlessly, like the token and label caches.
        self._projects: dict[tuple[str, ProjectConfig], ProjectFields] = {}

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

    async def _graphql(
        self, stage: str, target: TargetConfig, query: str, variables: dict[str, object]
    ) -> dict[str, Any]:
        """Run one GraphQL request; return its ``data``, or raise GitHubError(stage, status)."""
        token = await self._installation_token(target)
        status, data = await self._request(
            stage, GRAPHQL_URL, self._headers(token), {"query": query, "variables": variables}
        )
        if status == 401:
            # Never a keyed del: a concurrent filing may already have dropped it.
            self._tokens.pop(self._token_key(target), None)
            raise GitHubError(stage, status) from None
        # A GraphQL error comes back as 200 with an "errors" key; its text is never kept.
        if (
            status != 200
            or not isinstance(data, dict)
            or "errors" in data
            or not isinstance(data.get("data"), dict)
        ):
            raise GitHubError(stage, status) from None
        return data["data"]

    @staticmethod
    def _owner(target: TargetConfig) -> str:
        """The route repo's owner, the org its Project belongs to."""
        return target.github_repo.split("/")[0]

    @classmethod
    def _project_key(cls, target: TargetConfig) -> tuple[str, ProjectConfig]:
        """Cache key: the casefolded owner plus the route's ProjectConfig."""
        assert target.project is not None  # callers check it first
        return cls._owner(target).casefold(), target.project

    async def project_fields(self, target: TargetConfig) -> ProjectFields:
        """Return the route's Project ids, looked up once and cached; raise GitHubError otherwise."""
        if target.project is None:
            raise ValueError("route has no project")
        key = self._project_key(target)
        cached = self._projects.get(key)
        if cached is not None:
            return cached
        data = await self._graphql(
            "project",
            target,
            PROJECT_FIELDS_QUERY,
            {"org": self._owner(target), "number": target.project.number},
        )
        fields = _parse_project_fields(data, target.project)
        if fields is None:
            raise GitHubError("project", 200) from None
        self._projects[key] = fields
        return fields

    async def add_to_project(
        self, target: TargetConfig, issue: FiledIssue, band: Complexity
    ) -> str:
        """Add the issue to the route's Project, set its Status and Effort and return the item id.

        The returned id is the ``addProjectV2ItemById`` Project item id, so a caller can set
        more fields on that item. Raise GitHubError when any part of this fails.
        """
        fields = await self.project_fields(target)
        try:
            added = await self._graphql(
                "project-item",
                target,
                ADD_ITEM_MUTATION,
                {"project": fields.project_id, "content": issue.node_id},
            )
            add_result = added.get("addProjectV2ItemById")
            item = add_result.get("item") if isinstance(add_result, dict) else None
            item_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(item_id, str):
                raise GitHubError("project-item", 200) from None
            updated = await self._graphql(
                "project-field",
                target,
                SET_FIELDS_MUTATION,
                {
                    "project": fields.project_id,
                    "item": item_id,
                    "statusField": fields.status_field_id,
                    "status": fields.status_option_id,
                    "effortField": fields.effort_field_id,
                    "effort": fields.effort_option_ids[str(band)],
                },
            )
            for alias in ("status", "effort"):
                result = updated.get(alias)
                if not isinstance(result, dict) or not isinstance(
                    result.get("projectV2Item"), dict
                ):
                    raise GitHubError("project-field", 200) from None
            return item_id
        except GitHubError as exc:
            if exc.stage in ("project-item", "project-field"):
                # Ids changed on GitHub (e.g. a deleted and re-created option) are looked up
                # again on the next filing. Never a keyed del: a concurrent filing may have
                # dropped them already.
                self._projects.pop(self._project_key(target), None)
            raise
