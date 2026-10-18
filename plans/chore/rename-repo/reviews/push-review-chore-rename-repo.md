# Push Review: chore/rename-repo

## Review 1
Generated: 2026-10-18 02:34
Comparison: origin/main 9210a19bf1bc7156b593ef5524ae6b29564d3492..9e661e928eab2d2e6a53270c79b1c722392d0f9c
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
Docs-only rename; no secrets, injection or destructive operations. The new sandbox `allowWrite` path is narrowly scoped and intentional.
- Minor: `.claude/settings.json` lost its trailing newline.

#### 2. Correctness — PASS
Cross-references (rename plan's Owner checklist, README Docker lines, ROADMAP phrases, PR link form) match the repo.
- Minor: META-PLAN still titles F9 "Rename to discord-github-issue-management-bot" in the ★FOCUS line, Feature list, Backlog row, ledger row and F9 section, while the title and PR link form use `discord-github-issue-bot`. Deliberately deferred to F9's fold-back.
- Minor: settings.json reflow and missing trailing newline (JSON parses, values unchanged).

#### 3. Simplicity & Conciseness — PASS
- Minor: settings.json `allowedDomains` reflow is churn; only the added `allowWrite` path is a real change.
- Minor: CLAUDE.md's intro paragraph is a word-for-word copy of README's (CLAUDE.md: "Each fact has one home").
- Minor: the added ROADMAP Sequencing sentence is wrapped short to keep its grep phrase on one line.

#### 4. Test Coverage — PASS
No Python code or tests changed; matches F9's "no test-suite deltas" contract.

#### 5. Completeness & Cleanup — PASS
Only the intentional `allowWrite` path keeps the old name outside `plans/`; plan `finished: true` with every step box ticked.
- Minor: F9's META-PLAN title mismatch (see #2); settings.json trailing newline.

#### 6. Consistency & Style — PASS
Plan layout matches earlier plans; naming consistent.
- Minor: settings.json reflow and trailing newline; F9 title mismatch; ragged ROADMAP wrap.

#### 7. Integration Risk — PASS
No code, schema or dependency impact; PR link form resolves after the owner's rename; Docker tag change is README-only.
- Minor: settings.json trailing newline; F9 title mismatch (tools match on F-ID, so nothing breaks).

#### 8. Error Handling & Silent Failures — PASS
Prescribed gates fail loudly.
- Minor: the Owner checklist's `grep -c … || true` checks also swallow grep's exit 2 (missing file), which prints nothing on stdout.
- Minor: the `test -d … && ! test -e … && echo ok` checks don't say which condition failed.

### To-Do: Required Changes

- [ ] **Restore settings.json's trailing newline (and optionally single-line `allowedDomains`)** — `.claude/settings.json` — owner hand-edit (agents can't write this file); values must stay the same and both `allowWrite` paths must stay.
- [ ] **Rename F9's title to the final name at fold-back** — `plans/META-PLAN.md` — when `/run-feature F9` folds back, make sure no `discord-github-issue-management-bot` mention survives outside the history the fold-back deletes (★FOCUS line, Feature list, Backlog, ledger row, F9 section).
- [ ] **Make the zero-count Owner checks fail on a missing file** — `plans/chore/rename-repo/rename-repo.md` § Owner checklist (skill-config and stronghold META-PLAN checks) — replace `grep -c c4i-issue-bot <file> || true` with `grep -c c4i-issue-bot <file> || test $? -eq 1`, or state that only a printed `0` passes.
- [ ] **Say what a missing `ok` means** — `plans/chore/rename-repo/rename-repo.md` § Owner checklist (folder and history checks) — add "anything other than `ok` means the move is incomplete; `ls` both paths".
- [ ] **De-duplicate CLAUDE.md's intro** — `CLAUDE.md` — shorten the opening paragraph to one sentence and point to `README.md` for the description, per CLAUDE.md's "Each fact has one home".
- [ ] **Reflow the ROADMAP Sequencing sentence** — `plans/ROADMAP.md` § Sequencing rationale — rewrap to the file's ~90-column width, keeping `ahead of the rest of Phase 1` on one line.
