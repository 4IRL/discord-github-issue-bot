"""The Discord client: registers the intake commands and hands each report to a hook."""

import logging
import sys
from typing import Any

import discord
from discord import app_commands

from issue_bot.config import Config, TargetConfig
from issue_bot.github import GitHubClient, GitHubError
from issue_bot.handler import IssueCandidate
from issue_bot.intake import (
    NO_MENTIONS,
    CandidateHook,
    FilingCheck,
    discord_error_fields,
    intake_command,
)
from issue_bot.issue_type import IssueType
from issue_bot.issues import file_candidate
from issue_bot.threads import FILING_ERROR_REPLY, filed_reply, open_thread, thread_name

logger = logging.getLogger(__name__)


def build_intents() -> discord.Intents:
    """Least-privilege intents: guilds only (slash commands and modals need no intent)."""
    intents = discord.Intents.none()
    intents.guilds = True
    return intents


def channel_problems(channel: Any, route: TargetConfig, guild_id: int) -> list[str]:
    """Describe how a route's resolved intake channel differs from its configuration."""
    if channel is None:
        return [f"channel {route.channel_id} not found or not visible to the bot"]
    guild = getattr(channel, "guild", None)
    if guild is None:
        return [f"channel {channel.id} is not in a guild, expected guild {guild_id}"]
    problems: list[str] = []
    if guild.id != guild_id:
        problems.append(f"channel {channel.id} is in guild {guild.id}, expected {guild_id}")
    if channel.name != route.channel_name:
        problems.append(f"channel {channel.id} name is {channel.name!r}, expected {route.channel_name!r}")
    actual = channel.category.name if channel.category else None
    if actual != route.category:
        problems.append(f"channel {channel.id} category is {actual!r}, expected {route.category!r}")
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


async def _post_outcome(
    message: discord.Message, thread: discord.Thread | None, text: str, what: str
) -> None:
    """Post in the thread, else as a reply to the summary; log a Discord failure by type, status and code only."""
    try:
        if thread is not None:
            await thread.send(text, allowed_mentions=NO_MENTIONS, suppress_embeds=True)
        else:
            await message.reply(text, allowed_mentions=NO_MENTIONS, suppress_embeds=True)
    except discord.HTTPException as exc:
        logger.error(
            "could not send %s for message_id=%s thread_id=%s: %s status=%s code=%s",
            what,
            message.id,
            thread.id if thread else None,
            type(exc).__name__,
            exc.status,
            exc.code,
        )


def filing_hook(github: GitHubClient) -> CandidateHook:
    """Return the production hook: open the issue's thread, then file the issue on GitHub.

    The issue is filed even when the thread could not be opened. On success it posts
    ``filed_reply`` and on a ``GitHubError`` the fixed ``FILING_ERROR_REPLY``, in the thread
    or, with no thread, as a reply to the summary message. It never logs member text
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
            await _post_outcome(message, thread, FILING_ERROR_REPLY, "filing error")
            return
        logger.info(
            "filed %s message_id=%s (%s) thread_id=%s issue=%s",
            candidate.type,
            candidate.message_id,
            candidate.message_url,
            thread_id,
            issue.html_url,
        )
        await _post_outcome(message, thread, filed_reply(issue, candidate.title), "issue link")

    return file_and_report


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
    """Registers ``/bug`` and ``/feature`` in the configured guild.

    Each submitted report is posted as a public summary message in the route's intake channel, and
    that message and its candidate go to ``on_candidate`` (default: open its thread).
    ``filing_check``, when set, guards each command before its modal opens and runs once
    at startup. Production wires ``filing_hook`` as ``on_candidate`` and
    ``GitHubClient.check_access`` as ``filing_check`` in ``__main__``.
    """

    def __init__(
        self,
        config: Config,
        on_candidate: CandidateHook = open_issue_thread,
        filing_check: FilingCheck | None = None,
    ) -> None:
        super().__init__(intents=build_intents())
        self.config = config
        self.on_candidate = on_candidate
        self.filing_check = filing_check
        self._startup_checked: bool = False
        self.tree = IntakeTree(self)
        self._guild = discord.Object(id=config.guild_id)
        for issue_type in IssueType:
            # Always pass guild=: without it the command would be global.
            self.tree.add_command(
                intake_command(
                    issue_type,
                    config.routes,
                    config.unrouted,
                    self.on_candidate,
                    self.filing_check,
                ),
                guild=self._guild,
            )

    async def setup_hook(self) -> None:
        """Sync the intake commands to the configured guild, then check GitHub access.

        login() calls this once per process, unlike on_ready. A failed sync or access check
        is logged and the bot still runs: commands from an earlier sync keep working, and
        the per-command check still guards members.
        """
        await self._sync_commands()
        await self._check_github_access()

    async def _sync_commands(self) -> None:
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
        except Exception as exc:
            # Network, timeout or MissingApplicationID: log the type only, never exc_info.
            logger.error(
                "could not sync commands to guild %s: %s",
                self.config.guild_id,
                type(exc).__name__,
            )
            return
        logger.info("synced %d commands to guild %s", len(synced), self.config.guild_id)

    async def _check_github_access(self) -> None:
        if self.filing_check is None:
            return
        for route in self.config.routes.values():
            repo_id = route.github_repo_id
            try:
                await self.filing_check(route)
            except GitHubError as exc:
                logger.error(
                    "github access check failed for repo_id=%s: %s stage=%s status=%s",
                    repo_id,
                    type(exc).__name__,
                    exc.stage,
                    exc.status,
                )
                continue
            except Exception as exc:
                # A key or JWT failure must not stop the bot or log a traceback.
                logger.error(
                    "github access check failed for repo_id=%s: %s", repo_id, type(exc).__name__
                )
                continue
            logger.info("github access ok for repo_id=%s", repo_id)

    async def on_ready(self) -> None:
        """Check each route's intake channel once: on_ready fires again after each Gateway reconnect.

        The flag is set before the check, so a check that raises is logged once and not retried.
        """
        if self._startup_checked:
            return
        self._startup_checked = True
        logger.info("connected as %s", self.user)
        for route in self.config.routes.values():
            channel = self.get_channel(route.channel_id)
            # A missing channel leaves the route unable to work; a mismatched one still works.
            log_problem = logger.error if channel is None else logger.warning
            for problem in channel_problems(channel, route, self.config.guild_id):
                log_problem("%s", problem)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        """Log the exception type and event name only: tracebacks and args can quote member text."""
        error = sys.exc_info()[1]
        error_name = type(error).__name__ if error is not None else "unknown error"
        logger.error("unhandled %s in %s", error_name, event_method)
