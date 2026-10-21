# Push Review: chore/meta-plan-update-f10

## Review 1
Generated: 2026-10-21 14:20
Comparison: origin/main 9fee978b66e6ce702c011c94f67c0876b1d01619..b7b6b82b0d69d4603490880f72a4db9cc1c218e7 (+uncommitted: inline fixes below, committed with this review)
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
The Baseline, kept-contract facts, test count (212), main SHA (`9fee978`), FOCUS and tally were all verified against the merged code.
- (minor) The F3, F7 and F8 Assumed-starting-state lines still said "Baseline plus F10". **Fixed.**
- (minor) The F10 smoke-run claim isn't recorded in the repo. Kept as is: the owner confirmed it in the F10 session on 2026-10-21.
- (minor) The live-run permission list includes Read Message History, which README has but docs/SMOKE-TEST.md step 4 doesn't.

#### 5. Completeness & Cleanup — PASS
- (minor) The `README § Setup` cross-reference didn't resolve. **Fixed** (it now cites § Discord setup).
- (minor) The F5 contract said "F7 takes" the no-thread gap while F7's section didn't list it. **Fixed** to "may take".
- (minor) F8 said "tag → label map". **Fixed** to "type → label map".
- (minor) The F2 polish lapse list omitted the false-hint test and the human-started-thread items. **Fixed.**
- (minor) The kept-contract headings for F1 and F2 still say "tag parsing" and "tagged message".

### To-Do: Required Changes

- [x] **Drop "plus F10" from the F3, F7 and F8 Assumed-starting-state lines** — `plans/META-PLAN.md` — Fixed in this push.
- [x] **Fix the README cross-reference, the F5 "may take" wording, F8's type → label map and the F2 lapse list** — `plans/META-PLAN.md` — Fixed in this push.
- [ ] **Add Read Message History to SMOKE-TEST step 4** — `docs/SMOKE-TEST.md` — List it beside View Channel, matching README § Discord setup.
- [ ] **Retitle the F1 and F2 kept-contract headings** — `plans/META-PLAN.md` — Optionally use "F1 — Channel listener" and "F2 — Thread per report", since the tag path is gone.
