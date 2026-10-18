# Push Review: feature/issue-thread

## Review 1
Generated: 2026-10-18 11:29
Comparison: origin/main 7abf12e9a1e643128feb89d8c2578380ecd1dd08..d7c53e0490c9adbdbdc676fd5749fc0a9775ad3f
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No secrets, injection or destructive operations. Every new log line carries only ids, the message URL, the exception type, HTTP status and Discord code, never member text or names, which matches the CLAUDE.md logging rule.

#### 2. Correctness — PASS
The discord.py 2.7.1 APIs (`Message.thread`, `create_thread(name=)`, `fetch_thread`, `HTTPException.code/.status`) are used correctly, and control flow, truncation and docs are consistent.
- minor: `reply_format_hint` (issue_bot/bot.py) posts the hint into a pre-existing thread if a human already started one on a malformed message.
- minor: `thread_name` counts Python code points; emoji/combining sequences may count differently on Discord (accepted risk, DD-12).

#### 3. Simplicity & Conciseness — PASS
- minor: the `logger.error(... type, status, code ...)` block appears twice in `open_thread` and once in `reply_format_hint`; one helper would keep the never-log-text rule in one place.
- minor: `format_hint` is one long f-string line.

#### 4. Test Coverage — PASS
- minor: `test_malformed_hint_send_failure_logged_without_text` doesn't assert the "format hint" success line is absent.
- minor: no 101-character boundary case for `thread_name`.

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs or stray files.
- minor: META-PLAN's F1 kept contract and F2 rows are stale until the post-merge fold-back (carried by the plan's fold-back bullet).

#### 6. Consistency & Style — PASS
- minor: `format_hint`'s line is 206 characters; everything else is ≤ 100.
- minor: duplicated log block in `open_thread` (same as #3).
- minor: `candidate_from_message`'s docstring summary wraps over two lines.

#### 7. Integration Risk — PASS
Additive change; the only caller was updated, and there are no config, dependency or schema changes.
- minor: F5/F7 should get the thread via `open_thread` (idempotent), not the default hook (already in the plan's Decisions).
- minor: META-PLAN kept-contract text is stale after merge (fold-back).
- minor: live installs need the Create Public Threads and Send Messages in Threads permissions; call this out in the PR description.

#### 8. Error Handling & Silent Failures — PASS
Narrow `discord.HTTPException` catches, ids-only logs, and anything unexpected reaches `on_error`.
- minor: on a failed thread, `open_issue_thread` still logs "captured … thread_id=None" at INFO; consider distinct wording and a permission hint for 403.
- minor: both `open_thread` error logs say "could not open thread", so the create and fetch steps can't be told apart.

### To-Do: Required Changes

- [ ] **Extract a shared API-error log helper** — `issue_bot/threads.py`, `issue_bot/bot.py` — Add e.g. `log_api_error(action, message_id, exc, thread_id=None)` in `threads.py` that logs type, status and code only. Use it for both `open_thread` error paths and `reply_format_hint`'s send failure, and give each call a distinct action ("create thread", "fetch existing thread", "send format hint").
- [ ] **Split `format_hint`'s string** — `issue_bot/threads.py` — Build the hint from implicitly concatenated pieces so no line exceeds 100 characters; the text stays unchanged (test asserts equality).
- [ ] **Distinguish a failed thread in the candidate log** — `issue_bot/bot.py` (`open_issue_thread`) — When `open_thread` returns `None`, log a distinct INFO line (e.g. "no thread opened for %s message_id=%s (%s)") instead of "captured … thread_id=None", and update `test_default_hook_logs_when_thread_fails`.
- [ ] **Decide whether to skip the hint in a pre-existing human thread** — `issue_bot/bot.py` (`reply_format_hint`) — Either accept posting into an existing thread, or skip the hint when `message.thread` was already set; record the choice.
- [ ] **Tighten two tests** — `tests/test_bot.py`, `tests/test_threads.py` — In `test_malformed_hint_send_failure_logged_without_text` assert no INFO record contains "format hint"; add a 101-character `thread_name` case asserting length 100 and a trailing "…".
- [ ] **One-line docstring summary** — `issue_bot/handler.py` (`candidate_from_message`) — Shorten the summary to one line and move details below it.
- [ ] **Fold-back: refresh META-PLAN F1 contract and Baseline** — `plans/META-PLAN.md` — At /run-feature Phase C, apply the plan's fold-back bullet (Standing invariant 2 wording, F1 kept contract, Baseline Interfaces / Key modules sentences).
- [ ] **Mention the new Discord permissions in the PR description** — PR body — Operators must grant Create Public Threads and Send Messages in Threads before deploying.
