import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import issue_bot.__main__ as entry_point
from issue_bot.bot import IssueBot, build_intents, channel_problems
from issue_bot.config import Config
from issue_bot.handler import IssueCandidate
from issue_bot.tags import IssueType
from tests.conftest import MessageFactory

CONFIG_KEYS = (
    "DISCORD_TOKEN",
    "DISCORD_GUILD_ID",
    "DISCORD_CHANNEL_ID",
    "DISCORD_CHANNEL_NAME",
    "DISCORD_CATEGORY",
    "GITHUB_REPO",
    "GITHUB_REPO_ID",
    "GITHUB_LABEL_BUG",
    "GITHUB_LABEL_FEATURE",
)


def make_channel(
    *,
    guild_id: int = 111,
    name: str = "intake",
    category_name: str | None = "Intake",
) -> SimpleNamespace:
    category = SimpleNamespace(name=category_name) if category_name is not None else None
    return SimpleNamespace(
        id=555, name=name, guild=SimpleNamespace(id=guild_id), category=category
    )


def bot_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == "issue_bot.bot"]


def record_texts(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() + (record.exc_text or "") for record in caplog.records]


class FailingBot:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pytest.fail("IssueBot must not be constructed on a config error")


def test_intents() -> None:
    intents = build_intents()
    assert intents.message_content is True
    assert intents.guild_messages is True
    assert intents.guilds is True
    assert intents.members is False
    assert intents.presences is False


def test_matching_channel_has_no_problems(config: Config) -> None:
    assert channel_problems(make_channel(), config) == []


def test_missing_channel(config: Config) -> None:
    assert channel_problems(None, config) == ["channel 555 not found or not visible to the bot"]


def test_wrong_guild(config: Config) -> None:
    assert channel_problems(make_channel(guild_id=222), config) == [
        "channel 555 is in guild 222, expected 111"
    ]


def test_channel_without_guild(config: Config) -> None:
    private_channel = SimpleNamespace(id=555)
    assert channel_problems(private_channel, config) == [
        "channel 555 is not in a guild, expected guild 111"
    ]


def test_wrong_name(config: Config) -> None:
    assert channel_problems(make_channel(name="general"), config) == [
        "channel name is 'general', expected 'intake'"
    ]


def test_wrong_category(config: Config) -> None:
    assert channel_problems(make_channel(category_name="Other"), config) == [
        "channel category is 'Other', expected 'Intake'"
    ]


def test_no_category(config: Config) -> None:
    assert channel_problems(make_channel(category_name=None), config) == [
        "channel category is None, expected 'Intake'"
    ]


async def test_on_message_calls_hook_with_message_and_candidate(
    config: Config, make_message: MessageFactory
) -> None:
    hook = AsyncMock()
    bot = IssueBot(config, on_candidate=hook)
    message = make_message()
    await bot.on_message(message)
    hook.assert_awaited_once()
    awaited_message, candidate = hook.await_args.args
    assert awaited_message is message
    assert isinstance(candidate, IssueCandidate)
    assert candidate.type == IssueType.BUG


async def test_on_message_ignores_untagged(
    config: Config, make_message: MessageFactory
) -> None:
    hook = AsyncMock()
    bot = IssueBot(config, on_candidate=hook)
    await bot.on_message(make_message("anyone around tonight?"))
    hook.assert_not_awaited()


async def test_on_message_ignores_malformed(
    config: Config, make_message: MessageFactory
) -> None:
    hook = AsyncMock()
    bot = IssueBot(config, on_candidate=hook)
    await bot.on_message(make_message("!bug\nBody: x"))
    hook.assert_not_awaited()


async def test_default_hook_logs_ids_not_text(
    config: Config, make_message: MessageFactory, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    message = make_message("!bug\nTitle: Secret title words\nBody: Secret body words")
    with caplog.at_level(logging.INFO):
        await bot.on_message(message)
    info_messages = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.INFO
    ]
    assert any(
        "bug" in text and "99" in text and message.jump_url in text for text in info_messages
    )
    for text in record_texts(caplog):
        assert "Secret title words" not in text
        assert "Secret body words" not in text
        assert "Alice" not in text


async def test_on_ready_logs_missing_channel_as_error(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    monkeypatch.setattr(bot, "get_channel", lambda _id: None)
    with caplog.at_level(logging.INFO):
        await bot.on_ready()
    problems = [
        (record.levelno, record.getMessage())
        for record in bot_records(caplog)
        if record.levelno >= logging.WARNING
    ]
    assert problems == [(logging.ERROR, "channel 555 not found or not visible to the bot")]


async def test_on_ready_logs_channel_mismatch_as_warning(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    monkeypatch.setattr(bot, "get_channel", lambda _id: make_channel(name="general"))
    with caplog.at_level(logging.INFO):
        await bot.on_ready()
    problems = [
        (record.levelno, record.getMessage())
        for record in bot_records(caplog)
        if record.levelno >= logging.WARNING
    ]
    assert problems == [(logging.WARNING, "channel name is 'general', expected 'intake'")]


async def test_on_ready_matching_channel_logs_no_warning(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    monkeypatch.setattr(bot, "get_channel", lambda _id: make_channel())
    with caplog.at_level(logging.INFO):
        await bot.on_ready()
    assert not [record for record in bot_records(caplog) if record.levelno >= logging.WARNING]


async def test_on_ready_checks_channel_once_across_reconnects(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    lookups: list[int] = []

    def get_channel(channel_id: int) -> None:
        lookups.append(channel_id)
        return None

    monkeypatch.setattr(bot, "get_channel", get_channel)
    with caplog.at_level(logging.INFO):
        await bot.on_ready()
        await bot.on_ready()
    assert lookups == [555]
    bot_messages = [record.getMessage() for record in bot_records(caplog)]
    assert sum(text.startswith("connected as") for text in bot_messages) == 1
    assert sum("not found or not visible" in text for text in bot_messages) == 1


async def test_on_error_hides_exception_text(
    config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    with caplog.at_level(logging.INFO):
        try:
            raise RuntimeError("Secret title words")
        except RuntimeError:
            await bot.on_error("on_message")
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert any("RuntimeError" in text and "on_message" in text for text in errors)
    for text in record_texts(caplog):
        assert "Secret title words" not in text


async def test_on_error_without_active_exception(
    config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    with caplog.at_level(logging.INFO):
        await bot.on_error("on_ready")
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert errors == ["unhandled unknown error in on_ready"]


async def test_on_error_adds_message_id_for_on_message(
    config: Config, make_message: MessageFactory, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    message = make_message("!bug\nTitle: Secret title words", message_id=4242)
    with caplog.at_level(logging.INFO):
        try:
            raise RuntimeError("Secret title words")
        except RuntimeError:
            await bot.on_error("on_message", message)
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert errors == ["unhandled RuntimeError in on_message message_id=4242"]
    for text in record_texts(caplog):
        assert "Secret title words" not in text
        assert "Alice" not in text


async def test_raising_hook_dispatched_by_discord_logs_type_and_id_only(
    config: Config, make_message: MessageFactory, caplog: pytest.LogCaptureFixture
) -> None:
    hook = AsyncMock(side_effect=RuntimeError("Secret exception words"))
    bot = IssueBot(config, on_candidate=hook)
    message = make_message("!bug\nTitle: Secret title words", message_id=4242)
    with caplog.at_level(logging.INFO):
        # discord.py's own dispatch path: it catches the error and calls on_error.
        await bot._run_event(bot.on_message, "on_message", message)
    hook.assert_awaited_once()
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert errors == ["unhandled RuntimeError in on_message message_id=4242"]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
        assert "Secret title words" not in text
        assert "Alice" not in text


@pytest.mark.parametrize(
    ("event_method", "arguments"),
    [
        ("on_message", (SimpleNamespace(id="99"),)),
        ("on_message", (SimpleNamespace(id=True),)),
        ("on_message", (SimpleNamespace(),)),
        ("on_message", ()),
        ("on_guild_join", (SimpleNamespace(id=4242),)),
    ],
)
async def test_on_error_omits_non_message_ids(
    config: Config,
    caplog: pytest.LogCaptureFixture,
    event_method: str,
    arguments: tuple[SimpleNamespace, ...],
) -> None:
    bot = IssueBot(config)
    with caplog.at_level(logging.INFO):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            await bot.on_error(event_method, *arguments)
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert errors == [f"unhandled RuntimeError in {event_method}"]


def test_edits_not_handled() -> None:
    assert not hasattr(IssueBot, "on_message_edit")


def test_main_exits_on_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in CONFIG_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(entry_point, "IssueBot", FailingBot)
    with pytest.raises(SystemExit) as exit_info:
        entry_point.main()
    assert exit_info.value.code == 2


def test_main_config_error_hides_value(
    monkeypatch: pytest.MonkeyPatch, test_env: dict[str, str], caplog: pytest.LogCaptureFixture
) -> None:
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DISCORD_GUILD_ID", "secret-value")
    monkeypatch.setattr(entry_point, "IssueBot", FailingBot)
    with pytest.raises(SystemExit) as exit_info:
        entry_point.main()
    assert exit_info.value.code == 2
    assert caplog.records
    for text in record_texts(caplog):
        assert "secret-value" not in text


def test_main_runs_bot_with_token(
    monkeypatch: pytest.MonkeyPatch, test_env: dict[str, str]
) -> None:
    calls: dict[str, object] = {}

    class StubBot:
        def __init__(self, config: Config) -> None:
            calls["config"] = config

        def run(self, token: str, **kwargs: object) -> None:
            calls["token"] = token
            calls["kwargs"] = kwargs

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(entry_point, "IssueBot", StubBot)
    entry_point.main()
    config = calls["config"]
    assert isinstance(config, Config)
    assert config.guild_id == 111
    assert calls["token"] == "test-token"
    assert calls["kwargs"] == {"log_handler": None}
