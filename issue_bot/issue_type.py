"""The kinds of issue the bot files; each is one slash command and one target label."""

from enum import StrEnum


class IssueType(StrEnum):
    """The kind of issue a report files."""

    BUG = "bug"
    FEATURE = "feature"
