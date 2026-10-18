"""Recognize issue tags (``!bug``, ``!feature``) and the ``Title:`` / ``Body:`` fields.

A message files an issue only in the structured form::

    !feature
    Title: Sharing/Inviting to UTubs
    Body: allow easy sharing/inviting to UTubs for members outside the UTub

``Title:`` is one line and required; ``Body:`` is optional and runs to the end of the
message, or to a later ``Title:`` line while the title is still missing or blank. Labels
are case-insensitive and may be bolded. A blank label yields to a later one with the same
name; a repeated filled label is text inside the Body and is ignored elsewhere.
"""

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
    body: str = ""


@dataclass(frozen=True)
class MalformedTag:
    """A tagged message without a usable ``Title:`` field."""

    type: IssueType


TAG_PATTERN = re.compile(r"(?<![\w!/`])!(bug|feature)(?![\w`-])", re.IGNORECASE)
FIELD_LABEL = re.compile(r"^\s*[*_]*(title|body)[*_]*\s*:[*_]*[ \t]*", re.IGNORECASE)
BRACKETED_TAG = re.compile(
    rf"\(\s*{TAG_PATTERN.pattern}\s*\)|\[\s*{TAG_PATTERN.pattern}\s*\]"
    rf"|\{{\s*{TAG_PATTERN.pattern}\s*\}}|{TAG_PATTERN.pattern}",
    re.IGNORECASE,
)
TITLE_EDGE = " .,:;-|/"


def _is_filled(name: str, lines: list[str]) -> bool:
    """Whether a field holds text: for a title, a letter or digit (the usable-title rule)."""
    text = "".join(lines)
    if name == "title":
        return any(char.isalnum() for char in text)
    return bool(text.strip())


def parse_tag(text: str) -> ParsedTag | MalformedTag | None:
    """Return the first recognized tag's type with the message's title and body.

    Returns ``None`` when the text has no tag, and ``MalformedTag`` when it has a tag but
    no ``Title:`` line with a letter or digit. Every tag is stripped from both fields; a
    line that held only a tag is dropped, and a tagged line keeps its original indent.
    """
    match = TAG_PATTERN.search(text)
    if match is None:
        return None
    issue_type = IssueType(match.group(1).lower())
    fields: dict[str, list[str]] = {}
    body_lines: list[str] | None = None
    for raw_line in text.splitlines():
        line = BRACKETED_TAG.sub(" ", raw_line)
        if line != raw_line:
            if not line.strip():
                continue
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]
            line = indent + line.lstrip()
        label = FIELD_LABEL.match(line)
        name = label.group(1).lower() if label else None
        if label is not None and not _is_filled(name, fields.get(name, [])):
            fields[name] = [line[label.end() :]]
            body_lines = fields[name] if name == "body" else None
        elif body_lines is not None:
            body_lines.append(line)
    title = " ".join("".join(fields.get("title", [])).split()).strip(TITLE_EDGE)
    if not any(char.isalnum() for char in title):
        return MalformedTag(issue_type)
    body = "\n".join(line.rstrip() for line in fields.get("body", [])).strip("\n")
    return ParsedTag(issue_type, title, body)
