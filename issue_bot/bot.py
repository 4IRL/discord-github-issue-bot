"""The Discord client: listens to the intake channel and hands candidates to a hook."""

import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any

import discord

from issue_bot.config import Config
from issue_bot.handler import IssueCandidate, candidate_from_message

logger = logging.getLogger(__name__)

CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]


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


async def log_candidate(message: discord.Message, candidate: IssueCandidate) -> None:
    """Default hook: log ids and the message URL only, never member text or names."""
    logger.info(
        "captured %s message_id=%s (%s)",
        candidate.type,
        candidate.message_id,
        candidate.message_url,
    )


class IssueBot(discord.Client):
    """Turns new tagged messages in the intake channel into candidates for ``on_candidate``."""

    def __init__(self, config: Config, on_candidate: CandidateHook = log_candidate) -> None:
        super().__init__(intents=build_intents())
        self.config = config
        self.on_candidate = on_candidate
        self._startup_checked: bool = False

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
        candidate = candidate_from_message(message, self.config)
        if candidate is not None:
            await self.on_candidate(message, candidate)

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
