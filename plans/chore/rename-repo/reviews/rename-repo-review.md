# Review: Rename to discord-github-issue-bot (F9)

## Review — 2026-10-18
Plan snapshot: /home/rmila/Code/c4i-issue-bot plans/chore/rename-repo/rename-repo.md blob 9df90a9104766bb42629d7a3d6b57f4360818b9a

### Summary
The in-repo doc edits were accurate (every factual claim matched the repo). The gaps were all
in the hand-offs to `/run-feature` and the owner: pre-merge end-state facts with no
reconciliation, a settings.json change with no branch to land on, and an Owner checklist
whose "re-checked at fold-back" claim had no carrier. All are fixed below; needs a second
pass to confirm.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 3 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 3 major, 4 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 2 major, 3 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 1 major, 4 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 6 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 4 minor |

### Findings

#### Major (should fix)
- **[Step 4] `/run-feature` Phase A step 8 checks Expected-end-state facts that can't hold before merge** _(Subagents #2, #3, #5)_: `gh repo view 4IRL/<new-name>`, the origin URL, and META-PLAN's literal `grep -rn` (which also hits `.venv/` and `.claude/settings.json`) can't pass until the owner renames the repo after merge. No carrier told step 8 so. → DD-1.
- **[Owner checklist] settings.json commit has no branch** _(Subagents #2, #3, #4, #6)_: after merge, `main` is forbidden and the fold-back's `/git-push docs-only` stops on a path outside `plans/`. → DD-2.
- **[Owner checklist] "re-checked at F9's fold-back" has no carrier** _(Subagents #2, #4, #6; minor in #3, #5 for Step 4's copy-to-final-report box)_: `/run-feature` has no checklist step, and a step subagent's final report reaches only the `/run-plan` orchestrator. → DD-3.

#### Minor (nice to fix)
- **[Step 1] Inline `docker …` spans trigger `/run-plan` Phase 0's Docker check** _(#3)_.
- **[Step 4] End-state checks were absence-only** _(#5)_.
- **[Steps 3, 4] `git diff main` compares against main's tip, not the merge base** _(#5)_.
- **[Steps 1, 2, 4] Expected-empty gates exit 1 on success** _(#5)_.
- **[Step 3] Which PR link form F9's own ledger cell uses** _(#2)_.
- **[Owner checklist] No `git remote set-url` command** _(#2, #6)_.
- **[Owner checklist] Fold-back lookup uses `feature/<slug>`; F9's head is `chore/rename-repo`** _(#2)_. Also a `/run-feature` skill gap (hard-coded `feature/` prefix).
- **[Owner checklist] skill-config title line also carries the old name** _(#1, #4)_.
- **[Owner checklist] History move must precede any session in the new folder** _(#4)_.
- **[Owner checklist] settings.local.json may name the old path** _(#2)_.
- **[Owner checklist] Write check doesn't prove the settings item** _(#3)_: resolved by DD-3's per-item checks.
- **[Research Findings] Assumed-starting-state checks unrecorded** _(#6)_.

#### Descriptive (deferred to final cleanup)
- Stored test count `153` and a duplicate suite box in Step 5 _(#1, #4, #5)_.
- "13-file Python repo" stored count _(#1)_.
- Line citations `README.md:1` etc. in Research Findings (anchor lint).
- Trust prompt expected after the move (`~/.claude.json` keyed by old path) _(#6)_.
- Optional cleanup of a locally built `issue-bot` image _(#6)_: not applied (nothing deployed; owner's call).

### To-Do: Mechanical Fixes (auto-applied)
Applied inline by the orchestrator, in sequence (several fixes shared anchors in the Owner checklist, so parallel fixers would have collided).
- [x] Step 1 Docker-tag to-do reworded so no inline span starts with `docker`.
- [x] Steps 1, 2, 4: "(exit status 1 is the expected, passing result)" on expected-empty gates.
- [x] Steps 3, 4: diffs against `$(git merge-base main HEAD)`.
- [x] Step 4: positive gates for the new name, `4IRL GitHub org` openings and the Sequencing sentence; Steps 1 and 2 require those exact phrases.
- [x] Step 3: note on F9's own in-review link form.
- [x] Research Findings: Assumed-starting-state bullet.
- [x] Owner checklist: pre-rename PR/stash item, `git remote set-url`, skill-config title, history move reordered with the nesting warning, fold-back head-branch note.
- [x] Descriptive cleanup: Step 5 merged into one box without the count; "small Python repo"; line citations replaced by names; trust-prompt note.

### Design Decisions (awaiting user input)

#### DD-1: [Step 4] Pre-merge facts in F9's Expected end state
**Context:** `/run-feature` step 8 checks every listed fact before `/git-push`; three can't hold until after the merge and owner rename.

| # | Option | Trade-off |
|---|---|---|
| 1 | Carrier note in plan + Verification-log record | META-PLAN untouched; the orchestrator reads the note |
| 2 | Amend META-PLAN's F9 section | Self-documenting in META-PLAN; widens Step 3's scope and diff gate |

**Chosen:** Option 1 — Step 4 gained a *Pre-merge end state* note and a to-do recording the reconciliation in the Verification log.

#### DD-2: [Owner checklist] Where the settings.json change lands
**Context:** agents can't write `.claude/settings.json`; after merge no branch works.

| # | Option | Trade-off |
|---|---|---|
| 1 | Owner hand-edits on `chore/rename-repo`, `allowWrite` lists both paths; rides F9's PR | No extra PR; old path is a harmless leftover; needs an owner edit before Step 4 (canonical stop) |
| 2 | Separate PR after the folder move | Keeps F9's PR docs-only; one more full-review PR before fold-back |

**Chosen:** Option 1 — Step 4's first to-do checks for the owner's edit (canonical stop if missing) and stages it; the grep and name-only gates allow it; the Owner checklist item became a check.

#### DD-3: [Owner checklist] Carrier for the checklist
**Context:** `/run-feature` has no checklist step and step reports don't reach the owner.

| # | Option | Trade-off |
|---|---|---|
| 1 | Read-only check per item; owner runs them before the fold-back; orchestrator prints the checklist at Phase B | No skill change; relies on the owner running the checks |
| 2 | Same, plus log a `/run-feature` skill miss | Adds a ledger entry for a future skill gate |

**Chosen:** Option 1 — each item has a **Check**, the heading says the owner runs them, Step 4's copy box became a re-read box with a fixed final-report line, plus an orchestrator note for Phase B.

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding (applied; Pass 2 confirms)

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | No code changes; #3 confirmed |
| Type annotations | [x] | No code changes |
| Error handling (status codes, exceptions, user feedback) | [x] | No code paths touched; #2 traced skill hand-offs instead |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 dry-ran every gate; suite passes |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6: remote, venv, settings, history, index |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 read settings.json, skill-config, example.env |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 read project/global CLAUDE.md |

## Review — 2026-10-18 (Pass 2)
Plan snapshot: /home/rmila/Code/c4i-issue-bot plans/chore/rename-repo/rename-repo.md blob d94cf08f6fa12a6dcb6d84d6e7f5ef97bf568248

### Summary
Pass 1's resolutions held against the real files and skills (staging the write-denied
settings.json works; the two-path JSON parses; every gate fails on its defect state and
passes on a correct one). Pass 1's own fixes introduced four new gaps in the settings-edit
gate, the owner-edit timing and the fold-back hand-off; all are fixed below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 3 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 3 major, 1 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 2 major, 2 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 4 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 1 major, 2 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 1 major, 4 minor |

### Findings

#### Major (should fix)
- **[Step 4] Settings gate `git diff -- .claude/settings.json` is empty once the edit is staged or committed** _(#2, #3, #5; minor in #1, #4)_: a per-step commit sweeps the owner's edit in, and the gate then raises a false UNRESOLVED stop. Fixed: diff against `$(git merge-base main HEAD)`.
- **[Step 4] Owner-edit check runs after three commits, with no resume path** _(#2, #3)_ → DD-4.
- **[Step 3] META-PLAN's owner pointer is stale and contradicts DD-2/DD-3** _(#2)_ → DD-5.
- **[Step 4] Phase B "both confirmed" would fold back from the old folder before the Owner checklist** _(#6)_: Fixed: the orchestrator note tells the owner to leave "PR merged" unconfirmed in this session.

#### Minor (nice to fix)
- **[Step 4] `feature/<slug>` also hard-coded in Phase A step 10 and phase detection** _(#1, #2, #3, #6)_: the orchestrator note now covers every use.
- **[Step 3] Unsupported claim about which link form step 10 uses** _(#1)_: reworded.
- **[Step 2] Wrapped ROADMAP sentence would fail the phrase gate** _(#5)_: phrases must stay on one line.
- **[Step 4] No positive gate for the ROADMAP End-state rewrite** _(#5)_: `configured intake channels` gate added.
- **[Step 4] Verification log omits DD-2's settings deviation** _(#3)_: added.
- **[Owner checklist] Stronghold's own META-PLAN names c4i-issue-bot; the sweep doesn't fix it** _(#4)_: item added.
- **[Owner checklist] Write-check item has no Check** _(#4, #6)_: Check added (proved during fold-back, the stated exception).
- **[Owner checklist] GitHub rename has no revert note** _(#6)_: added.
- **[Owner checklist] settings.local.json sub-item has no check** _(#6)_: not applied; #4 confirmed settings.local.json names no paths today.

### To-Do: Mechanical Fixes (auto-applied)
Applied inline by the orchestrator, in sequence.
- [x] Settings gate diffs against the merge base; `git add` noted as a no-op if already committed.
- [x] Orchestrator note: `chore/rename-repo` for every `feature/<slug>`; leave Phase B's "PR merged" unconfirmed.
- [x] Step 3 link-form note reworded; Step 2 one-line phrase rule; `configured intake channels` gate; Verification-log DD-2 note.
- [x] Owner checklist: intro exception, rename revert note, write-check Check, stronghold META-PLAN item.
- [x] Whole-document re-run: anchor lint, stale `git diff -- .claude` / "re-checked at" sweep, and the new Step 3 gates dry-run on a scratch copy of META-PLAN (pointer gate: exit 1 now, exit 0 after the edit).

### Design Decisions

#### DD-4: [Step 4] Where the owner-edit check lives
| # | Option | Trade-off |
|---|---|---|
| 1 | Move the check and stop to Step 1's first to-do, with a resume line | Fails before any edit or commit |
| 2 | Keep it in Step 4, add a resume line | Smaller change; a stop lands after three commits |

**Chosen:** Option 1 — the check, staging and canonical stop are Step 1's first to-do, with **Resume:** `/run-plan rename-repo`, then `/run-feature F9` at Phase A step 7. Step 4 keeps a merge-base confirmation box.

#### DD-5: [Step 3] Fix META-PLAN's owner pointer in this PR
| # | Option | Trade-off |
|---|---|---|
| 1 | Widen Step 3 to edit *Shortest path* items 2–3 | The owner's durable carrier points at the right checklist |
| 2 | Leave META-PLAN alone | Relies on in-session carriers only |

**Chosen:** Option 1 — Step 3 edits both items, and its diff gate allows them plus a pointer gate and a "re-checks the checklist" absence gate.

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding (applied; Pass 3 confirms)

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | No code changes |
| Type annotations | [x] | No code changes |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced skill hand-offs |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 mutation-tested every gate on a clone |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6, #4 (stronghold META-PLAN) |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 parsed the two-path JSON |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 |

## Review — 2026-10-18 (Pass 3)
Plan snapshot: /home/rmila/Code/c4i-issue-bot plans/chore/rename-repo/rename-repo.md blob aaccc3ba11cbe157bd562cba4fcd66f28e7b1925

### Summary
All six reviewers PASS: 0 critical, 0 major. DD-1..DD-5 re-verified against the live repo and
skills; the owner's two-path settings edit is now in the working tree and Step 1's gates pass
on it. Ready for implementation.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 1 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 5 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 3 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 3 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 1 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 3 minor |

### To-Do: Mechanical Fixes (auto-applied)
- [x] Step 1 settings check replaced by a JSON check (both paths in `allowWrite`, any formatting) plus a merge-base name-only diff; dry-run: exit 0 on the owner's edit, exit 1 on `HEAD`'s copy _(#2, #3, #4, #5, #6)_.
- [x] Step 4 settings box and old-name gate reworded for the multi-line array _(#2, #4)_.
- [x] Step 1 resume line covers a fresh `/run-feature F9` session's Branch Guard _(#2, #3)_.
- [x] Step 4 checklist re-read box names which checks keep the old name _(#6)_.
- [x] Owner checklist: "staged by Step 1"; stronghold META-PLAN item gets a path-scoped commit _(#1, #2, #4, #6)_.
- [x] Step 3 item-2 edit also drops `.claude/settings.json` from the post-merge owner edits _(#4)_.

### Resolve During Implementation
- **[Owner checklist] No producer ticks the checklist, but F2/F5's Assumed starting state reads "F9's owner checklist is ticked"** _(#2)_: the per-item Checks are the record; F2/F5's cold survey should run them rather than look for ticks. Raise at F9's fold-back (Phase C can reword F2/F5's Assumed state).
- **[Step 1] The owner's settings.json edit reflows `allowedDomains` and drops the final newline** _(#2, #3)_: harmless (JSON parses, same values). If `/git-push` flags it, the owner fixes it by hand (agents can't write the file).

### Verdict
[x] Ready to proceed as-is
[ ] Proceed after minor fixes
[ ] Requires changes before proceeding

### Descriptive cleanup: 3 fixed, 0 dropped

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| Settings gate `git diff --` empties once committed (Pass 2) | major | step-5f:dd-application | fix_regression | DD-2 self-check ran the gate only on the unstaged state | yes | not logged |
| Owner-edit stop after three commits, no resume (Pass 2) | major | step-5f:dd-application | fix_regression | Added halt not walked (self-check 4, fail-early) | yes | not logged |
| Phase B "both confirmed" folds back from old folder (Pass 2) | major | subagent-6:completeness | scoped_too_narrowly | Same-session Phase B → C path not traced | yes | not logged |
| META-PLAN owner pointer stale (Pass 2) | major | subagent-2:full-stack-trace | scoped_too_narrowly | All-instances sweep stopped at the plan file | yes | not logged |

`not logged`: the ledger is in `review_due` and logs only critical misses.

### Plan-Creator Misses
6b: 0 misses
