# Review: Per-tag modal questions with preview and confirm (F3)

## Review — 2026-10-26
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/clarifying-questions/clarifying-questions.md blob d173e81d214564b0878041859301ca4dbed3fab6

### Summary
The design is sound and every reviewer agreed on its shape. Six reviewers found the same Step 5
test gap: the dispatch test needs `interaction.data`. Four found the same Step 1 fixture
break: `extra-docs` lands in a question table. Step 4 also left the suite red until Step 5,
and the preview's 10-minute expiry was not actually fixed. Needs changes; all are applied
below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 3 major, 4 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 1 major, 2 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 2 major, 4 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 3 major, 5 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 6 major, 7 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 5 minor |

### Findings

#### Major (should fix)
- **[Step 5] `View._scheduled_task` reads `interaction.data`; `make_interaction` has none** _(#1, #2, #3, #4, #5)_: the dispatch test would reach `on_error` with `AttributeError`, not the filing error. This was verified in the repo venv.
- **[Step 1] Question arrays after `.labels` break `test_bad_route_labels_raise[extra-docs]`** _(#1, #3, #4, #5)_: the appended `docs` key lands in the last question table. `without_route_keys` also can't drop `questions`, and `ROUTE_FILE_KEYS` doesn't list it.
- **[Step 4] The suite stays red across the Step 4 commit** _(#3, #5)_: two `test_bot.py` tests still assert filing on submit until Step 5.
- **[Step 4] The preview timeout restarts on every click** _(#2, #6)_: Edit then cancel pushes expiry past 10 minutes and past the 15-minute token, so the expired notice can't be shown.
- **[Step 4] Three live-Discord response behaviours are unproven by source or mocks** _(#1)_.
- **[Step 4] `test_submit_defers_privately_first` "as is" can't pass** _(#5)_: submit no longer calls `channel.send`.
- **[Step 4] The truncation test asks for four answers, but the fixture's bug type has two** _(#5)_.
- **[Step 4] The privacy test is vacuous without sentinel strings** _(#5)_.
- **[Step 4] No test that File acks before the slow path** _(#5)_.
- **[Step 6] The SMOKE-TEST `routes.smoke.toml` snippet lacks the required `questions`** _(#6)_: the owner's smoke run would exit 2.
- **[Step 4] F7's and F10's kept contracts are changed without being recorded** _(#4, descriptive)_.

#### Minor (nice to fix)
- `_report_error` log format and `what` values are unspecified (#5, #6). The preview-send failure log string is unspecified (#5).
- Error messages for a non-table `questions` value and a non-array type value are unassigned. The missing-key message is unstated (#1, #5, #6).
- Missing imports and type hints: `Sequence` in issues.py and handler.py, and the new signatures (#1, #3, #4).
- `field` shadows `dataclasses.field` in the Step 3 comprehension (#4).
- The example label `What does "done" look like?` needs a TOML literal string (#4).
- `test_handler.py` and `filled_modal` keyword callers are not listed (#1, #3).
- The `TargetConfig` questions check lacks the `Mapping` guard (#1).
- Stale docstrings, and the CLAUDE.md error-handler rule doesn't name the view (#4, #6).
- There is no rollback note for the required key (#6).
- The Step 4 edit submit's behaviour after expiry is unstated (#2, #6).
- Gaps in the example-shape test, the second-route questions test and the Edit-after-close/4096 boundary tests (#5).

### To-Do: Mechanical Fixes (auto-applied)
Applied by one sequential fixing subagent: the fixes share anchors in Steps 1, 2 and 4, so they
were applied in order, not in parallel.
- [x] Add `data={}` to `make_interaction`, and correct Step 5's `_scheduled_task` note
- [x] Insert the `extra-docs` key inside the labels table instead of appending it; update the `ROUTE_FILE_KEYS` comment and the `without_route_keys` docstring
- [x] `test_submit_defers_privately_first` attaches `followup.send`
- [x] Truncation test: two 4000-character answers
- [x] Privacy test seeds the sentinels under `caplog.at_level(logging.INFO)`
- [x] SMOKE-TEST section 1 `routes.smoke.toml` gets `questions` tables
- [x] Research Findings records F7's and F10's kept-contract changes for the fold-back
- [x] `_report_error` format; `what="modal"` / `"preview"`; exact view log line
- [x] Preview-send failure uses `_reply`'s log format
- [x] Missing-key message is `routes.<name>.questions is required`
- [x] `Sequence` imports and full type hints on the new signatures
- [x] Rename the comprehension variable to `answer_input`
- [x] TOML literal string for the `done` label
- [x] `test_handler.py` and `filled_modal` keyword callers listed
- [x] `Mapping` guard on the `TargetConfig` questions check
- [x] Docstrings (intake module, `IntakeModal`, `on_submit`, `issue_body`, `load_routes`, `IssueBot`, `make_interaction`); CLAUDE.md error-handler rule
- [x] README Upgrading rollback note; Manual checks pre-deploy reminder
- [x] Step 4 Verify notes the two test_bot tests: superseded by DD-5 (Step 5 merged into Step 4)

### Design Decisions (awaiting user input)

#### DD-1: [Step 4] Preview lifetime refreshed by clicks
**Context:** discord.py resets a View's expiry before every item callback (view.py `_scheduled_task`); `View.timeout`'s setter sets expiry to now + value.

| # | Option | Trade-off |
|---|---|---|
| 1 | Fixed deadline from submit; each callback resets `self.timeout` to the time remaining | Keeps "expires in 10 minutes" true and the notice inside the token |
| 2 | Accept the refresh-on-click and document it | Dead buttons with no notice after a long Edit-and-cancel |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (asked, dd-261026-020)

#### DD-2: [Step 4] Edit submit after the preview expired
| # | Option | Trade-off |
|---|---|---|
| 1 | Always show a fresh preview, stated and tested | Nothing lost |
| 2 | Refuse as expired | Answers lost |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (asked, dd-261026-021)

#### DD-3: [Step 4] Establishing three live-Discord behaviours
| # | Option | Trade-off |
|---|---|---|
| 1 | Owner smoke test at merge: add explicit checks to Manual checks and SMOKE-TEST | No agent live run; proof comes at the merge gate |
| 2 | Probe before Step 4 | Slower; needs a live go-ahead |

**Labels:** kind=dd category=testing reversible=yes rework=med · Recommended: 1

**Chosen:** 1 (asked, dd-261026-022)

#### DD-4: [Step 1] Fixture layout vs existing labels tests
| # | Option | Trade-off |
|---|---|---|
| 1 | Keep arrays after labels; insert `extra-docs` inside labels; add a `without_questions` cut helper for the missing-key test; leave `questions` out of `ROUTE_FILE_KEYS` with a comment | Small helper change |
| 2 | Move arrays before labels | Breaks the labels not-a-table case instead |

**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261026-023)

#### DD-5: [Step 4] Keep every commit green
| # | Option | Trade-off |
|---|---|---|
| 1 | Merge Step 5's test rewrites into Step 4 | One larger step |
| 2 | Allow a red commit | Breaks /run-plan's green-per-step rule |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261026-024)

#### DD-6: [Step 4] File ack-order test
| # | Option | Trade-off |
|---|---|---|
| 1 | Add an order test (edit_message before channel.send and the hook) | Guards the 3-second rule |
| 2 | Skip | A live-only failure can slip through |

**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261026-025)

#### DD-7: [Step 1] Message for a non-table `questions` value or a non-array type value
| # | Option | Trade-off |
|---|---|---|
| 1 | Both raise `routes.<name>.questions must map bug and feature to question lists` (labels precedent) | One message |
| 2 | Separate messages | More strings |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261026-026)

#### DD-8: [Step 1] Validate the example's questions
| # | Option | Trade-off |
|---|---|---|
| 1 | Run the real `_route_questions` on the raw example route | Catches typos in the shipped example |
| 2 | Leave as is | An operator's copy could exit 2 |

**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261026-027)

#### DD-9: [Step 1] Second route's own questions
| # | Option | Trade-off |
|---|---|---|
| 1 | Assert `routes[556].questions` | Pins per-route keying |
| 2 | Skip | |

**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261026-028)

#### DD-10: [Step 4] Edit-after-close and 4096 boundary tests
| # | Option | Trade-off |
|---|---|---|
| 1 | Add both | Pins `_closed` and the off-by-one |
| 2 | Skip | |

**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261026-029)

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 read config, issues, handler and intake; `Sequence` gaps found |
| Type annotations | [x] | #1 and #4 |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced the discord.py view, modal, interactions and webhook sources |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 read every test file |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6: route-file required key, SMOKE-TEST snippet |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4: no new deps or env keys |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4: `field` shadowing |

## Review — 2026-10-26 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/clarifying-questions/clarifying-questions.md blob b9fd4171f7ddf4f34c7c101d80c9c0225655f61b

### Summary
Pass 1's resolutions hold against the real source. #1 checked a real View carrying the
fixed-deadline line through `_scheduled_task` in the repo venv. One major regression from
Pass 1's privacy-test fix remains: a single preview can't log both `posted` and `preview expired`.
The rest are minor. Needs one more pass.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 5 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 3 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 3 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 4 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 1 major, 6 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 4 minor |

### Findings

#### Major (should fix)
- **[Step 4] The privacy test's one-preview sequence can't produce `preview expired`** _(#5; also #1 and #3 as minor)_. File closes the view, so a later Edit or timeout does nothing. Fix: use two previews (A: Edit, then timeout; B: File). This is a fix regression from Pass 1's privacy-test fix.

#### Minor (nice to fix)
- `make_interaction`: `edit_original_response` belongs on the interaction, not `response`; the `message` kwarg and the `followup.send` return value are unused (#1).
- The Known-limits wording reintroduces "Description" and trips Step 5's own grep (#1, #3, #5, #6).
- SMOKE-TEST § 4, the failure-path note and Troubleshooting still describe filing on submit (#4, #6).
- Fold-back notes miss Standing invariant 2's handler list and two Expected-end-state wordings (#6).
- `_question` must convert `style` to `QuestionStyle`, and a test must catch a raw string (#2).
- The moved test_bot tests don't say which interaction's `channel.send` is the summary; they could pass vacuously (#2, #5).
- Appended `questions = …` lines land in the labels table: build those files by cutting or inserting (#4, #5).
- Test import lists for the new names are not stated (#4).
- The `on_timeout` HTTPException log format is unspecified (#5).
- The "copy Manual checks into the final report" box has no carrier to the user (#3).
- Five DDs below.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Privacy test over two previews
- [x] `make_interaction`: `edit_original_response` on the namespace; drop the unused additions
- [x] Known-limits wording without "Description"
- [x] SMOKE-TEST § 4, failure-path note and Troubleshooting rows
- [x] Fold-back notes: invariant 2 handler list and the Expected-end-state wordings
- [x] `QuestionStyle(...)` conversion and a raw-string-catching assertion
- [x] Summary assertions on the button interaction's `channel.send`
- [x] Build `questions`-not-a-table files by cut plus insert, not append
- [x] Test import lists
- [x] `on_timeout` HTTPException log format
- [x] Manual-checks carrier: the final report names them for /run-feature's merge-gate brief

### Design Decisions

#### DD-1: [Step 1] A question missing `style` or `required`
**Chosen:** `…[<n>].style is required` / `…[<n>].required is required`, with two tests (asked, dd-261026-030)

#### DD-2: [Step 4] Edit-submit log line
**Chosen:** the same `previewed <type> interaction_id=<id>` line (asked, dd-261026-031)

#### DD-3: [Step 1] Helper parameter order
**Labels:** kind=dd category=naming-structure reversible=yes rework=low · Recommended: `(route, where)`
**Chosen:** `(route, where)`, like the sibling helpers (assumed: dd-policy, dd-261026-032)

#### DD-4: [Step 3] Draft repr test
**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: add
**Chosen:** add (assumed: dd-policy, dd-261026-033)

#### DD-5: [Step 4] New preview after Edit expires via the edit interaction
**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: add
**Chosen:** add (assumed: dd-policy, dd-261026-034)

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

## Review — 2026-10-26 (Pass 3)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/clarifying-questions/clarifying-questions.md blob 08e1693fbe21c57f9cbabbd57ffdde60da72e16e

### Summary
Five reviewers passed the plan, and Pass 2's resolutions hold. One major test-coverage gap
remained: no test pins that an Edit's changed answers are what the new preview shows and what
File files. It is settled below and applied. The rest are minor recipes and wording. The hard
cap is reached; nothing is left unresolved.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 1 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 2 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 1 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 4 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 1 major, 1 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 4 minor |

### Findings

#### Major (should fix)
- **[Step 4] The Edit submit's changed answers are never asserted through to File** _(#5)_. A defect that builds the new view from the old draft would pass every test.

#### Minor (nice to fix)
- Recipes for the zero-questions and question-not-a-table files; the not-an-array file starts from `without_questions` (#1, #4, #6).
- The `TargetConfig` equality literals need the fixture's exact questions (#6).
- `_question` should reuse `_route_str` for the label (#4).
- `_report_error` must be `async def` (#4).
- The moved second-route test's File interaction must be on channel 556 (#2).
- SMOKE-TEST "What it writes" count; F1's kept contract belongs in the fold-back list (#6).
- The Manual-checks carrier wording (#3, #4).
- Two DDs below.

### To-Do: Mechanical Fixes (auto-applied)
- [x] All minor mechanical findings above, applied by one sequential fixer

### Design Decisions

#### DD-1: [Step 4] Edit-submit test pins the changed answers
**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: seed changed values; assert the new embed and the filed candidate
**Chosen:** that option (assumed: dd-policy, dd-261026-039)

#### DD-2: [Step 4] Order of closing the old view on an Edit submit
**Chosen:** stop the old view only after `edit_message` succeeds (asked, dd-261026-040)

#### DD-3: [Step 4] The File-once test must be able to catch an await before the guard
**Labels:** kind=triage category=testing reversible=yes rework=low · Recommended: a yielding async ack side effect
**Chosen:** that option (assumed: dd-policy, dd-261026-041)

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes (applied)
[ ] Requires changes before proceeding

Pass 3 complete (hard cap). No issues remain for "resolve during implementation".

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| Privacy test's one-preview sequence can't log `preview expired` (found Pass 2) | major | step-5b:mechanical-fix | fix_regression | Pass 1's fixer added the sequence without walking it against the step's own Green spec | yes: self-check 2 should mutate against the plan's Green | plan-reviewer-20261026-001 |
| Edit-submit test never pins the changed answers (found Pass 3) | major | subagent-5:verification | verification_stopped_at_text | Passes 1–2 checked the call shape, not whether a plausible defect passes | maybe | plan-reviewer-20261026-002 |

### Plan-Creator Misses
6b: 0 misses (no Pass 1 Correctness or Integration finding showed the plan asserting a wrong fact about existing code)

### Descriptive cleanup: 29 fixed, 0 dropped
