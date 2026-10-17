# Push Review: docs/plan-phases-and-features

## Review 1
Generated: 2026-10-16 22:24
Comparison: origin/main d9a668eca5..aafd71aa49
Verdict: **BLOCKED**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — FAIL
Dependencies, phases, ledger, ★FOCUS and F-IDs are consistent; the effort tally is wrong.
- **major** `plans/META-PLAN.md:113` — Effort tally says 13 pts, but the Backlog rows sum to 14 (F1 L=3, F2 S=1, F5 M=2, F7 S=1, F3 L=3, F4 M=2, F6 M=2).
- **minor** `plans/ROADMAP.md:84` — Principles & constraints still holds unfilled template placeholders.
- **minor** `plans/META-PLAN.md:58` — "the Phase 1 skeleton runs F2 → F5 → F7" implies F5 depends on F2, but F5 depends only on F1.

#### 5. Completeness & Cleanup — FAIL
Cross-references and phases are consistent; the Verification row should be pending, and the effort tally is off by one.
- **major** `plans/META-PLAN.md:35` — Project facts sets Verification to `.venv/bin/pytest`, but no test runner exists yet, and F1 is the feature that sets it. The template says to write `pending — set by F<n>` until then, so `/run-feature` stops correctly.
- **minor** `plans/META-PLAN.md:113` — Effort tally 13 vs 14 (same as Correctness).

### To-Do: Required Changes

- [x] **Fix the effort tally** — `plans/META-PLAN.md` — Change `**Effort tally (remaining).** 13 pts` to `14 pts`, the sum of the Backlog rows.
- [x] **Mark Verification pending** — `plans/META-PLAN.md` — In Project facts, set Verification to `pending — set by F1`; F1's expected end state already sets the real command.
- [x] **Reword the Phase 1 path** — `plans/META-PLAN.md` — In "Shortest path to the focus feature", replace "runs F2 → F5 → F7" with "runs F2 and F5 (independent of each other), then F7", to match the dependency graph.
- [x] **Fill or trim Principles & constraints** — `plans/ROADMAP.md` — Replace the template bullets with real constraints (for example rule-based only with no LLM; no live Discord/GitHub calls in tests; IDs are config; least-privilege GitHub access; dependence on the Discord and GitHub APIs). This needs the owner's input, so it can be deferred.

## Review 2
Generated: 2026-10-16 22:37
Comparison: origin/main d9a668eca5..9a483dc9a4
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
Depends-on cells, diagram, Dependencies paragraphs, effort tally (14), ledger, phases, Delivered-by, ★FOCUS and Next F-ID (F8) are consistent.
- **minor** `plans/META-PLAN.md:276` — F3's Assumed-starting-state check requires "F5's issue-body builder exists and is the only place that formats an issue body", but F5's Expected end state never requires a single body builder; only the couplings section states it.

#### 5. Completeness & Cleanup — PASS
Cross-references, F-IDs, tally, phases and ledger are consistent.
- **minor** `plans/ROADMAP.md:71` — Capability 4's Delivered-by lists Phases 1 and 3, but Phase 2 also advances it (body built from the answers).

### To-Do: Required Changes

- [x] **Require a single issue-body builder in F5** — `plans/META-PLAN.md` — Add an F5 Expected-end-state bullet: "One issue-body builder function owns body formatting (F3 extends it)", so F3's starting-state check can pass.
- [x] **List Phase 2 under capability 4** — `plans/ROADMAP.md` — Change capability 4's Delivered-by to `Phases 1 (filed), 2 (structured body), 3 (roadmap)`.
- [x] **Fill or trim Principles & constraints** — `plans/ROADMAP.md` — Carried over from Review 1; needs the owner's input.

### Missed Findings

| Finding | Severity | Unit | Ledger id |
|---|---|---|---|
| F5 end state doesn't require the body builder F3 assumes | minor | subagent-2:correctness | not logged (minor; no open pair) |
| Capability 4 Delivered-by omits Phase 2 | minor | subagent-5:completeness | not logged (minor; no open pair) |

## Review 3
Generated: 2026-10-16 23:08
Comparison: origin/docs/plan-phases-and-features 5515d3d48c..187a1a9720
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
Cross-references and facts agree across ROADMAP, META-PLAN and CLAUDE.md: F3's builder check vs the new F5 bullet, Phase 2 under capability 4, the Projects permission vs F6, and Phase 4 retry and restart pickup.
- **minor** `plans/ROADMAP.md:98` — The External dependencies principle says a GitHub failure "is reported in the thread", but no Phase 1 scope bullet or exit criterion commits to that. Only F7's end state and F5's open risk (b) back it.

#### 5. Completeness & Cleanup — PASS
The checkboxes match the applied changes, Delivered-by matches Phase 2's "Advances 2, 4", and no template placeholders remain.
- **minor** `plans/META-PLAN.md:353` — F5 now requires a single issue-body builder, but its Test-suite deltas don't test the builder, and F3 builds on it.
- **minor** `plans/ROADMAP.md:87` — The "No live side effects" and "Identifiers are config" principles restate CLAUDE.md project rules, against CLAUDE.md's "Each fact has one home".

### To-Do: Required Changes

- [ ] **Commit Phase 1 to reporting GitHub failures** — `plans/ROADMAP.md` — Add a Phase 1 scope bullet or exit criterion that a failed filing posts a visible error in the thread (matching F7's end state), so the External dependencies principle is backed by a phase commitment.
- [ ] **Add issue-body builder tests to F5** — `plans/META-PLAN.md` — In F5's Test-suite deltas, append "plus issue-body builder tests (original text, author, message link)".
- [ ] **Trim the principles that copy CLAUDE.md** — `plans/ROADMAP.md` — Shorten "No live side effects…" and "Identifiers are config, not code" to the policy and its *Why*, and point to `CLAUDE.md` for the rule text instead of restating it.

6b: 0 misses
