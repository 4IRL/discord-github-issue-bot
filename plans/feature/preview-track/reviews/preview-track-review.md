# Review: Track dropdown in the private preview (F17)

## Review — 2026-10-29
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/preview-track/preview-track.md blob 02d67ffb40e414c5607d33cfd7d2902180991f84

### Summary
Sound design with one blocking ordering gap: Step 5's startup Track-count warning would crash an
existing test whose fake project check returns `None`. The live smoke check pointed at Project #2,
which the runbook forbids. Both are fixed; the remaining findings were imports, guards and test
coverage. Needs a second pass after the fixes.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 7 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 1 major, 3 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 5 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 1 major, 7 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 2 major, 8 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 6 minor |

### Findings

#### Major (should fix)
- **[Step 5] Startup Track-count warning crashes `test_setup_hook_project_check_failure_still_checks_second`** _(Subagents #2, #3, #4, #5, #6)_: its fake check returns `None` for the second route, so `len(fields.track_option_ids)` raises AttributeError out of `setup_hook`.
- **[Manual checks / Step 6] Live smoke check pointed at Project #2; SMOKE-TEST.md not updated** _(Subagents #4, #6; safety)_: the runbook's scratch route uses a separate test Project with no Track field and forbids Project #2.
- **[Step 4] No test that a band press or an Edit-submit keeps the Track field and pick** _(Subagent #5)_.

#### Minor (nice to fix)
- **[Step 2] `field` not imported in github.py** _(#1, #3, #4)_.
- **[Step 4] Select must exist before `__init__`'s `_paint()`; no-project and no-select guards implicit** _(#1, #2, #3, #4, #6)_.
- **[Step 4] Test imports (`replace`, `PROJECT`, new constants) not named** _(#1, #4)_.
- **[Step 4] Message Select sends `required: true` with `min_values: 0`** _(#1, #2)_.
- **[Step 4] Track-lookup failure log drops GitHubError stage/status** _(#4)_.
- **[Step 4] `FILING_CHECK_TIMEOUT` comment doesn't cover its second use** _(#4)_.
- **[Step 5] `TrackOptions`/`TRACK_OPTION_LIMIT` import into bot.py not prescribed** _(#3, #4)_.
- **[Step 6] A failed Track write shares stage `project-field`; hand-fix guidance skips Track** _(#6)_.
- **[Step 6] README Known limits don't mention cached Track options** _(#4, #6)_.
- **[Steps 3, 6] Gates run a subset of the suite though they touch shared inputs** _(#3)_.
- **[Step 2] "Option order kept" undetectable by dict equality; `set_track` "without a request" ambiguous on a cold cache** _(#5)_.
- **[Step 3] set_track-failure filing-hook case needs a candidate with a track** _(#5)_.
- **[Step 1] Padded and whitespace-only default names untested; [Step 4] default past the 25th option untested; [Step 6] example Track values unchecked** _(#5)_.
- **[Manual checks] Assumption 3 had no recorded evidence; live enablement unstated** _(#6)_.

#### Descriptive (deferred to final cleanup)
- Stored test count (448) in the Step 7 gate _(#1, #3, #4, #5, #6)_ — removed in this pass.
- Hedge on how a test sets select values (`select._values` is verified) _(#5, #6)_ — removed in this pass.
- Anchor lint: 16 `path:NNN` line citations.

### To-Do: Mechanical Fixes (auto-applied)
Applied inline in sequence (one plan file; parallel fixers would collide), each re-read after landing.
- [x] Step 5 (d): replace the `None` in `test_setup_hook_project_check_failure_still_checks_second` with a Track-less `ProjectFields` constant
- [x] Step 2: import `field` from `dataclasses`
- [x] Step 4: build the select before `_paint()`; `_paint` skips a missing select; explicit `project is not None` guards for the lookup and default
- [x] Step 4: name the test imports
- [x] Step 4: extend `FILING_CHECK_TIMEOUT`'s comment
- [x] Step 5: import `TRACK_OPTION_LIMIT` and `TrackOptions` into bot.py
- [x] Step 6: README Known limits bullet for cached Track options
- [x] Steps 2-6: every step gates on the full suite after its file subset
- [x] Step 2 (a)/(e): order checked with a reversed response and `tuple(...)`; (g) warms the cache first and asserts no further call
- [x] Step 3: the filing-hook failure case builds its candidate with `track`
- [x] Research Findings: Assumption 3 evidence from the cold survey's read-only query
- [x] Step 7: stored test count removed; Step 4 (f): hedge removed

### Design Decisions (awaiting user input)

#### DD-1: [Manual checks / Step 6] Where the live Track check runs (safety)
**Context:** The runbook's test Project has no Track field and Project #2 is off limits.

| # | Option | Trade-off |
|---|---|---|
| 1 | Add Track to the test Project; update SMOKE-TEST.md fully | Live coverage; owner setup and more runbook edits |
| 2 | No live Track check | Mocked tests only; first live use is the deployed route |

**Labels:** kind=dd category=security-safety reversible=costly rework=low · Recommended: 1

**Chosen:** 2 — No live Track check (owner, dd-261029-029). SMOKE-TEST.md gets a note and the hand-fix line only.

#### DD-2: [Step 2] Stage for a failed Track write
| # | Option | Trade-off |
|---|---|---|
| 1 | New stage `project-track` (drops the cache too) | Log and hand-fix text name the missing write |
| 2 | Keep `project-field`, reword hand-fix | Fewer changes; ambiguous log |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** 1 — New stage `project-track` (owner, dd-261029-030)

#### DD-3: [Step 4] Track-lookup failure log form
| # | Option | Trade-off |
|---|---|---|
| 1 | Match filing-check lines (stage/status, `: timeout`, type) | Consistent and diagnosable |
| 2 | Type only | Simpler; loses stage/status |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1

**Chosen:** 1 — Match filing-check lines (owner, dd-261029-031)

#### DD-4: [Step 4] `required=False` on the message Select
| # | Option | Trade-off |
|---|---|---|
| 1 | Pass `required=False` | Payload matches the optional row |
| 2 | Keep the default | Relies on Discord ignoring `required` in messages |

**Labels:** kind=dd category=approach reversible=yes rework=low · Recommended: 1

**Chosen:** Pass `required=False` (assumed: dd-policy, dd-261029-032)

#### DD-5: [Steps 1, 4, 6] Extra coverage
| # | Option | Trade-off |
|---|---|---|
| 1 | Add band/Edit Track-field, padded-default, past-25 and example-values tests | Pins user-visible behaviour |
| 2 | Skip | Fewer tests |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** Add all (assumed: dd-policy, dd-261029-033)

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding (applied; Pass 2 re-checks)

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | github.py, bot.py, test_intake.py imports; no cycle via issue_bot.github |
| Type annotations | [x] | ProjectCheck narrowing, TrackOptions alias |
| Error handling (status codes, exceptions, user feedback) | [x] | place_on_roadmap False path, lookup failures, stage names |
| Test coverage (happy path, sad path, edge cases) | [x] | test_intake/test_github/test_config/test_bot/test_issues read |
| Breaking changes (API contracts, shared state, DB schema) | [x] | positional callers, ProjectConfig hashability, PROJECT_FIELDS equality |
| Config consistency (env vars, requirements pins, lint rules) | [x] | no new packages; discord.py 2.7.1 Select probed |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | constants, log formats, CLAUDE.md logging rules |

## Review — 2026-10-29 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/preview-track/preview-track.md blob 3171c73f9a0ac8529db5399d59ff943c008fad91

### Summary
All six reviewers PASS: 0 critical, 0 major, 17 minor. Pass 1's fixes re-verified against the
source (the `ProjectFields` constant for the startup test, `field` import, select-before-`_paint`,
`required=False` accepted by discord.py 2.7.1's `Select`). Ready for implementation after the minor
fixes below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 2 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 1 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 1 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 5 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 5 minor |

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 4: the default pick applies on the fresh submit only; Edit keeps its carried `track` _(#1, #2, #4)_
- [x] Step 6: SMOKE-TEST row's id-refresh sentence and every hand-fix branch cover `project-track` _(#1, #4, #6)_
- [x] Step 6: README Status paragraph mentions F17 _(#4)_
- [x] Step 2: import `SET_TRACK_MUTATION` in test_github; specify `set_track`'s alias check _(#4, #6)_
- [x] Step 3: `set_track` on both `fake_github` namespaces _(#6)_
- [x] Step 1: `must map` cases sit under a `track_field`; the `needs track_field` case uses a well-formed table; check order stated _(#5, #6)_
- [x] Step 4: `filled_modal` passes the lookup through _(#5)_
- [x] Step 5: Red gate names which cases fail before the Green _(#3)_

### Design Decisions
#### DD-6: [Step 6] Recovering a lost Track pick
**Labels:** kind=dd category=docs-wording reversible=yes rework=low · Recommended: 1 (hand-fix text: ask the reporter; every branch names Track) vs 2 (log the option name)

**Chosen:** 1 (assumed: dd-policy, dd-261029-034)

#### DD-7: [Steps 4, 5] Name of the lookup callable
**Labels:** kind=dd category=naming-structure reversible=yes rework=low · Recommended: 1 (`track_lookup: TrackLookup`, like `filing_check`) vs 2 (keep `track_options` for both)

**Chosen:** 1 (assumed: dd-policy, dd-261029-035)

#### DD-8: [Steps 2, 4] Guard tests (no-project lookup; Track route without a lookup)
**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1 (add) vs 2 (skip)

**Chosen:** 1 (assumed: dd-policy, dd-261029-036)

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes (applied)
[ ] Requires changes before proceeding

Pass 2 clean (0 critical, 0 major executable/external). Plan is ready for implementation.

### Descriptive cleanup: 17 fixed, 0 dropped
Stored test count and the `select._values` hedge removed (Pass 1); 15 `path:NNN` line citations
reduced to file citations; anchor lint 0 problems.

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| Default-pick sentence not scoped to the fresh submit | minor | step-5b:mechanical-fix | fix_regression | Pass 1's guard fix reworded the sentence without re-reading it against the Edit branch | yes | not logged (review due: critical only) |
| SMOKE-TEST id-refresh and hand-fix branches stale after `project-track` | minor | step-5f:dd-application | fix_regression | DD-2 applied to one clause of the row, not its siblings | yes | not logged (review due: critical only) |
| Step 5 Red gate "(a)-(c) fail" though one case passes | minor | step-5b:mechanical-fix | fix_regression | Pass 1 added (d) and relabelled the gate without mutating it | yes | not logged (review due: critical only) |
| `fake_github` returns two namespaces | minor | subagent-5:verification | verification_stopped_at_text | Pass 1 accepted "give fake_github an attribute" without reading its two branches | yes | not logged (review due: critical only) |
| `must map` cases need `track_field` present | minor | subagent-5:verification | verification_stopped_at_text | Pass 1 checked messages, not check order | yes | not logged (review due: critical only) |

### Plan-Creator Misses
| Finding | Severity | Unit | Ledger id |
|---|---|---|---|
| Manual checks pointed the smoke run at Project #2, which docs/SMOKE-TEST.md forbids (Pass 1, #4) | major | research-4:test-infra | not logged (review due: critical only) |
