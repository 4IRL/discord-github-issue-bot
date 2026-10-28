"""The documented S/M/L/XL complexity rules (see docs/COMPLEXITY.md); pure, and never logs."""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType

from issue_bot.issue_type import IssueType


class Complexity(StrEnum):
    """A report's complexity band, smallest first (the order the preview's buttons use)."""

    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


STARTING_BAND: Mapping[IssueType, Complexity] = MappingProxyType(
    {IssueType.BUG: Complexity.S, IssueType.FEATURE: Complexity.M}
)
RAISE_ONE_AT = 800  # total answer characters that raise the band one step
RAISE_TWO_AT = 2000  # total answer characters that raise the band two steps


def rate(issue_type: IssueType, answers: Sequence[tuple[str, str]]) -> Complexity:
    """Rate a report from its type and the total stripped length of its answers, capped at XL."""
    length = sum(len(answer.strip()) for _, answer in answers)
    steps = (length >= RAISE_ONE_AT) + (length >= RAISE_TWO_AT)
    bands = list(Complexity)
    position = bands.index(STARTING_BAND[issue_type]) + steps
    return bands[min(position, len(bands) - 1)]


def complexity_label(band: Complexity) -> str:
    """Return the GitHub label a band is filed with."""
    return f"complexity:{band}"
