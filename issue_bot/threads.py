"""Open the public thread on a tagged message, and the helpers that name and fill it.

Thread names hold member text (the issue title), so they are never logged; logs carry
message and thread ids, and a caught Discord API error's type, HTTP status and code only.
"""

import logging

import discord

from issue_bot.tags import IssueType

logger = logging.getLogger(__name__)

THREAD_NAME_LIMIT = 100  # Discord's maximum thread-name length.
THREAD_ALREADY_CREATED = 160004  # Discord error code: the message already has a thread.
# Fixed text: it carries no member text and no GitHub response text.
FILING_ERROR_REPLY = "Sorry, I couldn't file this as a GitHub issue. Check the repo before reposting; to retry, post a new message (edits are ignored)."


def thread_name(title: str) -> str:
    """Return the title as a thread name, truncated with an ellipsis to Discord's limit."""
    if len(title) <= THREAD_NAME_LIMIT:
        return title
    return title[: THREAD_NAME_LIMIT - 1].rstrip() + "…"


def format_hint(issue_type: IssueType) -> str:
    """Return the reply that shows a malformed tag's author the expected message format."""
    return f"No issue was filed: this message has no usable `Title:` line. Post a new message (edits are ignored) in this form:\n```\n!{issue_type}\nTitle: <one-line summary>\nBody: <optional details>\n```"


async def open_thread(message: discord.Message, name: str) -> discord.Thread | None:
    """Return the message's public thread, creating it when there is none.

    An existing thread is reused, whether cached (``message.thread``) or reported by Discord
    as already created. A Discord API failure is logged without its text, returning ``None``.
    """
    if message.thread is not None:
        return message.thread
    try:
        return await message.create_thread(name=name)
    except discord.HTTPException as exc:
        if exc.code != THREAD_ALREADY_CREATED:
            logger.error(
                "could not open thread for message_id=%s: %s status=%s code=%s",
                message.id,
                type(exc).__name__,
                exc.status,
                exc.code,
            )
            return None
    try:
        return await message.fetch_thread()
    except discord.HTTPException as fetch_exc:
        logger.error(
            "could not open thread for message_id=%s: %s status=%s code=%s",
            message.id,
            type(fetch_exc).__name__,
            fetch_exc.status,
            fetch_exc.code,
        )
        return None
