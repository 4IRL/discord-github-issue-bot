# Push Review: feature/roadmap-project

## Review 1
Generated: 2026-10-29 09:19
Comparison: origin/main ef5499a7c8c8d53ee21e7f13781ae438a21e61da..8588d8150a07d4e51d1a39f23d0f03cd9284f598
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
GraphQL uses variables; the Projects permission is requested only for Project routes; new logs carry only type, ids, URLs, stage and status.

#### 2. Correctness — PASS
Token cache keying, GraphQL error handling, cache invalidation, the never-raising roadmap step and the reply notes behave as intended. No findings.

#### 3. Simplicity & Conciseness — PASS
- (minor) `issue_bot/bot.py` `_check_project`: two near-identical except branches (optional collapse; matches the access-check style).
- (minor) `issue_bot/github.py` `_single_select_options` / `_parse_project_fields`: long isinstance guard chains (intentional defensive parsing).
- (minor) `issue_bot/github.py` `_owner` / `_project_key`: tiny helpers (optional inline).

#### 4. Test Coverage — PASS
- (minor) `tests/test_bot.py`: the success-path filing_hook test should assert the posted reply contains `ROADMAP_ADDED_NOTE`.

#### 5. Completeness & Cleanup — PASS
- (minor) `plans/ROADMAP.md` / `plans/META-PLAN.md` bookkeeping: handled by /run-feature's fold-back after merge.
- (minor) `issue_bot/github.py` `_project_key`: bare `assert` as a caller-contract guard (stripped under `python -O`).

#### 6. Consistency & Style — PASS
- (minor) `issue_bot/bot.py` `ProjectCheck` alias lives in bot.py while `FilingCheck` lives in intake.py.
- (minor) `issue_bot/config.py` `_route_project`: local name `where_p` is cryptic.

#### 7. Integration Risk — PASS
- (minor) `issue_bot/github.py` Project cache keyed by `(owner, ProjectConfig)` relies on ProjectConfig staying hashable; F17 must not add a dict field to it.
- (minor) `TargetConfig.project` has no default: earlier-cut F16/F17 branches must rebase after merge.

#### 8. Error Handling & Silent Failures — PASS
- (minor) `project_fields` collapses every lookup mismatch into `GitHubError("project", 200)`; the operator can't tell which name is wrong.
- (minor) `place_on_roadmap`'s catch-all (DD-1) logs a programming bug at WARNING, like an expected failure.
- (minor) A project-field failure logs no item id (the stage already distinguishes it).

#### 9. Type Design — PASS
- (minor) `ProjectFields.effort_option_ids` keyed by `str` rather than `Complexity`.
- (minor) `ProjectConfig` has no `__post_init__` (consistent with `Question`: validation lives in the loader).

### To-Do: Required Changes

- [ ] **Assert the success note in the filing_hook roadmap test** — `tests/test_bot.py` — in the Project-route success test, assert the posted thread text ends with `"\n" + ROADMAP_ADDED_NOTE`.
- [ ] **Replace the bare assert in `_project_key`** — `issue_bot/github.py` — raise `ValueError("route has no project")` like `project_fields` does, so the guard survives `python -O`.
- [ ] **Rename `where_p`** — `issue_bot/config.py` `_route_project` — to `project_where`.
- [ ] **Record the ProjectConfig hashability constraint for F17** — `plans/META-PLAN.md` (fold-back's kept contract for F6) — note that the Project cache keys on `ProjectConfig`, so F17 must keep it hashable (tuple of pairs, or `field(hash=False, compare=False)`).
- [ ] **Decide whether lookup mismatches get a reason token** — `issue_bot/github.py` `_parse_project_fields`, `issue_bot/bot.py` `_check_project` — optional: a fixed reason (`project-missing`, `status-field`, `status-option`, `effort-field`, `effort-band`) in the startup log, carrying no response text.
- [ ] **Decide whether non-GitHubError roadmap failures log at ERROR** — `issue_bot/issues.py` `place_on_roadmap` — optional, so a bug is distinguishable from an expected GitHub failure.
- [ ] **Optional tidy-ups** — `issue_bot/bot.py` (collapse `_check_project` excepts; move `ProjectCheck` beside `FilingCheck`), `issue_bot/github.py` (`effort_option_ids: Mapping[Complexity, str]`; inline `_owner`).

6b: skipped (Review 1)

## Review 2
Generated: 2026-10-29 09:56
Comparison: origin/feature/roadmap-project bc741b79d8e2749c8fb2cb9f7e811e303c226d54..06fb3d739c1c5d05792a6316e4caedd2701197a9
Verdict: **PUSHED WITH MINOR FINDINGS**

Scope: the merge-gate overturn of DD-9 (dd-261029-013), `add_to_project` returns the Project item id.

### Results by Reviewer

#### 1. Safety & Security — PASS
No new inputs, secrets or logging.

#### 2. Correctness — PASS
The id is returned only after both mutations succeed; the failure path is unchanged.

#### 3. Simplicity & Conciseness — PASS
- (minor) `issue_bot/github.py` `add_to_project`: no caller uses the returned id yet (built for F17 by the owner's DD-9 decision).

#### 4. Test Coverage — PASS
Both success-path tests assert the id; fakes updated.

#### 5. Completeness & Cleanup — PASS
Docstring, plan and review records match.

#### 6. Consistency & Style — PASS

#### 7. Integration Risk — PASS
The only production caller (`place_on_roadmap`) ignores the value.

#### 8. Error Handling & Silent Failures — PASS

### To-Do: Required Changes

- [ ] **Use the returned item id in F17** — `issue_bot/issues.py` `place_on_roadmap` — F17's Track write consumes `add_to_project`'s return value; no change in F6.

6b: 0 misses
