# Review: Roadmap Project placement (F6)

## Review — 2026-10-29
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/roadmap-project/roadmap-project.md blob 57a86b226aa8cb0ce3d51b75c5fffec29e18d7f4

### Summary
Sound plan whose three owner decisions are implemented faithfully; needs changes. The set-fields
mutation's option variables must be `String!` (live introspection), the Step 5 startup tests could
never pass as written (no `filing_check`), a parsing bug after filing would drop the link message,
and the failure note was false for a field-set failure. All fixed or decided below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 2 major, 3 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 1 major, 3 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 6 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 12 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 3 major, 6 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 6 major, 2 minor |

### Findings

#### Major (should fix)
- **[Step 3] SET_FIELDS_MUTATION variable types unstated; option ids are `String`, not `ID`** _(#1, #2, #6)_: `ProjectV2FieldValue.singleSelectOptionId` is `String`; a `ID!` declaration fails with `variableMismatch` (verified read-only).
- **[Step 3] Never-exercised mutations and org-permission token have no probe** _(#1)_: DD-4.
- **[Step 4] A non-GitHubError from the roadmap step drops the issue-link post** _(#2, #5, #6)_: DD-1.
- **[Step 4] ROADMAP_FAILED_NOTE false when only the field set failed** _(#2, #6)_: DD-2.
- **[Step 5] Startup project-check tests build IssueBot without filing_check** _(#3, #5)_: `_check_github_access` returns at once when `filing_check` is None.
- **[Step 1] `project = 3` appended to ONE_ROUTE_TOML lands in the last question table** _(#5)_: verified with tomllib.
- **[Step 6] Smoke-test update lacks its new live writes, setup and teardown** _(#6)_.
- **[Step 6] The App's org-wide Projects permission has no revert path or reach note** _(#6)_.
- **[Step 6] F6 Expected end state and Standing invariant 3 contradict the decisions** _(#4, #6)_: DD-3.

#### Minor (nice to fix)
- **[Step 5] `test_main_builds_github_client` sentinel lacks `project_fields`** _(#1, #2)_.
- **[Step 3] Missing `MappingProxyType` import; [Step 5] `ProjectCheck` alias and imports** _(#4)_.
- **[Step 3] Token assert can't tell tokens apart; [Step 2] name `check_access` in the mint test** _(#5)_.
- **[Step 6] README Status/Reporting stale; SMOKE-TEST troubleshooting rows; example `number` comment** _(#4)_.
- **[Step 7] Conditional box lacks a tick-as-N/A form** _(#3)_.
- **[Step 3] Stale cached ids (DD-5), null nodes (DD-6), concurrent lookup (DD-12), untested ValueError guard (DD-13)** _(#5, #6)_.
- **[Step 5] Log key route= vs repo_id= (DD-7); [Step 1] TargetConfig default (DD-8); [Step 3] add_to_project return (DD-9); [Step 1] example table validator (DD-10); [Step 2] shared fixtures (DD-11)** _(#3, #4, #5)_.

#### Descriptive (deferred to final cleanup)
- Step 1 pointer to a non-existent Step 6 to-do (fixed with the Step 1 fixer); `"node_id": 5` parameter form (fixed); "19 test lines" derived count; Step 7 carrier note (fixed); Step 6 invariant parenthetical (fixed); anchor-lint line citations.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 1: `project = 3` case inserted via `ONE_ROUTE_TOML.replace(...)`; example.routes.toml box rewritten as a direct instruction with a `number` source comment _(applied by fixing subagent)_
- [x] Steps 2-3: full SET_FIELDS_MUTATION with `String!` option vars; `MappingProxyType` import; token-payload assert; `check_access`/`create_issue` mint cases; parametrize tuple form _(applied by fixing subagent)_
- [x] Step 5: tests build `IssueBot(<project config>, filing_check=access, project_check=check)`; order via parent `Mock`; `ProjectCheck` alias and imports; sentinel gains `project_fields` _(applied by fixing subagent)_
- [x] Step 6: SMOKE-TEST What it writes / setup / teardown / troubleshooting; permission reach note and revert; README Status and Reporting _(applied by fixing subagent)_
- [x] Step 7: tick-as-N/A form; Owner-checks carrier note _(applied by fixing subagent)_

### Design Decisions (awaiting user input)

#### DD-1: [Step 4] Contain non-GitHubError from the roadmap step
**Context:** after filing, any other exception reaches PreviewView.on_error and the link message is never posted.

| # | Option | Trade-off |
|---|---|---|
| 1 | place_on_roadmap also catches Exception (WARNING, type only; returns False) + a RuntimeError test | Link always posts |
| 2 | Malformed-shape tests only | Proves parsing, no runtime guard |
| 3 | Accept | Parsing bug drops the link |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261029-004)

#### DD-2: [Step 4] Failure-note wording
| # | Option | Trade-off |
|---|---|---|
| 1 | One note: "Couldn't finish adding it to the roadmap; the owner can fix it by hand." | True at both stages |
| 2 | Two notes, three-state result | More code and tests |
| 3 | Keep wording | False for field-set failures |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261029-005)

#### DD-3: [Step 6] Align META-PLAN F6 Expected end state and Standing invariant 3
| # | Option | Trade-off |
|---|---|---|
| 1 | Step 6 edits META-PLAN: end state says names are config and ids are looked up; invariant 3 gains the optional `project` table exception | Run-feature's end-state check passes |
| 2 | Leave to fold-back with a plan note | End-state check meets contradicting text |

**Labels:** kind=dd category=docs-wording reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-010)

#### DD-4: [Step 3] Gate the never-exercised mutations and org token
| # | Option | Trade-off |
|---|---|---|
| 1 | Record read-only probes in Research Findings; owner smoke test against a test Project is the live gate before merge | No mid-run owner action |
| 2 | Probe-first live box | Agent live write, owner action mid-run |

**Labels:** kind=dd category=testing reversible=yes rework=low (second labeler: costly/high) · Recommended: 1
**Chosen:** 1 (asked, dd-261029-008)

#### DD-5: [Step 3] Stale cached Project ids
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept; comment + README restart sentence | No code |
| 2 | Drop that route's cached ids on a project-item/project-field GitHubError, with a test | Self-heals |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1
**Chosen:** 2 (asked, dd-261029-007; owner override)

#### DD-6: [Step 3] Null `fields.nodes` entries
| # | Option | Trade-off |
|---|---|---|
| 1 | Add a `None` node to the success fixture; non-dict nodes are skipped | Covers introspected nullability |
| 2 | Rely on isinstance wording | Untested |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-011)

#### DD-7: [Step 5] Startup project-check log key
| # | Option | Trade-off |
|---|---|---|
| 1 | `github project ok for repo_id=%s project=%s` / `github project check failed for repo_id=%s project=%s: …`, like the sibling access line | Ids only |
| 2 | `route=<name>` | First route= key |
| 3 | Both | Longer |

**Labels:** kind=dd category=naming-structure reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-012)

#### DD-8: [Step 1] TargetConfig.project default
| # | Option | Trade-off |
|---|---|---|
| 1 | No default; `_route` passes it; three direct test constructions gain `project=None` | Keeps no-defaults convention |
| 2 | Keep `= None` | Fewer test edits |

**Labels:** kind=dd category=data-schema reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261029-006)

#### DD-9: [Step 3] add_to_project return value
| # | Option | Trade-off |
|---|---|---|
| 1 | Keep `-> None`; F17 reshapes in its own plan | Scope stays F6 |
| 2 | Return the item id | Pre-builds for F17 |

**Labels:** kind=dd category=approach reversible=yes rework=low · Recommended: 1
**Chosen:** 2 (overturned at review; was assumed dd-261029-013)

#### DD-10: [Step 1] Validate the example's project table
| # | Option | Trade-off |
|---|---|---|
| 1 | `test_example_routes_shape` also runs `_route_project` on each example route | Mirrors `_route_questions` |
| 2 | Key presence only | Typos pass |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-014)

#### DD-11: [Step 2] Shared Project-route test fixtures
| # | Option | Trade-off |
|---|---|---|
| 1 | Step 2 adds `PROJECT` and `project_route`/`project_config` fixtures to tests/conftest.py; Steps 3-5 use them | One definition |
| 2 | Each step builds its own | Drift |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-015)

#### DD-12: [Step 3] Concurrent first lookup
| # | Option | Trade-off |
|---|---|---|
| 1 | Accept; one-line code comment | Same as token/label caches |
| 2 | asyncio.Lock + test | More code |

**Labels:** kind=dd category=error-handling reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (asked, dd-261029-009)

#### DD-13: [Step 3] Test the no-project ValueError guard
| # | Option | Trade-off |
|---|---|---|
| 1 | Add the test (raises, no transport call) | Covers the guard |
| 2 | Leave untested | — |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-016)

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3/#4 read github.py, bot.py imports; MappingProxyType, Awaitable/Callable added |
| Type annotations | [x] | #1 read config.py, github.py, bot.py |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced intake → filing_hook → _post_outcome |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 read conftest and all affected test files |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 read META-PLAN, ROADMAP, docs |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 read CLAUDE.md, README, example.routes.toml; no linter configured |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 checked log lines against CLAUDE.md logging rules |

## Review — 2026-10-29 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/roadmap-project/roadmap-project.md blob 826e357b2f96f9d5a09e6c0c919b4cfd13be98b7

### Summary
Pass 1's fixes and decisions were re-verified against the source and hold; no regressions of
consequence. Pass 2 is clean (0 critical, 0 major): plan is ready for implementation after the
minor fixes below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 2 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 3 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 0 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 6 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 4 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 5 minor |

### Findings

#### Minor (nice to fix)
- **[Step 6] Troubleshooting row says "add it to the Project by hand" for every stage** _(#6)_: wrong after a project-field failure (DD-2's issue).
- **[Step 6] README never says to grant the Projects permission before adding a `project` table** _(#6)_.
- **[Step 6] Existing smoke-test checks still describe a two-line link post** _(#6)_; **README § Status link-message text** _(#4)_; **token-probe troubleshooting for a missing grant** _(#4)_; **wrong Project `number` as a `stage=project status=200` cause** _(#1, #2)_.
- **[Step 3] `project_fields` variables and `effort_option_ids` content left to inference** _(#2, #6)_; **test imports/URL constant listed unevenly** _(#4)_.
- **[Step 4] `fake_github`'s two return branches** _(#2)_; **[Step 2] 401 test call sequence unprescribed** _(#5)_; **[Step 5] `project_check=None` case passes in Red** _(#5)_.
- **[Step 5] `collections.abc` import placement breaks the repo's import order** _(#1, #4)_; **docstring sweep misses IssueBot, setup_hook, GitHubClient, TargetConfig** _(#4)_.
- **[Step 6] F6 Dependencies paragraph still says "field IDs are per-route config"** _(#4, #6)_ (descriptive).
- **[Step 1] No-value-leak test passes in Red** _(#5)_: DD-14. **[Step 4] Roadmap note texts unpinned** _(#5)_: DD-15.

### To-Do: Mechanical Fixes (auto-applied)
- [x] All Pass 2 minor mechanical findings above _(applied by fixing subagent)_

### Design Decisions (awaiting user input)

#### DD-14: [Step 1] No-value-leak test must fail in Red
| # | Option | Trade-off |
|---|---|---|
| 1 | `status = ["Secret words"]`; assert exact `must be a string` message and absence of the text | Fails in Red, passes in Green |
| 2 | Drop the test | Exact-message cases already cover it |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-017)

#### DD-15: [Step 4] Pin the roadmap note texts
| # | Option | Trade-off |
|---|---|---|
| 1 | `test_roadmap_notes_are_fixed_text` in tests/test_threads.py, like `test_filing_error_reply_is_fixed_text` | Member-facing text pinned |
| 2 | Leave unpinned | Typos pass |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1
**Chosen:** 1 (assumed: dd-policy, dd-261029-018)

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

Pass 2 clean (0 critical, 0 major executable/external). Plan is ready for implementation.

### Descriptive cleanup: 11 fixed, 0 dropped

### Missed-Finding Root Causes
Step 6: 0 misses (Pass 2 found only minor findings; none shares an open unit + cause_class pair).

### Plan-Creator Misses
6b: 0 misses (Pass 1's critical/major Correctness and Integration findings concerned unstated GraphQL variable types and unprobed live calls, not wrong facts about existing code).
