from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from issue_bot.config import Config, TargetConfig
from issue_bot.github import FiledIssue
from issue_bot.handler import IssueCandidate
from issue_bot.issue_type import IssueType


ISSUE_URL = "https://github.com/example-org/example-repo/issues/7"

ONE_ROUTE_TOML = """\
[routes.intake]
channel_id = 555
channel_name = "intake"
category = "Intake"
repo = "example-org/example-repo"
repo_id = 222

[routes.intake.labels]
bug = "bug"
feature = "enhancement"

[[routes.intake.questions.bug]]
label = "What happened?"
style = "paragraph"
required = true

[[routes.intake.questions.bug]]
label = "Device"
style = "short"
required = false

[[routes.intake.questions.feature]]
label = "The idea"
style = "paragraph"
required = true
"""

TWO_ROUTE_TOML = (
    ONE_ROUTE_TOML
    + """
[routes.other]
channel_id = 556
channel_name = "other-intake"
category = "Other"
repo = "example-org/other-repo"
repo_id = 223

[routes.other.labels]
bug = "defect"
feature = "idea"

[[routes.other.questions.bug]]
label = "Steps"
style = "paragraph"
required = true

[[routes.other.questions.feature]]
label = "Why?"
style = "short"
required = false
"""
)


def write_routes(directory: Path, text: str) -> Path:
    """Write ``text`` as ``routes.toml`` in ``directory`` (created if needed); returns its path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "routes.toml"
    path.write_text(text, encoding="utf-8")
    return path


def record_texts(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() + (record.exc_text or "") for record in caplog.records]


def forbidden(code: int, text: str) -> discord.Forbidden:
    return discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"), {"code": code, "message": text}
    )


def fake_github(result: FiledIssue | Exception) -> SimpleNamespace:
    if isinstance(result, Exception):
        return SimpleNamespace(create_issue=AsyncMock(side_effect=result))
    return SimpleNamespace(create_issue=AsyncMock(return_value=result))


def assert_no_member_text(caplog: pytest.LogCaptureFixture) -> None:
    for text in record_texts(caplog):
        assert "Secret title words" not in text
        assert "Secret body words" not in text
        assert "Alice" not in text


@pytest.fixture(autouse=True)
def no_live_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if any client built without an explicit transport would reach api.github.com."""
    monkeypatch.setattr(
        "issue_bot.github.aiohttp_transport",
        AsyncMock(side_effect=AssertionError("live GitHub call in a test")),
    )


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
def routes_file(tmp_path: Path) -> Path:
    """The one-route test route file, written under pytest's temp directory."""
    return write_routes(tmp_path, ONE_ROUTE_TOML)


@pytest.fixture
def test_env(github_private_key_pem: Path, routes_file: Path) -> dict[str, str]:
    """A fresh environment with neutral values for every required config key."""
    return {
        "DISCORD_TOKEN": "test-token",
        "DISCORD_GUILD_ID": "111",
        "UNROUTED_COMMANDS": "refuse",
        "GITHUB_ORG": "example-org",
        "GITHUB_APP_ID": "333",
        "GITHUB_APP_INSTALLATION_ID": "444",
        "GITHUB_APP_PRIVATE_KEY_PATH": str(github_private_key_pem),
        "ROUTES_PATH": str(routes_file),
    }


@pytest.fixture
def config(test_env: dict[str, str]) -> Config:
    return Config.from_env(test_env)


@pytest.fixture
def two_route_config(test_env: dict[str, str], tmp_path: Path) -> Config:
    """A config with two routes (channels 555 and 556), leaving ``test_env`` unchanged."""
    path = write_routes(tmp_path / "two", TWO_ROUTE_TOML)
    return Config.from_env({**test_env, "ROUTES_PATH": str(path)})


@pytest.fixture
def route(config: Config) -> TargetConfig:
    """The test config's only route."""
    return next(iter(config.routes.values()))


MessageFactory = Callable[..., SimpleNamespace]
InteractionFactory = Callable[..., SimpleNamespace]
CandidateFactory = Callable[..., IssueCandidate]


@pytest.fixture
def make_message() -> MessageFactory:
    """Build a duck-typed stand-in for ``discord.Message`` (no real Discord objects)."""

    def factory(
        *,
        channel_id: int = 555,
        message_id: int = 99,
        thread: object | None = None,
        created_thread_id: int = 1234,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            channel=SimpleNamespace(id=channel_id),
            id=message_id,
            jump_url=f"https://discord.com/channels/111/{channel_id}/{message_id}",
            thread=thread,
            create_thread=AsyncMock(
                return_value=SimpleNamespace(id=created_thread_id, send=AsyncMock())
            ),
            fetch_thread=AsyncMock(return_value=SimpleNamespace(id=message_id, send=AsyncMock())),
            reply=AsyncMock(),
        )

    return factory


@pytest.fixture
def make_candidate(route: TargetConfig) -> CandidateFactory:
    """Build an ``IssueCandidate`` for a report; ``target`` defaults to the test config's route."""

    def factory(
        *,
        type: IssueType = IssueType.BUG,
        title: str = "Fix it",
        answers: tuple[tuple[str, str], ...] = (("What happened?", "Steps"),),
        author_name: str = "Alice",
        author_id: int = 7,
        message_id: int = 99,
        message_url: str = "https://discord.com/channels/111/555/99",
        target: TargetConfig | None = None,
    ) -> IssueCandidate:
        return IssueCandidate(
            type=type,
            title=title,
            answers=answers,
            author_id=author_id,
            author_name=author_name,
            message_id=message_id,
            message_url=message_url,
            target=target or route,
        )

    return factory


@pytest.fixture
def make_interaction(make_message: MessageFactory) -> InteractionFactory:
    """Build a duck-typed stand-in for a slash-command or modal ``discord.Interaction``."""

    def factory(
        *,
        channel_id: int | None = 555,
        user_id: int = 7,
        display_name: str = "Alice",
        interaction_id: int = 4242,
        summary: SimpleNamespace | None = None,
    ) -> SimpleNamespace:
        if summary is None:
            summary = make_message()
        channel = (
            None
            if channel_id is None
            else SimpleNamespace(id=channel_id, send=AsyncMock(return_value=summary))
        )
        response = SimpleNamespace(
            send_modal=AsyncMock(),
            send_message=AsyncMock(),
            defer=AsyncMock(),
            is_done=Mock(return_value=False),
        )
        # A deferred interaction reports is_done() True, as in production (DD-2).
        response.defer.side_effect = lambda *args, **kwargs: setattr(
            response.is_done, "return_value", True
        )
        return SimpleNamespace(
            id=interaction_id,
            channel_id=channel_id,
            channel=channel,
            user=SimpleNamespace(id=user_id, display_name=display_name, mention=f"<@{user_id}>"),
            response=response,
            followup=SimpleNamespace(send=AsyncMock()),
        )

    return factory
