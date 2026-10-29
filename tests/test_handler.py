from types import SimpleNamespace

from issue_bot.complexity import Complexity
from issue_bot.config import TargetConfig
from issue_bot.handler import candidate_from_submission
from issue_bot.issue_type import IssueType


def test_candidate_from_submission_fields(route: TargetConfig) -> None:
    user = SimpleNamespace(id=7, display_name="Alice")
    message = SimpleNamespace(id=99, jump_url="https://discord.com/channels/111/555/99")
    candidate = candidate_from_submission(
        IssueType.BUG, "Fix it", (("Q", "A"),), Complexity.M, user, message, route
    )
    assert candidate.type is IssueType.BUG
    assert candidate.title == "Fix it"
    assert candidate.answers == (("Q", "A"),)
    assert candidate.complexity is Complexity.M
    assert candidate.author_id == 7
    assert candidate.author_name == "Alice"
    assert candidate.message_id == 99
    assert candidate.message_url == message.jump_url
    assert candidate.target is route


def test_submission_candidate_repr_hides_text(route: TargetConfig) -> None:
    user = SimpleNamespace(id=7, display_name="Alice")
    message = SimpleNamespace(id=99, jump_url="https://discord.com/channels/111/555/99")
    candidate = candidate_from_submission(
        IssueType.BUG,
        "Secret title words",
        (("Q", "Secret body words"),),
        Complexity.M,
        user,
        message,
        route,
    )
    text = repr(candidate)
    assert "Secret title words" not in text
    assert "Secret body words" not in text
    assert "Alice" not in text


def test_candidate_from_submission_track_defaults_none_and_shows_in_repr(
    route: TargetConfig,
) -> None:
    user = SimpleNamespace(id=7, display_name="Alice")
    message = SimpleNamespace(id=99, jump_url="https://discord.com/channels/111/555/99")
    plain = candidate_from_submission(
        IssueType.BUG, "Fix it", (("Q", "A"),), Complexity.M, user, message, route
    )
    assert plain.track is None
    picked = candidate_from_submission(
        IssueType.BUG, "Fix it", (("Q", "A"),), Complexity.M, user, message, route, "A · Bugs"
    )
    assert picked.track == "A · Bugs"
    # A Project option name is not member text, so it stays in repr.
    assert "track='A · Bugs'" in repr(picked)
