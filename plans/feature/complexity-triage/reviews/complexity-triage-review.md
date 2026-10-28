# Review: Complexity triage (S/M/L/XL)

## Review — 2026-10-27
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/complexity-triage/complexity-triage.md blob c8c181e00e16139a448c6f6edac80172586db900

### Summary
The plan is sound: its data flow, kept contracts and test inventory match the code. Every
mechanical defect found was a small prescription error, and all are fixed below: a missing
`replace` import, an unchanged positional call in the repr test, a deadline test that could never
fail, and stale runbook text. One external claim, that the label endpoint behaves as documented,
can only be proven live. Proceed after the design decisions below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 1 major, 5 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 5 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 6 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 9 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 2 major, 5 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 11 minor |

### Findings

#### Major (should fix)
- **[Step 4] `_choose` calls `dataclasses.replace`, but intake.py imports only `dataclass, field`** _(#3, also #1, #4)_: as written, every band press raises NameError.
- **[Step 4] The band-press deadline test could never fail** _(#5)_: a direct `.callback` call leaves `view.timeout` at `PREVIEW_TIMEOUT`, so "at or below the original deadline" passes even without `_keep_deadline()`.
- **[Step 3] The repr test's positional `candidate_from_submission` call also needs the band** _(#5, also #1, #2, #3, #4)_: "The repr test stays" read as "leave unchanged" raises TypeError.
- **[Step 2] `POST /repos/{o}/{r}/labels` has never been exercised** _(#1, external)_: whether `issues: write` covers it and whether an existing label returns 422 rest on GitHub's docs only. See DD-1.

#### Minor (nice to fix)
- **[Step 3] issues.py never imports `complexity_label`; the test modules' imports are unstated** _(#3)_.
- **[Step 3] `fake_github` has two return branches, and both need `ensure_label`** _(#3)_.
- **[Step 2] The Red step fails with ImportError at collection, not AttributeError; the transport error should be `ClientConnectionError()`** _(#5)_.
- **[Step 5] SMOKE-TEST still quotes the old `PREVIEW_REPLY`, expects only the type label, and has no `stage=label` row** _(#1, #3, #4, #6)_.
- **[Step 5] The drift test should resolve the doc from the repo root** _(#1, #4, #5)_.
- **[Step 5] The labels the bot creates have no stated reach or way to undo them** _(#6)_.
- Design-level minors: DD-2 through DD-9.

#### Descriptive (deferred to final cleanup)
- [Step 4] The count of `preview_embed` calls is wrong (two in `test_preview_embed_boundary`); pass `Complexity.S, Complexity.S`.
- [Step 1] Stored test count (333) in Research Findings and the Step 1 gate.
- [Step 3] Import placement (first in the project group, alphabetical) and complexity.py's imports.
- [Step 3] Docstrings left stale: intake module, `PreviewView`, `issue_labels`, `file_candidate`, `IssueCandidate`, `GitHubClient`.
- [Step 1] F6 coupling: name `Complexity` as the one home of the band names.
- [Manual checks] The embed field renders as a heading plus a value; a re-run files another issue.
- Anchor lint: 12 `path:NNN` line citations.

### Verification Gaps
- **Step 2**: the label endpoint's permission and its 422 behaviour can be proven only by the owner's live smoke run (DD-1).

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 4: `replace(...)`, with `replace` added to intake.py's `from dataclasses import` line _(applied inline)_
- [x] Step 3: the repr test's positional call gets `Complexity.M` too _(applied inline)_
- [x] Step 4: the deadline test mirrors `test_edit_keeps_the_deadline` (`_deadline -= 120`, bounded timeout) _(applied inline; pattern read at tests/test_intake.py `test_edit_keeps_the_deadline`)_
- [x] Step 2: the Red failure is an ImportError at collection; the transport error is `aiohttp.ClientConnectionError()` _(applied inline)_
- [x] Step 3: both `fake_github` branches gain `ensure_label` _(applied inline; conftest `fake_github` read)_
- [x] Step 3: issues.py imports `complexity_label`; each test module's imports are named _(applied inline)_
- [x] Step 5: SMOKE-TEST gets the new preview quote, the Issue label row, a Success check and a `stage=label` troubleshooting row _(applied inline; lines read in docs/SMOKE-TEST.md)_
- [x] Step 5: the drift test uses the `REPO_ROOT` path pattern _(applied inline)_
- [x] Step 5: COMPLEXITY.md states the labels' reach and how to remove them _(applied inline)_

### Design Decisions

#### DD-1: [Step 2] How is the never-exercised label endpoint proven before merge?
**Context:** `ensure_label` is the bot's first call to `POST /repos/{o}/{r}/labels`. If the
installation token can't create labels (403), every filing of an uncached band fails at
`stage=label`. No agent may make a live GitHub call.

| # | Option | Trade-off |
|---|---|---|
| 1 | The owner's live smoke run is a merge gate for it | The plan's Manual checks already file one band on the test repo; the Phase B brief names this as required. No code change. |
| 2 | Also make a failed `ensure_label` non-fatal (file without the complexity label, and log it) | Filing never breaks on a label problem, but this overturns plan DD-2's "nothing is filed". |

**Labels:** kind=dd category=ops-infra reversible=yes rework=low · Recommended: 1

**Chosen:** Also make it non-fatal (owner override; dd-261027-048)

#### DD-2: [Step 3] Track the override explicitly, or infer it from `complexity != suggested`?
**Context:** inferring the override breaks one sequence. The reporter presses L, an Edit re-rates
the answers to L, and a second Edit that re-rates to S then silently drops their L. Pressing the
suggested band also counts as "never changed".

| # | Option | Trade-off |
|---|---|---|
| 1 | An explicit `overridden: bool` on `Draft`, set by any band press and carried across Edit | Correct in every sequence; one more Draft field. |
| 2 | Keep the equality inference | No new field; drops the override in the double-Edit sequence. |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1

**Chosen:** Explicit overridden flag (dd-261027-049)

#### DD-3: [Step 2] Is every 422 "already exists", and are labels cached for the process?
**Context:** GitHub returns 422 for other validation errors too (unlikely with a fixed name and
colour). A label someone deletes on GitHub stays cached until a restart.

| # | Option | Trade-off |
|---|---|---|
| 1 | Accept both, with a code comment and a line in docs/COMPLEXITY.md | Simplest; the harm is one issue missing a label, fixable on GitHub (C3). |
| 2 | Narrow the success case to a 422 whose `errors[].code == "already_exists"` | Stricter; must parse the error body without ever logging it. |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Accept and document (dd-261027-050)

#### DD-4: [Step 4] A failed band-press edit leaves the view's band changed but the shown preview unchanged
**Context:** `_choose` sets the band before its `await` (the `_closed`-guard pattern). If
`edit_message` then fails, `on_error` replies, and a later File files a band the preview never
showed.

| # | Option | Trade-off |
|---|---|---|
| 1 | Accept, with a code comment | Needs a failed Discord edit; the label can be changed on GitHub (C3). |
| 2 | Roll the band back when the edit raises | Exact, but adds a try/except and a test. |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Accept, comment the failed edit (dd-261027-051)

#### DD-5: [Step 1] Should `rate` strip answers itself?
**Context:** DD-1 counts stripped answers, but `rate` relies on its caller having stripped them.

| # | Option | Trade-off |
|---|---|---|
| 1 | Strip inside `rate` (`len(answer.strip())`), with a whitespace-only test | The module matches its documented rule on its own. |
| 2 | Rely on callers | Correct today only because `on_submit` strips. |

**Labels:** kind=dd category=approach reversible=yes rework=low · Recommended: 1

**Chosen:** Strip inside rate (assumed: dd-policy, dd-261027-045)

#### DD-6: [Step 4] Should the override-then-Edit test also check the highlight and the field?
| # | Option | Trade-off |
|---|---|---|
| 1 | Also assert that the new view's L button is primary and the embed field shows the chosen text | Covers what the manual check relies on. |
| 2 | Assert only `draft.complexity` | Leaves `_paint` and the field untested on the Edit path. |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Also assert highlight and field (assumed: dd-policy, dd-261027-046)

#### DD-7: [Step 4] A band-press edit re-stores the view, which pushes the expiry back by the edit's round trip
**Context:** in discord.py 2.7.1, `edit_message(view=...)` re-stores the view and restarts its
timeout from `self.timeout`, which `_keep_deadline()` set at the start of the callback.

| # | Option | Trade-off |
|---|---|---|
| 1 | Accept (sub-second drift; the Edit-submit path already behaves this way) | No code. |
| 2 | Call `_keep_deadline()` again after the edit lands | Exact, but one more line plus a test. |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Accept, comment the failed edit (dd-261027-051)

#### DD-8: [Step 3] Add a `filing_hook`-level test for a label failure?
| # | Option | Trade-off |
|---|---|---|
| 1 | Add a test_bot test: `ensure_label` raises `GitHubError("label", 403)`; `FILING_ERROR_REPLY` is posted, `stage=label` is logged, `create_issue` is never awaited, and no member text is logged | Proves the member-visible path. |
| 2 | Rely on the `file_candidate` propagation test | Covers it only indirectly. |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Add the test_bot test (assumed: dd-policy, dd-261027-047)

#### DD-9: [Step 3] ROADMAP Phase 3's "the thread's final message shows the link with its rating"
**Context:** ROADMAP Phase 3 says the thread's final message shows the issue link together with
its rating and roadmap placement. Neither F4's Expected end state nor F6's owns the rating part.

| # | Option | Trade-off |
|---|---|---|
| 1 | F4 adds the band to the thread's link message (`filed_reply` gains the band: `Filed as GitHub issue #N (complexity L): …`) | Honours the ROADMAP now; touches F7's kept contract (`filed_reply`). |
| 2 | Leave it to F6, recorded in META-PLAN's F6 section at fold-back | No change here; F6 grows. |

**Labels:** kind=dd category=scope reversible=yes rework=low · Recommended: none

**Chosen:** F4 adds it now (dd-261027-052)

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 read intake/issues/handler imports; the `replace` and `complexity_label` imports were added |
| Type annotations | [x] | #1 checked the new signatures |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced the label failure to `FILING_ERROR_REPLY` |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 read test_intake/test_github/test_bot/test_handler/conftest |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 covered the label reach, rollback and the F6 coupling |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4: no route-file or env change; no new package |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 checked the logging rules, constants and the `REPO_ROOT` pattern |

## Review — 2026-10-27 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/complexity-triage/complexity-triage.md blob a08a7b9279d58dd7a4e284a4c497dd7cff03cda9

### Summary
A clean pass: 0 critical and 0 major findings, and all six subagents PASS. The Pass 1 fixes hold,
and the baseline suite is green. Every finding is minor. The two mechanical fixes pin how the
long-answer Edit-submit tests set their answers and the exact "chosen" field value. Five small
design decisions tighten the Step 2 and Step 4 tests and make the preview field follow the
`overridden` flag. Six descriptive gaps were left for the final cleanup.

Pass 1 resolutions re-checked: all nine `[x]` mechanical fixes still hold in the plan text. They
are the `replace` import, `Complexity.M` in the repr test's call, the bounded deadline test, the
collection-time ImportError and `ClientConnectionError()`, `ensure_label` on both `fake_github`
branches, the `complexity_label` and test-module imports, the SMOKE-TEST quote, Issue label row,
Success check and `stage=label` row, the `REPO_ROOT` drift path, and COMPLEXITY.md's label reach
and removal.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 1 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 1 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 1 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 3 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 4 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 4 minor |

### Findings

#### Minor (nice to fix)
- **[Step 4] The long-answer Edit-submit tests can't use `edited_submit`** _(#6)_: its fixed `"Steps v2"` never crosses a threshold. Mechanical fix below.
- **[Step 4] The L-press test's "chosen" field value was unpinned** _(#5)_: swapped `preview_embed` arguments would still pass. Mechanical fix below.
- **[Step 4] No band press runs under log capture** _(#5, #6)_: the gate's claim that `test_preview_flow_logs_ids_not_text` covers `_choose` was vacuous. See DD-1.
- **[Step 4] The preview field picked its text by `complexity == suggested`, while the override state uses `overridden`** _(#1)_. See DD-2.
- **[Step 4] A band press racing File can re-show dead buttons on the filed preview** _(#2)_. See DD-3.
- **[Step 4] The closed-view band-press test didn't check the draft** _(#5)_. See DD-4.
- **[Step 2] The label cache's per-repo key was untested** _(#5)_. See DD-5.
- Descriptive minors: listed below.

#### Descriptive (deferred to final cleanup)
- [Research Findings] The fold-back note should also cover F5's and F3's kept contracts and the Baseline's label-skip fact _(#6)_.
- [Step 5] SMOKE-TEST's `Re-runs` line should except a `complexity:<band>` label that already exists _(#6)_.
- [Step 5] README's Reporting step 4 should mention the band _(#4)_.
- [Step 3] issues.py's module docstring should state its log policy _(#4)_.
- [Step 5] COMPLEXITY.md should not re-quote the link-message text _(#4)_.
- [Steps 4-5] The Step 4 and Step 5 test imports should be named, as Step 3's are _(#3)_.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 4: the long-answer Edit-submits use `reopened_modal(view, make_interaction)`, set `modal.answer_inputs[0]._value`, call `await modal.on_submit(edit_interaction)` and read the new view from `edit_interaction.response.edit_message.await_args.kwargs["view"]` _(applied inline; helpers read in tests/test_intake.py)_
- [x] Step 4: the L-press field value is pinned to `COMPLEXITY_CHOSEN.format(band="L", suggested="S")` _(applied inline; `submitted_preview`'s default answers `("Steps",)` make a short bug, which rates S)_

### Design Decisions

#### DD-1: [Step 4] Should a band press get a log-privacy check?
**Context:** CLAUDE.md's log rule covers `_choose`, but no test presses a band under `caplog`, and
the Step 4 gate's claim rested on a flow test that never presses one.

| # | Option | Trade-off |
|---|---|---|
| 1 | One Step 4 test presses a band inside `caplog.at_level(logging.INFO)` with the secret title and answers and calls `assert_no_member_text(caplog)`; the gate sentence stops claiming the flow test covers `_choose` | Proves the hard rule on the new callback; one short test. |
| 2 | Leave it and only reword the gate | No test; the privacy property stays prose-only. |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Band press under caplog with `assert_no_member_text` (assumed: dd-policy, dd-261027-053)

#### DD-2: [Step 4] Should the preview field follow `overridden` or the band equality?
**Context:** pressing the suggested band sets `overridden`, but the equality rule still showed
"suggested by the rules". The same happened after an Edit re-rated to the pinned band.

| # | Option | Trade-off |
|---|---|---|
| 1 | Keep the equality test | No change; the field can misstate whether the choice is pinned. |
| 2 | Show the chosen text whenever `draft.overridden` is set | The field matches what Edit will keep. `preview_embed` changes shape, so every call and test changes. |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: none

**Chosen:** Follow `overridden`; `preview_embed(draft, author_name)` takes the `Draft` (dd-261027-054)

#### DD-3: [Step 4] A band press racing File can re-show dead buttons on the filed preview
**Context:** if the band press's edit lands after File's, the filed preview shows buttons again.
The view is stopped, so they no longer respond. Filing is correct.

| # | Option | Trade-off |
|---|---|---|
| 1 | Accept, with one clause in `_choose`'s code comment | No code; the harm is cosmetic on a private preview. |
| 2 | Guard: after the edit, if `_closed` is set, remove the view again | Exact, but adds an error-handled call and a test. |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** Accept, with a code comment (dd-261027-055)

#### DD-4: [Step 4] Should the closed-view band-press test also check the draft?
| # | Option | Trade-off |
|---|---|---|
| 1 | Also assert `view.draft` is unchanged | Catches a guard placed after the `replace` line. |
| 2 | Assert only that `edit_message` is not awaited | Misses that guard order. |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Also assert the draft is unchanged (assumed: dd-policy, dd-261027-056)

#### DD-5: [Step 2] Should a test pin the label cache's per-repo key?
| # | Option | Trade-off |
|---|---|---|
| 1 | Add a two-route test (`two_route_config`): the same label on a second repo makes a transport call | Catches a name-only cache, which would skip the second repo's label. |
| 2 | Rely on the single-route tests and code review | No test; a name-only cache passes. |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Add the two-route cache test (assumed: dd-policy, dd-261027-057)

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 checked that each producer lands before its consumers; the Step 4 and 5 test imports are now named |
| Type annotations | [x] | #1 checked the signatures and field orders against the code |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced the band-press/File race and the non-fatal label path |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 checked that each test fails on its defect; added the privacy, closed-view and per-repo cache checks |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 found the F5 and F3 kept-contract fold-back notes |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4: no package, env or route-file change; Python 3.12 stdlib only |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 checked the log rules, the one-home rule and the module docstrings |

### Descriptive cleanup: 13 fixed, 0 dropped
Pass 1's seven items are fixed: the `preview_embed` calls now pass a `Draft`, the stored test
count is gone, the import placement is stated, the six stale docstrings are covered, the F6
coupling is named, the Manual checks describe the field and re-runs, and the line citations are
replaced by names. Pass 2's six items are also fixed. The final anchor lint count is 0.

Step 6: the open pairs at review time included three that may match Pass 2 minor findings on content
Pass 1 examined. They were not logged: the ledger is in its `review_due` state, which logs only
critical misses (run plan-reviewer-run-20261027-002).

| Pass 2 finding | Pass 1 content | Open pair it may match | Ledger id |
|---|---|---|---|
| Field text by equality while the state uses `overridden` (#1) | Pass 1 DD-2 adopted `overridden`, but its application left `preview_embed` on the equality rule | `step-5f:dd-application` / `fix_regression` | not logged |
| The gate's `test_preview_flow_logs_ids_not_text` claim was vacuous (#5, #6) | Pass 1 #5 read the Step 4 tests and gate and accepted the claim as written | `subagent-5:verification` / `verification_stopped_at_text` | not logged |
| The fold-back note missed F5's and F3's kept contracts (#6) | Pass 1 #6 covered the kept contracts and the F6 coupling | `subagent-6:completeness` / `scoped_too_narrowly` | not logged |

6b: 0 misses

Step 7: skipped (nested; caller reviews assumed decisions)
