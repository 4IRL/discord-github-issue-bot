# Push Review: feature/post-issue-link

## Review 1
Generated: 2026-10-21 17:01
Comparison: origin/main 5df26a639d5dbd2988e9da8cb8961da258508ee8..6b46b26c2de6edcff7b9711e396cef87a75fb180
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
Posts use `NO_MENTIONS` and `suppress_embeds`, the member title is escaped, and logs carry only type, ids, status and code. No secrets and no destructive operations.

#### 2. Correctness — PASS
Thread-vs-reply branching, HTTPException-only handling, the send kwargs, the escaped title and the log-before-post ordering all hold.

#### 3. Simplicity & Conciseness — PASS
`_post_outcome` replaces a duplicated nested try/except and serves both reply paths. No dead code.

#### 4. Test Coverage — PASS
The success, error, no-thread, send-failure and unexpected-error paths are covered.
- minor: `filed_reply` is tested only with Markdown characters in the title, not with a mention or a URL. The send-level kwargs assertions partly cover this.
- minor: no `filing_hook` test covers the link post when `open_thread` falls back to `fetch_thread` (160004).

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs or stubs. Docs, docstrings and tests match the behavior.

#### 6. Consistency & Style — PASS
Naming, import order and logging patterns match the surrounding code.

#### 7. Integration Risk — PASS
An additive change in `bot.py` and `threads.py`, with no schema, config or dependency changes. The docs record the Read Message History need.

#### 8. Error Handling & Silent Failures — PASS
Only `discord.HTTPException` is caught, and it is logged by type, status, code and ids. Other exceptions propagate to the existing handlers.

### To-Do: Required Changes

- [ ] **Add a mention/URL title test for the link post** — `tests/test_bot.py` — Add a `filing_hook` case whose title is `"@everyone http://x"`. Assert the thread send carries `filed_reply(...)` with `allowed_mentions=NO_MENTIONS, suppress_embeds=True` and that no member text is logged.
- [ ] **Cover the link post on the fetch_thread recovery path** — `tests/test_bot.py` — Add a `filing_hook` test where `message.create_thread` raises a 160004 `HTTPException` (`THREAD_ALREADY_CREATED`). Assert the link goes to `message.fetch_thread.return_value.send` and that `message.reply` is not awaited.
