import pytest

from issue_bot.config import Config
from issue_bot.handler import IssueCandidate, candidate_from_message
from issue_bot.issues import ISSUE_TITLE_LIMIT, issue_body, issue_labels, issue_title
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
        "Steps here\n\n---\nReported by `Alice` in Discord: https://discord.com/channels/111/555/99"
    )


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
    assert issue_body(candidate).startswith("_No description given._\n\n---\n")


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
