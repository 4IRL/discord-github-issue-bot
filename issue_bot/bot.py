"""The Discord client: listens to the intake channel and hands tagged messages to hooks."""

import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any

import discord
from discord import app_commands

from issue_bot.config import Config
from issue_bot.github import GitHubClient, GitHubError
from issue_bot.handler import IssueCandidate, candidate_from_message
from issue_bot.intake import CandidateHook, discord_error_fields, intake_command
from issue_bot.issue_type import IssueType
from issue_bot.issues import file_candidate
from issue_bot.tags import MalformedTag
from issue_bot.threads import FILING_ERROR_REPLY, format_hint, open_thread, thread_name

logger = logging.getLogger(__name__)

MalformedHook = Callable[[discord.Message, MalformedTag], Awaitable[None]]


def build_intents() -> discord.Intents:
    """Least-privilege intents: guilds, guild messages and message content only."""
    intents = discord.Intents.none()
    intents.guilds = True
    intents.guild_messages = True
    intents.message_content = True
    return intents


def channel_problems(channel: Any, config: Config) -> list[str]:
    """Describe how the resolved intake channel differs from the configuration."""
    if channel is None:
        return [f"channel {config.target.channel_id} not found or not visible to the bot"]
    guild = getattr(channel, "guild", None)
    if guild is None:
        return [f"channel {channel.id} is not in a guild, expected guild {config.guild_id}"]
    problems: list[str] = []
    if guild.id != config.guild_id:
        problems.append(
            f"channel {channel.id} is in guild {guild.id}, expected {config.guild_id}"
        )
    if channel.name != config.target.channel_name:
        problems.append(
            f"channel name is {channel.name!r}, expected {config.target.channel_name!r}"
        )
    actual = channel.category.name if channel.category else None
    if actual != config.target.category:
        problems.append(f"channel category is {actual!r}, expected {config.target.category!r}")
    return problems


async def open_issue_thread(message: discord.Message, candidate: IssueCandidate) -> None:
    """Default hook: open the issue's thread and log ids and the message URL only.

    Never logs member text or names.
    """
    thread = await open_thread(message, thread_name(candidate.title))
    logger.info(
        "captured %s message_id=%s (%s) thread_id=%s",
        candidate.type,
        candidate.message_id,
        candidate.message_url,
        thread.id if thread else None,
    )


def filing_hook(github: GitHubClient) -> CandidateHook:
    """Return the production hook: open the issue's thread, then file the issue on GitHub.

    The issue is filed even when the thread could not be opened. On a ``GitHubError`` it
    replies in the thread with the fixed ``FILING_ERROR_REPLY``. It never logs member text
    or GitHub response text: only the type, ids, URLs, error type, stage and status.
    """

    async def file_and_report(message: discord.Message, candidate: IssueCandidate) -> None:
        thread = await open_thread(message, thread_name(candidate.title))
        thread_id = thread.id if thread else None
        try:
            issue = await file_candidate(github, candidate)
        except GitHubError as exc:
            logger.error(
                "could not file %s message_id=%s (%s) thread_id=%s: %s stage=%s status=%s",
                candidate.type,
                candidate.message_id,
                candidate.message_url,
                thread_id,
                type(exc).__name__,
                exc.stage,
                exc.status,
            )
            if thread is not None:
                try:
                    await thread.send(FILING_ERROR_REPLY)
                except discord.HTTPException as send_exc:
                    logger.error(
                        "could not send filing error for message_id=%s thread_id=%s: %s status=%s code=%s",
                        message.id,
                        thread.id,
                        type(send_exc).__name__,
                        send_exc.status,
                        send_exc.code,
                    )
            return
        logger.info(
            "filed %s message_id=%s (%s) thread_id=%s issue=%s",
            candidate.type,
            candidate.message_id,
            candidate.message_url,
            thread_id,
            issue.html_url,
        )

    return file_and_report


async def reply_format_hint(message: discord.Message, malformed: MalformedTag) -> None:
    """Default malformed hook: reply in a ``Format help`` thread with the expected format."""
    thread = await open_thread(message, f"Format help: !{malformed.type}")
    if thread is None:
        return
    try:
        await thread.send(format_hint(malformed.type))
    except discord.HTTPException as exc:
        logger.error(
            "could not send format hint for message_id=%s thread_id=%s: %s status=%s code=%s",
            message.id,
            thread.id,
            type(exc).__name__,
            exc.status,
            exc.code,
        )
        return
    logger.info("format hint %s message_id=%s thread_id=%s", malformed.type, message.id, thread.id)


class IntakeTree(app_commands.CommandTree):
    """The bot's command tree, with a privacy-safe error handler."""

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError, /
    ) -> None:
        """Replace discord.py's default traceback log, which can quote member text.

        Logs the exception type, the command name, the interaction id and a Discord API
        error's status and code only; never the traceback or the interaction's repr.
        """
        cause = error.original if isinstance(error, app_commands.CommandInvokeError) else error
        status, code = discord_error_fields(cause)
        logger.error(
            "unhandled %s in %s interaction_id=%s status=%s code=%s",
            type(cause).__name__,
            f"command {interaction.command.name}" if interaction.command else "command tree",
            interaction.id,
            status,
            code,
        )


class IssueBot(discord.Client):
    """Hands new tagged messages in the intake channel to hooks.

    A candidate goes to ``on_candidate`` (default: open its thread); a tagged message
    without a usable title goes to ``on_malformed`` (default: reply with the format hint).
    Production wires ``filing_hook`` as ``on_candidate`` in ``__main__``.
    """

    def __init__(
        self,
        config: Config,
        on_candidate: CandidateHook = open_issue_thread,
        on_malformed: MalformedHook = reply_format_hint,
    ) -> None:
        super().__init__(intents=build_intents())
        self.config = config
        self.on_candidate = on_candidate
        self.on_malformed = on_malformed
        self._startup_checked: bool = False
        self.tree = IntakeTree(self)
        self._guild = discord.Object(id=config.guild_id)
        for issue_type in IssueType:
            # Always pass guild=: without it the command would be global.
            self.tree.add_command(
                intake_command(issue_type, config.target, self.on_candidate), guild=self._guild
            )

    async def setup_hook(self) -> None:
        """Sync the intake commands to the configured guild.

        login() calls this once per process, unlike on_ready. A failed sync is logged and
        the bot still runs: commands from an earlier sync keep working.
        """
        try:
            synced = await self.tree.sync(guild=self._guild)
        except discord.HTTPException as exc:
            logger.error(
                "could not sync commands to guild %s: %s status=%s code=%s",
                self.config.guild_id,
                type(exc).__name__,
                exc.status,
                exc.code,
            )
            return
        logger.info("synced %d commands to guild %s", len(synced), self.config.guild_id)

    async def on_ready(self) -> None:
        """Check the intake channel once: on_ready fires again after each Gateway reconnect.

        The flag is set before the check, so a check that raises is logged once and not retried.
        """
        if self._startup_checked:
            return
        self._startup_checked = True
        logger.info("connected as %s", self.user)
        channel = self.get_channel(self.config.target.channel_id)
        # A missing channel leaves the bot unable to work; a mismatched one still works.
        log_problem = logger.error if channel is None else logger.warning
        for problem in channel_problems(channel, self.config):
            log_problem("%s", problem)

    async def on_message(self, message: discord.Message) -> None:
        result = candidate_from_message(message, self.config)
        if isinstance(result, IssueCandidate):
            await self.on_candidate(message, result)
        elif isinstance(result, MalformedTag):
            await self.on_malformed(message, result)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        """Log the exception type, event and on_message's message id only.

        Tracebacks and args can quote member text; an integer message id cannot.
        """
        error = sys.exc_info()[1]
        error_name = type(error).__name__ if error is not None else "unknown error"
        message = args[0] if event_method == "on_message" and args else None
        message_id = getattr(message, "id", None)
        if isinstance(message_id, int) and not isinstance(message_id, bool):
            logger.error(
                "unhandled %s in %s message_id=%d", error_name, event_method, message_id
            )
        else:
            logger.error("unhandled %s in %s", error_name, event_method)
