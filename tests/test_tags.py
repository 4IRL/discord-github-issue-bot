import pytest

from issue_bot.tags import IssueType, MalformedTag, ParsedTag, parse_tag


def test_roadmap_feature_example() -> None:
    text = (
        "!feature\n"
        "Title: Sharing/Inviting to UTubs\n"
        "Body: allow easy sharing/inviting to UTubs for members outside the UTub"
    )
    assert parse_tag(text) == ParsedTag(
        IssueType.FEATURE,
        "Sharing/Inviting to UTubs",
        "allow easy sharing/inviting to UTubs for members outside the UTub",
    )


def test_roadmap_untagged_example() -> None:
    assert parse_tag("anyone around tonight?") is None


def test_roadmap_bug_example() -> None:
    text = (
        "!bug\n"
        "Title: Chore bars turn red on the due date\n"
        "Body: They should turn red only after the due date."
    )
    assert parse_tag(text) == ParsedTag(
        IssueType.BUG,
        "Chore bars turn red on the due date",
        "They should turn red only after the due date.",
    )


def test_body_optional() -> None:
    assert parse_tag("!bug\nTitle: Crash on save") == ParsedTag(IssueType.BUG, "Crash on save")


def test_multiline_body_keeps_line_breaks() -> None:
    text = "!bug\nTitle: Crash\nBody: Steps:\n\n1. open\n2. save  \n\n"
    parsed = parse_tag(text)
    assert isinstance(parsed, ParsedTag)
    assert parsed.body == "Steps:\n\n1. open\n2. save"


def test_body_starting_on_next_line() -> None:
    parsed = parse_tag("!bug\nTitle: Crash\nBody:\n  indented detail")
    assert isinstance(parsed, ParsedTag)
    assert parsed.body == "  indented detail"


def test_body_before_title() -> None:
    assert parse_tag("Body: details\nmore\nTitle: Crash !bug") == ParsedTag(
        IssueType.BUG, "Crash", "details\nmore"
    )


def test_title_is_one_line_and_stray_lines_dropped() -> None:
    parsed = parse_tag("hey all\n!bug\nTitle: Crash\nnot part of anything")
    assert parsed == ParsedTag(IssueType.BUG, "Crash")


def test_repeated_label_inside_body_is_text() -> None:
    parsed = parse_tag("!bug\nTitle: Crash\nBody: one\nTitle: two\nBody: three")
    assert parsed == ParsedTag(IssueType.BUG, "Crash", "one\nTitle: two\nBody: three")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("!bug\nTitle:\nTitle: real", ParsedTag(IssueType.BUG, "real")),
        ("!bug\nTitle:  \nBody: one\nTitle: real", ParsedTag(IssueType.BUG, "real", "one")),
        ("!bug\nTitle: x\nBody:\n\nBody: real", ParsedTag(IssueType.BUG, "x", "real")),
        ("!bug\nTitle: -\nTitle: real", ParsedTag(IssueType.BUG, "real")),
        # A late Title: that fills a blank one ends the body.
        ("!bug\nTitle:\nBody: one\nTitle: real\nmore", ParsedTag(IssueType.BUG, "real", "one")),
    ],
)
def test_blank_label_yields_to_later_one(text: str, expected: ParsedTag) -> None:
    assert parse_tag(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("!bug\nTitle: x\nTitle: y", ParsedTag(IssueType.BUG, "x")),
        ("!bug\nTitle: x\nBody:\ntext\nBody: y", ParsedTag(IssueType.BUG, "x", "text\nBody: y")),
        # Outside the Body, a repeated filled label is ignored.
        (
            "!bug\nTitle:\nBody: one\nTitle: real\nBody: two",
            ParsedTag(IssueType.BUG, "real", "one"),
        ),
    ],
)
def test_filled_label_is_final(text: str, expected: ParsedTag) -> None:
    assert parse_tag(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "!feature\ntitle: Dark mode\nBODY: please",
        "!feature\n**Title:** Dark mode\n**Body:** please",
        "!feature\n  Title :Dark mode\nBody:please",
        "Title: Dark mode !feature\nBody: please",
        "[!feature] Title: Dark mode\nBody: please",
        "!feature Title: Dark mode\nBody: please !feature",
    ],
)
def test_label_and_tag_variants(text: str) -> None:
    assert parse_tag(text) == ParsedTag(IssueType.FEATURE, "Dark mode", "please")


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        ("!BUG\nTitle: crash on save", IssueType.BUG),
        ("!Feature\nTitle: dark mode", IssueType.FEATURE),
    ],
)
def test_case_insensitive(text: str, expected_type: IssueType) -> None:
    parsed = parse_tag(text)
    assert isinstance(parsed, ParsedTag)
    assert parsed.type is expected_type


def test_first_tag_wins_and_all_stripped() -> None:
    assert parse_tag("!feature\nTitle: dark mode !bug") == ParsedTag(
        IssueType.FEATURE, "dark mode"
    )


@pytest.mark.parametrize(
    "text",
    [
        "!bugfix for x",
        "!bug-report x",
        "foo!bug",
        "!!bug x",
        "!chore something",
        "#bug\nTitle: old channel-link syntax",
        "#feature x",
        "see https://x.com/!bug for it",
        "x/!bug y",
        "use `!bug` here",
        "Title: no tag here",
        "",
    ],
)
def test_not_a_tag(text: str) -> None:
    assert parse_tag(text) is None


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        ("!bug", IssueType.BUG),
        ("Display chore count next to Room tab name !feature", IssueType.FEATURE),
        ("!bug\nTitle:\nBody: details", IssueType.BUG),
        ("!bug\nTitle: .!\nBody: details", IssueType.BUG),
        ("!feature\nBody: only a body", IssueType.FEATURE),
        ("!feature\nSubject: wrong label", IssueType.FEATURE),
    ],
)
def test_missing_or_empty_title_is_malformed(text: str, expected_type: IssueType) -> None:
    assert parse_tag(text) == MalformedTag(expected_type)


@pytest.mark.parametrize(
    ("text", "expected_title"),
    [
        ("!bug\nTitle: broken.", "broken"),
        ("!bug\nTitle: (!bug) x", "x"),
        ("!bug\nTitle:   spaced    out   ", "spaced out"),
        ("!bug\nTitle: Why does it crash?", "Why does it crash?"),
    ],
)
def test_title_cleanup(text: str, expected_title: str) -> None:
    parsed = parse_tag(text)
    assert isinstance(parsed, ParsedTag)
    assert parsed.title == expected_title


def test_body_brackets_kept_unless_they_held_a_tag() -> None:
    parsed = parse_tag("!bug\nTitle: x\nBody: call save() fails [!bug]")
    assert isinstance(parsed, ParsedTag)
    assert parsed.body == "call save() fails"
