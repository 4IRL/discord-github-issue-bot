import pytest

from issue_bot.complexity import Complexity, complexity_label, rate
from issue_bot.issue_type import IssueType


def test_empty_answers_rate_the_starting_band() -> None:
    assert rate(IssueType.BUG, ()) is Complexity.S
    assert rate(IssueType.FEATURE, ()) is Complexity.M


@pytest.mark.parametrize(
    ("issue_type", "length", "expected"),
    [
        (IssueType.BUG, 799, Complexity.S),
        (IssueType.BUG, 800, Complexity.M),
        (IssueType.BUG, 1999, Complexity.M),
        (IssueType.BUG, 2000, Complexity.L),
        (IssueType.FEATURE, 799, Complexity.M),
        (IssueType.FEATURE, 800, Complexity.L),
        (IssueType.FEATURE, 2000, Complexity.XL),
        (IssueType.FEATURE, 5000, Complexity.XL),
    ],
)
def test_rate_boundaries(issue_type: IssueType, length: int, expected: Complexity) -> None:
    assert rate(issue_type, (("Q", "x" * length),)) is expected


def test_length_is_summed_across_answers() -> None:
    assert rate(IssueType.BUG, (("Q1", "x" * 400), ("Q2", "x" * 400))) is Complexity.M


def test_blank_and_whitespace_answers_add_nothing() -> None:
    assert rate(IssueType.BUG, (("Device", ""), ("Q", "x" * 799))) is Complexity.S
    assert rate(IssueType.BUG, (("Q", " " * 900),)) is Complexity.S
    assert rate(IssueType.BUG, (("Q", "x" * 798 + " " * 4),)) is Complexity.S


def test_complexity_label_and_band_order() -> None:
    assert complexity_label(Complexity.XL) == "complexity:XL"
    assert [str(band) for band in Complexity] == ["S", "M", "L", "XL"]
