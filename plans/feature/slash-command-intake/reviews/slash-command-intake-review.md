# Review: Slash-command intake (F10)

## Review — 2026-10-20
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/slash-command-intake/slash-command-intake.md blob 1afe2bbce579f28ce763711b4e82617d5d83124e

### Summary
The design is sound and grounded in discord.py 2.7.1's source, but the plan needs changes before
implementing. Several gates could not pass as written: the removal grep matched the rewritten
`test_intents`, `_scheduled_task` was called with two arguments instead of three, and unscoped
greps matched stale `.pyc` files. Two smoke-test hazards were also found: `.env` kept the live
guild, so a test run would sync `/bug` and `/feature` into the real server, and README's new
end-state facts had no gate. All of these were fixed mechanically. Ten design decisions remain.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 2 major, 8 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 5 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 2 major, 5 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 1 major, 8 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 4 major, 7 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 10 minor |

### Findings

#### Major (should fix)
- **[Step 5] Removal grep can never print nothing** _(#1, #3, #5)_: `message_content` matches the rewritten `test_intents`.
- **[Step 5] `modal._scheduled_task(interaction, [])` raises TypeError** _(#2, #4, #5, #6)_: the 2.7.1 signature is `(interaction, components, resolved)`.
- **[Step 5] test_issues.py keeps importing the deleted `candidate_from_message`** _(#3)_: this would make collection fail.
- **[Step 6] README end-state facts have no gate** _(#5)_: the `applications.commands` scope and the dropped Message Content intent are never checked.
- **[Step 6] Smoke-test `.env` keeps the live guild id** _(#6)_: a test run would sync the commands into the real 4irl server.
- **[Step 3] Live Discord behavior is unprobed** _(#1)_: guild sync, Label modals and the thinking defer are untested live → DD-1.
- **[Step 3] No success-path test through the real `filing_hook`** _(#5)_ → DD-7.

#### Minor (nice to fix)
- `record_texts`/`assert_no_member_text` were needed in test_intake but lived in test_bot (#3, #4, #5).
- The fixture was named `interaction_factory`, but tests call `make_interaction` (#5).
- The refusal log assertion was hard-coded to 556 in a test parametrized over None (#4, #5).
- Step 5 named the threads.py import by its pre-Step-1 text (#1, #3).
- Dead imports were missing from the lists: `collections.abc` in bot.py (#1, #3), and `pytest`/`IssueCandidate`/`IssueType` in the tests (#3).
- The end-to-end test must pass `on_candidate` to the constructor (#2).
- The CLAUDE.md log-rule wording contradicted the new handlers' logs (#4, #6).
- The exc_info gate matched the existing `sys.exc_info()` (#4, #5, #6).
- Unscoped greps matched `.pyc` files (#5).
- Docstrings for the new functions were unspecified (#4).
- example.env has no `DISCORD_GUILD_ID` comment to extend (#6).
- The ROADMAP As-of date was not bumped (#6).
- SMOKE-TEST L10/L166/L172 still assumed the long-title check (#6).
- The README Known-limits edit was ambiguous (#6).
- The two-process wording was unverified (#6).
- Seven minor design decisions follow below as DD-2…DD-10.

#### Descriptive (deferred to final cleanup)
- Stored derived test counts in Research Findings (#1, #5).
- "Unannotated interaction" vs the annotated closure (#1).
- "One-sentence intro" label (#6).

### To-Do: Mechanical Fixes (auto-applied)
_(Applied inline by the orchestrator in one pass: the ~20 mechanical findings overlapped heavily across subagents.)_
- [x] Step 5 removal grep: dropped `message_content`, added `--include='*.py'`, added a separate `issue_bot`-only `message_content` gate.
- [x] Step 5: `await modal._scheduled_task(interaction, [], {})`.
- [x] Step 5 test_issues: drop the `candidate_from_message` and `MessageFactory` imports.
- [x] Step 6 + 7: README gates (`applications.commands` present, `message content` absent) and the SMOKE-TEST `DISCORD_GUILD_ID` gate.
- [x] Step 6 SMOKE-TEST: test-guild `DISCORD_GUILD_ID` override, L10-11 counts, L166/L172 record and teardown, L126 two-process wording.
- [x] Step 3: moved `record_texts` and `assert_no_member_text` to conftest; renamed the fixture to `make_interaction`; parametrized the refusal log; docstrings for the new functions; CandidateHook prose.
- [x] Step 4: the end-to-end test builds `IssueBot(config, on_candidate=hook)`.
- [x] Step 5: threads.py import name, `collections.abc` dead import, extended test dead-import lists.
- [x] Step 6: CLAUDE.md log-rule wording, the example.env comment line, the ROADMAP As-of date, the README Known-limits replacements (plus the rollback note).
- [x] Step 1/5/7: no exact test counts in gates; `--include='*.py'` on recursive greps; exc_info gate → `exc_info=|%r|logger\.exception` prints nothing.

### Design Decisions (resolved 2026-10-20)

#### DD-1: [Steps 3-4] Live Discord behavior is never probed before implementing
**Context:** Guild sync, type-18 Label modals, `defer(ephemeral=True, thinking=True)` and non-pinging mentions are verified only against discord.py's source, offline. Agents may not touch live Discord.
| # | Option | Trade-off |
|---|---|---|
| 1 | Owner confirms at the merge gate (Owner checks) | No delay; a live surprise means rework on the same branch before merge |
| 2 | Owner probes a minimal command first, then implement | Earliest signal; blocks implementation on a manual run |

**Chosen:** Option 1: owner confirms at the merge gate (Owner checks / smoke test).

#### DD-2: [Steps 3/5] Fake `is_done` never flips after `defer`
| # | Option | Trade-off |
|---|---|---|
| 1 | `defer`'s side effect sets `is_done` to True in the fixture | Models production; the end-to-end error test asserts `followup.send` |
| 2 | The end-to-end test sets `is_done` itself | Smaller fixture; every such test must remember it |

**Chosen:** Option 1: the fixture's `defer` side effect flips `is_done()` to True.

#### DD-3: [Step 5] `make_candidate` fixture hard-binds `config.target`
| # | Option | Trade-off |
|---|---|---|
| 1 | Add a `target` keyword defaulting to `config.target` | One fixture serves the custom-target test |
| 2 | That one test builds `IssueCandidate` directly | Fixture stays minimal; one test differs |

**Chosen:** Option 1: `make_candidate(target=...)`, defaulting to `config.target`.

#### DD-4: [Step 3] None-channel failed post has no log line
| # | Option | Trade-off |
|---|---|---|
| 1 | ERROR `could not post %s summary interaction_id=%s: no channel`, pinned by the test | The operator sees it |
| 2 | Silent (the refusal stage already catches a None channel) | Less code; an unlogged failure |

**Chosen:** Option 1: ERROR `could not post %s summary interaction_id=%s: no channel`, pinned by the test.

#### DD-5: [Steps 3-4] Error handlers drop HTTP status and code for escaping Discord errors
| # | Option | Trade-off |
|---|---|---|
| 1 | Add `status=%s code=%s` when the (original) error is an `HTTPException` | Tells 10062 from 50013; still text-free |
| 2 | Type only | Simplest; less diagnosable |

**Chosen:** Option 1: both handlers log `status=%s code=%s` via `discord_error_fields` (None for non-HTTP errors).

#### DD-6: [Step 6] Drop Read Message History from the invite permissions?
| # | Option | Trade-off |
|---|---|---|
| 1 | Keep it | Safe for `fetch_thread`/`create_thread`; one extra permission |
| 2 | Drop it and verify in the smoke test | Least privilege; may fail live |

**Chosen:** Option 1: keep Read Message History.

#### DD-7: [Step 3] No success-path test through the real `filing_hook`
| # | Option | Trade-off |
|---|---|---|
| 1 | Add `test_submit_files_issue_through_filing_hook` | Thread on the summary plus `create_issue` with an author line linking the summary URL; covers the end-state fact directly |
| 2 | Accept the composed unit coverage | Fewer tests |

**Chosen:** Option 1: add `test_submit_files_issue_through_filing_hook`.

#### DD-8: [Step 5] No test pins that the message listeners are gone
| # | Option | Trade-off |
|---|---|---|
| 1 | Add `assert not hasattr(IssueBot, "on_message")` | One line; guards against a reintroduced handler |
| 2 | Rely on the grep | No test |

**Chosen:** Option 1: add `test_no_message_listeners`.

#### DD-9: [Step 6] ROADMAP Principles/Phase 4 "restart catch-up" lines
**Context:** With slash commands, catch-up of messages posted while the bot was down is impossible. The lines are L115-118 and L235-238, outside the owner-approved capability and phase scope.
| # | Option | Trade-off |
|---|---|---|
| 1 | Edit them in this PR (whole mention, L115-118 and L235-238) | ROADMAP stays true |
| 2 | Leave them; record a deferred follow-up | Stays inside the approved scope; ROADMAP is briefly stale |

**Chosen:** Option 1: edit L115-118 and L235-238 in this PR.

#### DD-10: [Step 3] MODAL_TIMEOUT value and rationale
**Context:** A modal submit is a new interaction with its own 15-minute token, so the comment's rationale is wrong. The timeout only bounds how long discord.py keeps the modal; a slower member's submit fails silently.
| # | Option | Trade-off |
|---|---|---|
| 1 | 30 minutes, comment "bounds discord.py's view store; a slower submit fails in Discord" | Room for long descriptions |
| 2 | 10 minutes, with a corrected comment | Smaller store; risks losing long reports |

**Chosen:** Option 1: 30 minutes (`MODAL_TIMEOUT = 1800`), corrected comment.

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 traced bot/handler/threads/tests imports; no cycle via issue_type/intake |
| Type annotations | [x] | #1 checked callback/Modal signatures against 2.7.1 |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced tree/modal on_error and every HTTPException site |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 mapped each Expected-end-state fact to a test or gate |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 checked F1/F2/F5 kept contracts and the smoke-test guild |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 read requirements, example.env, pyproject (no linter) |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 checked log rules and fixture naming |

## Review — 2026-10-20 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/slash-command-intake/slash-command-intake.md blob ee680bac9d98e2bfaa1875804024697b8a6706e5

### Summary
All of Pass 1's fixes and DD choices were re-verified against the code and hold. Three new majors
were found. One is a cross-fix regression: the CLAUDE.md log rule was written before DD-5 and
contradicts DD-5's status/code fields. The other two need design calls: the modal error handler's
unguarded `send_message` branch, and the persistent guild-command registration's revert path. The
plan is ready once those are applied.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 4 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 2 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 4 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 1 major, 4 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 1 major, 3 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 1 major, 6 minor |

### Findings

#### Major (should fix)
- **[Step 6] CLAUDE.md log rule contradicts DD-5 and the guild-id log lines** _(#4, #6)_: a fix regression from Pass 1's rewording.
- **[Step 3] Modal on_error's `send_message` branch is unguarded and untested** _(#5)_ → DD-11.
- **[Step 6] No working revert path for the persistent guild commands** _(#6)_: the Developer Portal claim was wrong → DD-12.

#### Minor (nice to fix)
- Step 1 repoint dropped `MalformedTag` from test_bot/test_handler (#1, #3).
- Helpers moved to conftest only after first use (#1, #3).
- `IntakeModal` was used before the to-do defining it (#3).
- The ported modal-error test would filter its log out through `bot_records` (#1, #4, #6).
- Missing test imports: `app_commands`, `IntakeModal`, `INTAKE_ERROR_REPLY`, `Mock`, `FiledIssue`, `SimpleNamespace`, `TargetConfig` (#2, #3, #4).
- "Exit 1 is the pass" note on empty-grep gates (#1, #5).
- README/SMOKE-TEST `!bug|!feature` gate (#5).
- SMOKE-TEST "What it writes" lacked the command registration (#6).
- Owner checks lacked the private-defer check and the Send Messages re-invite (#6).
- ROADMAP "tag" wording outside scope was left implicit (#4, #6).
- Two minor design decisions → DD-13, DD-14.

### To-Do: Mechanical Fixes (auto-applied)
- [x] CLAUDE.md log rule: guild ids, plus status/code for Discord API errors in the command/modal handlers.
- [x] Step 1: keep `MalformedTag` imported from `issue_bot.tags` in test_bot/test_handler until Step 5; global "empty grep exits 1" note.
- [x] Step 2: `SimpleNamespace` import in test_handler.
- [x] Step 3: the helper move (with `ISSUE_URL`), `Mock` and `FiledIssue` imports go in the first to-do; the modal-shape to-do now precedes the command callback and creates `intake.py`'s scaffolding; prose fixes.
- [x] Step 4: `from discord import app_commands` in test_bot; case-list formatting.
- [x] Step 5: the modal-error test reads `issue_bot.intake` records; the test_bot import list; `make_candidate` imports.
- [x] Step 6/7: README + SMOKE-TEST `!bug|!feature` gate; SMOKE-TEST Startup write bullet; ROADMAP tag-wording note.
- [x] Owner checks: Send Messages re-invite; the private "thinking" check.

### Design Decisions (resolved 2026-10-20)

#### DD-11: [Step 3] Guarding the modal on_error reply
| # | Option | Trade-off |
|---|---|---|
| 1 | Guard both branches in one try, test each | Explicit; small duplication with `_reply` |
| 2 | Route both through `_reply` branching on `is_done` | One helper; bigger function |

**Chosen:** Option 1.

#### DD-12: [Step 6] Revert path for guild commands
| # | Option | Trade-off |
|---|---|---|
| 1 | Remove the app under Server Settings → Integrations / kick the bot | No code; unverified until the smoke teardown |
| 2 | `--clear-commands` flag | Precise; more code |
| 3 | Owner-run API call | No code; manual token handling |

**Chosen:** Option 1 (marked unverified; the smoke-test teardown records the result).

#### DD-13: [Step 3] "Posted" confirmation when filing failed with no thread
| # | Option | Trade-off |
|---|---|---|
| 1 | Leave to F7 (F5 deferred no-thread fallback) | Keeps F5's hook contract |
| 2 | Fix in F10 | Changes `filing_hook`'s contract now |

**Chosen:** Option 1.

#### DD-14: [Step 3] Escape the title's markdown in the summary
| # | Option | Trade-off |
|---|---|---|
| 1 | `discord.utils.escape_markdown(title)` | The bot never renders member markdown (probed: escapes `**`, `[`, leading `#`/`-#`/`>`) |
| 2 | Raw | Members see their formatting |

**Chosen:** Option 1.

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

## Review — 2026-10-20 (Pass 3)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/slash-command-intake/slash-command-intake.md blob 8763025a5722ea64d5a494cc20c690d5735eb539

### Summary
All Pass 2 resolutions hold (DD-11, DD-14 and the Step 3 reordering were re-verified against
discord.py 2.7.1). One major finding: the Owner checks never covered the production cutover's
re-invite and permissions. It is fixed mechanically. Everything else is minor. The pass cap is
reached: the plan is ready to implement.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 1 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 0 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 3 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 5 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 1 major, 3 minor |

### To-Do: Mechanical Fixes (auto-applied)
- [x] Owner checks: live-server re-invite (`applications.commands`), View Channel + Send Messages on the live channel, the post-deploy sync log and a `/bug` check.
- [x] Step 5: no-Body tag maps to `body=""`; `open_issue_thread` stays imported from `issue_bot.bot`; `IssueType` import in test_issues; `CandidateFactory` alias.
- [x] Step 3: `intake.py` imports listed; the "posted" log line's arguments named.
- [x] Step 6: CLAUDE.md log rule *replaces* the old id list and exceptions sentence; gates for the CLAUDE.md log rule, `per-tag` and the example.env comment.
- [x] Step 5: `tagged` grep gate.
- [x] Step 7: fold-back notes for Standing invariant 2 and F8's risk.

### Design Decisions (resolved 2026-10-20)
- **DD-15** CLAUDE.md intro keeps the project goal (fleshed-out issues, roadmap). **Chosen:** keep the goal.
- **DD-16** The dispatch-path modal-error test asserts no member or exception text. **Chosen:** assert.
- **DD-17** A failed filing loses the typed Description. **Chosen:** accept, add a README known limit; F3's preview addresses it.
- **DD-18** F8 multi-container refusal race. **Chosen:** report it for the fold-back into F8's Open risks.

### Verdict
[x] Ready to proceed as-is
[ ] Proceed after minor fixes
[ ] Requires changes before proceeding

Pass 3 complete (hard cap). No unresolved findings remain.

### Descriptive cleanup: 6 fixed, 0 dropped
Research Findings line citations, stored test counts, the "unannotated interaction" wording and the "one-sentence intro" label were fixed. The 11 remaining anchor-lint hits are edit anchors in Steps 1-2. They still match the untouched files at the moment those steps run, so they are kept on purpose.

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| CLAUDE.md log rule contradicted DD-5 | major | step-5f:dd-application | fix_regression | DD application didn't re-sweep an earlier mechanical edit of the same rule | yes | not logged (review_due: critical only) |
| Revert path claimed a Developer Portal UI | major | step-5b:mechanical-fix | fix_regression | Mechanical fix wrote an unverified external claim | yes | not logged (review_due: critical only) |
| Modal on_error send_message branch unguarded | major | subagent-2:full-stack-trace | scoped_too_narrowly | Pass 1 traced only the followup reply branch | maybe | not logged (review_due: critical only) |
| Owner checks missed the production cutover | major | subagent-6:completeness | scoped_too_narrowly | Owner checks were read as test-guild-only | maybe | not logged (review_due: critical only) |

### Plan-Creator Misses
| Finding | Severity | Unit | Ledger id |
|---|---|---|---|
| `Modal._scheduled_task` called with 2 args (2.7.1 needs 3) | major | research-3:chain-tracing | plan-creator-20261020-001 |
