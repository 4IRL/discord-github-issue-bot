# Push Review: feature/slash-command-intake

## Review 1
Generated: 2026-10-21 05:10
Comparison: origin/main f5b6c5456c3dabc70ffdf99b8c851c48d5c5cd21..78f6bed96b1f8cb3b4c734fc4384c953ade41134
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No findings. Mentions are suppressed, the title's markdown is escaped, embeds are suppressed, the
commands are guild-scoped and gated to the intake channel, and the new logs carry no member text.

#### 2. Correctness — PASS
No findings. The discord.py 2.7.1 API usage was verified: `ui.Label(TextInput)`, `defer(thinking=True)`,
`suppress_embeds`, `add_command(guild=)`, the `setup_hook` sync and the `Modal.on_error` signature.

#### 3. Simplicity & Conciseness — PASS
- (minor) The HTTPException type/status/code logging is hand-written at four sites; `discord_error_fields` could be reused.
- (minor) The two `except` branches in `IntakeModal.on_error` (and in `setup_hook`) could collapse into one via `discord_error_fields`.

#### 4. Test Coverage — PASS
- (minor) Nothing asserts that `on_ready` never calls `tree.sync`. That is the regression guard for "sync once per process".

#### 5. Completeness & Cleanup — PASS
- (minor) Source comments cite plan ids (DD-10, DD-14, DD-2) that dangle once the plan is archived.
- (minor) META-PLAN's Baseline still describes the pre-F10 code. This is expected: `/run-feature`'s fold-back rewrites it.
- (minor) ROADMAP's Current-state table still lists capability 1 as not started. This is expected: the fold-back's phase close-out and current-state refresh fix it.

#### 6. Consistency & Style — PASS
- (minor) The first line of `intake.py`'s module docstring is about 125 characters; shorten it.
- (minor) The `IntakeModal.on_error` signature is split over three lines although it fits in 100 columns.
- (minor) Several constants run past 100 columns (a precedent exists in `FILING_ERROR_REPLY`).

#### 7. Integration Risk — PASS
- (minor) `intake_command(issue_type, target, on_candidate)` is the seam F8 must generalize; note it in META-PLAN for F8.
- (minor) README doesn't say the Message Content intent can now be switched off in the developer portal.

#### 8. Error Handling & Silent Failures — PASS
- (minor) `IntakeTree.on_error` logs but sends no private reply, so the member sees "application did not respond".
- (minor) When no thread opens and filing then fails, the reporter is still told "posted". This was left to F7 (DD-13).

#### 9. Type Design — PASS
- (minor) `IssueCandidate`'s title and message invariants are enforced only at `candidate_from_submission`. No change is needed while it stays the only constructor.
- (minor) `CandidateHook` lives in `intake.py` and is consumed by `bot.py`. Leave it as is.

### To-Do: Required Changes

- [ ] **Reuse `discord_error_fields` in the HTTPException log sites** — `issue_bot/intake.py` (`_reply`, the summary-post failure in `on_submit`, `IntakeModal.on_error`), `issue_bot/bot.py` (`setup_hook`) — Replace the hand-written `exc.status`/`exc.code` arguments with `*discord_error_fields(exc)`, and collapse each pair of `except discord.HTTPException`/`except Exception` branches into one `except Exception` whose log carries type, status and code (None for non-HTTP errors). Keep the log text and tests green.
- [ ] **Add an on_ready-does-not-sync test** — `tests/test_bot.py` — With `bot.tree.sync` mocked, await `bot.on_ready()` twice and assert `sync` was never awaited.
- [ ] **Drop the DD-n ids from source comments** — `issue_bot/intake.py` (the MODAL_TIMEOUT and summary_text comments), `tests/test_bot.py`, `tests/conftest.py` — Keep each comment's rationale and remove the plan-only `DD-n` tags.
- [ ] **Shorten intake.py's docstring first line and one-line the on_error signature** — `issue_bot/intake.py` — Use a summary line of at most 100 columns, e.g. `Slash-command intake: /bug and /feature open a modal and post a public summary.`, and write the `on_error` signature on one line.
- [ ] **Wrap the over-long constants** — `issue_bot/intake.py` — Put the long reply strings in parentheses across lines and move the MODAL_TIMEOUT inline comment above the constant.
- [ ] **Say the Message Content intent is no longer needed** — `README.md` Setup — Add one sentence: the bot no longer uses the Message Content intent, and it can be turned off in the developer portal.
- [ ] **Reply privately from `IntakeTree.on_error`** — `issue_bot/bot.py` — When `interaction.response.is_done()` is False, send `INTAKE_ERROR_REPLY` with `ephemeral=True` inside a try that logs failures by type, status and code, mirroring `IntakeModal.on_error`; add a test.
- [ ] **Record the F8 seam and the no-thread filing gap at fold-back** — `plans/META-PLAN.md` (in the Phase C fold-back, not this branch) — Under F8's contract note that `intake_command(issue_type, target, on_candidate)` is the registration seam to generalize. The no-thread "posted" gap stays with F7 (DD-13).
- [ ] **Leave `IssueCandidate` validation and `CandidateHook`'s home as is** — `issue_bot/handler.py`, `issue_bot/intake.py` — No action unless a second construction path or a third hook consumer appears. Close this item as "won't do".
