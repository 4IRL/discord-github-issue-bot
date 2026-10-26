import dataclasses
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from issue_bot.config import TargetConfig
from issue_bot.github import FiledIssue
from issue_bot.issue_type import IssueType
from issue_bot.issues import (
    ISSUE_TITLE_LIMIT,
    PREVIEW_LINK,
    file_candidate,
    issue_body,
    issue_labels,
    issue_title,
    render_body,
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


def test_issue_body_has_one_section_per_answer(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(answers=(("What happened?", "It broke"), ("Device", "Pixel")))
    assert issue_body(candidate) == (
        "Reported by `Alice` in Discord: https://discord.com/channels/111/555/99\n\n---\n\n"
        "### What happened?\n\nIt broke\n\n### Device\n\nPixel"
    )


@pytest.mark.parametrize("blank", ["", "  \n "])
def test_issue_body_leaves_out_blank_answers(
    make_candidate: CandidateFactory, blank: str
) -> None:
    candidate = make_candidate(answers=(("What happened?", "It broke"), ("Device", blank)))
    body = issue_body(candidate)
    assert body.endswith("### What happened?\n\nIt broke")
    assert "### Device" not in body


def test_issue_body_strips_answer_whitespace(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(answers=(("What happened?", "\n It broke \n"),))
    assert issue_body(candidate).endswith("### What happened?\n\nIt broke")


def test_issue_body_author_line_comes_before_member_text(
    make_candidate: CandidateFactory,
) -> None:
    # Member Markdown (an unclosed comment, a fake author line) can only affect what follows it.
    candidate = make_candidate(
        title="T", answers=(("What happened?", "<!--\nReported by `Mallory` in Discord: x"),)
    )
    body = issue_body(candidate)
    assert body.startswith("Reported by `Alice` in Discord: ")
    assert body.index("Reported by `Alice`") < body.index("<!--")


def test_issue_body_strips_backticks_from_author(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", answers=(), author_name="Al`ice`")
    assert issue_body(candidate).startswith("Reported by `Alice` in Discord: ")


def test_issue_body_neutralizes_mentions(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(
        title="T", answers=(("Ask @label", "ping @someone"),), author_name="@admin"
    )
    body = issue_body(candidate)
    assert "@someone" not in body
    assert "@admin" not in body
    assert "@label" not in body
    assert "@\u200bsomeone" in body
    assert "@\u200badmin" in body
    assert "### Ask @\u200blabel" in body


@pytest.mark.parametrize(
    "answers", [(), (("What happened?", ""),), (("What happened?", " "), ("Device", "\n"))]
)
def test_issue_body_without_answers_uses_placeholder(
    make_candidate: CandidateFactory, answers: tuple[tuple[str, str], ...]
) -> None:
    candidate = make_candidate(title="T", answers=answers)
    assert issue_body(candidate).endswith("\n\n---\n\n_No description given._")


def test_render_body_with_preview_link_matches_issue_body(
    make_candidate: CandidateFactory,
) -> None:
    answers = (("What happened?", "It broke"), ("Device", "Pixel"))
    candidate = make_candidate(answers=answers)
    assert render_body("Alice", PREVIEW_LINK, answers) == issue_body(candidate).replace(
        candidate.message_url, PREVIEW_LINK
    )


@pytest.mark.parametrize(
    ("issue_type", "expected"),
    [(IssueType.BUG, ["bug"]), (IssueType.FEATURE, ["enhancement"])],
)
def test_issue_labels_follow_config(
    make_candidate: CandidateFactory, issue_type: IssueType, expected: list[str]
) -> None:
    assert issue_labels(make_candidate(type=issue_type, title="T", answers=())) == expected


def test_issue_labels_use_target_mapping(
    route: TargetConfig, make_candidate: CandidateFactory
) -> None:
    custom_route = dataclasses.replace(
        route, labels={IssueType.BUG: "bug", IssueType.FEATURE: "idea"}
    )
    candidate = make_candidate(type=IssueType.FEATURE, title="T", answers=(), target=custom_route)
    assert issue_labels(candidate) == ["idea"]


async def test_file_candidate_passes_title_body_labels(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", answers=(("What happened?", "Steps here"),))
    filed = FiledIssue(7, "u")
    github = SimpleNamespace(create_issue=AsyncMock(return_value=filed))

    result = await file_candidate(github, candidate)  # type: ignore[arg-type]

    assert result is filed
    github.create_issue.assert_awaited_once_with(
        candidate.target, issue_title(candidate), issue_body(candidate), ["bug"]
    )
