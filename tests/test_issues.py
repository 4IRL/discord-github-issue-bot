import dataclasses
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from issue_bot.config import TargetConfig
from issue_bot.github import FiledIssue
from issue_bot.issue_type import IssueType
from issue_bot.issues import (
    ISSUE_TITLE_LIMIT,
    file_candidate,
    issue_body,
    issue_labels,
    issue_title,
)
from tests.conftest import CandidateFactory


def test_issue_title_is_message_title(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="Fix the login page")
    assert issue_title(candidate) == "Fix the login page"


def test_issue_title_truncated_to_256(make_candidate: CandidateFactory) -> None:
    long_title = issue_title(make_candidate(title="x" * 300))
    assert len(long_title) == ISSUE_TITLE_LIMIT == 256
    assert long_title.endswith("…")
    exact_title = "x" * 256
    assert issue_title(make_candidate(title=exact_title)) == exact_title


def test_issue_body_has_body_author_and_link(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", body="Steps here")
    assert issue_body(candidate) == (
        "Reported by `Alice` in Discord: https://discord.com/channels/111/555/99\n\n---\n\nSteps here"
    )


def test_issue_body_author_line_comes_before_member_text(
    make_candidate: CandidateFactory,
) -> None:
    # Member Markdown (an unclosed comment, a fake author line) can only affect what follows it.
    candidate = make_candidate(title="T", body="<!--\nReported by `Mallory` in Discord: x")
    body = issue_body(candidate)
    assert body.startswith("Reported by `Alice` in Discord: ")
    assert body.index("Reported by `Alice`") < body.index("<!--")


def test_issue_body_strips_backticks_from_author(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", body="", author_name="Al`ice`")
    assert issue_body(candidate).startswith("Reported by `Alice` in Discord: ")


def test_issue_body_neutralizes_mentions(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", body="ping @someone", author_name="@admin")
    body = issue_body(candidate)
    assert "@someone" not in body
    assert "@admin" not in body
    assert "@\u200bsomeone" in body
    assert "@\u200badmin" in body


def test_issue_body_without_body_uses_placeholder(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", body="")
    assert issue_body(candidate).endswith("\n\n---\n\n_No description given._")


@pytest.mark.parametrize(
    ("issue_type", "expected"),
    [(IssueType.BUG, ["bug"]), (IssueType.FEATURE, ["enhancement"])],
)
def test_issue_labels_follow_config(
    make_candidate: CandidateFactory, issue_type: IssueType, expected: list[str]
) -> None:
    assert issue_labels(make_candidate(type=issue_type, title="T", body="")) == expected


def test_issue_labels_use_target_mapping(
    route: TargetConfig, make_candidate: CandidateFactory
) -> None:
    custom_route = dataclasses.replace(
        route, labels={IssueType.BUG: "bug", IssueType.FEATURE: "idea"}
    )
    candidate = make_candidate(type=IssueType.FEATURE, title="T", body="", target=custom_route)
    assert issue_labels(candidate) == ["idea"]


async def test_file_candidate_passes_title_body_labels(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", body="Steps here")
    filed = FiledIssue(7, "u")
    github = SimpleNamespace(create_issue=AsyncMock(return_value=filed))

    result = await file_candidate(github, candidate)  # type: ignore[arg-type]

    assert result is filed
    github.create_issue.assert_awaited_once_with(
        candidate.target, issue_title(candidate), issue_body(candidate), ["bug"]
    )
