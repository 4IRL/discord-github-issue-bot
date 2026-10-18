from collections.abc import Callable
from types import SimpleNamespace

import discord
import pytest

from issue_bot.config import Config


@pytest.fixture
def test_env() -> dict[str, str]:
    """A fresh environment with neutral values for every required config key."""
    return {
        "DISCORD_TOKEN": "test-token",
        "DISCORD_GUILD_ID": "111",
        "DISCORD_CHANNEL_ID": "555",
        "DISCORD_CHANNEL_NAME": "intake",
        "DISCORD_CATEGORY": "Intake",
        "GITHUB_REPO": "example-org/example-repo",
        "GITHUB_REPO_ID": "222",
        "GITHUB_LABEL_BUG": "bug",
        "GITHUB_LABEL_FEATURE": "enhancement",
    }


@pytest.fixture
def config(test_env: dict[str, str]) -> Config:
    return Config.from_env(test_env)


MessageFactory = Callable[..., SimpleNamespace]


@pytest.fixture
def make_message() -> MessageFactory:
    """Build a duck-typed stand-in for ``discord.Message`` (no real Discord objects)."""

    def factory(
        content: str = "Fix it #bug",
        *,
        channel_id: int = 555,
        author_bot: bool = False,
        webhook_id: int | None = None,
        message_type: discord.MessageType = discord.MessageType.default,
        author_id: int = 7,
        author_name: str = "Alice",
        message_id: int = 99,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            content=content,
            channel=SimpleNamespace(id=channel_id),
            author=SimpleNamespace(bot=author_bot, id=author_id, display_name=author_name),
            webhook_id=webhook_id,
            type=message_type,
            id=message_id,
            jump_url=f"https://discord.com/channels/111/{channel_id}/{message_id}",
        )

    return factory
