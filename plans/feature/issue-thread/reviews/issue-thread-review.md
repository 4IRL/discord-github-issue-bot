# Review: Thread per tagged message (F2)

## Review — 2026-10-18
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/issue-thread/issue-thread.md blob cdb2564f04c990d5875f51446249952a085a2c57

### Summary
The plan's API claims, signatures and step ordering hold against the code and discord.py 2.7.1: a scratch simulation was green at every step's commit. It needed changes because two Step 3 Red tests already passed before Green, error handling after the guard (`thread.send`, the 160004 fetch) was unspecified, the new log fields went beyond CLAUDE.md's wording, and the thread APIs had never been exercised. All four are resolved by DD-1–DD-7.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 2 major, 3 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 1 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 5 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 1 major, 5 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 2 major, 4 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 4 minor |

### Findings

#### Major (should fix)
- **[Step 3] Red gate unsatisfiable: two new tests pass before Green** _(Subagents #1, #3, #5, #6)_: `test_default_hook_skips_message_with_thread` and `test_malformed_hint_skipped_when_thread_fails` pass against Step 2's code (verified in-repo). → DD-1.
- **[Steps 1, 3] Failures after the guard unspecified and untested** _(Subagents #6; #1, #2, #5 minor)_: `thread.send` (missing Send Messages in Threads) and `fetch_channel` on the 160004 path escape to `on_error`, without the status/code Decision (a) promises. → DD-2.
- **[Steps 1, 3] New log fields exceed CLAUDE.md's literal logging rule** _(Subagent #4)_: thread_id, caught-exception type, HTTP status and Discord code. → DD-3.
- **[Step 3] Default candidate hook's thread-failure branch untested** _(Subagent #5)_: an unguarded `thread.id` would crash exactly when permissions are missing. → DD-4.
- **[Step 1] Thread API calls never exercised against Discord** _(Subagent #1, external)_: the 160004 code and fetch-by-message-id come from documentation. → DD-5.

#### Minor (nice to fix)
- **[Step 3] `test_custom_on_malformed_hook` uses the well-formed default message** _(#1)_.
- **[Step 3] Missing test imports (`discord`, `MalformedTag`, `format_hint`)** _(#3, #4)_.
- **[Step 3] New hook signatures lack type hints** _(#4)_.
- **[Steps 3, 5] Expected-empty greps exit 1** _(#3)_.
- **[Step 5] Log grep can't show multi-line log-call arguments; misses `log_problem`** _(#4, #5)_.
- **[Step 4] README step has no verification** _(#5)_.
- **[Step 2] Malformed log says "ignored" though the bot now replies; hint not logged** _(#6)_. → DD-6.
- **[Step 5] Manual-check relay has no carrier through /run-plan's summary** _(#3)_. → DD-7.

#### Descriptive (deferred to final cleanup)
- Stored test count (153) and file count in Steps 1 and 5 and Research Findings _(#1, #3, #4, #5, #6)_. Applied with the mechanical batch.
- Step 2 Green prescribed `candidate` while asking for the local to be renamed `result` _(#3)_. Applied.
- How F5/F7 reach the thread after replacing the default hook _(#4)_. Applied.
- Manual check lacks test-channel config and cleanup note _(#6)_. Applied.

### Verification Gaps
- **Step 4**: added greps for the removed "F2 will …" sentences and the two permission names.

### To-Do: Mechanical Fixes (auto-applied)
- [x] `test_custom_on_malformed_hook` uses `make_message("!bug\nBody: x")` _(applied by fixing subagent)_
- [x] Step 3 Red lists its imports; Step 1 Red states the import grouping _(applied by fixing subagent)_
- [x] Step 3 Green hook signatures fully annotated _(applied by fixing subagent)_
- [x] `|| true` on the expected-empty greps (Step 3 `log_candidate`, Step 5 invariant 1) _(applied by fixing subagent)_
- [x] Step 5 log grep uses `-A6` and covers `log_problem` _(applied by fixing subagent)_
- [x] Step 4 verification box added _(applied by fixing subagent)_
- [x] Step 2 Green `result` local made consistent _(applied by fixing subagent)_
- [x] Descriptive: stored counts removed, F5/F7 thread-reuse sentence, manual-check config/cleanup note _(applied by fixing subagent)_

Note: the mechanical fixes were applied by one sequential fixer rather than one per finding, since all edit the same plan file.

### Design Decisions (awaiting user input)

#### DD-1: [Step 3] Two Red tests pass before Green
**Context:** The Red gate can't be met as written, and the two tests can't fail on a wrong Green.

| # | Option | Trade-off |
|---|---|---|
| 1 | Strengthen both | Skip test asserts INFO `thread_id=5`; failure test asserts one ERROR record (Forbidden, 99), no send, no fetch. Both fail in Red. |
| 2 | Reword the gate | Keep as regression guards; less coverage |

**Chosen:** 1 — Strengthen both.

#### DD-2: [Steps 1, 3] Failures after the guard
**Context:** `thread.send` and the 160004 fetch can raise `HTTPException` subclasses that `open_thread` doesn't catch.

| # | Option | Trade-off |
|---|---|---|
| 1 | Catch and log like create_thread | Uniform type/status/code/ids log; fetch failure returns None; two more tests |
| 2 | Let on_error handle it | Simpler; loses status/code |

**Chosen:** 1 — Catch and log like create_thread.

#### DD-3: [Steps 1, 3] Log fields vs CLAUDE.md
**Context:** CLAUDE.md says "issue type, message id and message URL only".

| # | Option | Trade-off |
|---|---|---|
| 1 | Widen CLAUDE.md wording | Keeps the permission diagnostic; fold-back extends Standing invariant 2 |
| 2 | Narrow the logs | Rule unchanged; loses the 50013 diagnostic |

**Chosen:** 1 — Widen CLAUDE.md wording.

#### DD-4: [Step 3] Default hook thread-failure test
| # | Option | Trade-off |
|---|---|---|
| 1 | Add `test_default_hook_logs_when_thread_fails` | Pins the None branch through the hook |
| 2 | Accept the gap | Relies on Step 1's isolated test |

**Chosen:** 1 — Add the test.

#### DD-5: [Step 1] Unexercised thread APIs
**Context:** No live call or repo precedent; live calls need the owner's per-run go-ahead.

| # | Option | Trade-off |
|---|---|---|
| 1 | Extend owner manual checks | Code as planned; duplicate path flagged documentation-derived |
| 2 | Use `message.fetch_thread()` + manual checks | discord.py's documented recovery call (wraps `guild.fetch_channel(self.id)`); mocks change |
| 3 | Probe-first box | Blocks /run-plan's autonomous run |

**Chosen:** 2 — Use `message.fetch_thread()`, keep the 160004 assumption flagged unverified, and extend the owner manual checks with the duplicate path.

#### DD-6: [Step 2] Malformed-path logging
| # | Option | Trade-off |
|---|---|---|
| 1 | Reword + log the hint | Accurate logs; test assertion updates |
| 2 | Keep as is | No change |

**Chosen:** 1 — Reword to `malformed …` and log a posted hint by type and ids.

#### DD-7: [Step 5] Manual-check relay
| # | Option | Trade-off |
|---|---|---|
| 1 | Address the orchestrator | Explicit carrier line read by /run-plan |
| 2 | Accept the gap | No change |

**Chosen:** 1 — Address the orchestrator.

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 read test_bot.py, bot.py, pyproject.toml; scratch simulation |
| Type annotations | [x] | #1, #4 read bot.py, handler.py, discord/message.py |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced on_message → hooks → create_thread/fetch/send → on_error |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 ran throwaway tests against current code |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 checked candidate_from_message's only caller and F1 contract |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4: no new packages or env keys |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 read CLAUDE.md, README, META-PLAN |

## Review — 2026-10-18 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/issue-thread/issue-thread.md blob 987d1adbc9b8737e8252ec30b5cb6dbecf5722ab

### Summary
DD-1–DD-7 were re-verified against the source and hold, with no cross-fix regressions. Four reviewers simulated the whole plan on scratch copies with the repo venv. Every Red failed for its stated reason and every Green was green at its commit (153 → 162 → 162 → 171). Two majors remained: the CLAUDE.md widening landed after the code that relies on it, and the owner's duplicate-path check could not reach the 160004 path. Both are resolved by DD-8 and DD-9.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 2 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 1 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 4 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 2 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 4 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 1 major, 3 minor |

### Findings

#### Major (should fix)
- **[Steps 1, 4] CLAUDE.md widening lands after the code that relies on it** _(Subagent #3)_: /next-step-taker's per-step CLAUDE.md-compliance reviewers would flag or strip the new log fields at Steps 1 and 3. → DD-8.
- **[Manual checks] Duplicate-path check never reaches 160004 → fetch_thread** _(Subagent #6, external)_: a restart re-caches active threads, and a fetched message carries its thread. → DD-9.

#### Minor (nice to fix)
- **[Step 5] Fold-back relay had no carrier past the step report; missed the F1 contract and Baseline sentences** _(#3, #4, #6)_. Mechanical: moved into Manual checks with the orchestrator carrier.
- **[Step 1] New untracked files invisible to next-step-taker's review (`git diff --name-only`)** _(#3)_. Mechanical.
- **[Step 5] Conditional "Investigate and fix" box lacked a tick-as-N/A form** _(#3)_. Mechanical.
- **[Step 5] Log gate would trip on the pre-existing `configuration error: %s` line** _(#5)_. Mechanical exemption.
- **[Steps 1, 2] DD-6 reword and 160004 success-path silence unpinned** _(#5)_. → DD-10.
- **[Step 1] Format-hint text unpinned** _(#6)_. → DD-11.
- **[Step 1] Thread-name length counted in code points; emoji counting unverified** _(#2, external)_. → DD-12.

#### Descriptive (deferred to final cleanup)
- README "is dropped" wording _(#1, #3, #4, #5, #6)_. Applied with the mechanical batch (whole bullet rewritten, plus a grep gate).
- Research Findings omitted `fetch_thread`'s `ValueError`/`InvalidData` _(#1)_. Applied.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 4 rewrites the whole README malformed bullet; `grep -n 'is dropped' README.md || true` gate _(applied by fixing subagent)_
- [x] Fold-back bullet moved into Manual checks, extended to F1 contract and Baseline sentences; Step 5 copies it _(applied by fixing subagent)_
- [x] Step 1 names its untracked new files to reviewers _(applied by fixing subagent)_
- [x] Step 5 "(none to fix)" tick form _(applied by fixing subagent)_
- [x] Step 5 ConfigError log exemption _(applied by fixing subagent)_
- [x] Research Findings: fetch_thread non-HTTP exceptions _(applied by fixing subagent)_

### Design Decisions

#### DD-8: [Steps 1, 4] Placement of the CLAUDE.md widening
| # | Option | Trade-off |
|---|---|---|
| 1 | Move to Step 1's first box | Rule and first dependent code land in one commit |
| 2 | Keep in Step 4 + reviewer note | Relies on the executor passing the note on |

**Chosen:** 1 — Move to Step 1's first box.

#### DD-9: [Manual checks] Reaching the 160004 path
| # | Option | Trade-off |
|---|---|---|
| 1 | Archived thread + `PartialMessage` from an owner REPL | Deterministic; `PartialMessage.thread` misses archived threads |
| 2 | Two racing instances | Non-deterministic |

**Chosen:** 1 — Archived thread + PartialMessage.

#### DD-10: [Steps 1, 2] Pin reword and recovery silence
**Chosen:** Pin both.

#### DD-11: [Step 1] Format-hint text
**Chosen:** Pin the exact text; the test asserts equality for BUG.

#### DD-12: [Step 1] Emoji thread-name length
**Chosen:** Accept the risk (the rejection is caught and logged by status/code); one-line note in the Thread name decision.

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

## Review — 2026-10-18 (Pass 3)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/issue-thread/issue-thread.md blob cee5173740df776a4a508e87837c93295c22cf0f

### Summary
Clean pass: 0 critical and 0 major findings, so the plan is ready for implementation. All six reviewers re-verified DD-1–DD-12 against the source and discord.py 2.7.1 and found no cross-fix regressions. Independent whole-plan simulations in separate scratch folders with the repo venv were green at every step commit (153 → 162 → 162 → 171), and every Red failed for its stated reason. Two reviewers briefly shared one scratch folder; both re-ran in their own folders, and their reported results come from those runs.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 0 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 1 minor (descriptive) |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 0 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 0 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 1 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 2 minor (descriptive) |

### Findings

#### Minor (nice to fix)
- **[Step 5] Log-argument gate exempted only the ConfigError line** _(#5)_: the pre-existing `connected as %s` and `log_problem("%s", problem)` calls also needed an exemption.

#### Descriptive (deferred to final cleanup)
- Two Step 1 log-asserting tests didn't say they take `caplog` _(#2)_.
- Duplicate-path manual check: no REPL recipe, ordering or cleanup _(#6)_.
- README Status rewrite didn't name the stale "Until F2 (clarifying thread)" clause, and no gate covered it _(#6)_.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 5 exemption extended to `connected as %s` and `log_problem` _(applied inline by orchestrator)_

### Descriptive cleanup: 3 fixed, 0 dropped

### Verdict
[x] Ready to proceed as-is
[ ] Proceed after minor fixes
[ ] Requires changes before proceeding

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| CLAUDE.md widening placed in Step 4, after the code that relies on it (Pass 2) | major | step-5f:dd-application | fix_regression | The DD-3 application put the rule edit in the docs step without simulating next-step-taker's per-step CLAUDE.md-compliance reviewers | possibly | not logged (plan-reviewer in review_due: only critical misses are logged) |
| Duplicate-path manual check could not reach 160004 (Pass 2) | major | step-5f:dd-application | fix_regression | The DD-5 application wrote a manual check without tracing discord.py's thread cache on restart and `Message._thread` | possibly | not logged (review_due) |

### Plan-Creator Misses
| Finding | Severity | Unit | Ledger id |
|---|---|---|---|
| Plan asserted the new log fields followed "CLAUDE.md rule, Standing invariant 2"; the rule's wording did not cover them (Pass 1, #4) | major | step-2b:complexity-gate | not logged (plan-creator in review_due: only critical misses are logged) |

skill-misses: review due for plan-reviewer (evaluation runs left open misses: 13 run(s), 8 input(s), 5 miss(es); evidence score 9 over 3 input(s); 5 open) -> run /skill-improver plan-reviewer
skill-misses: review due for plan-creator (collecting window closed: 7 run(s), 7 input(s), 3 miss(es); evidence score 7 over 3 input(s); 3 open) -> run /skill-improver plan-creator
