# Review: Never file a report twice (F12)

## Review — 2026-11-01
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/idempotent-filing/idempotent-filing.md blob 30ea270c7688652b4c024bb12d51ef9c7d905790

### Summary
Sound plan: signatures, fakes and ordering match the code, and it meets F12's Expected end state. One major external gap (the new list-issues GET had no live evidence) and minor test-assertion, docstring and docs gaps; all fixed or decided below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 1 major, 4 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 5 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 5 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 7 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 5 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 5 minor |

### Findings

#### Major (should fix)
- **[Step 1] The list-issues GET is a never-exercised external call with no live evidence** _(Subagent #1)_: all tests fake the transport; a wrong permission or query would only show as the DD-3 WARNING on every filing, dedup silently off. → DD-1.

#### Minor (nice to fix)
- **[Step 1] find_issue can fail with stage=token; GitHubError's stage list lacks lookup** _(#1, #2, #4, #6)_
- **[Step 1] LOOKUP_URL built from undefined API_URL in tests** _(#4)_
- **[Step 2] find_issue order assertion can't use assert_awaited_once_with(target)** _(#3, #5)_
- **[Step 2] reports_link misses CRLF bodies** _(#1, #2)_ → DD-2
- **[Step 3] recording_github's find_issue must be awaitable** _(#3)_
- **[Step 4] Failed File still sets report.filed** _(#1, #3, #6)_ → DD-3
- **[Step 4] Stale sibling Edit/band/Track presses still run** _(#2)_ → DD-4
- **[Step 4] No concurrent sibling-File test** _(#5)_ → DD-5
- **[Step 4] Refusal log lines not asserted** _(#5)_ → DD-6
- **[Step 4] intake.py module/PreviewView docstrings not updated** _(#4, #6)_
- **[Step 5] No SMOKE-TEST §2 step for the race** _(#4)_ → DD-7
- **[Step 5] README Reporting step 3 and intro sentence not targeted; 100-item window includes PRs** _(#2, #4)_
- **[Step 5] Stale-claim grep has expected matches unnamed** _(#4, #5)_
- **[Design decisions] "re-written with the same values" overstates** _(#1, #2)_
- **[Step 6] Stored test count 510** _(#3, #4, #5, #6)_
- **[Steps 2, 4] Red fails at collection (ImportError), not per test** _(#3)_
- **[Manual checks] Live check doesn't name what it writes** _(#6)_

### To-Do: Mechanical Fixes (auto-applied)
- [x] find_issue docstring names stage token; GitHubError stage list gains lookup; SMOKE row mentions stage=token _(applied inline, one file in sequence)_
- [x] LOOKUP_URL derived from ISSUE_URL _(applied inline)_
- [x] find_issue order assertion via attach_mock + ANY _(applied inline)_
- [x] recording_github find_issue is an AsyncMock side effect _(applied inline)_
- [x] intake module + PreviewView docstrings _(applied inline)_
- [x] README Reporting step 3 + intro F12; "issues and pull requests" in README text and LOOKUP_PAGE_SIZE comment/docstring _(applied inline)_
- [x] Stale-claim grep names its expected matches _(applied inline)_
- [x] Reuse wording: report's values overwrite hand changes (accepted) _(applied inline)_
- [x] Stored count 510 removed _(applied inline)_
- [x] Red wording: ImportError at collection is the expected red _(applied inline)_
- [x] Manual check names its writes and cleanup _(applied inline)_

### Design Decisions (awaiting user input)

#### DD-1: [Step 1] Live evidence for the list-issues call
| # | Option | Trade-off |
|---|---|---|
| 1 | Extend Manual check + SMOKE-TEST §2 step 1: log shows no lookup WARNING | No new step; proof arrives at the smoke run |
| 2 | User-run probe-first box in Step 1 | Earlier proof; blocks run-plan on the user |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261101-007)

#### DD-2: [Step 2] reports_link and CRLF bodies
| # | Option | Trade-off |
|---|---|---|
| 1 | `.rstrip("\r")` + CRLF test case | One token, no branch |
| 2 | Accept LF-only, prose note | Retry after a web edit duplicates |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261101-008)

#### DD-3: [Step 4] Failed File still consumes the session's File
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept; note in Report docstring and plan | Rare; reporter reruns |
| 2 | Reset report.filed on summary failure | Signature change + test |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261101-009)

#### DD-4: [Step 4] Stale sibling Edit/band/Track presses after filing
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept; prose note | Cosmetic, two clients needed |
| 2 | Guard them with report.filed | Consistent UI; more lines + test |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261101-010)

#### DD-5: [Step 4] Concurrent sibling-File test
| # | Option | Trade-off |
|---|---|---|
| 1 | Add asyncio.gather test like test_file_only_once | Pins the no-await rule |
| 2 | Accept the gap | Rule unpinned |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261101-011)

#### DD-6: [Step 4] Assert refusal log lines
| # | Option | Trade-off |
|---|---|---|
| 1 | caplog asserts + assert_no_member_text | Matches Steps 2-3 |
| 2 | Leave to grep | Weaker |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261101-012)

#### DD-7: [Step 5] SMOKE-TEST §2 step for the race
| # | Option | Trade-off |
|---|---|---|
| 1 | Append §2 step 7 | Durable owner procedure |
| 2 | Plan Manual checks only | Lost when plans are compacted |

**Labels:** kind=dd category=docs-wording reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261101-013)

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3: no deletions; github↔issues cycle avoided via predicate |
| Type annotations | [x] | #1: find_issue/_request/Report signatures checked |
| Error handling (status codes, exceptions, user feedback) | [x] | #2: GitHubError stages, DD-3 path, refusal replies |
| Test coverage (happy path, sad path, edge cases) | [x] | #5: test_github/test_issues/test_bot/test_intake |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6: fakes in conftest + test_issues covered |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4: no new deps/config; pyproject has pytest only |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4: log rules, fixed-text constants |

## Review — 2026-11-01 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/idempotent-filing/idempotent-filing.md blob 002daddaf9b7d5958e9ffa06ed0cfb766e09d64f

### Summary
Pass 1's fixes hold against the source; all six reviewers PASS with 0 critical and 0 major. Ready for implementation after the minor fixes below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 2 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 1 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 2 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 2 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 4 minor |

### To-Do: Mechanical Fixes (auto-applied)
- [x] Lookup-failure test fake gains ensure_label and a create_issue return _(applied inline)_
- [x] LOOKUP_URL "literal" parenthetical removed _(applied inline)_
- [x] Step 1 transport side_effect wording fits the error-path tests _(applied inline)_
- [x] Refusal log tests use interaction_id=4343 so the asserted id is the pressing interaction's _(applied inline)_
- [x] SMOKE-TEST *What it writes* count updated for §2 step 7 _(applied inline)_
- [x] README/SMOKE "retry" wording ties to F13 _(applied inline)_
- [x] Manual check cleanup names the Project item and label _(applied inline)_
- [x] Design decisions note: lookup is check-then-create; F13 keeps retries sequential _(applied inline)_

### Design Decisions (awaiting user input)

#### DD-1: [Step 1] Lookup trusts the author line, not the issue's author
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept; note it | Needs repo access + race; fixed by hand |
| 2 | Require performed_via_github_app | One more condition + test; field unverified live |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261101-016)

#### DD-2: [Step 4] Superseded concurrent-Edit preview expires and blanks its sibling
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept; note it (pre-existing, out of scope) | No control-flow change |
| 2 | Track newest preview on Report and stop the previous | Beyond F12's contract |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261101-017)

Pass 2 clean (0 critical, 0 major executable/external). Plan is ready for implementation.

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 |
| Type annotations | [x] | #1 |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 |

### Descriptive cleanup: 0 fixed, 0 dropped
(Descriptive findings were applied inline with each pass's mechanical fixes; anchor lint now reports 0 problems.)

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| Lookup-failure fake omits ensure_label | minor | subagent-1:correctness | verification_stopped_at_text | Pass 1 checked fake coverage for find_issue only | maybe | not logged (review_due: critical only) |
| Step 1 "each with" transport wording | minor | subagent-5:verification | verification_stopped_at_text | Blanket wording not checked per test | maybe | not logged (review_due: critical only) |
| LOOKUP_URL "literal" parenthetical left | minor | step-5b:mechanical-fix | fix_regression | Fix changed the value, not its description | yes | not logged (review_due: critical only) |
| Refusal-log ids indistinguishable (4242) | minor | step-5f:dd-application | fix_regression | DD-6 assertion added without checking fixture default | yes | not logged (review_due: critical only) |
| SMOKE *What it writes* count stale after §2 step 7 | minor | step-5f:dd-application | fix_regression | DD-7 added a filing without propagating to the write list | yes | not logged (review_due: critical only) |
| Check-then-create not atomic, unstated | minor | subagent-6:completeness | scoped_too_narrowly | Pass 1 didn't consider overlapping filings | maybe | not logged (review_due: critical only) |

### Plan-Creator Misses
6b: 0 misses

Step 7: skipped (nested; caller reviews assumed decisions)
