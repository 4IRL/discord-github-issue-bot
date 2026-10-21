"""Slash-command intake: ``/bug`` and ``/feature`` open a modal; a submit posts a public summary and hands it to ``on_candidate``.

Modal text and interaction payloads are member text: logs carry the issue type, the
interaction, message and channel ids and the summary URL only, and a Discord API error by its
type, HTTP status and Discord error code.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

import discord
from discord import app_commands

from issue_bot.config import TargetConfig
from issue_bot.github import GitHubError
from issue_bot.handler import IssueCandidate, candidate_from_submission
from issue_bot.issue_type import IssueType
from issue_bot.threads import THREAD_NAME_LIMIT

logger = logging.getLogger(__name__)

CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]
FilingCheck = Callable[[TargetConfig], Awaitable[None]]

TITLE_MAX_LENGTH = THREAD_NAME_LIMIT  # Owner's choice: a title is never cut in the thread name.
DESCRIPTION_MAX_LENGTH = 4000  # Discord's maximum text-input length.
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


class IntakeModal(discord.ui.Modal):
    """The report form: a required Title and an optional Description."""

    def __init__(
        self, issue_type: IssueType, target: TargetConfig, on_candidate: CandidateHook
    ) -> None:
        super().__init__(title=f"New {issue_type}", timeout=MODAL_TIMEOUT)
        self.issue_type = issue_type
        self.target = target
        self.on_candidate = on_candidate
        self.title_input: discord.ui.TextInput = discord.ui.TextInput(
            style=discord.TextStyle.short, required=True, max_length=TITLE_MAX_LENGTH
        )
        self.description_input: discord.ui.TextInput = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=DESCRIPTION_MAX_LENGTH,
        )
        self.add_item(discord.ui.Label(text="Title", component=self.title_input))
        self.add_item(discord.ui.Label(text="Description", component=self.description_input))

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        """Post the public summary, hand it and its candidate to the hook, then confirm privately."""
        # First: Discord allows 3 s, and without thinking=True a modal-submit defer is a
        # public message update.
        await interaction.response.defer(ephemeral=True, thinking=True)
        title = " ".join(self.title_input.value.split())
        description = self.description_input.value.strip()
        if not any(character.isalnum() for character in title):
            await _reply(interaction, BLANK_TITLE_REPLY, self.issue_type)
            return
        if interaction.channel is None:
            logger.error(
                "could not post %s summary interaction_id=%s: no channel",
                self.issue_type,
                interaction.id,
            )
            await _reply(interaction, SUMMARY_FAILED_REPLY, self.issue_type)
            return
        try:
            summary = await interaction.channel.send(
                summary_text(self.issue_type, title, interaction.user.mention),
                allowed_mentions=NO_MENTIONS,
                # A bare URL in a member's title must not unfurl under the bot's name.
                suppress_embeds=True,
            )
        except discord.HTTPException as exc:
            logger.error(
                "could not post %s summary interaction_id=%s: %s status=%s code=%s",
                self.issue_type,
                interaction.id,
                type(exc).__name__,
                exc.status,
                exc.code,
            )
            await _reply(interaction, SUMMARY_FAILED_REPLY, self.issue_type)
            return
        logger.info(
            "posted %s summary interaction_id=%s message_id=%s (%s)",
            self.issue_type,
            interaction.id,
            summary.id,
            summary.jump_url,
        )
        await self.on_candidate(
            summary,
            candidate_from_submission(
                self.issue_type, title, description, interaction.user, summary, self.target
            ),
        )
        await _reply(interaction, SUBMITTED_REPLY.format(url=summary.jump_url), self.issue_type)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        """Replace discord.py's default, which logs the traceback (it can quote member text).

        Logs the exception type, interaction id and Discord status and code only, then
        replies privately with fixed text.
        """
        status, code = discord_error_fields(error)
        logger.error(
            "unhandled %s in %s modal interaction_id=%s status=%s code=%s",
            type(error).__name__,
            self.issue_type,
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
                self.issue_type,
                interaction.id,
                type(exc).__name__,
                exc.status,
                exc.code,
            )
        except Exception as exc:
            # A network or timeout failure must not reach asyncio's traceback log.
            logger.error(
                "could not send %s reply interaction_id=%s: %s",
                self.issue_type,
                interaction.id,
                type(exc).__name__,
            )


def intake_command(
    issue_type: IssueType,
    target: TargetConfig,
    on_candidate: CandidateHook,
    filing_check: FilingCheck | None = None,
) -> app_commands.Command:
    """Return the slash command that opens the report modal in the intake channel only.

    When ``filing_check`` is set, it must pass within ``FILING_CHECK_TIMEOUT`` before the
    modal opens; otherwise the member gets ``FILING_UNAVAILABLE_REPLY`` privately.
    """

    # A closure: Command needs a real function, and functools.partial has no __globals__.
    async def report(interaction: discord.Interaction) -> None:
        if interaction.channel_id != target.channel_id:
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
