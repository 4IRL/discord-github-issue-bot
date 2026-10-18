"""Load the bot's configuration from environment variables.

Every key is required and nothing has a default in code: the deployment's
values live in its environment (see ``example.env``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from issue_bot.tags import IssueType

REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
ASCII_INTEGER_PATTERN = re.compile(r"-?[0-9]+")
DOT_SEGMENTS = frozenset({".", ".."})


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
    if not ASCII_INTEGER_PATTERN.fullmatch(raw_value):
        raise ConfigError(f"{key} must be an integer")
    try:
        number = int(raw_value)
    except ValueError:
        raise ConfigError(f"{key} must be an integer") from None
    if number <= 0:
        raise ConfigError(f"{key} must be a positive integer")
    return number


@dataclass(frozen=True)
class TargetConfig:
    """One intake channel and the GitHub repo its issues go to."""

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

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> TargetConfig:
        channel_id = _positive_int(env, "DISCORD_CHANNEL_ID")
        channel_name = _required(env, "DISCORD_CHANNEL_NAME")
        category = _required(env, "DISCORD_CATEGORY")
        github_repo = _required(env, "GITHUB_REPO")
        if not REPO_PATTERN.fullmatch(github_repo) or any(
            segment in DOT_SEGMENTS for segment in github_repo.split("/")
        ):
            raise ConfigError("GITHUB_REPO must be owner/name")
        github_repo_id = _positive_int(env, "GITHUB_REPO_ID")
        labels = {
            issue_type: _required(env, f"GITHUB_LABEL_{issue_type.name}")
            for issue_type in IssueType
        }
        return cls(
            channel_id=channel_id,
            channel_name=channel_name,
            category=category,
            github_repo=github_repo,
            github_repo_id=github_repo_id,
            labels=labels,
        )


@dataclass(frozen=True)
class Config:
    """Instance-wide settings plus the target route."""

    discord_token: str = field(repr=False)
    guild_id: int
    target: TargetConfig

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Config:
        discord_token = _required(env, "DISCORD_TOKEN")
        guild_id = _positive_int(env, "DISCORD_GUILD_ID")
        target = TargetConfig.from_env(env)
        return cls(discord_token=discord_token, guild_id=guild_id, target=target)
