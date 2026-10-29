import logging
from types import SimpleNamespace

import discord
import pytest

from issue_bot.complexity import Complexity
from issue_bot.github import FiledIssue
from issue_bot.threads import (
    FILING_ERROR_REPLY,
    THREAD_NAME_LIMIT,
    filed_reply,
    open_thread,
    thread_name,
)
from tests.conftest import ISSUE_URL, MessageFactory


def already_created_error() -> discord.HTTPException:
    return discord.HTTPException(
        SimpleNamespace(status=400, reason="Bad Request"),
        {"code": 160004, "message": "A thread has already been created for this message"},
    )


def thread_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == "issue_bot.threads"]


def test_thread_name_short_title_unchanged() -> None:
    assert thread_name("Fix it") == "Fix it"


def test_thread_name_exactly_limit_unchanged() -> None:
    title = "z" * 100
    assert thread_name(title) == title


def test_thread_name_truncated_to_limit() -> None:
    truncated = thread_name("x" * 150)
    assert len(truncated) == THREAD_NAME_LIMIT
    assert truncated.endswith("…")
    assert thread_name("a" * 98 + " bcd") == "a" * 98 + "…"


async def test_open_thread_creates_once(make_message: MessageFactory) -> None:
    message = make_message()
    result = await open_thread(message, "Fix it")
    assert result is message.create_thread.return_value
    message.create_thread.assert_awaited_once_with(name="Fix it")


async def test_open_thread_reuses_existing_thread(make_message: MessageFactory) -> None:
    existing = SimpleNamespace(id=5)
    message = make_message(thread=existing)
    result = await open_thread(message, "Fix it")
    assert result is existing
    message.create_thread.assert_not_awaited()


async def test_open_thread_fetches_on_already_created(
    make_message: MessageFactory, caplog: pytest.LogCaptureFixture
) -> None:
    message = make_message()
    message.create_thread.side_effect = already_created_error()
    with caplog.at_level(logging.INFO, logger="issue_bot"):
        result = await open_thread(message, "Fix it")
    assert result is message.fetch_thread.return_value
    message.fetch_thread.assert_awaited_once_with()
    assert not [record for record in thread_records(caplog) if record.levelno >= logging.WARNING]


async def test_open_thread_fetch_failure_returns_none(
    make_message: MessageFactory, caplog: pytest.LogCaptureFixture
) -> None:
    message = make_message()
    message.create_thread.side_effect = already_created_error()
    message.fetch_thread.side_effect = discord.NotFound(
        SimpleNamespace(status=404, reason="Not Found"),
        {"code": 10003, "message": "Secret error words"},
    )
    with caplog.at_level(logging.INFO, logger="issue_bot"):
        result = await open_thread(message, "Fix it")
    assert result is None
    errors = [
        record
        for record in thread_records(caplog)
        if record.levelno == logging.ERROR
        and all(part in record.getMessage() for part in ("NotFound", "404", "10003", "99"))
    ]
    assert len(errors) == 1
    assert not [record for record in caplog.records if "Secret error words" in record.getMessage()]


async def test_open_thread_logs_forbidden_without_text(
    make_message: MessageFactory, caplog: pytest.LogCaptureFixture
) -> None:
    message = make_message()
    message.create_thread.side_effect = discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"),
        {"code": 50013, "message": "Secret error words"},
    )
    with caplog.at_level(logging.INFO, logger="issue_bot"):
        result = await open_thread(message, "Secret title words")
    assert result is None
    errors = [
        record
        for record in thread_records(caplog)
        if record.levelno == logging.ERROR
        and all(part in record.getMessage() for part in ("Forbidden", "403", "50013", "99"))
    ]
    assert len(errors) == 1
    for record in caplog.records:
        text = record.getMessage()
        assert "Secret error words" not in text
        assert "Secret title words" not in text
    message.fetch_thread.assert_not_awaited()


def test_filing_error_reply_is_fixed_text() -> None:
    assert FILING_ERROR_REPLY == (
        "Sorry, I couldn't file this as a GitHub issue. Check the repo before reporting it "
        "again; to retry, run the command again."
    )


def test_filed_reply_has_number_title_and_url() -> None:
    assert filed_reply(FiledIssue(7, ISSUE_URL, "I_node7"), "Fix *it*", Complexity.L) == (
        f"Filed as GitHub issue #7 (complexity L): Fix \\*it\\*\n{ISSUE_URL}"
    )
