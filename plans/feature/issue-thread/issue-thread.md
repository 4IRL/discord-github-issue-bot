# Thread per tagged message (F2)

## Summary
For each tagged message in the intake channel, the bot opens a public thread on that message,
named from the issue title, so later features (F3's questions, F7's issue link) have
somewhere to talk. A tagged message that F1 drops as malformed (no usable `Title:` line) also
gets a thread, with a reply showing the expected `!tag` / `Title:` / `Body:` format, and
produces no candidate. Source contract: `plans/META-PLAN.md` § "F2 — Thread per tagged
message".

## Research Findings
Research was done inline: the codebase is one small layer (`issue_bot/` + `tests/`).
- `IssueBot.on_message` (`issue_bot/bot.py`) calls `candidate_from_message(message, config)`
  and awaits `self.on_candidate(message, candidate)` when it is not `None`. The default hook
  `log_candidate` logs `"captured %s message_id=%s (%s)"` on logger `issue_bot.bot`; F1's kept
  contract makes `on_candidate` the single seam for candidates.
- `candidate_from_message` (`issue_bot/handler.py`) returns `None` for a `MalformedTag` after
  logging `"ignored %s message_id=%s (%s): no usable Title: line"`. `bot.on_message` is its only
  caller; `tests/test_handler.py::test_malformed_ignored_and_logged_without_text` and
  `tests/test_bot.py::test_on_message_ignores_malformed` cover the malformed path. The handler
  test matches the log on `"feature"`, `"99"`, the jump URL and `"no usable Title: line"`, not
  on `"ignored"`; Step 2 adds a `text.startswith("malformed ")` check so the test pins the
  reworded log line.
- discord.py is pinned at 2.7.1. `Message.create_thread(*, name, auto_archive_duration=MISSING,
  slowmode_delay=None, reason=None) -> Thread`: omitting `auto_archive_duration` uses the
  channel's default. `Message.thread` returns the cached public thread started from the
  message (archived threads are not cached). `async Message.fetch_thread(self) -> Thread`
  (added in 2.4) retrieves the public thread attached to the message; it raises `NotFound`
  when there is none, `Forbidden` or another `HTTPException` on failure (it also raises
  `ValueError` when the message has no guild and `InvalidData` on an unexpected channel;
  neither is an `HTTPException`, so they reach `on_error`, which logs type and message id
  only).
  **Documentation-derived, not exercised live** until the owner's duplicate-path manual check
  runs: Discord rejects a second thread on one message with `HTTPException.code == 160004`,
  and `fetch_thread` finds the existing thread by the message's id (a thread started from a
  message has that message's id). `discord.Forbidden` and `discord.NotFound` subclass
  `discord.HTTPException`; each of them, and `HTTPException` itself, is built in a test as
  `cls(SimpleNamespace(status=<int>, reason="<str>"), {"code": <int>, "message": "..."})`,
  which sets `.status` and `.code`.
- Tests use `make_message` (`tests/conftest.py`), a `SimpleNamespace` stand-in with `content`,
  `channel.id`, `author`, `webhook_id`, `type`, `id`, `jump_url`; it has no `thread`,
  `create_thread` or `fetch_thread` yet. pytest-asyncio runs in `asyncio_mode = "auto"`.
- The thread name is member text (the title), so it is never logged; logs carry the issue
  type, message id, message URL and thread id only, and a caught Discord API error is logged
  by exception type, HTTP status and Discord error code. The CLAUDE.md rule (Standing
  invariant 2) names only the issue type, message id and message URL, so Step 1's first box
  widens its wording to cover thread ids and caught API errors, in the same commit as the
  first code that logs a thread id or an error's type, status and code.

## Decisions (Open risks from META-PLAN)
- **(a) Permissions.** The bot needs **Create Public Threads** and **Send Messages in Threads**
  on the intake channel, on top of F1's View Channel and Read Message History. A
  `discord.Forbidden` (or any other `HTTPException`) from `create_thread`, from the 160004
  recovery fetch (`message.fetch_thread()`) or from the format hint's `thread.send` is caught
  and logged at ERROR by exception type, HTTP status, Discord error code and message id (plus
  the thread id for `thread.send`), never the error text; the hook then returns without a
  thread or without the hint. README's Discord setup step 3 names both permissions.
- **(b) Auto-archive.** `create_thread` is called without `auto_archive_duration`, so the
  channel's default applies.
- **Duplicate guard.** If `message.thread` is set, that thread is reused and no
  `create_thread` call is made. If Discord answers 160004 (a thread exists but is not cached,
  e.g. a second instance sharing the token, F8 risk (b)), the existing thread is fetched with
  `await message.fetch_thread()` and reused. The 160004 code and the fetch-by-message-id
  behaviour are documentation-derived and not exercised live until the owner's duplicate-path
  manual check runs.
- **Thread name.** The title is already whitespace-collapsed by `parse_tag`. A title of at most
  100 characters is used as is; a longer one becomes `title[:99].rstrip() + "…"` (≤ 100
  characters). The malformed path has no title, so its thread is named `Format help: !<type>`,
  which holds no member text. Lengths are counted in Python code points; whether Discord counts
  non-BMP characters (emoji) the same way is unverified, and a rejection (e.g. 400 / code
  50035) is caught and logged by `open_thread`, leaving the candidate with no thread (accepted
  risk; revisit if that ERROR line appears).
- **Shape of the extension (F1 contract).** `candidate_from_message` returns
  `IssueCandidate | MalformedTag | None`; `IssueBot` gains an `on_malformed(message, malformed)`
  hook beside `on_candidate`. Candidates still have one dispatch path (`on_candidate`).
  Later hooks (F5's filing, F7's link) that replace or wrap `open_issue_thread` get the thread
  by calling `open_thread(message, thread_name(candidate.title))` again; its duplicate guard
  returns the existing thread instead of creating a second one.

## Steps

### 1. Thread helpers module (TDD) - COMPLETE (2026-10-18)
Widen the CLAUDE.md logging rule, then add `issue_bot/threads.py` with pure name/hint helpers and the thread opener with its duplicate guard. Both new files (`issue_bot/threads.py`, `tests/test_threads.py`) are untracked until the step's commit, so name them to the review subagents explicitly (`git diff --name-only` omits them).

**To-do:**
- [x] In the project `CLAUDE.md` § Project rules, replace the start of the logging bullet,
  currently "**Logs never contain members' message text or names.** Log the issue type,
  message id and message URL only; message content stays in Discord and the filed issue.",
  with "**Logs never contain members' message text or names.** Log the issue type, ids
  (message, thread) and message URL only; a caught Discord API error is logged by exception
  type, HTTP status and Discord error code, never its text; message content stays in Discord
  and the filed issue." Keep the rest of the bullet ("Exceptions escaping event handlers and
  hooks are logged by type and event name only. Never run the `discord` loggers at DEBUG: ...")
  unchanged. This box comes first so the rule is widened in the same commit as the first code
  that logs a thread id or an error's type, status and code. After the edit, run
  `grep -n 'ids (message, thread) and message URL only' CLAUDE.md` and
  `grep -n 'Never run the .discord. loggers at DEBUG' CLAUDE.md` and confirm each prints one
  line, and run `grep -n 'message id and message URL only' CLAUDE.md || true` and confirm it
  prints nothing.
- [x] Extend `make_message` in `tests/conftest.py` with keyword args `thread: object | None = None`
  and `created_thread_id: int = 1234`. The returned namespace gains
  `thread=thread`, `create_thread=AsyncMock(return_value=SimpleNamespace(id=created_thread_id,
  send=AsyncMock()))` and `fetch_thread=AsyncMock(return_value=SimpleNamespace(id=message_id,
  send=AsyncMock()))` (no `guild` attribute: nothing in `issue_bot/` or the tests reads
  `message.guild`). Import `AsyncMock` from `unittest.mock`. Run `.venv/bin/pytest` and
  confirm the whole suite still passes.
- [x] **Red:** create `tests/test_threads.py` with:
  - Imports, in the stdlib / third-party / project grouping of `tests/test_handler.py`:
    `import logging`, `from types import SimpleNamespace`; `import discord`, `import pytest`;
    `from issue_bot.tags import IssueType`, `from issue_bot.threads import THREAD_NAME_LIMIT,
    format_hint, open_thread, thread_name`, `from tests.conftest import MessageFactory`.
  - `test_thread_name_short_title_unchanged`: `thread_name("Fix it") == "Fix it"`.
  - `test_thread_name_exactly_limit_unchanged`: a 100-character title is returned unchanged.
  - `test_thread_name_truncated_to_limit`: for `"x" * 150`, the result has length
    `THREAD_NAME_LIMIT` (100) and ends with `"…"`; for `"a" * 98 + " bcd"` the trailing space
    before the ellipsis is stripped (`"a" * 98 + "…"`).
  - `test_format_hint_names_tag_and_fields`: `format_hint(IssueType.BUG)` equals exactly
    the string below, and `format_hint(IssueType.FEATURE)` contains `"!feature"`:

    ````python
    "No issue was filed: this message has no usable `Title:` line. Post a new message (edits are ignored) in this form:\n```\n!bug\nTitle: <one-line summary>\nBody: <optional details>\n```"
    ````
  - `test_open_thread_creates_once`: `await open_thread(message, "Fix it")` returns the mocked
    created thread; `message.create_thread.assert_awaited_once_with(name="Fix it")` (no
    `auto_archive_duration` kwarg).
  - `test_open_thread_reuses_existing_thread`: with `make_message(thread=existing)`, the result
    is `existing` and `create_thread` is not awaited.
  - `test_open_thread_fetches_on_already_created` (takes `caplog`): `create_thread.side_effect =
    discord.HTTPException(SimpleNamespace(status=400, reason="Bad Request"), {"code": 160004,
    "message": "A thread has already been created for this message"})`; under
    `caplog.at_level(logging.INFO, logger="issue_bot")`, the result is the
    `message.fetch_thread` return value, `message.fetch_thread.assert_awaited_once_with()`, and
    no record on logger `issue_bot.threads` has `levelno >= logging.WARNING`.
  - `test_open_thread_fetch_failure_returns_none` (takes `caplog`): `create_thread.side_effect` is the 160004
    `HTTPException` above and `message.fetch_thread.side_effect = discord.NotFound(
    SimpleNamespace(status=404, reason="Not Found"), {"code": 10003, "message": "Secret error
    words"})`; the result is `None`, exactly one ERROR record on logger `issue_bot.threads`
    contains `"NotFound"`, `"404"`, `"10003"` and `"99"`, and no record contains
    `"Secret error words"`.
  - `test_open_thread_logs_forbidden_without_text` (takes `caplog`): `side_effect = discord.Forbidden(
    SimpleNamespace(status=403, reason="Forbidden"), {"code": 50013, "message": "Secret error
    words"})`, title `"Secret title words"`; the result is `None`, exactly one ERROR record on
    logger `issue_bot.threads` contains `"Forbidden"`, `"403"`, `"50013"` and `"99"`, no
    record contains `"Secret error words"` or `"Secret title words"`, and
    `message.fetch_thread.assert_not_awaited()`.
  Run `.venv/bin/pytest tests/test_threads.py` and confirm the failures are `ImportError`/
  `ModuleNotFoundError` for `issue_bot.threads`.
- [x] **Green:** create `issue_bot/threads.py` (module docstring, `logger =
  logging.getLogger(__name__)`) with:
  - `THREAD_NAME_LIMIT = 100` (Discord's thread-name limit) and `THREAD_ALREADY_CREATED = 160004`.
  - `def thread_name(title: str) -> str` per the Thread name decision.
  - `def format_hint(issue_type: IssueType) -> str` returning exactly:

    ````python
    return f"No issue was filed: this message has no usable `Title:` line. Post a new message (edits are ignored) in this form:\n```\n!{issue_type}\nTitle: <one-line summary>\nBody: <optional details>\n```"
    ````

    (`f"!{IssueType.BUG}"` renders `!bug`, since `IssueType` is a `StrEnum`.)
  - `async def open_thread(message: discord.Message, name: str) -> discord.Thread | None`:
    return `message.thread` when it is not `None`; otherwise `return await
    message.create_thread(name=name)`; on `discord.HTTPException as exc` with
    `exc.code != THREAD_ALREADY_CREATED` log
    `logger.error("could not open thread for message_id=%s: %s status=%s code=%s",
    message.id, type(exc).__name__, exc.status, exc.code)` and return `None`. When
    `exc.code == THREAD_ALREADY_CREATED`, `return await message.fetch_thread()` inside its own
    `try/except discord.HTTPException as fetch_exc`, which logs the same ERROR line shape with
    `message.id, type(fetch_exc).__name__, fetch_exc.status, fetch_exc.code` (never the error
    text) and returns `None`.
  Run `.venv/bin/pytest tests/test_threads.py` and confirm it passes.
- [x] **Refactor:** check that no log call in `issue_bot/threads.py` passes `name`, the title,
  `exc.text`, `fetch_exc.text`, `str(exc)` or `str(fetch_exc)`. Run `.venv/bin/pytest` (whole
  suite green).

### 2. Malformed messages reach the bot (TDD) - COMPLETE (2026-10-18)
`candidate_from_message` returns the `MalformedTag` instead of `None`, so `IssueBot` can reply.

**To-do:**
- [x] **Red:** in `tests/test_handler.py::test_malformed_ignored_and_logged_without_text`, change
  `assert candidate_from_message(message, config) is None` to
  `assert candidate_from_message(message, config) == MalformedTag(IssueType.FEATURE)` (import
  `MalformedTag` from `issue_bot.tags`), and rename the test
  `test_malformed_returned_and_logged_without_text`. Add `text.startswith("malformed ")` to its
  log predicate (beside `"feature"`, `"99"`, the jump URL and `"no usable Title: line"`), so
  the test pins the reworded log line below; its no-text assertion stays unchanged. Run
  `.venv/bin/pytest tests/test_handler.py` and confirm it fails (the return is `None`, not the
  `MalformedTag`; the log line still starts with `ignored `).
- [x] **Green:** in `issue_bot/handler.py::candidate_from_message`, change the return annotation
  to `IssueCandidate | MalformedTag | None`, return `parsed` instead of `None` in the
  `MalformedTag` branch, reword its log line from `"ignored %s message_id=%s (%s): no usable
  Title: line"` to `"malformed %s message_id=%s (%s): no usable Title: line"` (same
  arguments; the message is no longer ignored), and update the docstring:
  "Return a candidate for a new, human, tagged message in the intake channel, the
  ``MalformedTag`` for a tagged one without a usable title, else ``None``." In
  `issue_bot/bot.py::IssueBot.on_message`, keep behaviour unchanged for now with
  `result = candidate_from_message(message, self.config)` then
  `if isinstance(result, IssueCandidate): await self.on_candidate(message, result)`. Run
  `.venv/bin/pytest` and confirm the whole suite passes (`test_on_message_ignores_malformed`
  must still pass).

### 3. Default hooks open the thread and reply with the format hint (TDD) - COMPLETE (2026-10-18)
Wire the thread helpers into `IssueBot` as the default `on_candidate` and a new `on_malformed` hook.

**To-do:**
- [x] **Red:** in `tests/test_bot.py` add:
  - Imports: `import discord` placed before `import pytest`; extend
    `from issue_bot.tags import IssueType` to `from issue_bot.tags import IssueType, MalformedTag`;
    add `from issue_bot.threads import format_hint` after the `issue_bot.tags` import (three
    groups stdlib / third-party / project, alphabetized). `logging`, `SimpleNamespace` and
    `AsyncMock` are already imported; the helpers `bot_records(caplog)` and
    `record_texts(caplog)` already exist in the file.
  - `test_default_hook_opens_one_thread_named_from_title`: `IssueBot(config)`,
    `make_message("!bug\nTitle: Fix it")`, `await bot.on_message(message)`;
    `message.create_thread.assert_awaited_once_with(name="Fix it")`.
  - `test_default_hook_truncates_long_title`: title `"y" * 150`; the awaited `name` kwarg has
    length 100.
  - `test_default_hook_skips_message_with_thread`: `existing = SimpleNamespace(id=5)`,
    `make_message(thread=existing)`, `IssueBot(config)`, `await bot.on_message(message)` under
    `caplog.at_level(logging.INFO)`; `create_thread` not awaited, and an INFO record on
    `issue_bot.bot` contains `"thread_id=5"`.
  - `test_default_hook_logs_when_thread_fails`: `IssueBot(config)`,
    `make_message("!bug\nTitle: Secret title words")`, `message.create_thread.side_effect =
    discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), {"code": 50013,
    "message": "x"})`; under `caplog.at_level(logging.INFO)`, `await bot.on_message(message)`
    does not raise, an INFO record on `issue_bot.bot` contains `"thread_id=None"`, an ERROR
    record on `issue_bot.threads` exists, and no record contains `"Secret title words"`.
  - `test_malformed_message_gets_format_hint_in_thread`: `IssueBot(config, on_candidate=hook)`
    with `hook = AsyncMock()`, `make_message("!bug\nBody: x")`, under
    `caplog.at_level(logging.INFO)`; `hook` not awaited,
    `create_thread.assert_awaited_once_with(name="Format help: !bug")`, the created
    thread's `send` awaited once with `format_hint(IssueType.BUG)`, and an INFO record on
    `issue_bot.bot` contains `"format hint bug"` and `"thread_id=1234"`.
  - `test_malformed_with_existing_thread_reuses_it`: `existing = SimpleNamespace(id=5,
    send=AsyncMock())`, `make_message("!bug\nBody: x", thread=existing)`; `create_thread` not
    awaited, `existing.send` awaited once.
  - `test_malformed_hint_skipped_when_thread_fails`: `IssueBot(config)`,
    `make_message("!bug\nBody: x")`, `create_thread.side_effect = discord.Forbidden(
    SimpleNamespace(status=403, reason="Forbidden"), {"code": 50013, "message": "x"})`; under
    `caplog.at_level(logging.INFO)`, `on_message` does not raise, exactly one ERROR record on
    `issue_bot.threads` contains `"Forbidden"` and `"99"`,
    `message.create_thread.return_value.send.assert_not_awaited()`, and
    `message.fetch_thread.assert_not_awaited()`.
  - `test_malformed_hint_send_failure_logged_without_text`: `IssueBot(config)`,
    `make_message("!bug\nBody: x")`, `message.create_thread.return_value.send.side_effect =
    discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), {"code": 50001,
    "message": "Secret error words"})`; under `caplog.at_level(logging.INFO)`, `on_message`
    does not raise, exactly one ERROR record on `issue_bot.bot` contains `"Forbidden"`,
    `"403"`, `"50001"` and `"99"`, and no record contains `"Secret error words"`.
  - `test_custom_on_malformed_hook`: `IssueBot(config, on_malformed=malformed_hook)` with an
    `AsyncMock` and `make_message("!bug\nBody: x")`; the hook is awaited once with
    `(message, MalformedTag(IssueType.BUG))` and `create_thread` is not awaited.
  Update `test_default_hook_logs_ids_not_text` to also assert one INFO record on
  `issue_bot.bot` contains `"thread_id=1234"`, keeping its no-text assertions. Rename
  `test_on_message_ignores_malformed` to `test_on_message_malformed_skips_candidate_hook` (it
  still asserts the candidate hook is not awaited). Run `.venv/bin/pytest tests/test_bot.py`
  and confirm each new or updated test fails for its expected reason:
  `test_default_hook_opens_one_thread_named_from_title`, `test_default_hook_truncates_long_title`
  (no thread created); `test_default_hook_skips_message_with_thread`,
  `test_default_hook_logs_when_thread_fails`, `test_default_hook_logs_ids_not_text` (no
  `thread_id=` in the log); `test_malformed_message_gets_format_hint_in_thread`,
  `test_malformed_with_existing_thread_reuses_it` (hint never sent);
  `test_malformed_hint_skipped_when_thread_fails`,
  `test_malformed_hint_send_failure_logged_without_text` (no ERROR record);
  `test_custom_on_malformed_hook` (`TypeError` for the unexpected `on_malformed` kwarg).
- [x] **Green:** in `issue_bot/bot.py`:
  - Import `MalformedTag` from `issue_bot.tags` and `format_hint, open_thread, thread_name`
    from `issue_bot.threads`.
  - Add `MalformedHook = Callable[[discord.Message, MalformedTag], Awaitable[None]]`.
  - Replace `log_candidate` with `async def open_issue_thread(message: discord.Message,
    candidate: IssueCandidate) -> None`
    (docstring: "Default hook: open the issue's thread and log ids and the message URL only,
    never member text or names."): `thread = await open_thread(message,
    thread_name(candidate.title))`, then `logger.info("captured %s message_id=%s (%s)
    thread_id=%s", candidate.type, candidate.message_id, candidate.message_url, thread.id if
    thread else None)`. Grep the repo for `log_candidate` (`grep -rn log_candidate issue_bot
    tests || true`) and update every remaining reference; after the update it prints nothing.
  - Add `async def reply_format_hint(message: discord.Message, malformed: MalformedTag) -> None`:
    `thread = await open_thread(message, f"Format help: !{malformed.type}")`; if `thread` is
    `None`, return. Otherwise `await thread.send(format_hint(malformed.type))` inside
    `try/except discord.HTTPException as exc`, which logs
    `logger.error("could not send format hint for message_id=%s thread_id=%s: %s status=%s
    code=%s", message.id, thread.id, type(exc).__name__, exc.status, exc.code)` and returns;
    after a successful send, log `logger.info("format hint %s message_id=%s thread_id=%s",
    malformed.type, message.id, thread.id)`.
  - `IssueBot.__init__(self, config, on_candidate: CandidateHook = open_issue_thread,
    on_malformed: MalformedHook = reply_format_hint)`; store `self.on_malformed`. Update the
    class docstring to mention both hooks.
  - `on_message`: `isinstance(result, IssueCandidate)` → `on_candidate`;
    `isinstance(result, MalformedTag)` → `await self.on_malformed(message, result)`.
  Run `.venv/bin/pytest` and confirm the whole suite passes.
- [x] **Refactor:** confirm `issue_bot/bot.py` has no unused imports and no log call passes a
  title, body, author name, thread name, `exc.text` or `str(exc)`. Run `.venv/bin/pytest`.

### 4. README - COMPLETE (2026-10-18)
Document the new behaviour and permissions.

**To-do:**
- [x] In `README.md` § Status, rewrite the F1 paragraph: it opens "F1 (channel listener and tag
  parser) and F2 (thread per tagged message) exist", and the sentence "Until F2 (clarifying
  thread) and F5 (issue filing) land, candidates are only logged, by issue type, message id and
  message URL." becomes: each candidate gets a public thread on its message, named from the
  title (truncated to 100 characters), and is logged by issue type, message id, message URL
  and thread id until F5 files it; a message that already has a thread reuses it.
- [x] In § Message format, replace the whole bullet "A tagged message with no usable `Title:`
  line is dropped, and the drop is logged by issue type, message id and message URL. F2 will
  reply in the thread with a format hint." with "A tagged message with no usable `Title:` line
  files no issue: the bot opens a `Format help: !<tag>` thread on it, replies with the expected
  format, and logs it by issue type, message id, message URL and thread id."
- [x] In § Discord setup step 3, add **Create Public Threads** and **Send Messages in Threads**
  to the listed permissions and drop "(F2 will add the thread permissions.)". Note that
  threads use the channel's default auto-archive duration.
- [x] Run `grep -nE 'F2 will (reply|add)' README.md || true` and
  `grep -n 'is dropped' README.md || true` and `grep -n 'Until F2' README.md || true` and
  confirm each prints nothing; run
  `grep -n 'Create Public Threads' README.md` and `grep -n 'Send Messages in Threads' README.md`
  and confirm each prints at least one line.

### 5. Verify All Tests Pass - COMPLETE (2026-10-18)
Run the full suite and the Standing-invariant checks.

**To-do:**
- [x] Run `.venv/bin/pytest` and confirm all tests pass.
- [x] Run `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues'
  --include='*.py' issue_bot || true` and confirm it prints nothing (Standing invariant 1).
- [x] Run `grep -nE -A6 '(logger\.(info|warning|error|debug|exception)|log_problem)\(' issue_bot/*.py`
  and read each call's arguments in the context lines and confirm none passes a title, body,
  content, author name, thread name or exception text (Standing invariant 2, as Step 1 widened
  it in CLAUDE.md). The pre-existing
  `configuration error: %s` call in `issue_bot/__main__.py` is exempt: it logs a `ConfigError`,
  whose message names the config key only, never its value. The pre-existing
  `connected as %s` call (the bot's own account, not a member) and `log_problem("%s", problem)`
  in `on_ready` (channel id, name and category from `channel_problems`, never member text) are
  exempt too.
- [x] Investigate and fix any failures before marking the plan finished; when every check above
  passed, tick this box with "(none to fix)". (none to fix)
- [x] Copy the "Manual checks (owner only)" bullets below, including the fold-back bullet,
  verbatim into your final report.

## Manual checks (owner only)
The "/run-feature fold-back" bullet is for /run-feature Phase C, not one of the owner's live
checks; this plan never edits META-PLAN itself.
- In a test channel with the bot granted Create Public Threads and Send Messages in Threads,
  post `!bug` / `Title: Thread smoke test`: a thread named "Thread smoke test" appears on the
  message. Post `!bug` with no `Title:` line: a `Format help: !bug` thread appears with the
  format reply. (Needs the owner's explicit go-ahead; never against the live channel.)
  Point the bot at the test channel through `.env` (`DISCORD_CHANNEL_ID`,
  `DISCORD_CHANNEL_NAME`, `DISCORD_CATEGORY`); never read `.env` as an agent. Each run creates
  new threads and a bot reply; delete the test messages and threads afterwards.
- Duplicate path (checks the documentation-derived 160004 code and `message.fetch_thread()`
  behaviour): with the owner's go-ahead, in the same test channel, archive the bot's thread on a
  test message, then from an owner REPL with the bot logged in run
  `await open_thread(channel.get_partial_message(<message id>), "dup check")` (with
  `from issue_bot.threads import open_thread` and `channel` the test channel; for example in
  `python -m asyncio`: `client = discord.Client(intents=discord.Intents.none())`,
  `await client.login(<token, typed by the owner>)`,
  `channel = await client.fetch_channel(<test channel id>)`, then `await client.close()`). Run
  this check before the first bullet's cleanup, and afterwards delete that test message, its
  thread and any "dup check" thread (one would mean the Fail case). In discord.py
  2.7.1, `TextChannel.get_partial_message(message_id, /) -> PartialMessage` exists, and
  `PartialMessage` has `create_thread`, `fetch_thread` and a `thread` property whose body is
  only `if self.guild is not None: return self.guild.get_thread(self.id)`, so an archived
  (uncached) thread reads as `None` and `open_thread` takes the `create_thread` → 160004 →
  `fetch_thread` path. Pass: the returned thread's id equals the message id, the thread is not
  renamed to "dup check", no second thread exists, and no ERROR line appears. Fail: note the
  `code=` from the ERROR line and record it in META-PLAN's Deferred follow-ups at fold-back.
- /run-feature fold-back: (1) extend Standing invariant 2's wording in `plans/META-PLAN.md` the
  same way Step 1 widened the CLAUDE.md logging bullet (log the issue type, ids (message,
  thread) and message URL only; a caught Discord API error is logged by exception type, HTTP
  status and Discord error code, never its text). (2) In `plans/META-PLAN.md`, rewrite F1's
  kept-contract bullet "A malformed tag (`MalformedTag`) is only logged; `candidate_from_message`
  returns `None` for it. F2's format-hint reply therefore has to extend
  `candidate_from_message`/`IssueBot`, for example with a malformed-message hook.", the
  Baseline **Interfaces** sentence "It logs a malformed tag by ids only and returns `None`."
  and the Baseline **Key modules / UI** sentence "`on_message` hands each candidate to an
  `on_candidate` hook (default: logs the type, message id and URL)." to say:
  `candidate_from_message` returns the `MalformedTag` for a tagged message without a usable
  title, and `IssueBot(config, on_candidate=open_issue_thread, on_malformed=reply_format_hint)`
  opens the issue thread / a `Format help: !<tag>` thread with the format hint; thread helpers
  live in `issue_bot/threads.py`.
- Orchestrator (/run-plan): append these bullets verbatim to the COMPLETE summary.

## Status
finished: true
