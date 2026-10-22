# Review: Multi-target routes and multi-instance deployment (F8)

## Review — 2026-10-22
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/multi-target/multi-target.md blob 6cfbabeaf7456e8c520226de587c73d14b4f2186

### Summary
The design is sound and the coupling is correctly mapped. All six reviewers failed the plan on
executable gaps, which are fixed below: an unsatisfiable invariant-2 grep, a fixture writing into a
directory that is never created, a `Config.from_env` key-order instruction that would misorder keys,
and Owner checks that mis-state shared-token logging and omit live-write setup and teardown. The
rest are minor test-specificity and doc-coverage items, now applied.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 2 major, 6 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 1 major, 4 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 4 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 1 major, 8 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 2 major, 8 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 7 minor |

### Findings

#### Major (should fix)
- **[Step 5] Invariant-2 gate `grep -rn 'exc_info' issue_bot` can never pass** _(#1, #5)_: it matches
  `bot.py`'s comment and `on_error`'s `sys.exc_info()`. It is now `grep -rnE 'exc_info *=|logger\.exception'`.
- **[Step 1 → Step 3] `write_routes` never creates its directory** _(#1, #2, #3, #4, #5, #6)_:
  `two_route_config` writes into `tmp_path / "two"`, which raises `FileNotFoundError`. The helper now
  does `mkdir(parents=True, exist_ok=True)`.
- **[Step 2] "Keep `github_org` as a local, read before the App keys"** _(#3)_: read literally, this
  reads `GITHUB_ORG` before `DISCORD_TOKEN` and breaks the first-missing-key order. The plan now reads
  the four leading keys into locals in `ALL_KEYS` order.
- **[Owner checks] Shared-token check says only container A logs** _(#6)_: container B logs
  `ignored bug outside this instance's routes …` by design.
- **[Owner checks] Live writes have no prerequisites, write list or teardown** _(#6, #4)_: the scratch
  repo was torn down on 2026-10-18, the second route's labels must exist, and extra test channels
  are needed.

#### Minor (nice to fix)
- **[Step 3] `two_route_config` mutated the shared `test_env`** _(#2, #5)_: it now uses a copy.
- **[Step 1] Route-name check must use `fullmatch`** _(#1)_.
- **[Step 1] Unknown-key TOML variants appended to `ONE_ROUTE_TOML` land in `labels`** _(#2)_.
- **[Step 1] The "empty" route file named explicitly as zero-byte** _(#6)_.
- **[Step 2] Test-helper callers enumerated** (`create`, `filled_modal`) _(#3)_.
- **[Step 2/4/5] Grep gates widened** to all removed keys, with `GITHUB_REPO\b` and a note that an expected-empty grep exits 1 _(#4, #5)_.
- **[Step 1/2] Import placement specified** _(#4)_.
- **[Step 3] Five-call transport sequence pinned** _(#1, #2, #3, #5, #6)_.
- **[Step 4] Stale single-target prose in README/SMOKE-TEST added to the to-dos** _(#1, #4, #6)_.
- **[Step 5] Bad-route-file exit-2 test made definite**: see DD-1 _(#1, #2, #5)_.
- **[Step 2] Refusal wording**: see DD-2 _(#1, #4)_.
- **[Step 3] No bot-level test for `ignore` wiring**: see DD-3 _(#5)_.
- **[Step 3] Second route's name/category check untested**: see DD-4 _(#5)_.

#### Descriptive (deferred to final cleanup)
- Stored test count "216 tests plus the new ones" _(#1, #3, #4, #5, #6)_; red check is a collection
  error, not test failures _(#5)_; contract section lacks the new `intake_command`/`channel_problems`
  seams _(#4)_; line citations in Research Findings (anchor lint, 6 hits); route-file error locator
  (DD-5) and old-key mapping (DD-6) _(#6)_.

### Verification Gaps
- **Step 3**: no bot-level test that `UNROUTED_COMMANDS=ignore` reaches the commands (DD-3), and none
  that a present second route's channel is name/category-checked (DD-4).

### To-Do: Mechanical Fixes (auto-applied)
Applied by one sequential fixer, since all the fixes edit the same plan file and parallel fixers
could lose each other's edits. Its self-check covered the whole document, so it doubles as the
whole-document gate re-run.
- [x] M1 Invariant-2 gate is now `grep -rnE --include='*.py' 'exc_info *=|logger\.exception' issue_bot` _(dry-run: no output today, exit 1; a variant with `exc_info=True` matches)_
- [x] M2 `write_routes` creates its directory
- [x] M3 `Config.from_env` reads the four leading keys into locals in `ALL_KEYS` order
- [x] M4 Shared-token owner check: B logs only `ignored …`
- [x] M5 Owner checks gain Before/Writes/teardown bullets (scratch repo re-created, labels, extra channels, image from this branch)
- [x] M6 `two_route_config` uses `{**test_env, "ROUTES_PATH": …}`
- [x] M7 `ROUTE_NAME_PATTERN.fullmatch`
- [x] M8 Stale README/SMOKE-TEST passages added to Step 4 (intro, Discord/GitHub App setup, Configuration opening, SMOKE-TEST §3/§4/§5, troubleshooting row)
- [x] M9 TOML variants are edited in place, not appended
- [x] M10 Five-call transport sequence pinned (`token_response()`/`issue_response()`)
- [x] M11 Callers of `create`/`filled_modal` enumerated; `test_handler` included
- [x] M12 Old-key gates widened with `--include='*.py'` and `GITHUB_REPO\b`; an expected-empty grep exits 1, which is the pass
- [x] M13 Import placement in config/intake/bot/test_issues
- [x] M14 Zero-byte route file named
- [x] D1–D4 Stored count dropped, red check is a collection error, contract seams added, line citations replaced (anchor lint: 0)

### Design Decisions (awaiting user input)

#### DD-1: [Step 5] Where the bad-route-file entry-point test lives
**Context:** `test_main_exits_on_config_error` stops at `DISCORD_TOKEN`, so nothing exercises
`__main__`'s exit 2 on a bad `ROUTES_PATH`. Step 5 made the test conditional and called it a
"parametrized case" of a test that isn't parametrized.

| # | Option | Trade-off |
|---|---|---|
| 1 | Definite `test_main_exits_on_bad_route_file` in Step 2's Red: bot | Lands with the behaviour it tests |
| 2 | Unconditional test in Step 5 | Adds a test in the verify-only step |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261022-009)

#### DD-2: [Step 2] Refusal wording with several intake channels

| # | Option | Trade-off |
|---|---|---|
| 1 | Keep F10's `INTAKE_REFUSAL` | Matches the spec ("F10's ephemeral refusal"); no churn |
| 2 | Reword to "an intake channel" | More accurate with several routes; vaguer with one |

**Labels:** kind=dd category=ux reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (asked, dd-261022-014)

#### DD-3: [Step 3] Bot-level test for `UNROUTED_COMMANDS=ignore` wiring

| # | Option | Trade-off |
|---|---|---|
| 1 | Add an `IssueBot(…ignore…)` tree-callback test (557 silent, 555 opens the modal) | Pins DD-1-of-planning's core behaviour |
| 2 | Rely on the `intake_command` unit tests and the owner check | A wrong wiring passes every test |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261022-010)

#### DD-4: [Step 3] Second route's present-but-mismatched channel at `on_ready`

| # | Option | Trade-off |
|---|---|---|
| 1 | Add a test with `make_channel(channel_id=556)` asserting both WARNING lines | Covers "name/category check for every route" |
| 2 | Accept the missing-556 test | Checks the per-route id only |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261022-011)

#### DD-5: [Step 4] How the owner locates a TOML error the ConfigError deliberately won't quote

| # | Option | Trade-off |
|---|---|---|
| 1 | Troubleshooting row with a `tomllib` one-liner, plus a BOM note | Docs only, no special case |
| 2 | Accept a BOM in code (`utf-8-sig`) plus a test | A carve-out (C4) |

**Labels:** kind=dd category=docs-wording reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261022-012)

#### DD-6: [Step 4/5] Old env keys → route-field mapping for the owner's existing `.env`

| # | Option | Trade-off |
|---|---|---|
| 1 | A sentence in SMOKE-TEST §0 | Conflicts with the old-key grep gate |
| 2 | In the PR description (Step 5 writes it into the final report) | No doc churn; reaches the owner at merge |
| 3 | Nothing | The fail-fast error alone |

**Labels:** kind=dd category=docs-wording reversible=yes rework=low · Recommended: 2

**Chosen:** 1 + README upgrade note (overturned at review; was assumed dd-261022-013)

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 read config/intake/bot imports and pyproject; no lint config. Placement added (#4) |
| Type annotations | [x] | #1 checked signatures against config.py/intake.py/bot.py |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced the callback, modal and filing paths, and discord.py's dispatch_modal |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 read conftest and every touched test file |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 covered the env migration (DD-6), kept contracts and the Owner live writes |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 read example.env, .dockerignore, requirements; no new dependency |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 checked against project/global CLAUDE.md and the logging rules |

## Review — 2026-10-22 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/multi-target/multi-target.md blob bcd113f42c0191895bb2eb1750cd6384a97a6a99

### Summary
Every Pass 1 resolution held when re-verified against the source. Five reviewers pass; Completeness
fails on two external majors in the Owner checks (the shared-token run never switches `.env` to the
container key path or stops the single-process bot, and teardown leaves the containers running,
`UNROUTED_COMMANDS=ignore` set and the extra channels in place). The rest are minor
specificity items: test-side imports, the missing-`labels` error path, setup_hook's sync log line
in an "exactly" assertion, the 556 submit's interaction channel, a few README/CLAUDE.md passages,
a stale `.dockerignore` header, threads in ignore mode, and the ignore-mode `.env` reset.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 3 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 4 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 4 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 7 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 5 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 4 minor |

### Findings

#### Major (should fix)
- **[Owner checks] Shared-token run keeps the host key path and the running local bot** _(#6)_.
- **[Owner checks] Teardown leaves containers, `UNROUTED_COMMANDS=ignore` and the extra channels** _(#6, #2)_.

#### Minor (nice to fix)
- Test-side imports for the new names _(#1, #2, #3, #4)_; the missing-`labels` path raises `… is required` _(#1, #6)_;
  "the logs are exactly" must filter out setup_hook's sync line _(#1, #2)_; the 556 submit test sets the interaction's channel
  _(#2)_; Step 2 log tests call `assert_no_member_text` _(#3)_; a tick-as-N/A form for "investigate and fix" _(#3)_; README
  passages, the troubleshooting directory wording, the `.dockerignore` header and the CLAUDE.md intro _(#4, #6)_; ignore mode
  in a thread _(#6)_; README Status paragraph _(#6)_; `docker run` flags and the stop command _(#6)_.
- **[Step 5] Old-key mapping has no carrier to the PR**: see DD-7 _(#3, #4)_.
- **[Step 2] `Config.routes` is read-only only through `load_routes`**: see DD-8 _(#4)_.
- **[Step 2/4] Config red check names which tests fail; positive doc gates for the `docker run` set** _(#5)_.
- **[Step 3] Continue-after-failure pinned only for `GitHubError`**: see DD-9 _(#5)_.

### Design Decisions (awaiting user input)

#### DD-7: [Step 5] How the old-key mapping reaches the PR body

| # | Option | Trade-off |
|---|---|---|
| 1 | `### PR notes` section in the committed plan, added to the PR body by `/run-feature` | Durable, with an explicit carrier |
| 2 | Final report only | May reach neither the PR nor the user |

**Labels:** kind=dd category=docs-wording reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261022-015)

#### DD-8: [Step 2] Config freezes its own `routes`

| # | Option | Trade-off |
|---|---|---|
| 1 | `Config.__post_init__` wraps `routes` in a `MappingProxyType`, like `TargetConfig.labels` | Matches the convention and the Contract |
| 2 | Rely on `load_routes`' proxy | A directly built `Config` would be mutable |

**Labels:** kind=dd category=approach reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (asked, dd-261022-016)

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3, #1, #2 and #4 converged on the test-side imports |
| Type annotations | [x] | #1 |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 re-traced callback/modal/filing and ignore mode |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 PASS (5 minor): every F8 end-state bullet and delta has a test, and the gates were dry-run |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6, with the Owner live-write lifecycle |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 |

#### DD-9: [Step 3] Continue-after-failure covers the generic-exception branch

| # | Option | Trade-off |
|---|---|---|
| 1 | Parametrize the two-route failure test over `GitHubError` and `RuntimeError("Secret exception words")` | Pins both `except` branches' `continue` |
| 2 | Cover only `GitHubError` | A leftover `return` in the generic branch passes |

**Labels:** kind=dd category=testing reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261022-017)

### To-Do: Mechanical Fixes (auto-applied)
- [x] All Pass 2 mechanical findings applied by one sequential fixer (test-side imports, the missing-`labels` path, filtered setup_hook log assertion, the 556 interaction channel, `assert_no_member_text`, tick-as-N/A, the Config red check, positive doc gates, README/SMOKE/CLAUDE.md/.dockerignore passages, threads in ignore mode, `docker run -d --rm --name` lines, Owner checks setup and teardown). Anchor lint: 0.

## Review — 2026-10-22 (Pass 3)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/multi-target/multi-target.md blob 226090ab873a5f9eeeb9287a592cdff43f2fa34f

### Summary
Clean: all six reviewers pass with 0 critical and 0 major findings, and every Pass 1–2 resolution held
against the source. Ten minor specificity items remain, all applied: what `get_channel` returns for 555 in the
two-route `on_ready` tests, closing `load_routes`' file handle, the `test_config` import placement,
a green check after Green: Config, fixed content for the no-`routes`-table case, a red-check command for
the drift tests, splitting the parametrized DD-9 case's extra assertions, the carrier from Owner checks to
`/run-feature`'s Phase B, F6's optional per-route keys in the Contract, and DD-10.
Pass 3 clean (0 critical, 0 major executable/external). Plan is ready for implementation.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 0 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 1 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 0 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 3 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 4 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 3 minor |

### Design Decisions

#### DD-10: [Step 4] Detached `--rm` containers hide a startup configuration error

| # | Option | Trade-off |
|---|---|---|
| 1 | Prose note: "No such container" means it exited at startup, so rerun without `-d` | Docs only |
| 2 | Drop `--rm` and add `docker rm` to README and teardown | More steps, and leftover containers |

**Labels:** kind=dd category=docs-wording reversible=yes rework=low · Recommended: 1

**Chosen:** 1 (assumed: dd-policy, dd-261022-018)

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3, #4 |
| Type annotations | [x] | #1 |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 |

### Descriptive cleanup: 0 fixed, 0 dropped
Every descriptive finding was applied inline by its pass's fixer (stored count, red-check wording,
contract seams, line citations, contract key note); anchor lint reports 0 problems on the final plan.

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| Pass 1's Owner-checks teardown left the containers, `UNROUTED_COMMANDS=ignore` and the extra channels | major | step-5b:mechanical-fix | fix_regression | The fixer wrote teardown for the setup it was told about, without walking every state the checks change | yes | not logged |
| Pass 1 missed the shared-token run keeping the host key path and the local bot running | major | subagent-6:completeness | scoped_too_narrowly | Live-write review didn't walk the local-to-container config handoff against SMOKE-TEST §4 | yes | not logged |

(Both were `not logged`: plan-reviewer is in `review_due`, which logs critical misses only.)

### Plan-Creator Misses
6b: 0 misses (Pass 1's Correctness/Integration majors concerned the plan's own new gates and fixtures, not wrong facts about existing code.)

Step 7: skipped (nested; caller reviews assumed decisions)
