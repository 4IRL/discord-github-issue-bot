"""Load the bot's configuration.

Instance-wide settings and secrets come from the environment, and the routes
come from the TOML file at ``ROUTES_PATH``. Every key is required and nothing
has a default in code.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from issue_bot.issue_type import IssueType

REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
ASCII_INTEGER_PATTERN = re.compile(r"-?[0-9]+")
DOT_SEGMENTS = frozenset({".", ".."})
ROUTE_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
OWNER_PATTERN = re.compile(r"[A-Za-z0-9_.-]+")
ROUTE_KEYS = ("channel_id", "channel_name", "category", "repo", "repo_id", "labels")


class ConfigError(Exception):
    """A required configuration key is missing or invalid.

    The message names the key only, never the rejected value.
    """


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigError(f"{key} is required")
    return value


def _positive_int(env: Mapping[str, str], key: str) -> int:
    raw_value = _required(env, key)
    # int() also raises ValueError past Python's int digit limit.
    try:
        if not ASCII_INTEGER_PATTERN.fullmatch(raw_value):
            raise ValueError
        number = int(raw_value)
    except ValueError:
        raise ConfigError(f"{key} must be an integer") from None
    if number <= 0:
        raise ConfigError(f"{key} must be a positive integer")
    return number


def _owner(env: Mapping[str, str], key: str) -> str:
    owner = _required(env, key)
    if not OWNER_PATTERN.fullmatch(owner) or owner in DOT_SEGMENTS:
        raise ConfigError(f"{key} must be an owner name")
    return owner


def _rsa_private_key(env: Mapping[str, str], key: str) -> RSAPrivateKey:
    path = _required(env, key)
    # The error names the key only: no path, no file contents, no library text.
    error_message = f"{key} must name a readable RSA private key"
    try:
        private_key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    except (OSError, ValueError, TypeError, UnsupportedAlgorithm):
        raise ConfigError(error_message) from None
    if not isinstance(private_key, RSAPrivateKey):
        raise ConfigError(error_message)
    return private_key


class UnroutedCommands(StrEnum):
    """What a command run outside this instance's routes gets.

    ``REFUSE`` replies with a private refusal; ``IGNORE`` sends no response at
    all, so another instance sharing the bot token can answer instead.
    """

    REFUSE = "refuse"
    IGNORE = "ignore"


def _unrouted(env: Mapping[str, str], key: str) -> UnroutedCommands:
    try:
        return UnroutedCommands(_required(env, key))
    except ValueError:
        raise ConfigError(f"{key} must be refuse or ignore") from None


@dataclass(frozen=True)
class TargetConfig:
    """One route: an intake channel and the GitHub repo its issues go to."""

    name: str
    channel_id: int
    channel_name: str
    category: str
    github_repo: str
    github_repo_id: int
    labels: Mapping[IssueType, str]

    def __post_init__(self) -> None:
        if not isinstance(self.labels, Mapping) or set(self.labels) != set(IssueType):
            raise ConfigError("labels must have one entry per IssueType")
        # Copy before wrapping, so a caller's dict can't change the labels later.
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


def _route_value(route: Mapping[str, object], where: str, key: str) -> object:
    if key not in route:
        raise ConfigError(f"{where}.{key} is required")
    return route[key]


def _route_int(route: Mapping[str, object], where: str, key: str) -> int:
    value = _route_value(route, where, key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{where}.{key} must be a positive integer")
    return value


def _route_str(route: Mapping[str, object], where: str, key: str) -> str:
    value = _route_value(route, where, key)
    if not isinstance(value, str):
        raise ConfigError(f"{where}.{key} must be a string")
    value = value.strip()
    if not value:
        raise ConfigError(f"{where}.{key} is required")
    return value


def _route_labels(route: Mapping[str, object], where: str) -> dict[IssueType, str]:
    labels = _route_value(route, where, "labels")
    error_message = f"{where}.labels must map bug and feature to label names"
    if not isinstance(labels, dict) or set(labels) != {
        issue_type.value for issue_type in IssueType
    }:
        raise ConfigError(error_message)
    stripped_labels: dict[IssueType, str] = {}
    for type_name, label in labels.items():
        if not isinstance(label, str) or not label.strip():
            raise ConfigError(error_message)
        stripped_labels[IssueType(type_name)] = label.strip()
    return stripped_labels


def _route(name: str, route: object, org: str) -> TargetConfig:
    where = f"routes.{name}"
    if not isinstance(route, dict):
        raise ConfigError(f"{where} must be a table")
    unknown_keys = sorted(set(route) - set(ROUTE_KEYS))
    if unknown_keys:
        raise ConfigError(f"{where} has unknown key {unknown_keys[0]!r}")
    # Keys are read in ROUTE_KEYS order, so the first bad one is reported.
    channel_id = _route_int(route, where, "channel_id")
    channel_name = _route_str(route, where, "channel_name")
    category = _route_str(route, where, "category")
    github_repo = _route_str(route, where, "repo")
    if not REPO_PATTERN.fullmatch(github_repo) or any(
        segment in DOT_SEGMENTS for segment in github_repo.split("/")
    ):
        raise ConfigError(f"{where}.repo must be owner/name")
    owner = github_repo.split("/")[0]
    if owner.casefold() != org.casefold():
        raise ConfigError(f"{where}.repo must be in GITHUB_ORG")
    github_repo_id = _route_int(route, where, "repo_id")
    return TargetConfig(
        name=name,
        channel_id=channel_id,
        channel_name=channel_name,
        category=category,
        github_repo=github_repo,
        github_repo_id=github_repo_id,
        labels=_route_labels(route, where),
    )


def load_routes(path: str, org: str) -> Mapping[int, TargetConfig]:
    """Load the route file: one ``[routes.<name>]`` table per intake channel.

    Each table holds ``channel_id``, ``channel_name``, ``category``, ``repo``
    (``owner/name``, owned by ``org``), ``repo_id`` and a ``labels`` table
    keyed ``bug``/``feature``. Returns a read-only mapping keyed by channel
    id, in file order. Errors name the key, never the value or file text.
    """
    try:
        with open(path, "rb") as file:
            document = tomllib.load(file)
    except (OSError, ValueError):
        raise ConfigError("ROUTES_PATH must name a readable TOML route file") from None
    unknown_keys = sorted(set(document) - {"routes"})
    if unknown_keys:
        raise ConfigError(f"ROUTES_PATH has unknown key {unknown_keys[0]!r}")
    route_tables = document.get("routes")
    if not isinstance(route_tables, dict) or not route_tables:
        raise ConfigError("ROUTES_PATH must define at least one [routes.<name>] table")
    routes: dict[int, TargetConfig] = {}
    seen: dict[int, str] = {}
    for name, route_table in route_tables.items():
        if not ROUTE_NAME_PATTERN.fullmatch(name):
            raise ConfigError("route names must be lowercase letters, digits, - or _")
        route = _route(name, route_table, org)
        if route.channel_id in seen:
            raise ConfigError(
                f"routes.{seen[route.channel_id]} and routes.{name} share channel_id"
            )
        seen[route.channel_id] = name
        routes[route.channel_id] = route
    return MappingProxyType(routes)


@dataclass(frozen=True)
class Config:
    """Instance-wide settings plus the routes, keyed by intake channel id."""

    discord_token: str = field(repr=False)
    guild_id: int
    unrouted: UnroutedCommands
    github_org: str
    github_app_id: int
    github_installation_id: int
    github_private_key: RSAPrivateKey = field(repr=False)
    routes: Mapping[int, TargetConfig]

    def __post_init__(self) -> None:
        # Copy before wrapping (dict() keeps file order), so the routes stay read-only.
        object.__setattr__(self, "routes", MappingProxyType(dict(self.routes)))

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Config:
        # Keys are read in order, so the first bad one is reported.
        discord_token = _required(env, "DISCORD_TOKEN")
        guild_id = _positive_int(env, "DISCORD_GUILD_ID")
        unrouted = _unrouted(env, "UNROUTED_COMMANDS")
        github_org = _owner(env, "GITHUB_ORG")
        return cls(
            discord_token=discord_token,
            guild_id=guild_id,
            unrouted=unrouted,
            github_org=github_org,
            github_app_id=_positive_int(env, "GITHUB_APP_ID"),
            github_installation_id=_positive_int(env, "GITHUB_APP_INSTALLATION_ID"),
            github_private_key=_rsa_private_key(env, "GITHUB_APP_PRIVATE_KEY_PATH"),
            routes=load_routes(_required(env, "ROUTES_PATH"), github_org),
        )
