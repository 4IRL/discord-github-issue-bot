# Post the issue link in the thread (F7)

## Summary
After `filing_hook` files a report as a GitHub issue, the bot posts a short confirmation with
the issue number, the escaped title and the `html_url` GitHub returned in the report's thread.
When no thread could be opened, the link (or F5's fixed `FILING_ERROR_REPLY`) is posted as a
reply to the bot's summary message instead, so a missing thread no longer leaves the outcome
visible only in the log (a Discord failure on the post itself is logged, after the issue URL).
This completes the Phase 1 skeleton (META-PLAN § F7).

## Research Findings
Research was done inline (20 source files, one layer, change confined to `issue_bot/bot.py`,
`issue_bot/threads.py`, tests and two docs).
- `issue_bot/bot.py` `filing_hook(github)` → inner `file_and_report(message, candidate)`: opens
  the thread with `open_thread(message, thread_name(candidate.title))`, calls
  `file_candidate(github, candidate)` (returns `FiledIssue(number, html_url)`, the
  `FiledIssue` dataclass in `issue_bot/github.py`), on `GitHubError` logs and sends `FILING_ERROR_REPLY` only
  `if thread is not None` (its own `try/except discord.HTTPException` logging
  `could not send filing error for message_id=%s thread_id=%s: %s status=%s code=%s`), and on
  success logs `filed %s message_id=%s (%s) thread_id=%s issue=%s` and posts nothing.
- `issue_bot/threads.py` holds the fixed reply constant
  `FILING_ERROR_REPLY = "Sorry, I couldn't file this as a GitHub issue. …"`; `issue_bot/intake.py`
  holds `NO_MENTIONS = discord.AllowedMentions.none()` and `summary_text`, which escapes the title
  with `discord.utils.escape_markdown(title)` and is sent with `allowed_mentions=NO_MENTIONS,
  suppress_embeds=True`. `AllowedMentions.none()` also sets `replied_user=False`, so a reply
  pings nobody.
- `candidate.title` is already whitespace-normalized by `IntakeModal.on_submit` and capped at
  `TITLE_MAX_LENGTH` (100), so the link message stays far under Discord's 2000-character limit.
- discord.py is 2.7.1: `Message.reply(content, **kwargs)` forwards `allowed_mentions` and
  `suppress_embeds` to `send`.
- Tests: `tests/test_bot.py` has `test_filing_hook_files_issue_and_logs_url` (currently asserts
  `message.create_thread.return_value.send.assert_not_awaited()`, which F7 inverts),
  `test_filing_hook_failure_replies_and_logs_status`, `test_filing_hook_files_even_without_thread`,
  `test_filing_hook_failure_without_thread_logs_only` (asserts no send; F7 changes it to a reply),
  `test_filing_error_send_failure_logged_without_text`, and
  `test_filing_hook_unexpected_error_reaches_modal_on_error`. Helpers: `secret_candidate`,
  `bot_records`, `record_texts`, `assert_no_member_text`, `forbidden(code, text)`,
  `fake_github(result)`, `ISSUE_URL = "https://github.com/example-org/example-repo/issues/7"`.
  `tests/test_intake.py` also runs `filing_hook` through a submitted modal (`filled_modal`):
  `test_github_error_still_posts_filing_error_reply` asserts the thread `send` with
  `FILING_ERROR_REPLY` and no kwargs (F7 adds the kwargs), and
  `test_submit_files_issue_through_filing_hook` files an issue but doesn't check the thread.
  `make_message` in `tests/conftest.py` builds a `SimpleNamespace` with `create_thread` and
  `fetch_thread` AsyncMocks whose threads have `send=AsyncMock()`; it has no `reply`.
- Docs that describe today's "posts nothing" behaviour: `README.md` lines 3, 9 and 33, and
  `docs/SMOKE-TEST.md` line 110 (`with **nothing** posted in it (the link post comes with F7)`)
  and line 128. The Read Message History permission, which `Message.reply` needs, is explained in
  README § Discord setup and missing from `docs/SMOKE-TEST.md` setup step 4 and its troubleshooting
  table.

## Decisions
- **DD-1 — success message content.** **Chosen:** issue number, escaped title and URL (asked;
  ledger `dd-261021-009`). Text: `Filed as GitHub issue #<number>: <escaped title>\n<html_url>`.
- **DD-2 — embeds.** **Chosen:** `suppress_embeds=True`, as on the summary, so a URL inside a
  member's title can't unfurl under the bot's name (asked; ledger `dd-261021-010`).
- **DD-3 — no-thread fallback.** **Chosen:** reply to the summary message (`message.reply`) with
  the same text the thread would have got, success link or `FILING_ERROR_REPLY` (assumed:
  dd-policy, `dd-261021-011`). Takes F5's deferred "message-reply fallback when filing fails and
  no thread opened" and closes F10 DD-13's gap.
- **DD-4 — send helper.** **Chosen:** one private helper in `bot.py` for both sends, with
  distinct log wording per message kind (assumed: dd-policy, `dd-261021-012`).
- **DD-5 — end-to-end test location.** **Chosen:** extend
  `tests/test_intake.py::test_submit_files_issue_through_filing_hook` with the link and
  confirmation assertions instead of a near-copy in `tests/test_bot.py` (assumed: dd-policy,
  `dd-261021-013`).
- **DD-6 — send helper exceptions.** **Chosen:** `discord.HTTPException` only, like `open_thread`
  and the existing error send; a rare transport error after filing reaches `IntakeModal.on_error`,
  with the issue's URL already logged (assumed: dd-policy, `dd-261021-014`).
- **DD-7 — live check of the reply fallback.** **Chosen:** no live check; the mocked unit tests
  cover the fallback (overturned at review; was assumed `dd-261021-015`).

## Steps

### 1. Test fixture: summary messages can be replied to
Give the `make_message` stand-in a `reply` mock so tests can assert the fallback.

**To-do:**
- [x] In `tests/conftest.py` `make_message.factory`, add `reply=AsyncMock()` to the returned
  `SimpleNamespace` (after `fetch_thread`).
- [x] Run `.venv/bin/pytest -q` and confirm the suite passes. - COMPLETE (2026-10-21): 212 passed

### 2. Red → Green: link posted in the thread on success
One thread message with the issue number, escaped title and URL; no mentions, no embeds.

**To-do:**
- [x] **Red.** In `tests/test_threads.py`, add `test_filed_reply_has_number_title_and_url`:
  `filed_reply(FiledIssue(7, ISSUE_URL), "Fix *it*")` equals
  `f"Filed as GitHub issue #7: Fix \\*it\\*\n{ISSUE_URL}"`. Imports: add
  `from issue_bot.github import FiledIssue` above the `from issue_bot.threads import (` block, add
  `filed_reply,` to that block between `THREAD_NAME_LIMIT,` and `open_thread,` (constants, then
  functions), and change `from tests.conftest import MessageFactory` to
  `from tests.conftest import ISSUE_URL, MessageFactory`.
  Run it; confirm it fails with an `ImportError` for `filed_reply`.
- [x] **Green.** In `issue_bot/threads.py`, below `FILING_ERROR_REPLY`, add
  `FILED_REPLY = "Filed as GitHub issue #{number}: {title}\n{url}"` and
  `def filed_reply(issue: FiledIssue, title: str) -> str` returning
  `FILED_REPLY.format(number=issue.number, title=discord.utils.escape_markdown(title), url=issue.html_url)`
  with a one-line docstring (the title is member text: escaped here, sent with no mentions by the
  caller, never logged). Add `from issue_bot.github import FiledIssue` as a project import group
  after `import discord`, separated by a blank line (no cycle: `issue_bot.github` imports only
  `issue_bot.config`). Update the module docstring's
  first line to mention the replies it formats. Run the test; confirm it passes.
- [x] **Red.** In `tests/test_bot.py`, rename `test_filing_hook_files_issue_and_logs_url` to
  `test_filing_hook_files_issue_posts_link_and_logs_url` and replace its
  `message.create_thread.return_value.send.assert_not_awaited()` with
  `message.create_thread.return_value.send.assert_awaited_once_with(filed_reply(FiledIssue(7, ISSUE_URL), "Secret title words"), allowed_mentions=NO_MENTIONS, suppress_embeds=True)`
  plus `message.reply.assert_not_awaited()`. Imports: change the intake line to
  `from issue_bot.intake import FILING_UNAVAILABLE_REPLY, INTAKE_ERROR_REPLY, NO_MENTIONS, IntakeModal`
  and the threads line to `from issue_bot.threads import FILING_ERROR_REPLY, filed_reply`. Keep its log and `assert_no_member_text` assertions.
  Run it; confirm it fails because `send` was not awaited.
- [x] **Green.** In `issue_bot/bot.py`, add a module-level
  `async def _post_outcome(message: discord.Message, thread: discord.Thread | None, text: str, what: str) -> None`
  (DD-4): inside `try:` call `await thread.send(text, allowed_mentions=NO_MENTIONS, suppress_embeds=True)` when
  `thread is not None`, else `await message.reply(text, allowed_mentions=NO_MENTIONS, suppress_embeds=True)`;
  `except discord.HTTPException as exc:` log
  `logger.error("could not send %s for message_id=%s thread_id=%s: %s status=%s code=%s", what, message.id, thread.id if thread else None, type(exc).__name__, exc.status, exc.code)`.
  `what` is a fixed string (`"issue link"` or `"filing error"`), never member text. Docstring:
  one line saying it posts in the thread, else as a reply to the summary, logging a Discord
  failure by type, status and code only. Imports: replace the intake line with a parenthesized
  block, one name per line: `NO_MENTIONS`, `CandidateHook`, `FilingCheck`,
  `discord_error_fields`, `intake_command`; change the threads line to
  `from issue_bot.threads import FILING_ERROR_REPLY, filed_reply, open_thread, thread_name`.
- [x] In `file_and_report`, after the `filed …` `logger.info`, add
  `await _post_outcome(message, thread, filed_reply(issue, candidate.title), "issue link")`.
  (The link is posted after the log so a failed send never hides the filed issue's URL.) Run the
  test; confirm it passes.
- [x] **Refactor.** Replace the `GitHubError` branch's `if thread is not None: try: await thread.send(FILING_ERROR_REPLY) … except …` block with
  `await _post_outcome(message, thread, FILING_ERROR_REPLY, "filing error")` (the `return`
  stays). The log line keeps its `could not send filing error for message_id=…` prefix, so
  `test_filing_error_send_failure_logged_without_text`'s substring check still matches; update
  that test only if it fails. Update `filing_hook`'s docstring: on
  success it posts `filed_reply` and on a `GitHubError` the fixed `FILING_ERROR_REPLY`, in the
  thread or, with no thread, as a reply to the summary message.
- [x] Update `test_filing_hook_failure_replies_and_logs_status`'s
  `send.assert_awaited_once_with(FILING_ERROR_REPLY)` to
  `assert_awaited_once_with(FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True)`
  and add `message.reply.assert_not_awaited()`, so a failed filing posts the error and no link
  (Expected end state).
- [x] In `tests/test_intake.py` `test_github_error_still_posts_filing_error_reply`, change
  `summary.create_thread.return_value.send.assert_awaited_once_with(FILING_ERROR_REPLY)` to
  `assert_awaited_once_with(FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True)`
  and add `summary.reply.assert_not_awaited()`. `NO_MENTIONS` is already in that file's
  `from issue_bot.intake import (` block, so no import changes.
- [x] Run `.venv/bin/pytest -q tests/test_bot.py tests/test_threads.py tests/test_intake.py`;
  confirm green. - COMPLETE (2026-10-21): 84 passed (full suite 213 passed)

### 3. Red → Green: no-thread fallback and send failures
With no thread, the same text goes to a reply on the summary; a failed link send is logged
without text.

**To-do:**
- [x] Extend `test_filing_hook_files_even_without_thread` (rename it to
  `test_filing_hook_without_thread_replies_link_on_summary`): assert
  `message.reply.assert_awaited_once_with(filed_reply(FiledIssue(7, ISSUE_URL), "Secret title words"), allowed_mentions=NO_MENTIONS, suppress_embeds=True)`
  and `message.create_thread.return_value.send.assert_not_awaited()`. It passes already, since Step 2's
  `_post_outcome` helper covers the no-thread path; run it and confirm it passes.
- [x] Rename `test_filing_hook_failure_without_thread_logs_only` to
  `test_filing_hook_failure_without_thread_replies_error_on_summary` and replace its two
  `send.assert_not_awaited()` lines with
  `message.reply.assert_awaited_once_with(FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True)`;
  keep the single-ERROR-line assertion (the thread-open failure is logged by `threads`, not
  `bot`, so `bot_records` still has one error). Run it; confirm it passes.
- [x] Add `test_link_send_failure_logged_without_text`, modelled on
  `test_filing_error_send_failure_logged_without_text`: `fake_github(FiledIssue(7, ISSUE_URL))`,
  thread `send.side_effect = forbidden(50001, "Secret error words")`; assert exactly one bot ERROR
  record containing `could not send issue link`, `Forbidden`, `403`, `50001`, `message_id=99`,
  `thread_id=1234`; the `filed bug` INFO record is still present; no record contains
  `Secret error words`; `assert_no_member_text(caplog)`.
- [x] Add `test_summary_reply_failure_logged_without_text`: `create_thread.side_effect =
  forbidden(50013, "x")`, `message.reply.side_effect = forbidden(50001, "Secret error words")`,
  success filing; assert one bot ERROR containing `could not send issue link` and
  `thread_id=None`, and no `Secret error words` in any record; `assert_no_member_text(caplog)`.
- [x] In `test_filing_hook_unexpected_error_reaches_modal_on_error`, keep
  `summary.create_thread.return_value.send.assert_not_awaited()` and add
  `summary.reply.assert_not_awaited()` (an unexpected error posts nothing; it reaches `on_error`).
- [x] Extend `tests/test_intake.py::test_submit_files_issue_through_filing_hook` (DD-5); it
  already submits `filled_modal(config, filing_hook(github))` (title `"Fix it"`) with
  `summary = interaction.channel.send.return_value`. After its `body.startswith(…)` assertion add
  `summary.create_thread.return_value.send.assert_awaited_once_with(filed_reply(FiledIssue(7, ISSUE_URL), "Fix it"), allowed_mentions=NO_MENTIONS, suppress_embeds=True)`,
  `summary.reply.assert_not_awaited()` and
  `interaction.followup.send.assert_awaited_once_with(SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True)`
  (the private confirmation still goes out). Change `from issue_bot.threads import FILING_ERROR_REPLY`
  to `from issue_bot.threads import FILING_ERROR_REPLY, filed_reply`. This is the META-PLAN
  "message → thread → mocked issue → link posted" handler test.
- [x] Run `.venv/bin/pytest -q`; confirm green. - COMPLETE (2026-10-21): 216 passed (review fix: `test_summary_reply_failure_logged_without_text` now asserts type/status/code/message_id, and `test_summary_error_reply_failure_logged_without_text` added for a failed summary reply on the filing-error path)

### 4. Docs
Describe the new behaviour where the docs still say nothing is posted.

**To-do:**
- [x] `README.md` line 3: drop "Posting the issue's link back in the thread," from the planned
  list (keep "clarifying questions and roadmap placement are planned features").
- [x] `README.md` line 9: add F7 to the list of features that exist; replace the last two
  sentences with: on success the bot posts the issue number, title and link in the thread; if
  filing fails it posts a fixed error reply there; with no thread, either goes as a reply to the
  summary message.
- [x] `README.md` § Reporting step 3 (line 18): add that it then posts the issue's link in the
  thread. Line 33: the confirmation still means only the summary was posted; the filing outcome
  (link or error) appears in the thread, or as a reply to the summary when no thread opened; if
  that post fails too, the outcome shows only in the log (`could not send issue link …` or
  `could not send filing error …`).
- [x] `docs/SMOKE-TEST.md` line 11: success checks include one link post per submission. Line
  110: the thread row expects one bot message `Filed as GitHub issue #<n>: <title>` with the
  issue link and no preview card. Line 128: the failure reply goes in the thread, or as a reply to
  the summary with no thread. Keep the rest of the runbook unchanged.
- [x] `README.md` § Discord setup step 2: the sentence "Read Message History is kept for opening and
  fetching threads on the summary message." becomes "Read Message History is kept for opening and
  fetching threads on the summary message, and for replying to the summary when no thread could be
  opened."
- [x] `docs/SMOKE-TEST.md`: in setup step 4, "The bot needs View Channel, Send Messages, Create
  Public Threads and Send Messages in Threads there" becomes "The bot needs View Channel, Read
  Message History, Send Messages, Create Public Threads and Send Messages in Threads there"; in the
  troubleshooting row "A submit gets a private error and no summary", "the bot has View Channel,
  Send Messages, Create Public Threads and Send Messages in Threads there" gains Read Message
  History the same way.
- [x] `docs/SMOKE-TEST.md` troubleshooting table: after the "A submit gets a private error and no
  summary" row, add the row
  `` | The issue is filed but no link appears in the thread | The bot couldn't post it. Check the log for `could not send issue link …` (its status and code): the thread post needs Send Messages in Threads; the reply on the summary (when no thread opened) needs Send Messages and Read Message History. | ``
  (two columns, like the rest of the table).
- [x] `grep -n "comes with F7\|nothing\*\* posted\|link post comes\|link back in the thread" README.md docs/SMOKE-TEST.md || true`
  prints nothing (before Step 4 it prints README's opening paragraph, README's Status paragraph
  and SMOKE-TEST's "Discord thread" row). - COMPLETE (2026-10-21): grep prints nothing; full suite 216 passed; 3 reviewers PASS

### 5. Verify All Tests Pass

Run the full test suites to confirm nothing is broken:

**To-do:**
- [x] Run `.venv/bin/pytest` and confirm all tests pass. - COMPLETE (2026-10-21): 216 passed, 0 failed
- [x] Standing invariant 1: `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot || true` prints nothing. - COMPLETE (2026-10-21): prints nothing
- [x] Standing invariant 2: `grep -n 'candidate\.\(title\|body\|author_name\)' issue_bot/bot.py`
  shows only `thread_name(candidate.title)` and `filed_reply(issue, candidate.title)` uses, none
  inside a `logger.` call; the new tests' `assert_no_member_text` checks pass. - COMPLETE (2026-10-21): hits at bot.py:61 and :102 (`thread_name(candidate.title)`) and :127 (`filed_reply(issue, candidate.title)` passed to `_post_outcome`), none in a logger call; suite green
- [x] Investigate and fix any failures before marking the plan finished. - COMPLETE (2026-10-21): no failures

### Manual checks (owner, not executor)
- Live smoke test per `docs/SMOKE-TEST.md` in the separate test server: each `/bug` and
  `/feature` submission gets one `Filed as GitHub issue #<n>: <title>` message with the link in
  its thread, and no preview card.

**To-do:**
- [x] Copy the "Manual checks" bullets above verbatim into the final report. - COMPLETE (2026-10-21)

## Status
finished: true
