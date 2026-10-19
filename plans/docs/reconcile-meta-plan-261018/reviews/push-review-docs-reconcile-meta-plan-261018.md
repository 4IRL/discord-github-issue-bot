# Push Review: docs/reconcile-meta-plan-261018

## Review 1
Generated: 2026-10-18 21:39
Comparison: origin/main ba53e2c9f9fa6e8b292d1d7e9d7c93ec66a9b3f2..850bfd95819e413ceac6167110d9c49947fea61f
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
Ranked table, Status ledger, per-feature sections, diagram, effort tally (13), Next F-ID (F11), Baseline (PR #10, `ba53e2c`), code names and Discord facts all agree; only stale minor wording in F8/F4.
- minor — `plans/META-PLAN.md:509` — F8's Assumed starting state lists Phase 1 as F1, F2, F5, F7 but omits F10, which F8 now hard-depends on.
- minor — `plans/META-PLAN.md:535` — F8 open risk (c) still refers to "F3's state store"; F3 dropped persisted state.
- minor — `plans/META-PLAN.md:402` — F4's Assumed starting state says "F3's conversation and answers"; F3 no longer has a conversation.
- minor — `plans/META-PLAN.md:64` — "swaps the Message Content intent for the `applications.commands` scope" conflates a Gateway intent with an invite scope.

#### 5. Completeness & Cleanup — PASS
No stale FOCUS/F7, F3-thread or F3-depends-on-F2 content remains; only minor leftovers.
- minor — `plans/META-PLAN.md:402` — same F4 "conversation" wording as above.
- minor — `plans/META-PLAN.md:536` — same F8 "state store" wording as above.
- minor — `plans/META-PLAN.md:520` — the F8 dispatch bullet runs one line far past the file's ~95-column wrap.
- minor — `plans/META-PLAN.md:583` — F10 open risks omit: Send Messages (and View Channel) in the intake channel for the public summary, missing from the live-run permission list; a cutover notice when the old tags stop working; the modal Title `max_length` (thread name 100, issue title 256); optional command permission scoping.
- minor — `CLAUDE.md:3` — the repo CLAUDE.md intro still describes `!bug`/`!feature` tagged messages and thread questions; F10 risk (d) covers only ROADMAP.

### To-Do: Required Changes

- [x] **Add F10 to F8's Assumed starting state** — `plans/META-PLAN.md` (F8 section, ~line 509) — List F10 alongside F1, F2, F5, F7 and add a Verify bullet that F10's `/bug`/`/feature` interaction intake exists, since F8 hard-depends on it.
- [ ] **Reword F8 open risk (c)** — `plans/META-PLAN.md` (~line 535) — Replace "per-target persistence keys for F3's state store" with per-target question-set keys for F3 and per-target Project config for F6, matching F3's amended risk (a) that drops the `data/` store.
- [ ] **Fix F4's Assumed starting state wording** — `plans/META-PLAN.md` (~line 402) — Change "F3's conversation and answers" to "F3's modal answers and preview".
- [ ] **Separate intent and scope in the live-run note** — `plans/META-PLAN.md` (~line 64) — Say F10 adds the `applications.commands` invite scope and drops the Message Content intent, instead of "swaps … for".
- [ ] **Re-wrap the F8 dispatch bullet** — `plans/META-PLAN.md` (~line 520) — Wrap "…one in an unrouted channel gets F10's ephemeral refusal. Filing, labels and the posted link use that route's repo." at ~95 columns.
- [ ] **Add F10 open risk (f)** — `plans/META-PLAN.md` (F10 section, ~line 583) — Cover the intake-channel Send Messages/View Channel permission (and add it to the live-run list near line 64), a cutover notice for the removed tags, the Title `max_length` (thread name 100, issue title 256), and optional command permission scoping.
- [ ] **Extend F10 risk (d) to the repo CLAUDE.md** — `plans/META-PLAN.md` (F10 risk (d)) — Note that `CLAUDE.md`'s intro (`!bug`/`!feature` tags, thread questions) also needs updating with or before F10.
