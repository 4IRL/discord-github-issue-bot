from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from issue_bot.config import Config
from issue_bot.github import FiledIssue
from issue_bot.handler import IssueCandidate, candidate_from_message
from issue_bot.issues import (
    ISSUE_TITLE_LIMIT,
    file_candidate,
    issue_body,
    issue_labels,
    issue_title,
)
from tests.conftest import MessageFactory


def make_candidate(
    make_message: MessageFactory, config: Config, content: str, author_name: str = "Alice"
) -> IssueCandidate:
    candidate = candidate_from_message(make_message(content, author_name=author_name), config)
    assert isinstance(candidate, IssueCandidate)
    return candidate


def test_issue_title_is_message_title(config: Config, make_message: MessageFactory) -> None:
    candidate = make_candidate(make_message, config, "!bug\nTitle: Fix the login page")
    assert issue_title(candidate) == "Fix the login page"


def test_issue_title_truncated_to_256(config: Config, make_message: MessageFactory) -> None:
    long_title = issue_title(make_candidate(make_message, config, "!bug\nTitle: " + "x" * 300))
    assert len(long_title) == ISSUE_TITLE_LIMIT == 256
    assert long_title.endswith("…")
    exact_title = "x" * 256
    assert issue_title(make_candidate(make_message, config, "!bug\nTitle: " + exact_title)) == (
        exact_title
    )


def test_issue_body_has_body_author_and_link(config: Config, make_message: MessageFactory) -> None:
    candidate = make_candidate(make_message, config, "!bug\nTitle: T\nBody: Steps here")
    assert issue_body(candidate) == (
        "Reported by `Alice` in Discord: https://discord.com/channels/111/555/99\n\n---\n\nSteps here"
    )


def test_issue_body_author_line_comes_before_member_text(
    config: Config, make_message: MessageFactory
) -> None:
    # Member Markdown (an unclosed comment, a fake author line) can only affect what follows it.
    candidate = make_candidate(
        make_message, config, "!bug\nTitle: T\nBody: <!--\nReported by `Mallory` in Discord: x"
    )
    body = issue_body(candidate)
    assert body.startswith("Reported by `Alice` in Discord: ")
    assert body.index("Reported by `Alice`") < body.index("<!--")


def test_issue_body_strips_backticks_from_author(
    config: Config, make_message: MessageFactory
) -> None:
    candidate = make_candidate(make_message, config, "!bug\nTitle: T", author_name="Al`ice`")
    assert issue_body(candidate).startswith("Reported by `Alice` in Discord: ")


def test_issue_body_neutralizes_mentions(config: Config, make_message: MessageFactory) -> None:
    candidate = make_candidate(
        make_message, config, "!bug\nTitle: T\nBody: ping @someone", author_name="@admin"
    )
    body = issue_body(candidate)
    assert "@someone" not in body
    assert "@admin" not in body
    assert "@\u200bsomeone" in body
    assert "@\u200badmin" in body


def test_issue_body_without_body_uses_placeholder(
    config: Config, make_message: MessageFactory
) -> None:
    candidate = make_candidate(make_message, config, "!bug\nTitle: T")
    assert issue_body(candidate).endswith("\n\n---\n\n_No description given._")


@pytest.mark.parametrize(
    ("content", "expected"),
    [("!bug\nTitle: T", ["bug"]), ("!feature\nTitle: T", ["enhancement"])],
)
def test_issue_labels_follow_config(
    config: Config, make_message: MessageFactory, content: str, expected: list[str]
) -> None:
    assert issue_labels(make_candidate(make_message, config, content)) == expected


def test_issue_labels_use_target_mapping(
    test_env: dict[str, str], make_message: MessageFactory
) -> None:
    custom_config = Config.from_env({**test_env, "GITHUB_LABEL_FEATURE": "idea"})
    candidate = make_candidate(make_message, custom_config, "!feature\nTitle: T")
    assert issue_labels(candidate) == ["idea"]


async def test_file_candidate_passes_title_body_labels(
    config: Config, make_message: MessageFactory
) -> None:
    candidate = make_candidate(make_message, config, "!bug\nTitle: T\nBody: Steps here")
    filed = FiledIssue(7, "u")
    github = SimpleNamespace(create_issue=AsyncMock(return_value=filed))

    result = await file_candidate(github, candidate)  # type: ignore[arg-type]

    assert result is filed
    github.create_issue.assert_awaited_once_with(
        candidate.target, issue_title(candidate), issue_body(candidate), ["bug"]
    )
