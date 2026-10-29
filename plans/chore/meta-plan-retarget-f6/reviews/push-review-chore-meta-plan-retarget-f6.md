# Push Review: chore/meta-plan-retarget-f6

## Review 1
Generated: 2026-10-28 21:32
Comparison: origin/main 95ec1e8..dfa3b20
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
No leftover references to a new Project, a Complexity Project field, a `cond:` gate or a gated F6 remain in META-PLAN; Assumption 2, the F6 section, F4's kept contract and the Backlog cell are consistent.
- minor: `plans/ROADMAP.md:152` said "Status and complexity fields"; the Project field is now `Effort`.

#### 5. Completeness & Cleanup — PASS
All old-plan references are updated and the edited sentences are complete.
- minor: `plans/ROADMAP.md:152`, same as above.
- minor: Assumption 2 should say `Days left`. Dismissed: Project #2's field is named `Days` (GraphQL read, 2026-10-28).
- minor: open risk (b) not re-wrapped. Dismissed: the lines are already wrapped.

### To-Do: Required Changes

- [x] **Name the Effort field in ROADMAP's Phase 3 goal** — `plans/ROADMAP.md` — Reword "Status and complexity fields" to "Status and Effort (complexity band) fields" on org Project #2. Fixed before push.

## Review 2
Generated: 2026-10-28 21:45
Comparison: origin/chore/meta-plan-retarget-f6 d83b8c0..688c26f
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
The Phase 4 pre-load (F11-F16), F17, Next F-ID F18, the effort tally (17 pts), backlog order, dependencies, couplings and homelab#P3 refs are consistent.
- minor: `plans/META-PLAN.md:549`: F6's Rank rationale still says "Phase 3's last feature", but F17 now closes Phase 3.
- minor: `README.md:43`: Known limits still calls `--clear-commands` "a deferred follow-up", but the Deferred entry was folded into F11 (F11's end state already updates README Known limits).

#### 5. Completeness & Cleanup — PASS
The Feature list, Backlog, Status ledger, contracts, dependency graph and effort tally agree for F6 and F11-F17.
- minor: same two findings as Correctness.

### To-Do: Required Changes

- [x] **Fix F6's stale phase-position phrase** — `plans/META-PLAN.md` (F6 Rank rationale, ~line 549) — Replace "Phase 3's last feature" with wording saying F17 closes Phase 3 (e.g. "Phase 3's roadmap-placement feature; F17 closes the phase"), keeping the shared-band-contract sentence.
- [x] **Repoint README's `--clear-commands` note** — `README.md` (Known limits, line 43) — Reword "a deferred follow-up" to say it is planned in F11 (Phase 4), or leave it for F11, whose end state updates Known limits. (assumed: dd-policy, dd-261028-014)

6b: 0 misses (the F6 phrase became stale in this diff; README.md was outside Review 1's diff)
