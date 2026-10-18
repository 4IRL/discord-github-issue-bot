"""Turn a tagged intake-channel message into an issue candidate."""

import logging
from dataclasses import dataclass, field

import discord

from issue_bot.config import Config, TargetConfig
from issue_bot.tags import IssueType, MalformedTag, parse_tag

logger = logging.getLogger(__name__)

ACCEPTED_MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)


@dataclass(frozen=True)
class IssueCandidate:
    """A new tagged message, ready for the thread and filing steps.

    Member text and names are hidden from ``repr`` so logs and tracebacks never carry them.
    """

    type: IssueType
    title: str = field(repr=False)
    body: str = field(repr=False)
    content: str = field(repr=False)
    author_id: int
    author_name: str = field(repr=False)
    message_id: int
    message_url: str
    target: TargetConfig


def candidate_from_message(message: discord.Message, config: Config) -> IssueCandidate | None:
    """Return a candidate for a new, human, tagged message in the intake channel, else ``None``.

    Messages in threads are dropped too: their ``channel.id`` is the thread's id.
    """
    if message.channel.id != config.target.channel_id:
        return None
    if message.author.bot:
        return None
    if message.webhook_id is not None:
        return None
    if message.type not in ACCEPTED_MESSAGE_TYPES:
        return None
    parsed = parse_tag(message.content)
    if parsed is None:
        return None
    if isinstance(parsed, MalformedTag):
        logger.info(
            "ignored %s message_id=%s (%s): no usable Title: line",
            parsed.type,
            message.id,
            message.jump_url,
        )
        return None
    return IssueCandidate(
        type=parsed.type,
        title=parsed.title,
        body=parsed.body,
        content=message.content,
        author_id=message.author.id,
        author_name=message.author.display_name,
        message_id=message.id,
        message_url=message.jump_url,
        target=config.target,
    )
