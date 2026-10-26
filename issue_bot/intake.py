"""Slash-command intake: ``/bug`` and ``/feature`` open a modal; a submit shows a private preview.

The preview's **File** button posts the public summary and hands it to ``on_candidate``;
**Edit** reopens the modal prefilled; an expired preview files nothing.

Modal text and interaction payloads are member text: logs carry the issue type, the
interaction, message and channel ids and the summary URL only, and a Discord API error by its
type, HTTP status and Discord error code.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field

import discord
from discord import app_commands

from issue_bot.config import QuestionStyle, TargetConfig, UnroutedCommands
from issue_bot.github import GitHubError
from issue_bot.handler import IssueCandidate, candidate_from_submission
from issue_bot.issue_type import IssueType
from issue_bot.issues import PREVIEW_LINK, render_body
from issue_bot.threads import THREAD_NAME_LIMIT

logger = logging.getLogger(__name__)

CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]
FilingCheck = Callable[[TargetConfig], Awaitable[None]]

TITLE_MAX_LENGTH = THREAD_NAME_LIMIT  # Owner's choice: a title is never cut in the thread name.
ANSWER_MAX_LENGTH = 4000  # Discord's maximum text-input length.
MODAL_TIMEOUT = 1800  # Seconds an open modal is kept; a later submit fails in Discord, unfiled (DD-10).
FILING_CHECK_TIMEOUT = 2.0  # Seconds; Discord needs the modal within 3 s of the command.
NO_MENTIONS = discord.AllowedMentions.none()
# Fixed text: none of these carries member text.
INTAKE_REFUSAL = "Reports go in the intake channel: run this command there."
BLANK_TITLE_REPLY = "No report was posted: the title needs a letter or digit. Run the command again."
SUMMARY_FAILED_REPLY = "Sorry, I couldn't post your report in the channel, so nothing was filed. Try again later."
SUBMITTED_REPLY = "Thanks! Your report is posted: {url}"
FILING_UNAVAILABLE_REPLY = "Sorry, reports can't be filed to GitHub right now, so the form didn't open. Try again later."
INTAKE_ERROR_REPLY = "Sorry, something went wrong with this report. Check the channel before running the command again."
PREVIEW_TIMEOUT = 600  # Seconds; under Discord's 15-minute interaction token (DD-5).
PREVIEW_EMBED_LIMIT = 4096  # Discord's maximum embed description.
PREVIEW_REPLY = "Here's your report as it will be filed. **File** posts it; **Edit** changes it. This preview expires in 10 minutes."
PREVIEW_SHORTENED_NOTE = "\n\n_…preview shortened; the full text will be filed._"
FILING_REPLY = "Filing your report…"
PREVIEW_EXPIRED_REPLY = "This preview expired, so nothing was filed. Run the command again to report it."
BLANK_TITLE_EDIT_REPLY = "The title needs a letter or digit. Press Edit to fix it."


def discord_error_fields(error: BaseException) -> tuple[int | None, int | None]:
    """Return a Discord API error's HTTP status and Discord error code, else ``(None, None)``."""
    if isinstance(error, discord.HTTPException):
        return error.status, error.code
    return None, None


def summary_text(issue_type: IssueType, title: str, reporter_mention: str) -> str:
    """Return the public summary line, with the member's title markdown-escaped (DD-14)."""
    return f"**New {issue_type}** from {reporter_mention}: {discord.utils.escape_markdown(title)}"


async def _reply(interaction: discord.Interaction, text: str, issue_type: IssueType) -> None:
    """Send fixed text privately as a follow-up, logging a Discord failure without its text."""
    try:
        await interaction.followup.send(text, ephemeral=True)
    except discord.HTTPException as exc:
        logger.error(
            "could not send %s reply interaction_id=%s: %s status=%s code=%s",
            issue_type,
            interaction.id,
            type(exc).__name__,
            exc.status,
            exc.code,
        )


async def _report_error(
    interaction: discord.Interaction, error: Exception, issue_type: IssueType, what: str
) -> None:
    """Log an unhandled error by type, ids and Discord status and code, then reply privately.

    Replaces discord.py's default handlers, which log the traceback (it can quote member text).
    """
    status, code = discord_error_fields(error)
    logger.error(
        "unhandled %s in %s %s interaction_id=%s status=%s code=%s",
        type(error).__name__,
        issue_type,
        what,
        interaction.id,
        status,
        code,
    )
    try:
        if interaction.response.is_done():
            await interaction.followup.send(INTAKE_ERROR_REPLY, ephemeral=True)
        else:
            await interaction.response.send_message(INTAKE_ERROR_REPLY, ephemeral=True)
    except discord.HTTPException as exc:
        logger.error(
            "could not send %s reply interaction_id=%s: %s status=%s code=%s",
            issue_type,
            interaction.id,
            type(exc).__name__,
            exc.status,
            exc.code,
        )
    except Exception as exc:
        # A network or timeout failure must not reach asyncio's traceback log.
        logger.error(
            "could not send %s reply interaction_id=%s: %s",
            issue_type,
            interaction.id,
            type(exc).__name__,
        )


@dataclass(frozen=True)
class Draft:
    """A report's title and ``(label, answer)`` pairs: member text, hidden from repr."""

    title: str = field(repr=False)
    answers: tuple[tuple[str, str], ...] = field(repr=False)


def preview_embed(
    title: str, answers: Sequence[tuple[str, str]], author_name: str
) -> discord.Embed:
    """Return the preview embed: the issue body as filed, with ``PREVIEW_LINK`` for the summary link.

    A body past ``PREVIEW_EMBED_LIMIT`` is cut and ends with ``PREVIEW_SHORTENED_NOTE``; the
    filed issue is never cut (DD-3).
    """
    text = render_body(author_name, PREVIEW_LINK, answers)
    if len(text) > PREVIEW_EMBED_LIMIT:
        text = text[: PREVIEW_EMBED_LIMIT - len(PREVIEW_SHORTENED_NOTE)] + PREVIEW_SHORTENED_NOTE
    return discord.Embed(title=title, description=text)


async def _post_and_file(
    interaction: discord.Interaction,
    issue_type: IssueType,
    target: TargetConfig,
    on_candidate: CandidateHook,
    draft: Draft,
) -> None:
    """Post the public summary, hand it and its candidate to the hook, then confirm privately."""
    if interaction.channel is None:
        logger.error(
            "could not post %s summary interaction_id=%s: no channel",
            issue_type,
            interaction.id,
        )
        await _reply(interaction, SUMMARY_FAILED_REPLY, issue_type)
        return
    try:
        summary = await interaction.channel.send(
            summary_text(issue_type, draft.title, interaction.user.mention),
            allowed_mentions=NO_MENTIONS,
            # A bare URL in a member's title must not unfurl under the bot's name.
            suppress_embeds=True,
        )
    except discord.HTTPException as exc:
        logger.error(
            "could not post %s summary interaction_id=%s: %s status=%s code=%s",
            issue_type,
            interaction.id,
            type(exc).__name__,
            exc.status,
            exc.code,
        )
        await _reply(interaction, SUMMARY_FAILED_REPLY, issue_type)
        return
    logger.info(
        "posted %s summary interaction_id=%s message_id=%s (%s)",
        issue_type,
        interaction.id,
        summary.id,
        summary.jump_url,
    )
    await on_candidate(
        summary,
        candidate_from_submission(
            issue_type,
            draft.title,
            draft.answers,
            interaction.user,
            summary,
            target,
        ),
    )
    await _reply(interaction, SUBMITTED_REPLY.format(url=summary.jump_url), issue_type)


class PreviewView(discord.ui.View):
    """The private preview's buttons: **File** files the draft once, **Edit** reopens the modal.

    The preview expires ``PREVIEW_TIMEOUT`` seconds after the submit that showed it; a button
    press never extends that deadline (DD-5).
    """

    def __init__(
        self,
        issue_type: IssueType,
        target: TargetConfig,
        on_candidate: CandidateHook,
        draft: Draft,
        interaction: discord.Interaction,
    ) -> None:
        super().__init__(timeout=PREVIEW_TIMEOUT)
        self.issue_type = issue_type
        self.target = target
        self.on_candidate = on_candidate
        self.draft = draft
        # The interaction whose original response is the preview message.
        self.interaction = interaction
        self._closed = False
        self._deadline = time.monotonic() + PREVIEW_TIMEOUT

    def _keep_deadline(self) -> None:
        # discord.py 2.7.1 resets the expiry to now + timeout before every callback; the
        # timeout setter puts it back on the deadline.
        self.timeout = max(self._deadline - time.monotonic(), 1.0)

    @discord.ui.button(label="File", style=discord.ButtonStyle.success)
    async def file_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self._keep_deadline()
        if self._closed:
            return
        # No await before closing: each click runs as its own task, so this guard files once.
        self._closed = True
        self.stop()
        await interaction.response.edit_message(content=FILING_REPLY, view=None)
        await _post_and_file(
            interaction, self.issue_type, self.target, self.on_candidate, self.draft
        )

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary)
    async def edit_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self._keep_deadline()
        if self._closed:
            return
        # The view stays open, so a cancelled Edit leaves the preview usable.
        await interaction.response.send_modal(
            IntakeModal(
                self.issue_type, self.target, self.on_candidate, draft=self.draft, preview=self
            )
        )

    async def on_timeout(self) -> None:
        """Edit the preview to ``PREVIEW_EXPIRED_REPLY``, keeping its embed; nothing is filed."""
        if self._closed:
            return
        self._closed = True
        logger.info(
            "preview expired %s interaction_id=%s", self.issue_type, self.interaction.id
        )
        try:
            await self.interaction.edit_original_response(
                content=PREVIEW_EXPIRED_REPLY, view=None
            )
        except discord.HTTPException as exc:
            logger.error(
                "could not expire %s preview interaction_id=%s: %s status=%s code=%s",
                self.issue_type,
                self.interaction.id,
                type(exc).__name__,
                exc.status,
                exc.code,
            )
        except Exception as exc:
            # A network or timeout failure must not reach asyncio's traceback log.
            logger.error(
                "could not expire %s preview interaction_id=%s: %s",
                self.issue_type,
                self.interaction.id,
                type(exc).__name__,
            )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item, /
    ) -> None:
        """Replace discord.py's default, which logs the traceback (it can quote member text)."""
        await _report_error(interaction, error, self.issue_type, "preview")


class IntakeModal(discord.ui.Modal):
    """The report form: a required Title plus the route's questions for the issue type."""

    def __init__(
        self,
        issue_type: IssueType,
        target: TargetConfig,
        on_candidate: CandidateHook,
        draft: Draft | None = None,
        preview: PreviewView | None = None,
    ) -> None:
        super().__init__(title=f"New {issue_type}", timeout=MODAL_TIMEOUT)
        self.issue_type = issue_type
        self.target = target
        self.on_candidate = on_candidate
        # The preview an Edit reopened this modal from; None for a fresh report.
        self.preview = preview
        self.questions = target.questions[issue_type]
        self.title_input: discord.ui.TextInput = discord.ui.TextInput(
            style=discord.TextStyle.short,
            required=True,
            max_length=TITLE_MAX_LENGTH,
            default=draft.title if draft else None,
        )
        self.add_item(discord.ui.Label(text="Title", component=self.title_input))
        self.answer_inputs: list[discord.ui.TextInput] = []
        for index, question in enumerate(self.questions):
            answer_input: discord.ui.TextInput = discord.ui.TextInput(
                style=(
                    discord.TextStyle.short
                    if question.style is QuestionStyle.SHORT
                    else discord.TextStyle.paragraph
                ),
                required=question.required,
                max_length=ANSWER_MAX_LENGTH,
                default=draft.answers[index][1] if draft else None,
            )
            self.answer_inputs.append(answer_input)
            self.add_item(discord.ui.Label(text=question.label, component=answer_input))

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        """Show the private preview, or, after Edit, update the preview in place."""
        if self.preview is None:
            # First: Discord allows 3 s, and without thinking=True a modal-submit defer is a
            # public message update.
            await interaction.response.defer(ephemeral=True, thinking=True)
        title = " ".join(self.title_input.value.split())
        answers = tuple(
            (question.label, answer_input.value.strip())
            for question, answer_input in zip(self.questions, self.answer_inputs)
        )
        if not any(character.isalnum() for character in title):
            if self.preview is None:
                await _reply(interaction, BLANK_TITLE_REPLY, self.issue_type)
            else:
                await interaction.response.send_message(BLANK_TITLE_EDIT_REPLY, ephemeral=True)
            return
        # Always a fresh preview with its own deadline, even if the old one expired (DD-6).
        view = PreviewView(
            self.issue_type, self.target, self.on_candidate, Draft(title, answers), interaction
        )
        logger.info("previewed %s interaction_id=%s", self.issue_type, interaction.id)
        embed = preview_embed(title, answers, interaction.user.display_name)
        if self.preview is None:
            try:
                await interaction.followup.send(
                    PREVIEW_REPLY,
                    embed=embed,
                    view=view,
                    ephemeral=True,
                    allowed_mentions=NO_MENTIONS,
                )
            except discord.HTTPException as exc:
                logger.error(
                    "could not send %s reply interaction_id=%s: %s status=%s code=%s",
                    self.issue_type,
                    interaction.id,
                    type(exc).__name__,
                    exc.status,
                    exc.code,
                )
            return
        await interaction.response.edit_message(content=PREVIEW_REPLY, embed=embed, view=view)
        # Only after the edit lands: a failed edit leaves the old preview usable (DD-13).
        self.preview._closed = True
        self.preview.stop()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        """Replace discord.py's default, which logs the traceback (it can quote member text).

        Logs the exception type, interaction id and Discord status and code only, then
        replies privately with fixed text.
        """
        await _report_error(interaction, error, self.issue_type, "modal")


def intake_command(
    issue_type: IssueType,
    routes: Mapping[int, TargetConfig],
    unrouted: UnroutedCommands,
    on_candidate: CandidateHook,
    filing_check: FilingCheck | None = None,
) -> app_commands.Command:
    """Return the slash command that opens the report modal in a routed intake channel.

    Elsewhere it refuses privately or, with ``UnroutedCommands.IGNORE``, stays silent.

    When ``filing_check`` is set, it must pass within ``FILING_CHECK_TIMEOUT`` before the
    modal opens; otherwise the member gets ``FILING_UNAVAILABLE_REPLY`` privately.
    """

    # A closure: Command needs a real function, and functools.partial has no __globals__.
    async def report(interaction: discord.Interaction) -> None:
        target = routes.get(interaction.channel_id)
        if target is None and unrouted is UnroutedCommands.IGNORE:
            # Another instance on this bot token may own the channel; any reply here would race it.
            logger.info(
                "ignored %s outside this instance's routes interaction_id=%s channel_id=%s",
                issue_type,
                interaction.id,
                interaction.channel_id,
            )
            return
        if target is None:
            logger.info(
                "refused %s outside the intake channel interaction_id=%s channel_id=%s",
                issue_type,
                interaction.id,
                interaction.channel_id,
            )
            await interaction.response.send_message(INTAKE_REFUSAL, ephemeral=True)
            return
        if filing_check is not None:
            try:
                await asyncio.wait_for(filing_check(target), FILING_CHECK_TIMEOUT)
            except GitHubError as exc:
                logger.error(
                    "filing unavailable for %s interaction_id=%s: %s stage=%s status=%s",
                    issue_type,
                    interaction.id,
                    type(exc).__name__,
                    exc.stage,
                    exc.status,
                )
                await interaction.response.send_message(FILING_UNAVAILABLE_REPLY, ephemeral=True)
                return
            except TimeoutError:
                logger.error(
                    "filing unavailable for %s interaction_id=%s: timeout",
                    issue_type,
                    interaction.id,
                )
                await interaction.response.send_message(FILING_UNAVAILABLE_REPLY, ephemeral=True)
                return
            except Exception as exc:
                # A key or JWT failure: reply rather than leave Discord's "did not respond".
                logger.error(
                    "filing unavailable for %s interaction_id=%s: %s",
                    issue_type,
                    interaction.id,
                    type(exc).__name__,
                )
                await interaction.response.send_message(FILING_UNAVAILABLE_REPLY, ephemeral=True)
                return
        await interaction.response.send_modal(IntakeModal(issue_type, target, on_candidate))

    return app_commands.Command(
        name=str(issue_type),
        description=f"Report a {issue_type} as a GitHub issue",
        callback=report,
    )
