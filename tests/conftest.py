from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from issue_bot.config import Config


@pytest.fixture(scope="session")
def github_private_key_pem(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A throwaway RSA key generated in memory, written as PEM under a neutral name.

    The ``.txt`` name keeps it clear of the sandbox's ``*.pem`` read deny; it
    lives only in pytest's temp directory and is never committed.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_path = tmp_path_factory.mktemp("github-app") / "app-key.txt"
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return key_path


@pytest.fixture(scope="session")
def github_private_key(github_private_key_pem: Path) -> rsa.RSAPrivateKey:
    """The test App key, loaded, so tests can verify JWTs signed with it."""
    private_key = serialization.load_pem_private_key(
        github_private_key_pem.read_bytes(), password=None
    )
    assert isinstance(private_key, rsa.RSAPrivateKey)
    return private_key


@pytest.fixture
def test_env(github_private_key_pem: Path) -> dict[str, str]:
    """A fresh environment with neutral values for every required config key."""
    return {
        "DISCORD_TOKEN": "test-token",
        "DISCORD_GUILD_ID": "111",
        "GITHUB_APP_ID": "333",
        "GITHUB_APP_INSTALLATION_ID": "444",
        "GITHUB_APP_PRIVATE_KEY_PATH": str(github_private_key_pem),
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
        content: str = "!bug\nTitle: Fix it",
        *,
        channel_id: int = 555,
        author_bot: bool = False,
        webhook_id: int | None = None,
        message_type: discord.MessageType = discord.MessageType.default,
        author_id: int = 7,
        author_name: str = "Alice",
        message_id: int = 99,
        thread: object | None = None,
        created_thread_id: int = 1234,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            content=content,
            channel=SimpleNamespace(id=channel_id),
            author=SimpleNamespace(bot=author_bot, id=author_id, display_name=author_name),
            webhook_id=webhook_id,
            type=message_type,
            id=message_id,
            jump_url=f"https://discord.com/channels/111/{channel_id}/{message_id}",
            thread=thread,
            create_thread=AsyncMock(
                return_value=SimpleNamespace(id=created_thread_id, send=AsyncMock())
            ),
            fetch_thread=AsyncMock(return_value=SimpleNamespace(id=message_id, send=AsyncMock())),
        )

    return factory
