# Review: Retry and rate limits (F13)

## Review — 2026-11-17
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/retry-rate-limits/retry-rate-limits.md blob 26cee911d3461c50ca77ce9c5c1708f4c71e9d01

### Summary
Sound design and the right choke points, but Step 2's retry loop would break existing single-failure tests the plan never listed. The loop spec left variables unbound across attempts, call counts ignored the token mint, an existing filing test would sleep for real, and DD-12 rested on a false premise about discord.py 2.7.1's logging. Mechanical fixes applied; seven design decisions settled (six asked, one assumed). Needs changes before proceeding (this pass applies them).

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 2 major, 8 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 1 major, 8 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 3 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 1 major, 9 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 5 major, 5 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 5 major, 9 minor |

### Findings

#### Major (should fix)
- **[Step 2] Retry loop breaks existing single-failure tests on idempotent stages** _(Subagents #1, #3, #4, #5, #6)_: tests that script one 5xx/transport failure and then a success, or nothing after it, either stop raising or hit StopAsyncIteration once `_request` retries. Mechanical (M1).
- **[Step 2] `_request` loop leaves `data`/`headers` unbound and the transport-failure flag stale across attempts** _(Subagents #1, #2, #6)_: mechanical (M2).
- **[Step 2/3] Prescribed call counts ignore the token-mint transport call** _(Subagents #1, #5)_: mechanical (M3).
- **[Step 5] An existing filing_hook test with a transient error would sleep 2 s for real** _(Subagents #1–#6)_: mechanical (M5).
- **[Step 6] The concurrent-press test yields on the wrong press** _(Subagents #2, #5)_: mechanical (M7).
- **[Step 6] No test shows the Retry press files as a fail-closed re-filing** _(Subagent #5)_: pass1-DD-5.
- **[Step 7] DD-12 premise is false for discord.py 2.7.1** _(Subagents #1, #2)_: discord.http has no token routes; webhook/interaction routes log only the webhook id. pass1-DD-1.
- **[Step 2] Rate-limited response with no usable wait header retries after 1 s/2 s, against GitHub's "wait at least one minute"** _(Subagent #6)_: pass1-DD-3.
- **[Step 5] Filing-level re-run on a rate-limited (incl. over-cap) error contradicts DD-10** _(Subagents #1, #6)_: pass1-DD-2.
- **[Step 5] Retries can outlive the File press's 15-minute followup token** _(Subagents #1, #2, #6)_: pass1-DD-4.

#### Minor (nice to fix)
- **[Step 1] 3-tuple conversion misses parametrized/inline tuples and builder annotations** _(Subagents #1, #4)_: M4.
- **[Step 6] RetryView never stores `retry`/`issue_type`; "no custom_id" is unassertable; signatures differ from PreviewView** _(Subagents #1, #2, #4, #5, #6)_: M6.
- **[Step 8] Two README Known-limits bullets become false; CLAUDE.md's logging rule doesn't name the Retry view** _(Subagents #1, #4, #6)_: M8.
- **[Step 5] Stale docstrings, unspecified import placement, unpinned sleep count** _(Subagents #4, #5)_: M9.
- **[Step 6] `_report_error` imported across modules as a private name** _(Subagent #4)_: pass1-DD-6.
- **[Step 6] Pressed error post keeps "Press **Retry**" text with no button** _(Subagent #2)_: pass1-DD-7.
- **[Step 7] Test file naming and global logger cleanup** _(Subagents #4, #5)_: moot (Step 7 dropped by pass1-DD-1).

#### Descriptive (deferred to final cleanup)
- Stored test counts; Step 3 Red already green after Step 2; a duplicated FILING_ERROR_REPLY pin; a test name contradicting its input; prose notes on duplicate-post-after-landed-send, late-landing create after the re-filing lookup, startup-check retry time, and RetryView lifetime vs archived threads.

### Verification Gaps
- **Step 6**: the Retry press's re-filing mode had no check of what reaches GitHub (pass1-DD-5 adds `test_retry_press_lookup_failure_fails_closed`).

### To-Do: Mechanical Fixes (auto-applied)
- [x] M1 Step 2: list and rework the seven existing single-failure tests (script MAX_ATTEMPTS failures, recording sleep) _(applied by fixing subagent)_
- [x] M2 Step 2: per-attempt reset of status/data/headers/flag; every raise `from None` outside the except _(applied by fixing subagent)_
- [x] M3 Steps 2–3: side_effect lists start with token_response(); counts by URL include the mint _(applied by fixing subagent)_
- [x] M4 Step 1: name the builders, annotations, parametrized and inline tuples to convert _(applied by fixing subagent)_
- [x] M5 Step 5: update test_filing_hook_failure_without_thread_replies_error_on_summary to inject sleep and expect the re-run _(applied by fixing subagent)_
- [x] M6 Step 6: RetryView stores `_retry`/`issue_type`; assert `retry_button.is_persistent()` is False; PreviewView-style signatures _(applied by fixing subagent)_
- [x] M7 Step 6: concurrent-press test yields on the first press's ack _(applied by fixing subagent)_
- [x] M8 Step 8: rewrite the two README bullets; CLAUDE.md logging rule names the Retry-view handler _(applied by fixing subagent)_
- [x] M9 Steps 2/5: docstrings, import placement, pinned sleep count _(applied by fixing subagent)_

The nine clusters were applied by one fixing subagent in sequence (one plan file; parallel fixers would race), each with its own dry-run against the repo's tests.

### Design Decisions (awaiting user input)

#### pass1-DD-1: [Step 7] DD-12's premise is false
**Context:** discord.py 2.7.1's discord.http has no token-bearing route; interaction and webhook routes go through discord.webhook.async_, whose 429 WARNING logs the webhook id only. The filter would never redact anything.

| # | Option | Trade-off |
|---|---|---|
| 1 | Drop Step 7 | No dead code; invariant 2 already holds |
| 2 | Keep as defense-in-depth | Guards a hypothetical future discord.py; guards no current line |

**Labels:** kind=dd category=security-safety reversible=yes rework=low · Recommended: none (asked)

**Chosen:** Drop Step 7 (asked; dd-261117-055)

#### pass1-DD-2: [Step 5] Filing-level re-run on rate-limited errors
**Context:** `transient` includes `rate_limited`, so an exhausted or over-cap rate limit triggers one re-filing 2 s later, contrary to DD-10's "stop and show Retry".

| # | Option | Trade-off |
|---|---|---|
| 1 | Re-run only for transport errors and 5xx | Matches DD-10; one more condition |
| 2 | Also re-run on rate-limited | One uniform rule; one extra failed lookup before the button |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Also re-run on rate-limited (asked; dd-261117-056). Keep `transient` as specified, and say in Step 5 that an over-cap or exhausted limit costs one extra (fail-closed) lookup before the Retry button.

#### pass1-DD-3: [Step 2] Rate limit with no usable wait header
**Context:** GitHub: with no `retry-after` and no `x-ratelimit-reset`, wait at least a minute; the plan backed off 1 s/2 s.

| # | Option | Trade-off |
|---|---|---|
| 1 | Fail at once, show Retry | No hammering, no long block; the reporter retries later |
| 2 | Wait 60 s, then retry | Follows guidance; up to 120 s of blocking per request |
| 3 | Keep 1 s / 2 s | Departs from the guidance |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: none (asked)

**Chosen:** Fail at once, show Retry (asked; dd-261117-057). A rate-limited response whose wait is unknown or ≤ 0 raises `GitHubError(stage, status, rate_limited=True)` with no sleep, like a wait over MAX_RETRY_WAIT.

#### pass1-DD-4: [Step 5] Worst-case retries outlive the 15-minute followup token
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept, add a note | Rare; only SUBMITTED_REPLY is lost (logged) |
| 2 | Send SUBMITTED_REPLY before filing | Changes the reply's meaning; test churn |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Accept, add a note (asked; dd-261117-058)

#### pass1-DD-5: [Step 6] Prove the Retry press files as a fail-closed re-filing
| # | Option | Trade-off |
|---|---|---|
| 1 | Add test_retry_press_lookup_failure_fails_closed | Checks what reaches GitHub |
| 2 | Monkeypatch file_candidate and assert refiling=True | Checks the argument, not the behavior |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Add test_retry_press_lookup_failure_fails_closed (assumed: dd-policy, dd-261117-059)

#### pass1-DD-6: [Step 6] Share `_report_error` with bot.py
| # | Option | Trade-off |
|---|---|---|
| 1 | Rename to public `report_error` | Follows the `discord_error_fields` precedent; two call sites change |
| 2 | Import the private name | Breaks the module-private convention |

**Labels:** kind=dd category=naming-structure reversible=yes rework=low · Recommended: 1

**Chosen:** Rename to public `report_error` (asked; dd-261117-060)

#### pass1-DD-7: [Step 6] Retry press acknowledgement
| # | Option | Trade-off |
|---|---|---|
| 1 | Edit to fixed "Retrying…" text and remove the button | Matches file_button's FILING_REPLY pattern |
| 2 | Only remove the button | Leaves "Press **Retry**" with no button |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1

**Chosen:** Show "Retrying…" (asked; dd-261117-061)

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 read bot.py/intake.py import graph; no cycle from importing intake into bot (bot already imports intake) |
| Type annotations | [x] | #1, #4: Transport, builders, RetryView signatures |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced File press → filing → _post_outcome → Retry press |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 read conftest and all affected test files; ran probes |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6: Transport shape, GitHubError, _post_outcome, file_candidate signatures |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4: no new config keys or dependencies (aiohttp already pinned) |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4: constants, test names, private-name import (pass1-DD-6) |

## Review — 2026-11-17 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/retry-rate-limits/retry-rate-limits.md blob d6f6384cd90925c276ae110e6e20fa4d0a62e9b7

### Summary
Clean: 0 critical, 0 major. All six reviewers PASS and re-verified pass 1's fixes and decisions against the source. Remaining minor items are mechanical test-setup clarifications, a SMOKE-TEST.md row Step 7 must update, and four minor decisions. Ready to proceed after this pass's fixes.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 2 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 2 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 2 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 3 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 6 minor |

### Findings

#### Minor (nice to fix)
- **[Step 6] Red setup offers recording_github, whose only failure is now auto-recovered; the RuntimeError on_error test doesn't say how a view exists** _(Subagents #1, #2, #5, #6)_: mechanical.
- **[Step 1] aiohttp_transport's return annotation and docstring still describe the 2-tuple** _(Subagents #1, #6)_: mechanical.
- **[Step 7] docs/SMOKE-TEST.md's lookup troubleshooting row states pre-F13 behaviour** _(Subagents #4, #6)_: mechanical.
- **[Step 6] `report_error` out of alphabetical order in bot.py's intake import block** _(Subagent #4)_: mechanical.
- **[Step 2] Several Red tests are regression guards that already pass at Red** _(Subagent #5)_: mechanical (say so).
- **[Step 8] Expected-empty grep gates exit 1 on their passing result** _(Subagent #5)_: mechanical.
- **[Step 2] `now` passed to `_retry_wait` has no stated source** _(Subagent #6)_: mechanical (`self._clock()`).
- **[Step 6] A press after stop() gets no bot reply** _(Subagent #2)_: pass2-DD-1.
- **[Step 5] `_post_outcome` tests would be the suite's first private import** _(Subagent #4)_: pass2-DD-2.
- **[Step 2] test_401_still_drops_token_once is unspecified and duplicates existing 401 tests** _(Subagent #6)_: pass2-DD-3.
- **[Step 5] A Discord transport error in open_thread still aborts filing** _(Subagent #6)_: pass2-DD-4.

#### Descriptive (deferred to final cleanup)
- Step 5's filing_hook docstring describes Step 6's button; Step 6 lists an assertion Step 5 already removed; aiohttp_transport docstring.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 6 Red setup: a failing fake (`fake_github(GitHubError("issue", 422))`, non-transient) produces the error post; the on_error test gets its view from a first failed filing, then makes the retry raise RuntimeError _(applied by fixing subagent)_
- [x] Step 1: aiohttp_transport return annotation and docstring _(applied by fixing subagent)_
- [x] Step 7: update docs/SMOKE-TEST.md's lookup row _(applied by fixing subagent)_
- [x] Step 6: import order _(applied by fixing subagent)_
- [x] Step 2: mark regression guards as passing at Red _(applied by fixing subagent)_
- [x] Step 8: guard expected-empty grep gates _(applied by fixing subagent)_
- [x] Step 2: `now = self._clock()` _(applied by fixing subagent)_

### Design Decisions (awaiting user input)

#### pass2-DD-1: [Step 6] A press after stop() gets no bot reply
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept, add a note | Matches file_button's ordering; nothing files twice |
| 2 | stop() after the ack | Presses during the ack get RETRY_ALREADY_REPLY; departs from precedent |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Accept, add a note (asked; dd-261117-062)

#### pass2-DD-2: [Step 5] Testing `_post_outcome` without a private import
| # | Option | Trade-off |
|---|---|---|
| 1 | Drive the tests through `filing_hook(github, sleep=...)` | No private import; matches the suite's convention |
| 2 | Import `_post_outcome` in tests | First private import in the suite |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Drive the tests through filing_hook (assumed: dd-policy, dd-261117-063)

#### pass2-DD-3: [Step 2] Underspecified 401 Red test
| # | Option | Trade-off |
|---|---|---|
| 1 | Drop it; the existing `test_*_401_drops_*` tests pin that a 401 isn't retried | No duplicate |
| 2 | Specify it fully | Duplicates existing coverage |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Drop it (assumed: dd-policy, dd-261117-064)

#### pass2-DD-4: [Step 5] Discord transport error in open_thread aborts filing
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept, add a note | Outside DD-7's scope; unchanged from today |
| 2 | Catch aiohttp/timeout errors in open_thread | Filing proceeds; one more test |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Accept, add a note (asked; dd-261117-065)

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

Pass 2 clean (0 critical, 0 major executable/external). Plan is ready for implementation.

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3, #4: bot.py imports, report_error rename |
| Type annotations | [x] | #1: aiohttp_transport annotation |
| Error handling (status codes, exceptions, user feedback) | [x] | #2: ViewStore dispatch after stop(); open_thread |
| Test coverage (happy path, sad path, edge cases) | [x] | #5: probes against conftest fakes |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4: no config or dependency change |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 |

### Descriptive cleanup: 14 fixed, 2 dropped

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| docs/SMOKE-TEST.md lookup row becomes false (found in pass 2) | minor | subagent-6:completeness | scoped_too_narrowly | Pass 1 checked README/CLAUDE.md docs only | maybe | not logged (review_due: critical only) |

### Plan-Creator Misses
| Finding | Severity | Unit | Ledger id |
|---|---|---|---|
| Research claimed discord.http logs token URLs (DD-12 premise false) | major | research-3:chain-tracing | not logged (review_due: critical only) |

Step 7: skipped (nested; caller reviews assumed decisions)
