import logging
from types import SimpleNamespace

import discord
import pytest

from issue_bot.config import Config
from issue_bot.handler import IssueCandidate, candidate_from_message, candidate_from_submission
from issue_bot.issue_type import IssueType
from issue_bot.tags import MalformedTag
from tests.conftest import MessageFactory


def test_tagged_message_becomes_candidate(config: Config, make_message: MessageFactory) -> None:
    candidate = candidate_from_message(make_message(), config)
    assert isinstance(candidate, IssueCandidate)
    assert candidate.type == IssueType.BUG
    assert candidate.title == "Fix it"
    assert candidate.body == ""
    assert candidate.author_id == 7
    assert candidate.author_name == "Alice"
    assert candidate.message_id == 99
    assert candidate.message_url == "https://discord.com/channels/111/555/99"
    assert candidate.target is config.target


def test_candidate_repr_hides_text(config: Config, make_message: MessageFactory) -> None:
    candidate = candidate_from_message(
        make_message(
            "!bug\nTitle: Secret title words\nBody: Secret body words", author_name="Alice"
        ),
        config,
    )
    assert candidate is not None
    text = repr(candidate)
    assert "Secret title words" not in text
    assert "Secret body words" not in text
    assert "!bug" not in text
    assert "Alice" not in text
    assert "message_id=99" in text


def test_other_channel_ignored(config: Config, make_message: MessageFactory) -> None:
    assert candidate_from_message(make_message(channel_id=556), config) is None


def test_thread_message_ignored(config: Config, make_message: MessageFactory) -> None:
    # 777 stands for a thread under the configured channel: its channel.id is the thread's.
    assert candidate_from_message(make_message("!bug\nTitle: x", channel_id=777), config) is None


def test_bot_author_ignored(config: Config, make_message: MessageFactory) -> None:
    assert candidate_from_message(make_message(author_bot=True), config) is None


def test_webhook_ignored(config: Config, make_message: MessageFactory) -> None:
    assert candidate_from_message(make_message(webhook_id=123), config) is None


def test_system_message_ignored(config: Config, make_message: MessageFactory) -> None:
    message = make_message(message_type=discord.MessageType.thread_created)
    assert candidate_from_message(message, config) is None


def test_reply_type_accepted(config: Config, make_message: MessageFactory) -> None:
    message = make_message(message_type=discord.MessageType.reply)
    assert isinstance(candidate_from_message(message, config), IssueCandidate)


def test_untagged_ignored(config: Config, make_message: MessageFactory) -> None:
    assert candidate_from_message(make_message("anyone around tonight?"), config) is None


@pytest.mark.parametrize(
    "content",
    ["Secret words without fields !feature", "!feature\nTitle: ?!?\nBody: Secret words"],
)
def test_malformed_returned_and_logged_without_text(
    config: Config,
    make_message: MessageFactory,
    caplog: pytest.LogCaptureFixture,
    content: str,
) -> None:
    message = make_message(content)
    with caplog.at_level(logging.INFO, logger="issue_bot"):
        assert candidate_from_message(message, config) == MalformedTag(IssueType.FEATURE)
    texts = [record.getMessage() for record in caplog.records]
    assert any(
        text.startswith("malformed ")
        and "feature" in text
        and "99" in text
        and message.jump_url in text
        and "no usable Title: line" in text
        for text in texts
    )
    assert all("Secret words" not in text for text in texts)


def test_candidate_from_submission_fields(config: Config) -> None:
    user = SimpleNamespace(id=7, display_name="Alice")
    message = SimpleNamespace(id=99, jump_url="https://discord.com/channels/111/555/99")
    candidate = candidate_from_submission(
        IssueType.BUG, "Fix it", "Steps", user, message, config.target
    )
    assert candidate.type is IssueType.BUG
    assert candidate.title == "Fix it"
    assert candidate.body == "Steps"
    assert candidate.author_id == 7
    assert candidate.author_name == "Alice"
    assert candidate.message_id == 99
    assert candidate.message_url == message.jump_url
    assert candidate.target is config.target


def test_submission_candidate_repr_hides_text(config: Config) -> None:
    user = SimpleNamespace(id=7, display_name="Alice")
    message = SimpleNamespace(id=99, jump_url="https://discord.com/channels/111/555/99")
    candidate = candidate_from_submission(
        IssueType.BUG, "Secret title words", "Secret body words", user, message, config.target
    )
    text = repr(candidate)
    assert "Secret title words" not in text
    assert "Secret body words" not in text
    assert "Alice" not in text
