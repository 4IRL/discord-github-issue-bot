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
