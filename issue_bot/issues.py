"""Turns a candidate into the GitHub issue's title, body and labels; the only place an issue body is formatted.

Also places a filed issue on its route's roadmap Project, setting its Track when the reporter
picked one, and reuses an issue already filed for the same summary message (F12). Its log lines
(a found existing issue, a failed lookup, a skipped complexity label, a roadmap placement and a
failed one) carry the issue type, the message id, the issue URL and an error's type (with a
``GitHubError``'s stage and status) only, never member text, response text or exception text.
"""

import logging
from collections.abc import Sequence

from issue_bot.complexity import complexity_label
from issue_bot.github import FiledIssue, GitHubClient, GitHubError
from issue_bot.handler import IssueCandidate

logger = logging.getLogger(__name__)

ISSUE_TITLE_LIMIT = 256  # GitHub's maximum issue-title length.
PREVIEW_LINK = "(link added when filed)"  # Stands in for the summary link in the private preview.
AUTHOR_LINK_SEPARATOR = " in Discord: "  # Joins the author to the link on a body's first line.


def issue_title(candidate: IssueCandidate) -> str:
    """Return the candidate's title, truncated with an ellipsis to GitHub's limit."""
    if len(candidate.title) <= ISSUE_TITLE_LIMIT:
        return candidate.title
    return candidate.title[: ISSUE_TITLE_LIMIT - 1].rstrip() + "…"


def _defang_mentions(text: str) -> str:
    """Follow every ``@`` with a zero-width space so GitHub renders no @mention."""
    return text.replace("@", "@\u200b")


def render_body(author_name: str, link: str, answers: Sequence[tuple[str, str]]) -> str:
    """Return a body: the author and ``link``, then one section per answered question (or a placeholder).

    The author line comes first so member Markdown (an unclosed comment or fence, a fake author
    line) can't hide or precede it; backticks are stripped so the name can't close its code span.
    Blank answers are left out.
    """
    sections = "\n\n".join(
        f"### {_defang_mentions(label)}\n\n{_defang_mentions(answer.strip())}"
        for label, answer in answers
        if answer.strip()
    )
    author = _defang_mentions(author_name.replace("`", ""))
    return (
        f"Reported by `{author}`{AUTHOR_LINK_SEPARATOR}{link}\n\n---\n\n"
        f"{sections or '_No description given._'}"
    )


def reports_link(body: str, link: str) -> bool:
    """Whether ``body``'s first line is ``render_body``'s author line for ``link``."""
    return body.split("\n", 1)[0].rstrip("\r").endswith(f"{AUTHOR_LINK_SEPARATOR}{link}")


def issue_body(candidate: IssueCandidate) -> str:
    """Return the issue body: the author and message link, then one section per answered question (or a placeholder)."""
    return render_body(candidate.author_name, candidate.message_url, candidate.answers)


def issue_labels(candidate: IssueCandidate) -> list[str]:
    """Return the target repo's label for the candidate's issue type, then its ``complexity:<band>`` label."""
    return [
        candidate.target.labels[candidate.type],
        complexity_label(candidate.complexity),
    ]


async def file_candidate(github: GitHubClient, candidate: IssueCandidate) -> FiledIssue:
    """File the candidate as an issue in its target repo and return the filed (or already-filed) issue.

    An issue whose author line already links this summary message is returned instead of filing
    again; a failed lookup is a WARNING and the issue is filed (DD-3). The complexity label is
    created on the repo first if missing; if that fails, a WARNING is logged and the issue is
    filed with the type label only. A ``GitHubError`` from ``create_issue`` propagates.
    """
    try:
        existing = await github.find_issue(
            candidate.target, lambda body: reports_link(body, candidate.message_url)
        )
    except GitHubError as exc:
        logger.warning(
            "could not look up an existing issue for %s message_id=%s: %s stage=%s status=%s",
            candidate.type,
            candidate.message_id,
            type(exc).__name__,
            exc.stage,
            exc.status,
        )
        existing = None
    if existing is not None:
        logger.info(
            "found existing issue for %s message_id=%s issue=%s",
            candidate.type,
            candidate.message_id,
            existing.html_url,
        )
        return existing
    labels = issue_labels(candidate)
    try:
        await github.ensure_label(candidate.target, labels[1])
    except GitHubError as exc:
        logger.warning(
            "could not create complexity label for %s message_id=%s: %s stage=%s status=%s",
            candidate.type,
            candidate.message_id,
            type(exc).__name__,
            exc.stage,
            exc.status,
        )
        labels = labels[:1]
    return await github.create_issue(
        candidate.target, issue_title(candidate), issue_body(candidate), labels
    )


def _track_note(candidate: IssueCandidate) -> str:
    # The pick is a Project option name, not member text; a failed roadmap step leaves it unset,
    # so the WARNING names it for the owner's hand fix.
    return "" if candidate.track is None else f" track={candidate.track!r}"


async def place_on_roadmap(
    github: GitHubClient, candidate: IssueCandidate, issue: FiledIssue
) -> bool | None:
    """Add the filed issue to its route's Project; return ``None`` for a route with no Project.

    Returns ``True`` once the issue is on the roadmap with its Status and Effort set (and its
    Track, when the candidate carries one), and ``False`` (after a WARNING) when any part of that
    failed, a failed Track write included; the WARNING ends with ``track='<option>'`` when the
    candidate carries a pick. It never raises: the issue is already filed, and its
    link message must still be posted.
    """
    if candidate.target.project is None:
        return None
    try:
        item_id = await github.add_to_project(candidate.target, issue, candidate.complexity)
        if candidate.track is not None:
            await github.set_track(candidate.target, item_id, candidate.track)
    except GitHubError as exc:
        logger.warning(
            "could not add %s message_id=%s to the roadmap issue=%s: %s stage=%s status=%s%s",
            candidate.type,
            candidate.message_id,
            issue.html_url,
            type(exc).__name__,
            exc.stage,
            exc.status,
            _track_note(candidate),
        )
        return False
    except Exception as exc:
        # The issue is already filed, so a parsing bug must not drop the link message.
        # Log the type only, never exc_info or its text.
        logger.warning(
            "could not add %s message_id=%s to the roadmap issue=%s: %s%s",
            candidate.type,
            candidate.message_id,
            issue.html_url,
            type(exc).__name__,
            _track_note(candidate),
        )
        return False
    logger.info(
        "added %s message_id=%s to the roadmap issue=%s",
        candidate.type,
        candidate.message_id,
        issue.html_url,
    )
    return True
