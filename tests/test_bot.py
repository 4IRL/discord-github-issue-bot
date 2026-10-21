import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from discord import app_commands

import issue_bot.__main__ as entry_point
from issue_bot.bot import (
    IssueBot,
    build_intents,
    channel_problems,
    filing_hook,
    open_issue_thread,
)
from issue_bot.config import Config
from issue_bot.github import FiledIssue, GitHubError
from issue_bot.handler import IssueCandidate
from issue_bot.intake import INTAKE_ERROR_REPLY, IntakeModal
from issue_bot.issue_type import IssueType
from issue_bot.threads import FILING_ERROR_REPLY
from tests.conftest import (
    ISSUE_URL,
    CandidateFactory,
    InteractionFactory,
    MessageFactory,
    assert_no_member_text,
    fake_github,
    forbidden,
    record_texts,
)

CONFIG_KEYS = (
    "DISCORD_TOKEN",
    "DISCORD_GUILD_ID",
    "GITHUB_APP_ID",
    "GITHUB_APP_INSTALLATION_ID",
    "GITHUB_APP_PRIVATE_KEY_PATH",
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


class FailingBot:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pytest.fail("IssueBot must not be constructed on a config error")


def test_intents() -> None:
    intents = build_intents()
    assert intents.guilds is True
    assert intents.message_content is False
    assert intents.guild_messages is False
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


def test_no_message_listeners() -> None:
    assert not hasattr(IssueBot, "on_message")
    assert not hasattr(IssueBot, "on_message_edit")


async def test_default_hook_logs_ids_not_text(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    message = make_message()
    candidate = make_candidate(title="Secret title words", body="Secret body words")
    with caplog.at_level(logging.INFO):
        await open_issue_thread(message, candidate)
    info_messages = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.INFO
    ]
    assert any(
        "bug" in text and "99" in text and message.jump_url in text for text in info_messages
    )
    assert sum("thread_id=1234" in text for text in info_messages) == 1
    for text in record_texts(caplog):
        assert "Secret title words" not in text
        assert "Secret body words" not in text
        assert "Alice" not in text


async def test_default_hook_opens_one_thread_named_from_title(
    make_message: MessageFactory, make_candidate: CandidateFactory
) -> None:
    message = make_message()
    await open_issue_thread(message, make_candidate(title="Fix it"))
    message.create_thread.assert_awaited_once_with(name="Fix it")


async def test_default_hook_truncates_long_title(
    make_message: MessageFactory, make_candidate: CandidateFactory
) -> None:
    message = make_message()
    await open_issue_thread(message, make_candidate(title="y" * 150))
    message.create_thread.assert_awaited_once()
    assert len(message.create_thread.await_args.kwargs["name"]) == 100


async def test_default_hook_skips_message_with_thread(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    existing = SimpleNamespace(id=5)
    message = make_message(thread=existing)
    with caplog.at_level(logging.INFO):
        await open_issue_thread(message, make_candidate())
    message.create_thread.assert_not_awaited()
    assert any(
        record.levelno == logging.INFO and "thread_id=5" in record.getMessage()
        for record in bot_records(caplog)
    )


async def test_default_hook_logs_when_thread_fails(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    message = make_message()
    message.create_thread.side_effect = forbidden(50013, "x")
    with caplog.at_level(logging.INFO):
        await open_issue_thread(message, make_candidate(title="Secret title words"))
    assert any(
        record.levelno == logging.INFO and "thread_id=None" in record.getMessage()
        for record in bot_records(caplog)
    )
    assert any(
        record.name == "issue_bot.threads" and record.levelno == logging.ERROR
        for record in caplog.records
    )
    for text in record_texts(caplog):
        assert "Secret title words" not in text


def secret_candidate(make_candidate: CandidateFactory) -> IssueCandidate:
    return make_candidate(
        title="Secret title words", body="Secret body words", author_name="Alice"
    )


async def test_filing_hook_files_issue_and_logs_url(
    config: Config,
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL))
    message = make_message()
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    message.create_thread.assert_awaited_once_with(name="Secret title words")
    github.create_issue.assert_awaited_once()
    target, _title, _body, labels = github.create_issue.await_args.args
    assert target == config.target
    assert labels == ["bug"]
    message.create_thread.return_value.send.assert_not_awaited()
    info_messages = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.INFO
    ]
    filed = [text for text in info_messages if "filed bug" in text]
    assert len(filed) == 1
    assert all(
        part in filed[0]
        for part in ("message_id=99", message.jump_url, "thread_id=1234", ISSUE_URL)
    )
    assert_no_member_text(caplog)


async def test_filing_hook_failure_replies_and_logs_status(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(GitHubError("issue", 422))
    message = make_message()
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    message.create_thread.return_value.send.assert_awaited_once_with(FILING_ERROR_REPLY)
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert len(errors) == 1
    assert all(
        part in errors[0]
        for part in (
            "could not file bug",
            "message_id=99",
            "thread_id=1234",
            "GitHubError",
            "stage=issue",
            "status=422",
        )
    )
    assert_no_member_text(caplog)


async def test_filing_hook_files_even_without_thread(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL))
    message = make_message()
    message.create_thread.side_effect = forbidden(50013, "x")
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    github.create_issue.assert_awaited_once()
    assert any(
        record.levelno == logging.INFO
        and "filed bug" in record.getMessage()
        and "thread_id=None" in record.getMessage()
        for record in bot_records(caplog)
    )
    assert_no_member_text(caplog)


async def test_filing_hook_failure_without_thread_logs_only(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(GitHubError("token", None))
    message = make_message()
    message.create_thread.side_effect = forbidden(50013, "x")
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert len(errors) == 1
    assert "could not file bug" in errors[0] and "thread_id=None" in errors[0]
    message.create_thread.return_value.send.assert_not_awaited()
    message.fetch_thread.return_value.send.assert_not_awaited()
    assert_no_member_text(caplog)


async def test_filing_error_send_failure_logged_without_text(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(GitHubError("issue", 422))
    message = make_message()
    message.create_thread.return_value.send.side_effect = forbidden(50001, "Secret error words")
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    send_errors = [
        record.getMessage()
        for record in bot_records(caplog)
        if record.levelno == logging.ERROR and "could not send filing error" in record.getMessage()
    ]
    assert len(send_errors) == 1
    assert all(part in send_errors[0] for part in ("Forbidden", "403", "50001", "99"))
    for text in record_texts(caplog):
        assert "Secret error words" not in text
    assert_no_member_text(caplog)


async def test_filing_hook_unexpected_error_reaches_modal_on_error(
    config: Config, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    github = fake_github(RuntimeError("Secret exception words"))
    modal = IntakeModal(IssueType.BUG, config.target, filing_hook(github))
    interaction = make_interaction()
    # discord.py's own seed for a submitted value: a real submit needs the Gateway.
    modal.title_input._value = "Secret title words"
    modal.description_input._value = "Secret body words"
    with caplog.at_level(logging.INFO):
        # discord.py's own dispatch path (2.7.1: interaction, components, resolved): empty
        # components keep the seeded values, and an exception in on_submit reaches on_error.
        await modal._scheduled_task(interaction, [], {})
    github.create_issue.assert_awaited_once()
    summary = interaction.channel.send.return_value
    summary.create_thread.return_value.send.assert_not_awaited()
    intake_errors = [
        record.getMessage()
        for record in caplog.records
        if record.name == "issue_bot.intake" and record.levelno == logging.ERROR
    ]
    assert intake_errors == [
        "unhandled RuntimeError in bug modal interaction_id=4242 status=None code=None"
    ]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
    assert_no_member_text(caplog)
    interaction.followup.send.assert_awaited_once_with(INTAKE_ERROR_REPLY, ephemeral=True)
    interaction.response.send_message.assert_not_awaited()


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
            await bot.on_error("on_ready")
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert errors == ["unhandled RuntimeError in on_ready"]
    for text in record_texts(caplog):
        assert "Secret title words" not in text


async def test_raising_event_dispatched_by_discord_logs_type_only(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    on_ready = AsyncMock(side_effect=RuntimeError("Secret title words"))
    monkeypatch.setattr(bot, "on_ready", on_ready)
    with caplog.at_level(logging.INFO):
        # discord.py's own dispatch path: it catches the error and calls on_error.
        await bot._run_event(bot.on_ready, "on_ready")
    on_ready.assert_awaited_once()
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert errors == ["unhandled RuntimeError in on_ready"]
    assert_no_member_text(caplog)


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
        def __init__(self, config: Config, **kwargs: object) -> None:
            calls["config"] = config
            calls["init_kwargs"] = kwargs

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
    init_kwargs = calls["init_kwargs"]
    assert isinstance(init_kwargs, dict)
    assert callable(init_kwargs["on_candidate"])


def test_main_builds_github_client(
    monkeypatch: pytest.MonkeyPatch, test_env: dict[str, str]
) -> None:
    recorded: dict[str, tuple[object, ...]] = {}
    sentinel = object()

    class StubBot:
        def __init__(self, config: Config, **kwargs: object) -> None:
            pass

        def run(self, token: str, **kwargs: object) -> None:
            pass

    def record_client(*args: object) -> object:
        recorded["args"] = args
        return sentinel

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(entry_point, "IssueBot", StubBot)
    monkeypatch.setattr(entry_point, "GitHubClient", record_client)
    entry_point.main()
    app_id, installation_id, private_key = recorded["args"]
    assert (app_id, installation_id) == (333, 444)
    assert isinstance(private_key, rsa.RSAPrivateKey)


def test_commands_registered_for_guild_only(config: Config) -> None:
    bot = IssueBot(config)
    guild_commands = bot.tree.get_commands(guild=discord.Object(111))
    assert sorted(command.name for command in guild_commands) == ["bug", "feature"]
    assert bot.tree.get_commands() == []


async def test_setup_hook_syncs_guild_once(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    sync = AsyncMock(return_value=[SimpleNamespace(), SimpleNamespace()])
    monkeypatch.setattr(bot.tree, "sync", sync)
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    sync.assert_awaited_once()
    assert sync.await_args.args == ()
    assert list(sync.await_args.kwargs) == ["guild"]
    assert sync.await_args.kwargs["guild"].id == 111
    for call in sync.await_args_list:
        assert call.kwargs.get("guild") is not None
    assert "synced 2 commands to guild 111" in [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.INFO
    ]


async def test_setup_hook_sync_failure_logged_without_text(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    monkeypatch.setattr(
        bot.tree, "sync", AsyncMock(side_effect=forbidden(50001, "Secret error words"))
    )
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert any("Forbidden" in text and "403" in text and "50001" in text for text in errors)
    for text in record_texts(caplog):
        assert "Secret error words" not in text


async def test_setup_hook_non_http_sync_failure_logged_type_only(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(config)
    monkeypatch.setattr(
        bot.tree, "sync", AsyncMock(side_effect=RuntimeError("Secret exception words"))
    )
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert errors == ["could not sync commands to guild 111: RuntimeError"]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text


@pytest.mark.parametrize(
    ("error_kind", "expected"),
    [
        (
            "invoke_runtime",
            "unhandled RuntimeError in command bug interaction_id=4242 status=None code=None",
        ),
        (
            "check_failure",
            "unhandled CheckFailure in command tree interaction_id=4242 status=None code=None",
        ),
        (
            "invoke_forbidden",
            "unhandled Forbidden in command bug interaction_id=4242 status=403 code=50013",
        ),
    ],
)
async def test_tree_on_error_logs_type_only(
    config: Config, caplog: pytest.LogCaptureFixture, error_kind: str, expected: str
) -> None:
    bot = IssueBot(config)
    command = bot.tree.get_command("bug", guild=discord.Object(111))
    error: app_commands.AppCommandError
    if error_kind == "invoke_runtime":
        error = app_commands.CommandInvokeError(command, RuntimeError("Secret exception words"))
        interaction = SimpleNamespace(id=4242, command=command)
    elif error_kind == "check_failure":
        error = app_commands.CheckFailure("Secret exception words")
        interaction = SimpleNamespace(id=4242, command=None)
    else:
        error = app_commands.CommandInvokeError(command, forbidden(50013, "Secret error words"))
        interaction = SimpleNamespace(id=4242, command=command)
    with caplog.at_level(logging.INFO):
        await bot.tree.on_error(interaction, error)
    assert [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ] == [expected]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
        assert "Secret error words" not in text


async def test_command_callback_reaches_hook_end_to_end(
    config: Config, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    # The command captures the hook at construction: assigning bot.on_candidate later
    # would not reach it.
    bot = IssueBot(config, on_candidate=hook)
    command = bot.tree.get_command("bug", guild=discord.Object(111))
    interaction = make_interaction()
    await command.callback(interaction)
    modal = interaction.response.send_modal.await_args.args[0]
    # discord.py's own seed for a submitted value: a real submit needs the Gateway.
    modal.title_input._value = "Fix it"
    modal.description_input._value = "Steps"
    await modal.on_submit(interaction)
    hook.assert_awaited_once()
    summary, candidate = hook.await_args.args
    assert summary is interaction.channel.send.return_value
    assert isinstance(candidate, IssueCandidate)
    assert candidate.type is IssueType.BUG
    assert candidate.title == "Fix it"
    assert candidate.message_id == summary.id
