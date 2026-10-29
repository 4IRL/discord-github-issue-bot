import dataclasses
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from issue_bot.complexity import Complexity
from issue_bot.config import TargetConfig
from issue_bot.github import FiledIssue, GitHubError
from issue_bot.issue_type import IssueType
from issue_bot.issues import (
    ISSUE_TITLE_LIMIT,
    PREVIEW_LINK,
    file_candidate,
    issue_body,
    issue_labels,
    issue_title,
    place_on_roadmap,
    render_body,
)
from tests.conftest import ISSUE_URL, CandidateFactory, assert_no_member_text, record_texts


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
    [
        (IssueType.BUG, ["bug", "complexity:S"]),
        (IssueType.FEATURE, ["enhancement", "complexity:S"]),
    ],
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
    assert issue_labels(candidate) == ["idea", "complexity:S"]


def test_issue_labels_end_with_candidate_band(make_candidate: CandidateFactory) -> None:
    labels = issue_labels(make_candidate(complexity=Complexity.XL))
    assert labels[-1] == "complexity:XL"


async def test_file_candidate_passes_title_body_labels(make_candidate: CandidateFactory) -> None:
    candidate = make_candidate(title="T", answers=(("What happened?", "Steps here"),))
    filed = FiledIssue(7, "u", "I_node7")
    github = SimpleNamespace(
        create_issue=AsyncMock(return_value=filed), ensure_label=AsyncMock()
    )
    order = Mock()
    order.attach_mock(github.ensure_label, "ensure_label")
    order.attach_mock(github.create_issue, "create_issue")

    result = await file_candidate(github, candidate)  # type: ignore[arg-type]

    assert result is filed
    github.ensure_label.assert_awaited_once_with(candidate.target, "complexity:S")
    github.create_issue.assert_awaited_once_with(
        candidate.target, issue_title(candidate), issue_body(candidate), ["bug", "complexity:S"]
    )
    call_names = [name for name, _args, _kwargs in order.mock_calls]
    assert call_names.index("ensure_label") < call_names.index("create_issue")


async def test_file_candidate_files_without_complexity_label_when_label_fails(
    make_candidate: CandidateFactory, caplog: pytest.LogCaptureFixture
) -> None:
    candidate = make_candidate(
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        author_name="Alice",
    )
    filed = FiledIssue(7, "u", "I_node7")
    github = SimpleNamespace(
        create_issue=AsyncMock(return_value=filed),
        ensure_label=AsyncMock(side_effect=GitHubError("label", 500)),
    )

    with caplog.at_level(logging.INFO):
        result = await file_candidate(github, candidate)  # type: ignore[arg-type]

    assert result is filed
    github.create_issue.assert_awaited_once()
    _target, _title, _body, labels = github.create_issue.await_args.args
    assert labels == ["bug"]
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name == "issue_bot.issues" and record.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert "could not create complexity label for bug" in warnings[0]
    assert "message_id=99" in warnings[0]
    assert "GitHubError" in warnings[0]
    assert "stage=label" in warnings[0]
    assert "status=500" in warnings[0]
    assert_no_member_text(caplog)


def issues_records(caplog: pytest.LogCaptureFixture, level: int) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "issue_bot.issues" and record.levelno == level
    ]


async def test_place_on_roadmap_skips_route_without_project(
    make_candidate: CandidateFactory,
) -> None:
    github = SimpleNamespace(add_to_project=AsyncMock())
    issue = FiledIssue(7, ISSUE_URL, "I_node7")

    result = await place_on_roadmap(github, make_candidate(), issue)  # type: ignore[arg-type]

    assert result is None
    github.add_to_project.assert_not_awaited()


async def test_place_on_roadmap_adds_issue_and_logs(
    project_route: TargetConfig,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    candidate = make_candidate(
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        complexity=Complexity.M,
        target=project_route,
    )
    github = SimpleNamespace(add_to_project=AsyncMock(return_value="PVTI_1"))
    issue = FiledIssue(7, ISSUE_URL, "I_node7")

    with caplog.at_level(logging.INFO):
        result = await place_on_roadmap(github, candidate, issue)  # type: ignore[arg-type]

    assert result is True
    github.add_to_project.assert_awaited_once_with(project_route, issue, Complexity.M)
    assert issues_records(caplog, logging.INFO) == [
        f"added bug message_id=99 to the roadmap issue={ISSUE_URL}"
    ]
    assert_no_member_text(caplog)


async def test_place_on_roadmap_github_error_returns_false_and_warns(
    project_route: TargetConfig,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    candidate = make_candidate(
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        target=project_route,
    )
    github = SimpleNamespace(
        add_to_project=AsyncMock(side_effect=GitHubError("project-item", 200))
    )

    with caplog.at_level(logging.INFO):
        result = await place_on_roadmap(
            github, candidate, FiledIssue(7, ISSUE_URL, "I_node7")  # type: ignore[arg-type]
        )

    assert result is False
    assert issues_records(caplog, logging.WARNING) == [
        f"could not add bug message_id=99 to the roadmap issue={ISSUE_URL}: "
        "GitHubError stage=project-item status=200"
    ]
    assert not issues_records(caplog, logging.INFO)
    assert_no_member_text(caplog)


async def test_place_on_roadmap_other_error_returns_false_and_logs_type_only(
    project_route: TargetConfig,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    github = SimpleNamespace(
        add_to_project=AsyncMock(side_effect=RuntimeError("Secret exception words"))
    )

    with caplog.at_level(logging.INFO):
        result = await place_on_roadmap(
            github,  # type: ignore[arg-type]
            make_candidate(target=project_route),
            FiledIssue(7, ISSUE_URL, "I_node7"),
        )

    assert result is False
    assert issues_records(caplog, logging.WARNING) == [
        f"could not add bug message_id=99 to the roadmap issue={ISSUE_URL}: RuntimeError"
    ]
    assert not [text for text in record_texts(caplog) if "Secret exception words" in text]


async def test_place_on_roadmap_sets_track_after_adding(
    project_route: TargetConfig,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    candidate = make_candidate(
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        complexity=Complexity.M,
        target=project_route,
        track="A · Bugs",
    )
    calls = Mock()
    calls.add_to_project = AsyncMock(return_value="PVTI_1")
    calls.set_track = AsyncMock(return_value=None)
    github = SimpleNamespace(add_to_project=calls.add_to_project, set_track=calls.set_track)
    issue = FiledIssue(7, ISSUE_URL, "I_node7")

    with caplog.at_level(logging.INFO):
        result = await place_on_roadmap(github, candidate, issue)  # type: ignore[arg-type]

    assert result is True
    assert [call[0] for call in calls.mock_calls] == ["add_to_project", "set_track"]
    github.add_to_project.assert_awaited_once_with(project_route, issue, Complexity.M)
    github.set_track.assert_awaited_once_with(project_route, "PVTI_1", "A · Bugs")
    assert issues_records(caplog, logging.INFO) == [
        f"added bug message_id=99 to the roadmap issue={ISSUE_URL}"
    ]
    assert not issues_records(caplog, logging.WARNING)
    assert_no_member_text(caplog)


async def test_place_on_roadmap_without_track_skips_set_track(
    project_route: TargetConfig,
    make_candidate: CandidateFactory,
) -> None:
    github = SimpleNamespace(
        add_to_project=AsyncMock(return_value="PVTI_1"), set_track=AsyncMock()
    )

    result = await place_on_roadmap(
        github,  # type: ignore[arg-type]
        make_candidate(target=project_route),
        FiledIssue(7, ISSUE_URL, "I_node7"),
    )

    assert result is True
    github.set_track.assert_not_awaited()


@pytest.mark.parametrize(
    ("error", "suffix"),
    [
        (GitHubError("project-track", 200), "GitHubError stage=project-track status=200"),
        (RuntimeError("Secret exception words"), "RuntimeError"),
    ],
    ids=["github-error", "other-error"],
)
async def test_place_on_roadmap_track_failure_returns_false_and_warns(
    error: Exception,
    suffix: str,
    project_route: TargetConfig,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    candidate = make_candidate(
        title="Secret title words",
        answers=(("What happened?", "Secret body words"),),
        target=project_route,
        track="A · Bugs",
    )
    github = SimpleNamespace(
        add_to_project=AsyncMock(return_value="PVTI_1"),
        set_track=AsyncMock(side_effect=error),
    )

    with caplog.at_level(logging.INFO):
        result = await place_on_roadmap(
            github, candidate, FiledIssue(7, ISSUE_URL, "I_node7")  # type: ignore[arg-type]
        )

    assert result is False
    assert issues_records(caplog, logging.WARNING) == [
        f"could not add bug message_id=99 to the roadmap issue={ISSUE_URL}: {suffix}"
        " track='A · Bugs'"
    ]
    assert not issues_records(caplog, logging.INFO)
    assert not [text for text in record_texts(caplog) if "Secret exception words" in text]
    assert_no_member_text(caplog)


async def test_place_on_roadmap_add_failure_names_the_track_pick(
    project_route: TargetConfig,
    make_candidate: CandidateFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Any failed step leaves the pick unset, so the WARNING names it for the owner's hand fix.
    github = SimpleNamespace(
        add_to_project=AsyncMock(side_effect=GitHubError("project-item", 200)),
        set_track=AsyncMock(),
    )

    with caplog.at_level(logging.INFO):
        result = await place_on_roadmap(
            github,  # type: ignore[arg-type]
            make_candidate(target=project_route, track="A · Bugs"),
            FiledIssue(7, ISSUE_URL, "I_node7"),
        )

    assert result is False
    github.set_track.assert_not_awaited()
    assert issues_records(caplog, logging.WARNING) == [
        f"could not add bug message_id=99 to the roadmap issue={ISSUE_URL}: "
        "GitHubError stage=project-item status=200 track='A · Bugs'"
    ]
