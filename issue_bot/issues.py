"""Turns a candidate into the GitHub issue's title, body and labels; the only place an issue body is formatted."""

from issue_bot.handler import IssueCandidate

ISSUE_TITLE_LIMIT = 256  # GitHub's maximum issue-title length.


def issue_title(candidate: IssueCandidate) -> str:
    """Return the candidate's title, truncated with an ellipsis to GitHub's limit."""
    if len(candidate.title) <= ISSUE_TITLE_LIMIT:
        return candidate.title
    return candidate.title[: ISSUE_TITLE_LIMIT - 1].rstrip() + "…"


def _defang_mentions(text: str) -> str:
    """Follow every ``@`` with a zero-width space so GitHub renders no @mention."""
    return text.replace("@", "@\u200b")


def issue_body(candidate: IssueCandidate) -> str:
    """Return the issue body: the member's body (or a placeholder), the author and the message link."""
    body = _defang_mentions(candidate.body) or "_No description given._"
    author = _defang_mentions(candidate.author_name)
    return f"{body}\n\n---\nReported by `{author}` in Discord: {candidate.message_url}"


def issue_labels(candidate: IssueCandidate) -> list[str]:
    """Return the target repo's label for the candidate's issue type."""
    return [candidate.target.labels[candidate.type]]
