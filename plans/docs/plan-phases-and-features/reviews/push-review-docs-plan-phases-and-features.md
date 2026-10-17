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
- [ ] **Fill or trim Principles & constraints** — `plans/ROADMAP.md` — Replace the template bullets with real constraints (for example rule-based only with no LLM; no live Discord/GitHub calls in tests; IDs are config; least-privilege GitHub access; dependence on the Discord and GitHub APIs). This needs the owner's input, so it can be deferred.
