# Push Review: docs/reconcile-meta-plan-261117

## Review 1
Generated: 2026-11-17 09:34
Comparison: origin/main ba17bec2bc14c6dff0774becc373e67b888aebf4..eec2a98b22f6f96dc7236df2670b880f5d8efcd0
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
Facts about GitHubClient, GITHUB_ORG, UNROUTED_COMMANDS, filing_check and README sections check out against code; F-IDs, Next F-ID F20, effort tally (21), ledger, backlog and couplings are consistent; only two minor ROADMAP wording gaps remain.
- minor — `plans/ROADMAP.md:189` — Sequencing rationale still reads `1 -> 1.5 -> 2 -> 3 -> 4` and says nothing about the new Phase 5.
- minor — `plans/ROADMAP.md:23` — End state (lines 23, 36) and capabilities 4 and 6 still say "configured repos of the 4IRL GitHub org", contradicting the amended Out of scope (line 73); META-PLAN's F19 rewording names only capabilities 1 and 6.

#### 5. Completeness & Cleanup — PASS
Phase 5 rows, effort tally (21), Next F-ID (F20), status ledger and dependency graph are all consistent; only minor ROADMAP staleness.
- minor — `plans/ROADMAP.md:193` — same sequencing-chain gap as above.
- minor — `plans/ROADMAP.md:173` — the ROADMAP header says it never lists F-IDs, but the new Phase 5 section cites F18 and F19.
- minor — `plans/ROADMAP.md:73` — the Out-of-scope bullet carries a dated history note ("came into scope on 2026-11-17"), while the Maintaining section says history lives in git; same End-state / capability 4 wording gap as above.

### To-Do: Required Changes

- [ ] **Extend the sequencing rationale to Phase 5** — `plans/ROADMAP.md` (Sequencing rationale, ~line 189) — Change the chain to `1 -> 1.5 -> 2 -> 3 -> 4 -> 5` and add one sentence: Phase 5 hard-depends only on the Phase 1.5 route model and follows Phase 4 by the owner's ordering choice.
- [ ] **Drop F-IDs from the ROADMAP Phase 5 section** — `plans/ROADMAP.md` (~line 173) — Remove the `(F18)` and `(F19)` references from the scope bullets; the META-PLAN rows already cite Phase 5.
- [ ] **Remove the dated history note from Out of scope** — `plans/ROADMAP.md` (~line 73) — Reduce the bullet to the current rule (e.g. "Channels in other Discord servers.") without "came into scope on 2026-11-17".
- [ ] **Cover End state and capability 4 in the org-scope rewording** — `plans/ROADMAP.md` (End state ~lines 23, 36; capability 4) and `plans/META-PLAN.md` (F19 section) — Either add a "from Phase 5, any repo whose owner installed the App" clause to the End state and capabilities 4 and 6 now, or extend F19's "ROADMAP capabilities 1 and 6 are reworded" bullet to also name capability 4 and the End state paragraphs.

6b: skipped (Review 1)
