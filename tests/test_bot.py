import dataclasses
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

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
from issue_bot.complexity import Complexity
from issue_bot.config import Config, TargetConfig
from issue_bot.github import FiledIssue, GitHubClient, GitHubError
from issue_bot.handler import IssueCandidate
from issue_bot.intake import FILING_UNAVAILABLE_REPLY, INTAKE_ERROR_REPLY, NO_MENTIONS, IntakeModal
from issue_bot.issue_type import IssueType
from issue_bot.threads import FILING_ERROR_REPLY, filed_reply
from tests.conftest import (
    ISSUE_URL,
    PROJECT,
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
    "UNROUTED_COMMANDS",
    "GITHUB_ORG",
    "GITHUB_APP_ID",
    "GITHUB_APP_INSTALLATION_ID",
    "GITHUB_APP_PRIVATE_KEY_PATH",
    "ROUTES_PATH",
)


def make_channel(
    *,
    channel_id: int = 555,
    guild_id: int = 111,
    name: str = "intake",
    category_name: str | None = "Intake",
) -> SimpleNamespace:
    category = SimpleNamespace(name=category_name) if category_name is not None else None
    return SimpleNamespace(
        id=channel_id, name=name, guild=SimpleNamespace(id=guild_id), category=category
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


def test_matching_channel_has_no_problems(config: Config, route: TargetConfig) -> None:
    assert channel_problems(make_channel(), route, config.guild_id) == []


def test_missing_channel(config: Config, route: TargetConfig) -> None:
    assert channel_problems(None, route, config.guild_id) == [
        "channel 555 not found or not visible to the bot"
    ]


def test_wrong_guild(config: Config, route: TargetConfig) -> None:
    assert channel_problems(make_channel(guild_id=222), route, config.guild_id) == [
        "channel 555 is in guild 222, expected 111"
    ]


def test_channel_without_guild(config: Config, route: TargetConfig) -> None:
    private_channel = SimpleNamespace(id=555)
    assert channel_problems(private_channel, route, config.guild_id) == [
        "channel 555 is not in a guild, expected guild 111"
    ]


def test_wrong_name(config: Config, route: TargetConfig) -> None:
    assert channel_problems(make_channel(name="general"), route, config.guild_id) == [
        "channel 555 name is 'general', expected 'intake'"
    ]


def test_wrong_category(config: Config, route: TargetConfig) -> None:
    assert channel_problems(make_channel(category_name="Other"), route, config.guild_id) == [
        "channel 555 category is 'Other', expected 'Intake'"
    ]


def test_no_category(config: Config, route: TargetConfig) -> None:
    assert channel_problems(make_channel(category_name=None), route, config.guild_id) == [
        "channel 555 category is None, expected 'Intake'"
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
    candidate = make_candidate(
        title="Secret title words", answers=(("What happened?", "Secret body words"),)
    )
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
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        author_name="Alice",
    )


async def test_filing_hook_files_issue_posts_link_and_logs_url(
    route: TargetConfig,
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL, "I_node7"))
    message = make_message()
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    message.create_thread.assert_awaited_once_with(name="Secret title words")
    github.create_issue.assert_awaited_once()
    target, _title, _body, labels = github.create_issue.await_args.args
    assert target == route
    assert labels == ["bug", "complexity:S"]
    message.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(
            FiledIssue(7, ISSUE_URL, "I_node7"), "Secret title words", Complexity.S, None
        ),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    message.reply.assert_not_awaited()
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


async def test_filing_hook_files_without_complexity_label_when_label_fails(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL, "I_node7"))
    github.ensure_label.side_effect = GitHubError("label", 403)
    message = make_message()
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    github.create_issue.assert_awaited_once()
    _target, _title, _body, labels = github.create_issue.await_args.args
    assert labels == ["bug"]
    message.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(
            FiledIssue(7, ISSUE_URL, "I_node7"), "Secret title words", Complexity.S, None
        ),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name == "issue_bot.issues" and record.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert "stage=label" in warnings[0]
    assert "status=403" in warnings[0]
    assert not [record for record in bot_records(caplog) if record.levelno == logging.ERROR]
    assert_no_member_text(caplog)


def project_candidate(
    make_candidate: CandidateFactory, project_route: TargetConfig
) -> IssueCandidate:
    return make_candidate(
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        author_name="Alice",
        complexity=Complexity.M,
        target=project_route,
    )


async def test_filing_hook_project_route_adds_to_roadmap_after_filed_log(
    project_route: TargetConfig,
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    issue = FiledIssue(7, ISSUE_URL, "I_node7")
    github = fake_github(issue)
    message = make_message()
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, project_candidate(make_candidate, project_route))
    github.add_to_project.assert_awaited_once_with(project_route, issue, Complexity.M)
    message.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(issue, "Secret title words", Complexity.M, True),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    messages = [record.getMessage() for record in caplog.records]
    filed_index = next(index for index, text in enumerate(messages) if "filed bug" in text)
    added_index = next(
        index for index, text in enumerate(messages) if "to the roadmap" in text
    )
    assert filed_index < added_index
    assert_no_member_text(caplog)


@pytest.mark.parametrize(
    "error",
    [GitHubError("project-field", 200), RuntimeError("Secret exception words")],
    ids=["github-error", "other-error"],
)
async def test_filing_hook_roadmap_failure_posts_failed_note(
    error: Exception,
    project_route: TargetConfig,
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    issue = FiledIssue(7, ISSUE_URL, "I_node7")
    github = fake_github(issue)
    github.add_to_project.side_effect = error
    message = make_message()
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, project_candidate(make_candidate, project_route))
    message.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(issue, "Secret title words", Complexity.M, False),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    assert any("filed bug" in record.getMessage() for record in bot_records(caplog))
    assert not [record for record in bot_records(caplog) if record.levelno == logging.ERROR]
    assert not [text for text in record_texts(caplog) if "Secret exception words" in text]
    assert_no_member_text(caplog)


async def test_filing_hook_track_failure_posts_failed_note(
    project_route: TargetConfig,
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    issue = FiledIssue(7, ISSUE_URL, "I_node7")
    github = fake_github(issue)
    github.set_track.side_effect = GitHubError("project-track", 200)
    message = make_message()
    candidate = make_candidate(
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        author_name="Alice",
        complexity=Complexity.M,
        track="A · Bugs",
        target=project_route,
    )
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, candidate)
    github.set_track.assert_awaited_once_with(project_route, "PVTI_1", "A · Bugs")
    message.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(issue, "Secret title words", Complexity.M, False),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    assert not [record for record in bot_records(caplog) if record.levelno == logging.ERROR]
    assert_no_member_text(caplog)


async def test_filing_hook_plain_route_skips_roadmap(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
) -> None:
    issue = FiledIssue(7, ISSUE_URL, "I_node7")
    github = fake_github(issue)
    message = make_message()
    await filing_hook(github)(message, secret_candidate(make_candidate))
    github.add_to_project.assert_not_awaited()
    message.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(issue, "Secret title words", Complexity.S, None),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )


async def test_filing_hook_failure_replies_and_logs_status(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(GitHubError("issue", 422))
    message = make_message()
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    message.create_thread.return_value.send.assert_awaited_once_with(
        FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True
    )
    message.reply.assert_not_awaited()
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


async def test_filing_hook_without_thread_replies_link_on_summary(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL, "I_node7"))
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
    message.reply.assert_awaited_once_with(
        filed_reply(
            FiledIssue(7, ISSUE_URL, "I_node7"), "Secret title words", Complexity.S, None
        ),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    message.create_thread.return_value.send.assert_not_awaited()
    assert_no_member_text(caplog)


async def test_filing_hook_failure_without_thread_replies_error_on_summary(
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
    message.reply.assert_awaited_once_with(
        FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True
    )
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


async def test_link_send_failure_logged_without_text(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL, "I_node7"))
    message = make_message()
    message.create_thread.return_value.send.side_effect = forbidden(50001, "Secret error words")
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert len(errors) == 1
    assert all(
        part in errors[0]
        for part in (
            "could not send issue link",
            "Forbidden",
            "403",
            "50001",
            "message_id=99",
            "thread_id=1234",
        )
    )
    assert any(
        record.levelno == logging.INFO and "filed bug" in record.getMessage()
        for record in bot_records(caplog)
    )
    for text in record_texts(caplog):
        assert "Secret error words" not in text
    assert_no_member_text(caplog)


async def test_summary_reply_failure_logged_without_text(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL, "I_node7"))
    message = make_message()
    message.create_thread.side_effect = forbidden(50013, "x")
    message.reply.side_effect = forbidden(50001, "Secret error words")
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert len(errors) == 1
    assert all(
        part in errors[0]
        for part in (
            "could not send issue link",
            "Forbidden",
            "403",
            "50001",
            "message_id=99",
            "thread_id=None",
        )
    )
    for text in record_texts(caplog):
        assert "Secret error words" not in text
    assert_no_member_text(caplog)


async def test_summary_error_reply_failure_logged_without_text(
    make_message: MessageFactory,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = fake_github(GitHubError("issue", 422))
    message = make_message()
    message.create_thread.side_effect = forbidden(50013, "x")
    message.reply.side_effect = forbidden(50001, "Secret error words")
    with caplog.at_level(logging.INFO):
        await filing_hook(github)(message, secret_candidate(make_candidate))
    send_errors = [
        record.getMessage()
        for record in bot_records(caplog)
        if record.levelno == logging.ERROR and "could not send filing error" in record.getMessage()
    ]
    assert len(send_errors) == 1
    assert all(
        part in send_errors[0]
        for part in ("Forbidden", "403", "50001", "message_id=99", "thread_id=None")
    )
    for text in record_texts(caplog):
        assert "Secret error words" not in text
    assert_no_member_text(caplog)


async def test_filing_hook_unexpected_error_reaches_preview_on_error(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    github = fake_github(RuntimeError("Secret exception words"))
    modal = IntakeModal(IssueType.BUG, route, filing_hook(github))
    interaction = make_interaction()
    # discord.py's own seed for a submitted value: a real submit needs the Gateway.
    modal.title_input._value = "Secret title words"
    modal.answer_inputs[0]._value = "Secret body words"
    button_interaction = make_interaction()
    with caplog.at_level(logging.INFO):
        await modal.on_submit(interaction)
        view = interaction.followup.send.await_args.kwargs["view"]
        # discord.py's own dispatch path (2.7.1: item, interaction): it reads
        # interaction.data, and an exception in the File callback reaches on_error.
        await view._scheduled_task(view.file_button, button_interaction)
    github.create_issue.assert_awaited_once()
    summary = button_interaction.channel.send.return_value
    summary.create_thread.return_value.send.assert_not_awaited()
    summary.reply.assert_not_awaited()
    intake_errors = [
        record.getMessage()
        for record in caplog.records
        if record.name == "issue_bot.intake" and record.levelno == logging.ERROR
    ]
    assert intake_errors == [
        "unhandled RuntimeError in bug preview interaction_id=4242 status=None code=None"
    ]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
    assert_no_member_text(caplog)
    button_interaction.followup.send.assert_awaited_once_with(INTAKE_ERROR_REPLY, ephemeral=True)
    button_interaction.response.send_message.assert_not_awaited()


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
    assert problems == [(logging.WARNING, "channel 555 name is 'general', expected 'intake'")]


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


async def test_on_ready_checks_each_route_once(
    two_route_config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(two_route_config)
    lookups: list[int] = []

    def get_channel(channel_id: int) -> SimpleNamespace | None:
        lookups.append(channel_id)
        return make_channel() if channel_id == 555 else None

    monkeypatch.setattr(bot, "get_channel", get_channel)
    with caplog.at_level(logging.INFO):
        await bot.on_ready()
        await bot.on_ready()
    assert lookups == [555, 556]
    problems = [
        (record.levelno, record.getMessage())
        for record in bot_records(caplog)
        if record.levelno >= logging.WARNING
    ]
    assert problems == [(logging.ERROR, "channel 556 not found or not visible to the bot")]
    assert_no_member_text(caplog)


async def test_on_ready_checks_each_route_against_its_own_name_and_category(
    two_route_config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = IssueBot(two_route_config)
    channels = {555: make_channel(), 556: make_channel(channel_id=556)}
    monkeypatch.setattr(bot, "get_channel", channels.get)
    with caplog.at_level(logging.INFO):
        await bot.on_ready()
    problems = [
        (record.levelno, record.getMessage())
        for record in bot_records(caplog)
        if record.levelno >= logging.WARNING
    ]
    assert problems == [
        (logging.WARNING, "channel 556 name is 'intake', expected 'other-intake'"),
        (logging.WARNING, "channel 556 category is 'Intake', expected 'Other'"),
    ]
    assert_no_member_text(caplog)


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


def test_main_exits_on_bad_route_file(
    monkeypatch: pytest.MonkeyPatch,
    test_env: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    missing_path = str(tmp_path / "missing.toml")
    monkeypatch.setenv("ROUTES_PATH", missing_path)
    monkeypatch.setattr(entry_point, "IssueBot", FailingBot)
    with pytest.raises(SystemExit) as exit_info:
        entry_point.main()
    assert exit_info.value.code == 2
    texts = record_texts(caplog)
    assert "configuration error: ROUTES_PATH must name a readable TOML route file" in texts
    for text in texts:
        assert missing_path not in text
    assert_no_member_text(caplog)


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
    filing_check = init_kwargs["filing_check"]
    assert isinstance(filing_check.__self__, GitHubClient)
    assert filing_check.__func__ is GitHubClient.check_access
    project_check = init_kwargs["project_check"]
    assert isinstance(project_check.__self__, GitHubClient)
    assert project_check.__func__ is GitHubClient.project_fields


def test_main_builds_github_client(
    monkeypatch: pytest.MonkeyPatch, test_env: dict[str, str]
) -> None:
    recorded: dict[str, tuple[object, ...]] = {}
    sentinel = SimpleNamespace(check_access=AsyncMock(), project_fields=AsyncMock())

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


def test_two_routes_register_one_command_set(two_route_config: Config) -> None:
    bot = IssueBot(two_route_config)
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


async def test_setup_hook_logs_github_access_ok(
    config: Config,
    route: TargetConfig,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    check = AsyncMock()
    bot = IssueBot(config, filing_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    check.assert_awaited_once_with(route)
    assert "github access ok for repo_id=222" in [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.INFO
    ]


@pytest.mark.parametrize("sync_fails", [False, True], ids=["synced", "sync-failed"])
async def test_setup_hook_github_access_failure_logged_and_survived(
    config: Config,
    route: TargetConfig,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    sync_fails: bool,
) -> None:
    check = AsyncMock(side_effect=GitHubError("token", 401))
    bot = IssueBot(config, filing_check=check)
    sync = AsyncMock(
        side_effect=forbidden(50001, "Secret error words") if sync_fails else None,
        return_value=[],
    )
    monkeypatch.setattr(bot.tree, "sync", sync)
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    sync.assert_awaited_once()
    check.assert_awaited_once_with(route)
    errors = [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ]
    assert (
        "github access check failed for repo_id=222: GitHubError stage=token status=401" in errors
    )


async def test_setup_hook_unexpected_check_failure_logged_type_only(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    check = AsyncMock(side_effect=RuntimeError("Secret exception words"))
    bot = IssueBot(config, filing_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    assert [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ] == ["github access check failed for repo_id=222: RuntimeError"]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text


async def test_setup_hook_checks_every_route_in_order(
    two_route_config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    check = AsyncMock()
    bot = IssueBot(two_route_config, filing_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    await bot.setup_hook()
    assert [call.args for call in check.await_args_list] == [
        (two_route_config.routes[555],),
        (two_route_config.routes[556],),
    ]


@pytest.mark.parametrize(
    ("error", "first_line"),
    [
        (
            GitHubError("token", 401),
            "github access check failed for repo_id=222: GitHubError stage=token status=401",
        ),
        (
            RuntimeError("Secret exception words"),
            "github access check failed for repo_id=222: RuntimeError",
        ),
    ],
    ids=["github-error", "unexpected-error"],
)
async def test_setup_hook_first_route_failure_still_checks_second(
    two_route_config: Config,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    first_line: str,
) -> None:
    check = AsyncMock(side_effect=[error, None])
    bot = IssueBot(two_route_config, filing_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    assert check.await_count == 2
    assert check.await_args_list[1].args == (two_route_config.routes[556],)
    assert [
        record.getMessage()
        for record in bot_records(caplog)
        if record.getMessage().startswith("github access")
    ] == [first_line, "github access ok for repo_id=223"]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
    assert_no_member_text(caplog)


def project_records(caplog: pytest.LogCaptureFixture) -> list[str]:
    """The bot's startup Project-check log lines, in order."""
    return [
        record.getMessage()
        for record in bot_records(caplog)
        if record.getMessage().startswith("github project")
    ]


async def test_setup_hook_checks_project_after_access(
    project_config: Config,
    project_route: TargetConfig,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    access = AsyncMock()
    check = AsyncMock()
    order = Mock()
    order.attach_mock(access, "access")
    order.attach_mock(check, "check")
    bot = IssueBot(project_config, filing_check=access, project_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    check.assert_awaited_once_with(project_route)
    assert [name for name, _args, _kwargs in order.mock_calls] == ["access", "check"]
    assert "github project ok for repo_id=222 project=2" in [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.INFO
    ]


async def test_setup_hook_project_check_github_error_logged(
    project_config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    check = AsyncMock(side_effect=GitHubError("project", 200))
    bot = IssueBot(project_config, filing_check=AsyncMock(), project_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    assert [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ] == ["github project check failed for repo_id=222 project=2: GitHubError stage=project status=200"]


async def test_setup_hook_project_check_failure_still_checks_second(
    two_route_config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    config = dataclasses.replace(
        two_route_config,
        routes={
            channel_id: dataclasses.replace(target, project=PROJECT)
            for channel_id, target in two_route_config.routes.items()
        },
    )
    check = AsyncMock(side_effect=[GitHubError("project", 200), None])
    bot = IssueBot(config, filing_check=AsyncMock(), project_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    assert check.await_count == 2
    assert check.await_args_list[1].args == (config.routes[556],)
    assert project_records(caplog) == [
        "github project check failed for repo_id=222 project=2: GitHubError stage=project status=200",
        "github project ok for repo_id=223 project=2",
    ]


async def test_setup_hook_unexpected_project_check_failure_logged_type_only(
    project_config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    check = AsyncMock(side_effect=RuntimeError("Secret exception words"))
    bot = IssueBot(project_config, filing_check=AsyncMock(), project_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    assert [
        record.getMessage() for record in bot_records(caplog) if record.levelno == logging.ERROR
    ] == ["github project check failed for repo_id=222 project=2: RuntimeError"]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text


async def test_setup_hook_skips_project_check_for_route_without_project(
    config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    check = AsyncMock()
    bot = IssueBot(config, filing_check=AsyncMock(), project_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    check.assert_not_awaited()
    assert project_records(caplog) == []


async def test_setup_hook_without_project_check_runs_access_check_only(
    project_config: Config,
    project_route: TargetConfig,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    access = AsyncMock()
    bot = IssueBot(project_config, filing_check=access)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    access.assert_awaited_once_with(project_route)
    assert project_records(caplog) == []


async def test_setup_hook_without_filing_check_skips_project_check(
    project_config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    check = AsyncMock()
    bot = IssueBot(project_config, filing_check=None, project_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    await bot.setup_hook()
    check.assert_not_awaited()


async def test_setup_hook_failed_access_check_skips_project_check(
    project_config: Config, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    check = AsyncMock()
    access = AsyncMock(side_effect=GitHubError("token", 401))
    bot = IssueBot(project_config, filing_check=access, project_check=check)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(return_value=[]))
    with caplog.at_level(logging.INFO):
        await bot.setup_hook()
    check.assert_not_awaited()
    assert project_records(caplog) == []


async def test_bot_commands_refuse_when_filing_check_fails(
    config: Config, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    check = AsyncMock(side_effect=GitHubError("token", 404))
    bot = IssueBot(config, on_candidate=hook, filing_check=check)
    for name in ("bug", "feature"):
        command = bot.tree.get_command(name, guild=discord.Object(111))
        interaction = make_interaction()
        await command.callback(interaction)
        interaction.response.send_message.assert_awaited_once_with(
            FILING_UNAVAILABLE_REPLY, ephemeral=True
        )
        interaction.response.send_modal.assert_not_awaited()
    assert check.await_count == 2
    hook.assert_not_awaited()


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
    modal.answer_inputs[0]._value = "Steps"
    await modal.on_submit(interaction)
    view = interaction.followup.send.await_args.kwargs["view"]
    button_interaction = make_interaction()
    await view.file_button.callback(button_interaction)
    hook.assert_awaited_once()
    summary, candidate = hook.await_args.args
    assert summary is button_interaction.channel.send.return_value
    assert isinstance(candidate, IssueCandidate)
    assert candidate.type is IssueType.BUG
    assert candidate.title == "Fix it"
    assert candidate.message_id == summary.id


async def test_silent_mode_through_real_tree(
    test_env: dict[str, str], make_interaction: InteractionFactory
) -> None:
    bot = IssueBot(Config.from_env({**test_env, "UNROUTED_COMMANDS": "ignore"}))
    command = bot.tree.get_command("bug", guild=discord.Object(id=111))
    unrouted = make_interaction(channel_id=557)
    await command.callback(unrouted)
    unrouted.response.send_message.assert_not_awaited()
    unrouted.response.send_modal.assert_not_awaited()
    unrouted.response.defer.assert_not_awaited()
    routed = make_interaction()
    await command.callback(routed)
    routed.response.send_modal.assert_awaited_once()
