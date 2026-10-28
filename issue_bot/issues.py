"""Turns a candidate into the GitHub issue's title, body and labels; the only place an issue body is formatted.

Its one log line, a skipped complexity label, carries the issue type, the message id and the
``GitHubError``'s type, stage and status only, never member text or response text.
"""

import logging
from collections.abc import Sequence

from issue_bot.complexity import complexity_label
from issue_bot.github import FiledIssue, GitHubClient, GitHubError
from issue_bot.handler import IssueCandidate

logger = logging.getLogger(__name__)

ISSUE_TITLE_LIMIT = 256  # GitHub's maximum issue-title length.
PREVIEW_LINK = "(link added when filed)"  # Stands in for the summary link in the private preview.


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
        f"Reported by `{author}` in Discord: {link}\n\n---\n\n"
        f"{sections or '_No description given._'}"
    )


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
    """File the candidate as an issue in its target repo and return the created issue.

    The complexity label is created on the repo first if missing; if that fails, a WARNING is
    logged and the issue is filed with the type label only. A ``GitHubError`` from
    ``create_issue`` propagates.
    """
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
