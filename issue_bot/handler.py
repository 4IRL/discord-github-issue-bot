"""The issue candidate a slash-command report becomes."""

from collections.abc import Sequence
from dataclasses import dataclass, field

import discord

from issue_bot.complexity import Complexity
from issue_bot.config import TargetConfig
from issue_bot.issue_type import IssueType


@dataclass(frozen=True)
class IssueCandidate:
    """A report ready for the thread and filing steps.

    ``answers`` holds one ``(question label, answer)`` pair per question the modal asked.
    ``complexity`` is the band the reporter filed with; it is not member text, so it stays in
    ``repr``. Member text and names are hidden from ``repr`` so logs and tracebacks never carry them.
    """

    type: IssueType
    title: str = field(repr=False)
    answers: tuple[tuple[str, str], ...] = field(repr=False)
    complexity: Complexity
    author_id: int
    author_name: str = field(repr=False)
    message_id: int
    message_url: str
    target: TargetConfig


def candidate_from_submission(
    issue_type: IssueType,
    title: str,
    answers: Sequence[tuple[str, str]],
    complexity: Complexity,
    reporter: discord.abc.User,
    message: discord.Message,
    target: TargetConfig,
) -> IssueCandidate:
    """Return the candidate for a submitted report, tied to the bot's summary ``message``."""
    return IssueCandidate(
        type=issue_type,
        title=title,
        answers=tuple(answers),
        complexity=complexity,
        author_id=reporter.id,
        author_name=reporter.display_name,
        message_id=message.id,
        message_url=message.jump_url,
        target=target,
    )
