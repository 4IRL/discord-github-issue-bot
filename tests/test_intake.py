import asyncio
import logging
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from issue_bot.bot import filing_hook
from issue_bot.config import Config, TargetConfig, UnroutedCommands
from issue_bot.github import FiledIssue, GitHubError
from issue_bot.intake import (
    BLANK_TITLE_REPLY,
    FILING_UNAVAILABLE_REPLY,
    INTAKE_ERROR_REPLY,
    INTAKE_REFUSAL,
    MODAL_TIMEOUT,
    NO_MENTIONS,
    SUBMITTED_REPLY,
    SUMMARY_FAILED_REPLY,
    CandidateHook,
    FilingCheck,
    IntakeModal,
    intake_command,
    summary_text,
)
from issue_bot.issue_type import IssueType
from issue_bot.threads import FILING_ERROR_REPLY, filed_reply
from tests.conftest import (
    ISSUE_URL,
    InteractionFactory,
    assert_no_member_text,
    fake_github,
    forbidden,
    record_texts,
)


def intake_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == "issue_bot.intake"]


def intake_messages(caplog: pytest.LogCaptureFixture, level: int) -> list[str]:
    return [record.getMessage() for record in intake_records(caplog) if record.levelno == level]


def filled_modal(
    route: TargetConfig,
    hook: CandidateHook,
    *,
    issue_type: IssueType = IssueType.BUG,
    title: str = "Fix it",
    description: str = "Steps",
) -> IntakeModal:
    modal = IntakeModal(issue_type, route, hook)
    # discord.py's own seed for a submitted value: a real submit needs the Gateway.
    modal.title_input._value = title
    modal.description_input._value = description
    return modal


def test_modal_fields(route: TargetConfig) -> None:
    modal = IntakeModal(IssueType.FEATURE, route, AsyncMock())
    assert modal.title == "New feature"
    assert modal.timeout == MODAL_TIMEOUT
    assert len(modal.children) == 2
    assert all(isinstance(child, discord.ui.Label) for child in modal.children)
    assert [child.text for child in modal.children] == ["Title", "Description"]
    assert modal.title_input.style is discord.TextStyle.short
    assert modal.title_input.required is True
    assert modal.title_input.max_length == 100
    assert modal.description_input.style is discord.TextStyle.paragraph
    assert modal.description_input.required is False
    assert modal.description_input.max_length == 4000


def test_command_names_follow_issue_type(config: Config) -> None:
    for issue_type in IssueType:
        command = intake_command(issue_type, config.routes, config.unrouted, AsyncMock())
        assert command.name == str(issue_type)
        assert len(command.description) < 100


async def test_command_opens_modal_in_intake_channel(
    config: Config, make_interaction: InteractionFactory
) -> None:
    command = intake_command(IssueType.FEATURE, config.routes, config.unrouted, AsyncMock())
    interaction = make_interaction()
    await command.callback(interaction)
    interaction.response.send_modal.assert_awaited_once()
    modal = interaction.response.send_modal.await_args.args[0]
    assert isinstance(modal, IntakeModal)
    assert modal.issue_type is IssueType.FEATURE
    interaction.response.send_message.assert_not_awaited()


@pytest.mark.parametrize("channel_id", [556, None])
async def test_command_refused_outside_intake_channel(
    config: Config,
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
    channel_id: int | None,
) -> None:
    hook = AsyncMock()
    command = intake_command(IssueType.BUG, config.routes, config.unrouted, hook)
    interaction = make_interaction(channel_id=channel_id)
    with caplog.at_level(logging.INFO):
        await command.callback(interaction)
    interaction.response.send_message.assert_awaited_once_with(INTAKE_REFUSAL, ephemeral=True)
    interaction.response.send_modal.assert_not_awaited()
    hook.assert_not_awaited()
    assert intake_messages(caplog, logging.INFO) == [
        f"refused bug outside the intake channel interaction_id=4242 channel_id={channel_id}"
    ]


@pytest.mark.parametrize("channel_id", [556, None])
async def test_command_ignored_outside_routes(
    config: Config,
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
    channel_id: int | None,
) -> None:
    hook = AsyncMock()
    check = AsyncMock()
    command = intake_command(IssueType.BUG, config.routes, UnroutedCommands.IGNORE, hook, check)
    interaction = make_interaction(channel_id=channel_id)
    with caplog.at_level(logging.INFO):
        await command.callback(interaction)
    interaction.response.send_message.assert_not_awaited()
    interaction.response.send_modal.assert_not_awaited()
    interaction.response.defer.assert_not_awaited()
    check.assert_not_awaited()
    hook.assert_not_awaited()
    assert [(record.levelno, record.getMessage()) for record in intake_records(caplog)] == [
        (
            logging.INFO,
            "ignored bug outside this instance's routes "
            f"interaction_id=4242 channel_id={channel_id}",
        )
    ]
    assert_no_member_text(caplog)


async def test_command_opens_modal_in_routed_channel_when_ignoring(
    config: Config, make_interaction: InteractionFactory
) -> None:
    command = intake_command(IssueType.BUG, config.routes, UnroutedCommands.IGNORE, AsyncMock())
    interaction = make_interaction()
    await command.callback(interaction)
    interaction.response.send_modal.assert_awaited_once()
    interaction.response.send_message.assert_not_awaited()


async def test_command_opens_modal_when_filing_check_passes(
    config: Config, route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    check = AsyncMock()
    command = intake_command(IssueType.BUG, config.routes, config.unrouted, AsyncMock(), check)
    interaction = make_interaction()
    await command.callback(interaction)
    check.assert_awaited_once_with(route)
    interaction.response.send_modal.assert_awaited_once()
    interaction.response.send_message.assert_not_awaited()


async def test_command_refused_when_filing_check_fails(
    config: Config, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    hook = AsyncMock()
    check = AsyncMock(side_effect=GitHubError("token", 404))
    command = intake_command(IssueType.BUG, config.routes, config.unrouted, hook, check)
    interaction = make_interaction()
    with caplog.at_level(logging.INFO):
        await command.callback(interaction)
    interaction.response.send_message.assert_awaited_once_with(
        FILING_UNAVAILABLE_REPLY, ephemeral=True
    )
    interaction.response.send_modal.assert_not_awaited()
    hook.assert_not_awaited()
    assert intake_messages(caplog, logging.ERROR) == [
        "filing unavailable for bug interaction_id=4242: GitHubError stage=token status=404"
    ]


async def test_command_refused_when_filing_check_times_out(
    config: Config,
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("issue_bot.intake.FILING_CHECK_TIMEOUT", 0.01)

    async def never_finishes(_target: TargetConfig) -> None:
        await asyncio.Event().wait()

    command = intake_command(
        IssueType.FEATURE, config.routes, config.unrouted, AsyncMock(), never_finishes
    )
    interaction = make_interaction()
    with caplog.at_level(logging.INFO):
        await command.callback(interaction)
    interaction.response.send_message.assert_awaited_once_with(
        FILING_UNAVAILABLE_REPLY, ephemeral=True
    )
    interaction.response.send_modal.assert_not_awaited()
    assert intake_messages(caplog, logging.ERROR) == [
        "filing unavailable for feature interaction_id=4242: timeout"
    ]


async def test_command_refused_when_filing_check_raises_unexpectedly(
    config: Config, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    check = AsyncMock(side_effect=ValueError("Secret exception words"))
    command = intake_command(IssueType.BUG, config.routes, config.unrouted, AsyncMock(), check)
    interaction = make_interaction()
    with caplog.at_level(logging.INFO):
        await command.callback(interaction)
    interaction.response.send_message.assert_awaited_once_with(
        FILING_UNAVAILABLE_REPLY, ephemeral=True
    )
    interaction.response.send_modal.assert_not_awaited()
    assert intake_messages(caplog, logging.ERROR) == [
        "filing unavailable for bug interaction_id=4242: ValueError"
    ]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text


async def test_command_refused_outside_channel_before_filing_check(
    config: Config, make_interaction: InteractionFactory
) -> None:
    check: FilingCheck = AsyncMock()
    command = intake_command(IssueType.BUG, config.routes, config.unrouted, AsyncMock(), check)
    interaction = make_interaction(channel_id=556)
    await command.callback(interaction)
    interaction.response.send_message.assert_awaited_once_with(INTAKE_REFUSAL, ephemeral=True)
    check.assert_not_awaited()
    interaction.response.send_modal.assert_not_awaited()


async def test_submit_defers_privately_first(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    interaction = make_interaction()
    order = Mock()
    order.attach_mock(interaction.response.defer, "defer")
    order.attach_mock(interaction.channel.send, "send")
    await filled_modal(route, AsyncMock()).on_submit(interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    call_names = [name for name, _args, _kwargs in order.mock_calls]
    assert call_names.index("defer") < call_names.index("send")


def test_summary_text_escapes_markdown() -> None:
    assert (
        summary_text(IssueType.BUG, "**x** [y](https://e.com)", "<@7>")
        == "**New bug** from <@7>: \\*\\*x\\*\\* \\[y](https://e.com)"
    )


async def test_submit_posts_summary_without_pings(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    interaction = make_interaction()
    await filled_modal(route, AsyncMock()).on_submit(interaction)
    interaction.channel.send.assert_awaited_once()
    send_call = interaction.channel.send.await_args
    assert send_call.args == (summary_text(IssueType.BUG, "Fix it", "<@7>"),)
    assert send_call.kwargs["allowed_mentions"] is NO_MENTIONS
    assert send_call.kwargs["suppress_embeds"] is True


async def test_submit_hands_summary_and_candidate_to_hook(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    interaction = make_interaction()
    summary = interaction.channel.send.return_value
    await filled_modal(route, hook).on_submit(interaction)
    hook.assert_awaited_once()
    awaited_message, candidate = hook.await_args.args
    assert awaited_message is summary
    assert candidate.type is IssueType.BUG
    assert candidate.title == "Fix it"
    assert candidate.body == "Steps"
    assert candidate.author_name == "Alice"
    assert candidate.author_id == 7
    assert candidate.message_id == 99
    assert candidate.message_url == summary.jump_url
    assert candidate.target is route


async def test_submit_confirms_privately(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    interaction = make_interaction()
    summary = interaction.channel.send.return_value
    await filled_modal(route, AsyncMock()).on_submit(interaction)
    interaction.followup.send.assert_awaited_once_with(
        SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True
    )


async def test_submit_normalizes_title_and_description(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    modal = filled_modal(route, hook, title="  Fix   it \n", description="\n Steps \n more \n")
    await modal.on_submit(make_interaction())
    _message, candidate = hook.await_args.args
    assert candidate.title == "Fix it"
    assert candidate.body == "Steps \n more"


async def test_submit_files_issue_through_filing_hook(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL))
    interaction = make_interaction()
    summary = interaction.channel.send.return_value
    await filled_modal(route, filing_hook(github)).on_submit(interaction)
    summary.create_thread.assert_awaited_once_with(name="Fix it")
    github.create_issue.assert_awaited_once()
    target, title, body, labels = github.create_issue.await_args.args
    assert target is route
    assert title == "Fix it"
    assert labels == ["bug"]
    assert body.startswith(
        "Reported by `Alice` in Discord: https://discord.com/channels/111/555/99"
    )
    summary.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(FiledIssue(7, ISSUE_URL), "Fix it"),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    summary.reply.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(
        SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True
    )


async def test_submit_logs_ids_not_text(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    modal = filled_modal(route, AsyncMock(), title="Secret title words", description="Secret body words")
    with caplog.at_level(logging.INFO):
        await modal.on_submit(make_interaction())
    messages = intake_messages(caplog, logging.INFO)
    assert any("interaction_id=4242" in text and "message_id=99" in text for text in messages)
    assert_no_member_text(caplog)


async def test_blank_title_files_nothing(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    interaction = make_interaction()
    await filled_modal(route, hook, title="  ...  ").on_submit(interaction)
    interaction.channel.send.assert_not_awaited()
    hook.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(BLANK_TITLE_REPLY, ephemeral=True)


async def test_summary_failure_files_nothing(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    hook = AsyncMock()
    interaction = make_interaction()
    interaction.channel.send.side_effect = forbidden(50013, "Secret error words")
    with caplog.at_level(logging.INFO):
        await filled_modal(route, hook).on_submit(interaction)
    hook.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(SUMMARY_FAILED_REPLY, ephemeral=True)
    errors = intake_messages(caplog, logging.ERROR)
    assert errors == [
        "could not post bug summary interaction_id=4242: Forbidden status=403 code=50013"
    ]
    for text in record_texts(caplog):
        assert "Secret error words" not in text


async def test_missing_channel_files_nothing(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    hook = AsyncMock()
    interaction = make_interaction(channel_id=None)
    with caplog.at_level(logging.INFO):
        await filled_modal(route, hook).on_submit(interaction)
    hook.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(SUMMARY_FAILED_REPLY, ephemeral=True)
    assert intake_messages(caplog, logging.ERROR) == [
        "could not post bug summary interaction_id=4242: no channel"
    ]


async def test_followup_failure_logged_without_text(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    interaction = make_interaction()
    interaction.followup.send.side_effect = forbidden(50001, "Secret error words")
    with caplog.at_level(logging.INFO):
        await filled_modal(route, AsyncMock()).on_submit(interaction)
    assert intake_messages(caplog, logging.ERROR) == [
        "could not send bug reply interaction_id=4242: Forbidden status=403 code=50001"
    ]
    for text in record_texts(caplog):
        assert "Secret error words" not in text


async def test_github_error_still_posts_filing_error_reply(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    interaction = make_interaction()
    summary = interaction.channel.send.return_value
    await filled_modal(route, filing_hook(fake_github(GitHubError("issue", 422)))).on_submit(
        interaction
    )
    summary.create_thread.return_value.send.assert_awaited_once_with(
        FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True
    )
    summary.reply.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(
        SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            RuntimeError("Secret exception words"),
            "unhandled RuntimeError in bug modal interaction_id=4242 status=None code=None",
        ),
        (
            forbidden(50013, "Secret error words"),
            "unhandled Forbidden in bug modal interaction_id=4242 status=403 code=50013",
        ),
    ],
)
async def test_modal_on_error_logs_type_only(
    route: TargetConfig,
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    expected: str,
) -> None:
    modal = IntakeModal(IssueType.BUG, route, AsyncMock())
    with caplog.at_level(logging.INFO):
        await modal.on_error(make_interaction(), error)
    assert intake_messages(caplog, logging.ERROR) == [expected]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
        assert "Secret error words" not in text


@pytest.mark.parametrize("is_done", [True, False])
async def test_modal_on_error_replies_privately(
    route: TargetConfig, make_interaction: InteractionFactory, is_done: bool
) -> None:
    modal = IntakeModal(IssueType.BUG, route, AsyncMock())
    interaction = make_interaction()
    interaction.response.is_done.return_value = is_done
    await modal.on_error(interaction, RuntimeError("boom"))
    if is_done:
        interaction.followup.send.assert_awaited_once_with(INTAKE_ERROR_REPLY, ephemeral=True)
        interaction.response.send_message.assert_not_awaited()
    else:
        interaction.response.send_message.assert_awaited_once_with(
            INTAKE_ERROR_REPLY, ephemeral=True
        )
        interaction.followup.send.assert_not_awaited()


@pytest.mark.parametrize("is_done", [True, False])
async def test_modal_on_error_reply_failure_swallowed(
    route: TargetConfig,
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
    is_done: bool,
) -> None:
    modal = IntakeModal(IssueType.BUG, route, AsyncMock())
    interaction = make_interaction()
    interaction.response.is_done.return_value = is_done
    failing = interaction.followup.send if is_done else interaction.response.send_message
    failing.side_effect = forbidden(50013, "Secret error words")
    with caplog.at_level(logging.INFO):
        await modal.on_error(interaction, RuntimeError("boom"))
    assert (
        "could not send bug reply interaction_id=4242: Forbidden status=403 code=50013"
        in intake_messages(caplog, logging.ERROR)
    )
    for text in record_texts(caplog):
        assert "Secret error words" not in text


async def test_modal_on_error_reply_non_http_failure_swallowed(
    route: TargetConfig,
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    modal = IntakeModal(IssueType.BUG, route, AsyncMock())
    interaction = make_interaction()
    interaction.response.send_message.side_effect = RuntimeError("Secret exception words")
    with caplog.at_level(logging.INFO):
        await modal.on_error(interaction, RuntimeError("boom"))
    assert (
        "could not send bug reply interaction_id=4242: RuntimeError"
        in intake_messages(caplog, logging.ERROR)
    )
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
