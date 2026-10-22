# Review: Post the issue link in the thread (F7)

## Review — 2026-10-21
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/post-issue-link/post-issue-link.md blob 289aabe689fc4711f28a32cb82071c4a55718cd9

### Summary
The plan's facts about `bot.py`, `threads.py`, `intake.py`, the fixtures and discord.py 2.7.1
hold. One reviewer applied Steps 1–3 to a scratch copy, and the planned tests pass there. One
major gap: Step 2's refactor breaks `tests/test_intake.py::test_github_error_still_posts_filing_error_reply`,
which the plan never names, and Step 2's gate skips that file. Proceed after the fixes below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 1 major, 5 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 3 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 5 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 4 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 1 major, 4 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 1 major, 6 minor |

### Findings

#### Major (should fix)
- **[Step 2] Refactor breaks `test_intake.py::test_github_error_still_posts_filing_error_reply`** _(Subagents #1, #3, #5, #6)_: it asserts `summary.create_thread.return_value.send.assert_awaited_once_with(FILING_ERROR_REPLY)` with no kwargs; `_post_outcome` adds `allowed_mentions` and `suppress_embeds`. Step 2's gate runs only `test_bot.py` and `test_threads.py`, so a red suite would be committed at Step 2. Subagent #5 reproduced the failure on a scratch copy.

#### Minor (nice to fix)
- **[Step 2] Dead `destination` local in `_post_outcome`** _(#1, #2, #4, #6)_: nothing reads it; `thread_id=None` already tells the two paths apart.
- **[Step 2] Import placement and line width unspecified** _(#4)_: bot.py's intake import grows past ~100 columns. Existing imports list constants first, then classes, then functions, and wrap in a parenthesized block once they get that long.
- **[Step 3] The end-to-end test duplicates `test_intake.py::test_submit_files_issue_through_filing_hook`** _(#1, #3, #5, #6)_: decision DD-1 below.
- **[Step 2] A non-HTTP failure on the link send reaches `IntakeModal.on_error`** _(#2, #6)_: decision DD-2 below.
- **[Step 4] The docs grep gate matches the F7 mention Step 4 itself adds, and exits 1 when clean** _(#1, #3, #4, #5, #6)_.
- **[Step 4] The reply fallback needs Read Message History** _(#1, #2, #6)_: `Message.reply` sends a `message_reference`, which Discord's docs say needs Read Message History (not tested live). README's stated reason for the permission doesn't mention replies, and `docs/SMOKE-TEST.md` setup step 4 and its troubleshooting row leave it out.
- **[Step 5] The Standing invariant 2 gate can't see log arguments** _(#5)_: `grep -n "logger\."` prints only the opening line of each multi-line call.

#### Descriptive (deferred to final cleanup)
- [Steps 1, 5] Stored test count (212) _(#1, #3, #4, #5, #6)_.
- [Step 3] The first box is labelled **Red** but expects a pass _(#3)_.
- Anchor lint: `issue_bot/github.py:46` line citation; `DD-13` reference (F10's decision, not this plan's).

### Verification Gaps
- **Step 2**: the gate must include `tests/test_intake.py` (fixed below).

### To-Do: Mechanical Fixes (auto-applied)
- [x] M1 [Step 2] Added a to-do updating `test_intake.py::test_github_error_still_posts_filing_error_reply` (kwargs + `summary.reply.assert_not_awaited()`; `NO_MENTIONS` already imported); Step 2's gate now includes `tests/test_intake.py`; Research Findings name the test_intake tests. Sweep found no other affected assertion.
- [x] M2 [Step 2] Dropped the dead `destination` local from `_post_outcome`.
- [x] M3 [Step 2] Spelled out import placement for `bot.py`, `threads.py`, `tests/test_bot.py` and `tests/test_threads.py`.
- [x] M4 [Step 4] Docs gate is now `grep -n "comes with F7\|nothing\*\* posted\|link post comes" README.md docs/SMOKE-TEST.md || true`, expected to print nothing.
- [x] M5 [Step 4] Added Read Message History to-dos for README § Discord setup step 2 and SMOKE-TEST setup step 4 plus its troubleshooting row.
- [x] M6 [Step 5] Standing invariant 2 now greps `candidate\.\(title\|body\|author_name\)` in `bot.py`.

### Design Decisions (awaiting user input)

#### DD-1: [Step 3] Where the end-to-end link test lives
**Context:** META-PLAN wants a "message → thread → mocked issue → link posted" handler test. `tests/test_intake.py::test_submit_files_issue_through_filing_hook` already runs that flow with `filled_modal(config, filing_hook(fake_github(FiledIssue(7, ISSUE_URL))))`, but doesn't assert the link.

| # | Option | Trade-off |
|---|---|---|
| 1 | Extend the existing test_intake test with the link and confirmation assertions | No duplicate setup; follows where modal-submit tests already live |
| 2 | New test in test_bot.py, as planned | A self-contained F7 test, but a near-copy that hand-seeds the modal |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Extend the existing test_intake test (assumed: dd-policy, dd-261021-013)

#### DD-2: [Step 2] Exceptions `_post_outcome` catches
**Context:** Before F7 the success path made no Discord call. A transport error (aiohttp `ClientError`, timeout) on the link send would now reach `IntakeModal.on_error`, which replies `INTAKE_ERROR_REPLY` instead of `SUBMITTED_REPLY`. The issue is already filed, and its URL is logged first.

| # | Option | Trade-off |
|---|---|---|
| 1 | Keep HTTPException-only | Matches `open_thread` and the existing error send. The failure is rare and recoverable (C3) |
| 2 | Also catch other exceptions and log the type | No error reply after a filed issue, but adds a broad except unlike the sibling code |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Keep HTTPException-only (assumed: dd-policy, dd-261021-014)

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | `issue_bot/github.py` imports only config, so `threads` → `github` makes no cycle; there are no dead imports |
| Type annotations | [x] | `_post_outcome` and `filed_reply` signatures given |
| Error handling (status codes, exceptions, user feedback) | [x] | HTTPException path traced; non-HTTP path → DD-2 |
| Test coverage (happy path, sad path, edge cases) | [x] | Scratch-copy run; test_intake gap found |
| Breaking changes (API contracts, shared state, DB schema) | [x] | No schema; FILING_ERROR_REPLY send kwargs change → test_intake |
| Config consistency (env vars, requirements pins, lint rules) | [x] | No new packages/env; no lint config in repo |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | Import order convention noted |

## Review — 2026-10-21 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/post-issue-link/post-issue-link.md blob a73e8d6356dafe6c145ff6c83cb277beed04d27d

### Summary
All six subagents PASS; 0 critical, 0 major. Pass 1's fixes M1–M6 and both DDs hold against source; Steps 1–3 applied to a scratch copy give a green suite at every step. Minor gate and docs fixes applied below. Plan is ready for implementation.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 1 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 2 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 0 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 1 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 3 minor |

### Findings

#### Minor (nice to fix)
- **[Step 5] Standing invariant 1 gate exits 1 on its expected empty result** _(#2, #4, #5)_: needs `|| true`.
- **[Step 4] The closing docs gate misses README line 3** _(#5, #6)_: "Posting the issue's link back in the thread" in the opening paragraph isn't matched by any of its patterns.
- **[Step 4] Known limits drops the residual log-only case** _(#6)_: when the thread post or the summary reply itself fails, the outcome still shows only in the log.
- **[Step 4] No troubleshooting row for a missing link** _(#6)_: `docs/SMOKE-TEST.md`'s symptom table has nothing for a filed issue whose link never appears.
- **[Manual checks] The reply fallback is never checked live** _(#5)_: decision DD-3 below.
- **[Summary] "never visible only in the log" overclaims** _(#1, #2, descriptive)_: a failed post is still log-only.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 5 Standing invariant 1: appended ` || true` inside the gate's backticks.
- [x] Step 4 closing docs gate: added `\|link back in the thread`; it prints README:3, README:9 and SMOKE-TEST:110 today and nothing on a scratch copy with Step 4 applied. Its parenthetical now names README's opening paragraph too.
- [x] Step 4 README Known-limits to-do: if that post fails too, the outcome shows only in the log (`could not send issue link …` or `could not send filing error …`).
- [x] Step 4: new to-do adding the "The issue is filed but no link appears in the thread" row to `docs/SMOKE-TEST.md`'s troubleshooting table after "A submit gets a private error and no summary" (two columns, like the table).

### Design Decisions

#### DD-3: [Manual checks] Live check of the reply fallback
**Context:** The no-thread fallback (`message.reply` on the summary) is covered only by mocked tests; the live smoke test always opens a thread, so the reply path and its Read Message History need never meet real Discord.

| # | Option | Trade-off |
|---|---|---|
| 1 | Add optional owner manual-check bullet | One extra `/bug` in the test server with Create Public Threads removed, then restored |
| 2 | Leave to unit tests | No extra owner work, but the permission and reply rendering stay unverified live |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Leave to unit tests (overturned at review; was assumed dd-261021-015)

---

### Verdict
[x] Ready to proceed as-is
[ ] Proceed after minor fixes
[ ] Requires changes before proceeding

### Descriptive cleanup: 4 fixed, 1 dropped
- Fixed: Summary overclaim reworded (a missing thread no longer leaves the outcome log-only; a failed post is logged after the issue URL).
- Fixed: stored test count (212) removed from Steps 1 and 5 (Pass 1 descriptive).
- Fixed: Step 3's first box no longer labelled **Red**; it says the box passes already via Step 2's helper (Pass 1 descriptive).
- Fixed: `issue_bot/github.py:46` line citation replaced by the `FiledIssue` dataclass in `issue_bot/github.py` (Pass 1 descriptive); anchor lint now reports 0 problems.
- Dropped: `DD-13` anchor-lint hit (Pass 1 descriptive) is already gone from the lint output.

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| Pass 1 fix M4's docs gate dropped coverage of README line 3 | minor | step-5b:mechanical-fix | fix_regression | Fixer checked the gate against the old pattern's matches, not every sentence Step 4 rewrites | yes (open pair) | not logged |

Other Pass 2 minors (invariant-1 `|| true`, Known-limits residual case, troubleshooting row) have no open unit/cause pair and were not kept.

### Plan-Creator Misses
| Finding | Severity | Unit | Ledger id |
|---|---|---|---|
| Inline research missed `tests/test_intake.py`'s `FILING_ERROR_REPLY` send assertion | major | step-2b:complexity-gate | plan-creator-20261021-001 |
