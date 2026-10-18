"""Recognize issue tags (``#bug``, ``#feature``) in message text and derive a title."""

import re
from dataclasses import dataclass
from enum import StrEnum


class IssueType(StrEnum):
    BUG = "bug"
    FEATURE = "feature"


@dataclass(frozen=True)
class ParsedTag:
    type: IssueType
    title: str


TAG_PATTERN = re.compile(r"(?<![\w#/`])#(bug|feature)(?![\w`-])", re.IGNORECASE)
EMPTY_BRACKETS = re.compile(r"\(\s*\)|\[\s*\]|\{\s*\}")
TITLE_EDGE = " .,:;-|/"


def parse_tag(text: str) -> ParsedTag | None:
    """Return the first recognized tag's type and the text with every tag removed.

    Returns ``None`` when the text has no tag or nothing but the tag.
    """
    match = TAG_PATTERN.search(text)
    if match is None:
        return None
    without_tags = EMPTY_BRACKETS.sub(" ", TAG_PATTERN.sub(" ", text))
    title = " ".join(without_tags.split()).strip(TITLE_EDGE)
    if not any(char.isalnum() for char in title):
        return None
    return ParsedTag(IssueType(match.group(1).lower()), title)
