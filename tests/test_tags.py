import pytest

from issue_bot.tags import IssueType, ParsedTag, parse_tag


def test_roadmap_feature_example() -> None:
    text = (
        "Display chore count next to Room tab name in parentheses "
        "when each Room tab is active #feature"
    )
    assert parse_tag(text) == ParsedTag(
        IssueType.FEATURE,
        "Display chore count next to Room tab name in parentheses when each Room tab is active",
    )


def test_roadmap_untagged_example() -> None:
    assert parse_tag("anyone around tonight?") is None


def test_roadmap_bug_example() -> None:
    parsed = parse_tag("Chore bars turn red on the due date instead of after it #bug")
    assert parsed == ParsedTag(
        IssueType.BUG, "Chore bars turn red on the due date instead of after it"
    )


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        ("#BUG crash on save", IssueType.BUG),
        ("#Feature dark mode", IssueType.FEATURE),
    ],
)
def test_case_insensitive(text: str, expected_type: IssueType) -> None:
    parsed = parse_tag(text)
    assert parsed is not None
    assert parsed.type is expected_type


@pytest.mark.parametrize(
    "text", ["#bug login button broken", "login #bug button broken"]
)
def test_tag_anywhere(text: str) -> None:
    assert parse_tag(text) == ParsedTag(IssueType.BUG, "login button broken")


def test_first_tag_wins_and_all_stripped() -> None:
    assert parse_tag("#feature dark mode #bug") == ParsedTag(
        IssueType.FEATURE, "dark mode"
    )


@pytest.mark.parametrize(
    "text",
    [
        "#bugfix for x",
        "#bug-report x",
        "foo#bug",
        "##bug x",
        "#chore something",
        "see https://x.com/#bug for it",
        "x/#bug y",
        "use `#bug` here",
        "",
    ],
)
def test_not_a_tag(text: str) -> None:
    assert parse_tag(text) is None


@pytest.mark.parametrize("text", ["#bug", "  #feature  ", "#bug.", "#feature !"])
def test_tag_only_returns_none(text: str) -> None:
    assert parse_tag(text) is None


@pytest.mark.parametrize(
    ("text", "expected_title"),
    [
        ("#bug: broken", "broken"),
        ("(#bug) x", "x"),
        ("[#feature] dark mode", "dark mode"),
        ("Why does it crash? #bug", "Why does it crash?"),
    ],
)
def test_title_cleanup(text: str, expected_title: str) -> None:
    parsed = parse_tag(text)
    assert parsed is not None
    assert parsed.title == expected_title


def test_multiline() -> None:
    assert parse_tag("line one\n#bug\nline two") == ParsedTag(
        IssueType.BUG, "line one line two"
    )
