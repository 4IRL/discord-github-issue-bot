import asyncio
import logging
from collections.abc import Sequence
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from issue_bot.bot import filing_hook
from issue_bot.complexity import Complexity, rate
from issue_bot.config import Config, TargetConfig, UnroutedCommands
from issue_bot.github import FiledIssue, GitHubError
from issue_bot.intake import (
    ANSWER_MAX_LENGTH,
    BLANK_TITLE_EDIT_REPLY,
    BLANK_TITLE_REPLY,
    FILING_REPLY,
    FILING_UNAVAILABLE_REPLY,
    INTAKE_ERROR_REPLY,
    INTAKE_REFUSAL,
    MODAL_TIMEOUT,
    NO_MENTIONS,
    PREVIEW_EMBED_LIMIT,
    PREVIEW_EXPIRED_REPLY,
    PREVIEW_REPLY,
    PREVIEW_SHORTENED_NOTE,
    PREVIEW_TIMEOUT,
    SUBMITTED_REPLY,
    SUMMARY_FAILED_REPLY,
    CandidateHook,
    Draft,
    FilingCheck,
    IntakeModal,
    PreviewView,
    intake_command,
    preview_embed,
    summary_text,
)
from issue_bot.issue_type import IssueType
from issue_bot.issues import PREVIEW_LINK, render_body
from issue_bot.threads import FILING_ERROR_REPLY, filed_reply
from tests.conftest import (
    ISSUE_URL,
    InteractionFactory,
    MessageFactory,
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
    answers: Sequence[str] = ("Steps",),
) -> IntakeModal:
    modal = IntakeModal(issue_type, route, hook)
    # discord.py's own seed for a submitted value: a real submit needs the Gateway.
    modal.title_input._value = title
    for index, answer in enumerate(answers):
        modal.answer_inputs[index]._value = answer
    return modal


async def submitted_preview_of(
    modal: IntakeModal, interaction: SimpleNamespace
) -> PreviewView:
    """Submit ``modal`` and return the preview view its private follow-up carries."""
    await modal.on_submit(interaction)
    return interaction.followup.send.await_args.kwargs["view"]


async def submitted_preview(
    route: TargetConfig,
    hook: CandidateHook,
    interaction: SimpleNamespace,
    **kwargs: object,
) -> PreviewView:
    """Submit a filled modal (``filled_modal``'s keywords) and return its preview view."""
    return await submitted_preview_of(filled_modal(route, hook, **kwargs), interaction)


async def reopened_modal(view: PreviewView, make_interaction: InteractionFactory) -> IntakeModal:
    """Press Edit on ``view`` and return the prefilled modal it reopens."""
    click = make_interaction()
    await view.edit_button.callback(click)
    return click.response.send_modal.await_args.args[0]


async def edited_submit(modal: IntakeModal, interaction: SimpleNamespace) -> None:
    """Submit a reopened modal with a changed title and first answer (DD-12)."""
    # discord.py's own seed for a submitted value; the Device input keeps its "" default.
    modal.title_input._value = "Fix it now"
    modal.answer_inputs[0]._value = "Steps v2"
    await modal.on_submit(interaction)


def test_bug_modal_fields(route: TargetConfig) -> None:
    modal = IntakeModal(IssueType.BUG, route, AsyncMock())
    assert modal.title == "New bug"
    assert modal.timeout == MODAL_TIMEOUT
    assert len(modal.children) == 3
    assert all(isinstance(child, discord.ui.Label) for child in modal.children)
    assert [child.text for child in modal.children] == ["Title", "What happened?", "Device"]
    assert modal.title_input.style is discord.TextStyle.short
    assert modal.title_input.required is True
    assert modal.title_input.max_length == 100
    assert modal.answer_inputs[0].style is discord.TextStyle.paragraph
    assert modal.answer_inputs[0].required is True
    assert modal.answer_inputs[0].max_length == ANSWER_MAX_LENGTH
    assert modal.answer_inputs[1].style is discord.TextStyle.short
    assert modal.answer_inputs[1].required is False


def test_feature_modal_fields(route: TargetConfig) -> None:
    modal = IntakeModal(IssueType.FEATURE, route, AsyncMock())
    assert modal.title == "New feature"
    assert modal.timeout == MODAL_TIMEOUT
    assert len(modal.children) == 2
    assert all(isinstance(child, discord.ui.Label) for child in modal.children)
    assert [child.text for child in modal.children] == ["Title", "The idea"]
    assert modal.title_input.style is discord.TextStyle.short
    assert modal.title_input.required is True
    assert modal.title_input.max_length == 100


def test_modal_prefills_from_draft(route: TargetConfig) -> None:
    draft = Draft(
        "Fix it",
        (("What happened?", "Steps"), ("Device", "")),
        Complexity.S,
        Complexity.S,
        False,
    )
    modal = IntakeModal(IssueType.BUG, route, AsyncMock(), draft=draft)
    assert modal.title_input.default == "Fix it"
    assert modal.answer_inputs[0].default == "Steps"
    assert modal.answer_inputs[1].default == ""
    blank = IntakeModal(IssueType.BUG, route, AsyncMock())
    assert blank.title_input.default is None
    assert all(answer_input.default is None for answer_input in blank.answer_inputs)


def test_draft_repr_hides_text() -> None:
    text = repr(
        Draft(
            "Secret title words",
            (("Q", "Secret body words"),),
            Complexity.S,
            Complexity.S,
            False,
        )
    )
    assert "Secret title words" not in text
    assert "Secret body words" not in text


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


@pytest.mark.parametrize(("channel_id", "route_name"), [(555, "intake"), (556, "other")])
async def test_two_routes_dispatch_by_channel(
    two_route_config: Config,
    make_interaction: InteractionFactory,
    channel_id: int,
    route_name: str,
) -> None:
    check = AsyncMock()
    command = intake_command(
        IssueType.BUG, two_route_config.routes, two_route_config.unrouted, AsyncMock(), check
    )
    interaction = make_interaction(channel_id=channel_id)
    await command.callback(interaction)
    route = two_route_config.routes[channel_id]
    assert route.name == route_name
    check.assert_awaited_once_with(route)
    interaction.response.send_modal.assert_awaited_once()
    modal = interaction.response.send_modal.await_args.args[0]
    assert modal.target.name == route_name
    interaction.response.send_message.assert_not_awaited()


async def test_two_routes_refuse_unrouted_channel(
    two_route_config: Config, make_interaction: InteractionFactory
) -> None:
    command = intake_command(
        IssueType.BUG, two_route_config.routes, UnroutedCommands.REFUSE, AsyncMock()
    )
    interaction = make_interaction(channel_id=557)
    await command.callback(interaction)
    interaction.response.send_message.assert_awaited_once_with(INTAKE_REFUSAL, ephemeral=True)
    interaction.response.send_modal.assert_not_awaited()


async def test_two_routes_ignore_unrouted_channel(
    two_route_config: Config, make_interaction: InteractionFactory
) -> None:
    command = intake_command(
        IssueType.BUG, two_route_config.routes, UnroutedCommands.IGNORE, AsyncMock()
    )
    interaction = make_interaction(channel_id=557)
    await command.callback(interaction)
    interaction.response.send_message.assert_not_awaited()
    interaction.response.send_modal.assert_not_awaited()
    interaction.response.defer.assert_not_awaited()


async def test_second_route_file_files_to_its_repo_with_its_labels(
    two_route_config: Config,
    make_interaction: InteractionFactory,
    make_message: MessageFactory,
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL))
    other = two_route_config.routes[556]
    view = await submitted_preview(other, filing_hook(github), make_interaction(channel_id=556))
    button_interaction = make_interaction(channel_id=556, summary=make_message(channel_id=556))
    await view.file_button.callback(button_interaction)
    github.create_issue.assert_awaited_once()
    target, _title, body, labels = github.create_issue.await_args.args
    assert target is other
    assert target.github_repo == "example-org/other-repo"
    assert labels == ["defect", "complexity:S"]
    assert body.startswith(
        "Reported by `Alice` in Discord: https://discord.com/channels/111/556/99"
    )


async def test_submit_defers_privately_first(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    interaction = make_interaction()
    order = Mock()
    order.attach_mock(interaction.response.defer, "defer")
    order.attach_mock(interaction.followup.send, "send")
    await filled_modal(route, AsyncMock()).on_submit(interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    call_names = [name for name, _args, _kwargs in order.mock_calls]
    assert call_names.index("defer") < call_names.index("send")


def test_summary_text_escapes_markdown() -> None:
    assert (
        summary_text(IssueType.BUG, "**x** [y](https://e.com)", "<@7>")
        == "**New bug** from <@7>: \\*\\*x\\*\\* \\[y](https://e.com)"
    )


async def test_submit_sends_private_preview_only(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    interaction = make_interaction()
    await filled_modal(route, hook, title="  Fix   it \n").on_submit(interaction)
    interaction.followup.send.assert_awaited_once()
    send_call = interaction.followup.send.await_args
    assert send_call.args == (PREVIEW_REPLY,)
    assert set(send_call.kwargs) == {"embed", "view", "ephemeral", "allowed_mentions"}
    assert send_call.kwargs["ephemeral"] is True
    assert send_call.kwargs["allowed_mentions"] is NO_MENTIONS
    embed = send_call.kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert embed.title == "Fix it"
    assert embed.description == render_body(
        "Alice", PREVIEW_LINK, (("What happened?", "Steps"), ("Device", ""))
    )
    view = send_call.kwargs["view"]
    assert isinstance(view, PreviewView)
    assert view.timeout == PREVIEW_TIMEOUT
    interaction.channel.send.assert_not_awaited()
    hook.assert_not_awaited()


async def test_long_preview_is_shortened(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    interaction = make_interaction()
    await filled_modal(route, AsyncMock(), answers=("x" * 4000, "y" * 4000)).on_submit(
        interaction
    )
    description = interaction.followup.send.await_args.kwargs["embed"].description
    assert len(description) <= PREVIEW_EMBED_LIMIT
    assert description.endswith(PREVIEW_SHORTENED_NOTE)


def test_preview_embed_boundary() -> None:
    overhead = len(render_body("Alice", PREVIEW_LINK, (("What happened?", "x"),))) - 1
    length = PREVIEW_EMBED_LIMIT - overhead
    answers = (("What happened?", "x" * length),)
    body = render_body("Alice", PREVIEW_LINK, answers)
    assert len(body) == PREVIEW_EMBED_LIMIT
    embed = preview_embed("T", answers, "Alice")
    assert embed.title == "T"
    assert embed.description == body
    assert not embed.description.endswith(PREVIEW_SHORTENED_NOTE)
    longer = preview_embed("T", (("What happened?", "x" * (length + 1)),), "Alice")
    assert len(longer.description) == PREVIEW_EMBED_LIMIT
    assert longer.description.endswith(PREVIEW_SHORTENED_NOTE)


async def test_file_acks_then_posts_summary_without_pings(
    route: TargetConfig, make_interaction: InteractionFactory, make_message: MessageFactory
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction())
    button_interaction = make_interaction(summary=make_message())
    await view.file_button.callback(button_interaction)
    button_interaction.response.edit_message.assert_awaited_once_with(
        content=FILING_REPLY, view=None
    )
    button_interaction.channel.send.assert_awaited_once()
    send_call = button_interaction.channel.send.await_args
    assert send_call.args == (summary_text(IssueType.BUG, "Fix it", "<@7>"),)
    assert send_call.kwargs["allowed_mentions"] is NO_MENTIONS
    assert send_call.kwargs["suppress_embeds"] is True


async def test_file_acks_first(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    view = await submitted_preview(route, hook, make_interaction())
    button_interaction = make_interaction()
    order = Mock()
    order.attach_mock(button_interaction.response.edit_message, "edit_message")
    order.attach_mock(button_interaction.channel.send, "send")
    order.attach_mock(hook, "hook")
    await view.file_button.callback(button_interaction)
    call_names = [name for name, _args, _kwargs in order.mock_calls]
    assert call_names.index("edit_message") < call_names.index("send")
    assert call_names.index("edit_message") < call_names.index("hook")


async def test_file_hands_summary_and_candidate_to_hook(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    view = await submitted_preview(route, hook, make_interaction())
    button_interaction = make_interaction()
    summary = button_interaction.channel.send.return_value
    await view.file_button.callback(button_interaction)
    hook.assert_awaited_once()
    awaited_message, candidate = hook.await_args.args
    assert awaited_message is summary
    assert candidate.type is IssueType.BUG
    assert candidate.title == "Fix it"
    assert candidate.answers == (("What happened?", "Steps"), ("Device", ""))
    assert candidate.author_name == "Alice"
    assert candidate.author_id == 7
    assert candidate.message_id == 99
    assert candidate.message_url == summary.jump_url
    assert candidate.target is route


async def test_file_confirms_privately(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction())
    button_interaction = make_interaction()
    summary = button_interaction.channel.send.return_value
    await view.file_button.callback(button_interaction)
    button_interaction.followup.send.assert_awaited_once_with(
        SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True
    )


async def test_file_only_once(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    view = await submitted_preview(route, hook, make_interaction())
    first = make_interaction()
    second = make_interaction()

    async def ack(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(0)
        first.response.is_done.return_value = True

    first.response.edit_message.side_effect = ack
    await asyncio.gather(view.file_button.callback(first), view.file_button.callback(second))
    hook.assert_awaited_once()
    assert view.is_finished()


async def test_submit_normalizes_title_and_answers(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    modal = filled_modal(route, hook, title="  Fix   it \n", answers=("\n Steps \n more \n",))
    view = await submitted_preview_of(modal, make_interaction())
    await view.file_button.callback(make_interaction())
    _message, candidate = hook.await_args.args
    assert candidate.title == "Fix it"
    assert candidate.answers == (("What happened?", "Steps \n more"), ("Device", ""))


async def test_file_files_issue_through_filing_hook(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL))
    view = await submitted_preview(route, filing_hook(github), make_interaction())
    button_interaction = make_interaction()
    summary = button_interaction.channel.send.return_value
    await view.file_button.callback(button_interaction)
    summary.create_thread.assert_awaited_once_with(name="Fix it")
    github.create_issue.assert_awaited_once()
    target, title, body, labels = github.create_issue.await_args.args
    assert target is route
    assert title == "Fix it"
    assert labels == ["bug", "complexity:S"]
    assert body.startswith(
        "Reported by `Alice` in Discord: https://discord.com/channels/111/555/99"
    )
    summary.create_thread.return_value.send.assert_awaited_once_with(
        filed_reply(FiledIssue(7, ISSUE_URL), "Fix it", Complexity.S),
        allowed_mentions=NO_MENTIONS,
        suppress_embeds=True,
    )
    summary.reply.assert_not_awaited()
    button_interaction.followup.send.assert_awaited_once_with(
        SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True
    )


async def test_file_logs_ids_not_text(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    modal = filled_modal(route, AsyncMock(), title="Secret title words", answers=("Secret body words",))
    with caplog.at_level(logging.INFO):
        view = await submitted_preview_of(modal, make_interaction())
        await view.file_button.callback(make_interaction())
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
    view = await submitted_preview(route, hook, make_interaction())
    button_interaction = make_interaction()
    button_interaction.channel.send.side_effect = forbidden(50013, "Secret error words")
    with caplog.at_level(logging.INFO):
        await view.file_button.callback(button_interaction)
    hook.assert_not_awaited()
    button_interaction.followup.send.assert_awaited_once_with(
        SUMMARY_FAILED_REPLY, ephemeral=True
    )
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
    view = await submitted_preview(route, hook, make_interaction())
    button_interaction = make_interaction(channel_id=None)
    with caplog.at_level(logging.INFO):
        await view.file_button.callback(button_interaction)
    hook.assert_not_awaited()
    button_interaction.followup.send.assert_awaited_once_with(
        SUMMARY_FAILED_REPLY, ephemeral=True
    )
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
    hook = filing_hook(fake_github(GitHubError("issue", 422)))
    view = await submitted_preview(route, hook, make_interaction())
    button_interaction = make_interaction()
    summary = button_interaction.channel.send.return_value
    await view.file_button.callback(button_interaction)
    summary.create_thread.return_value.send.assert_awaited_once_with(
        FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True
    )
    summary.reply.assert_not_awaited()
    button_interaction.followup.send.assert_awaited_once_with(
        SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True
    )


async def test_edit_reopens_modal_prefilled(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    interaction = make_interaction()
    view = await submitted_preview(route, hook, interaction, answers=("Steps", "Pixel"))
    button_interaction = make_interaction()
    await view.edit_button.callback(button_interaction)
    button_interaction.response.send_modal.assert_awaited_once()
    modal = button_interaction.response.send_modal.await_args.args[0]
    assert isinstance(modal, IntakeModal)
    assert modal.issue_type is IssueType.BUG
    assert modal.title_input.default == "Fix it"
    assert [answer_input.default for answer_input in modal.answer_inputs] == ["Steps", "Pixel"]
    assert not view.is_finished()
    hook.assert_not_awaited()
    interaction.channel.send.assert_not_awaited()
    button_interaction.channel.send.assert_not_awaited()


async def test_edit_keeps_the_deadline(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction())
    # Moving the deadline, not patching time.monotonic, which also drives the event loop.
    view._deadline -= 120
    await view.edit_button.callback(make_interaction())
    assert PREVIEW_TIMEOUT - 121 < view.timeout <= PREVIEW_TIMEOUT - 120
    view._deadline -= PREVIEW_TIMEOUT
    await view.edit_button.callback(make_interaction())
    assert view.timeout == 1.0


async def test_edit_after_close_does_nothing(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    view = await submitted_preview(route, hook, make_interaction())
    view._closed = True
    button_interaction = make_interaction()
    await view.edit_button.callback(button_interaction)
    button_interaction.response.send_modal.assert_not_awaited()
    hook.assert_not_awaited()


async def test_edit_submit_updates_preview_in_place(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    interaction = make_interaction()
    view = await submitted_preview(route, AsyncMock(), interaction)
    modal = await reopened_modal(view, make_interaction)
    edit_interaction = make_interaction(interaction_id=4343)
    with caplog.at_level(logging.INFO):
        await edited_submit(modal, edit_interaction)
    edit_interaction.response.edit_message.assert_awaited_once()
    edit_call = edit_interaction.response.edit_message.await_args
    assert set(edit_call.kwargs) == {"content", "embed", "view"}
    assert edit_call.kwargs["content"] == PREVIEW_REPLY
    expected = preview_embed("Fix it now", (("What happened?", "Steps v2"), ("Device", "")), "Alice")
    assert edit_call.kwargs["embed"].title == expected.title
    assert edit_call.kwargs["embed"].description == expected.description
    new_view = edit_call.kwargs["view"]
    assert isinstance(new_view, PreviewView)
    assert new_view is not view
    edit_interaction.response.defer.assert_not_awaited()
    edit_interaction.followup.send.assert_not_awaited()
    assert view.is_finished()
    assert "previewed bug interaction_id=4343" in intake_messages(caplog, logging.INFO)
    await new_view.on_timeout()
    edit_interaction.edit_original_response.assert_awaited_once_with(
        content=PREVIEW_EXPIRED_REPLY, view=None
    )
    interaction.edit_original_response.assert_not_awaited()


async def test_edit_submit_blank_title_keeps_old_preview(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction())
    modal = await reopened_modal(view, make_interaction)
    modal.title_input._value = "  ...  "
    edit_interaction = make_interaction()
    await modal.on_submit(edit_interaction)
    edit_interaction.response.send_message.assert_awaited_once_with(
        BLANK_TITLE_EDIT_REPLY, ephemeral=True
    )
    edit_interaction.response.edit_message.assert_not_awaited()
    edit_interaction.response.defer.assert_not_awaited()
    assert not view.is_finished()
    assert view._closed is False


async def test_edit_submit_failed_edit_keeps_old_preview(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction())
    modal = await reopened_modal(view, make_interaction)
    edit_interaction = make_interaction()
    edit_interaction.response.edit_message.side_effect = forbidden(50027, "Secret error words")
    with pytest.raises(discord.Forbidden):
        await edited_submit(modal, edit_interaction)
    assert not view.is_finished()
    assert view._closed is False


async def test_edit_submit_files_the_edited_text(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    view = await submitted_preview(route, hook, make_interaction())
    modal = await reopened_modal(view, make_interaction)
    edit_interaction = make_interaction()
    await edited_submit(modal, edit_interaction)
    new_view = edit_interaction.response.edit_message.await_args.kwargs["view"]
    await new_view.file_button.callback(make_interaction())
    hook.assert_awaited_once()
    _message, candidate = hook.await_args.args
    assert candidate.title == "Fix it now"
    assert candidate.answers == (("What happened?", "Steps v2"), ("Device", ""))


async def test_edit_submit_after_expiry_still_previews(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction())
    modal = await reopened_modal(view, make_interaction)
    view._closed = True
    edit_interaction = make_interaction()
    await edited_submit(modal, edit_interaction)
    edit_interaction.response.edit_message.assert_awaited_once()
    edit_call = edit_interaction.response.edit_message.await_args
    assert edit_call.kwargs["content"] == PREVIEW_REPLY
    assert isinstance(edit_call.kwargs["embed"], discord.Embed)
    assert isinstance(edit_call.kwargs["view"], PreviewView)


async def test_timeout_expires_preview_and_files_nothing(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    hook = AsyncMock()
    interaction = make_interaction()
    view = await submitted_preview(route, hook, interaction)
    await view.on_timeout()
    interaction.edit_original_response.assert_awaited_once_with(
        content=PREVIEW_EXPIRED_REPLY, view=None
    )
    hook.assert_not_awaited()
    interaction.channel.send.assert_not_awaited()


async def test_timeout_edit_failure_logged_without_text(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    interaction = make_interaction()
    view = await submitted_preview(route, AsyncMock(), interaction)
    interaction.edit_original_response.side_effect = forbidden(50027, "Secret error words")
    with caplog.at_level(logging.INFO):
        await view.on_timeout()
    assert intake_messages(caplog, logging.ERROR) == [
        "could not expire bug preview interaction_id=4242: Forbidden status=403 code=50027"
    ]
    for text in record_texts(caplog):
        assert "Secret error words" not in text


async def test_timeout_after_file_does_nothing(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    interaction = make_interaction()
    view = await submitted_preview(route, AsyncMock(), interaction)
    await view.file_button.callback(make_interaction())
    await view.on_timeout()
    interaction.edit_original_response.assert_not_awaited()


@pytest.mark.parametrize("is_done", [True, False])
async def test_preview_on_error_logs_type_and_replies_privately(
    route: TargetConfig,
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
    is_done: bool,
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction())
    button_interaction = make_interaction()
    button_interaction.response.is_done.return_value = is_done
    with caplog.at_level(logging.INFO):
        await view.on_error(
            button_interaction, RuntimeError("Secret exception words"), view.file_button
        )
    assert intake_messages(caplog, logging.ERROR) == [
        "unhandled RuntimeError in bug preview interaction_id=4242 status=None code=None"
    ]
    for text in record_texts(caplog):
        assert "Secret exception words" not in text
    if is_done:
        button_interaction.followup.send.assert_awaited_once_with(
            INTAKE_ERROR_REPLY, ephemeral=True
        )
        button_interaction.response.send_message.assert_not_awaited()
    else:
        button_interaction.response.send_message.assert_awaited_once_with(
            INTAKE_ERROR_REPLY, ephemeral=True
        )
        button_interaction.followup.send.assert_not_awaited()


async def test_preview_flow_logs_ids_not_text(
    route: TargetConfig, make_interaction: InteractionFactory, caplog: pytest.LogCaptureFixture
) -> None:
    secret = {"title": "Secret title words", "answers": ("Secret body words",)}
    with caplog.at_level(logging.INFO):
        # Preview A: submit, Edit, Edit submit, then expiry.
        view_a = await submitted_preview(route, AsyncMock(), make_interaction(), **secret)
        modal = await reopened_modal(view_a, make_interaction)
        modal.title_input._value = "Secret title words"
        modal.answer_inputs[0]._value = "Secret body words"
        edit_interaction = make_interaction()
        await modal.on_submit(edit_interaction)
        await edit_interaction.response.edit_message.await_args.kwargs["view"].on_timeout()
        # Preview B: submit, then File.
        view_b = await submitted_preview(route, AsyncMock(), make_interaction(), **secret)
        await view_b.file_button.callback(make_interaction())
    assert_no_member_text(caplog)
    messages = intake_messages(caplog, logging.INFO)
    assert messages.count("previewed bug interaction_id=4242") == 3
    assert any(text.startswith("posted bug summary interaction_id=4242") for text in messages)
    assert "preview expired bug interaction_id=4242" in messages


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


async def test_fresh_submit_draft_carries_suggested_band(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    view = await submitted_preview(route, AsyncMock(), make_interaction(), answers=("Steps",))
    expected = rate(IssueType.BUG, (("What happened?", "Steps"), ("Device", "")))
    assert view.draft.suggested == view.draft.complexity == expected
    assert view.draft.overridden is False


async def test_long_bug_is_filed_with_raised_band(
    route: TargetConfig, make_interaction: InteractionFactory
) -> None:
    github = fake_github(FiledIssue(7, ISSUE_URL))
    view = await submitted_preview(
        route, filing_hook(github), make_interaction(), answers=("x" * 900,)
    )
    await view.file_button.callback(make_interaction())
    github.create_issue.assert_awaited_once()
    _target, _title, _body, labels = github.create_issue.await_args.args
    assert labels == ["bug", "complexity:M"]
