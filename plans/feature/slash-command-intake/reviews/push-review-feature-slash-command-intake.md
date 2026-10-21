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

## Review 2
Generated: 2026-10-21 09:30
Comparison: origin/feature/slash-command-intake f108039312cdfe0564007fae03d746f4e440ff56..5e7aa94 (+uncommitted: the owner's example.env edit, not pushed)
Verdict: **PUSHED WITH MINOR FINDINGS**

Scope: F10 Step 8. Merge-gate follow-ups from the owner's smoke test: `GitHubClient.check_access`, a filing check before the modal, a startup self-check, and revert-path docs. 8 reviewers ran; Type Design was skipped because no type was added or reshaped.

### Results by Reviewer

#### 1. Safety & Security — PASS
- (minor) A failed token mint isn't cached, so while GitHub access is broken every `/bug` run makes a fresh token request.

#### 2. Correctness — PASS
- (minor) `wait_for` cancels a slow cold-cache mint, so during sustained slow GitHub every command refuses; `asyncio.shield` would let the mint finish and warm the cache.
- (minor) The startup check has no timeout of its own (bounded by the transport's 30 s).

#### 3. Simplicity & Conciseness — PASS
- (minor) The three except branches in the pre-modal check repeat the same reply and return.
- (minor) `_check_github_access` could use try/except/else and drop the redundant returns.

#### 4. Test Coverage — PASS
- (minor) No test covers the refusal reply itself failing.
- (minor) `test_main_runs_bot_with_token` asserts bound-method internals (`__func__`).
- (minor) No test asserts that `setup_hook` with `filing_check=None` logs no "github access" line.

#### 5. Completeness & Cleanup — PASS
- (minor) The plan's Step 8 Done line misstated the `example.env` status. **Fixed in this push.**
- (minor) The `check_access` docstring is about 107 characters.

#### 6. Consistency & Style — PASS
- (minor) `_sync_commands` and `_check_github_access` have no docstrings.
- (minor) The repeated except-branch tail is the same as the Simplicity finding.

#### 7. Integration Risk — PASS
- (minor) The 2 s check timeout means slow-GitHub periods refuse commands; note it in README Known limits.
- (minor) The startup check delays `login()` by up to 30 s on a hung GitHub.
- (none) The new `intake → github` import edge has no cycle.

#### 8. Error Handling & Silent Failures — PASS
- (minor) The startup check has no explicit timeout; this is the same as the Correctness and Integration findings.

### To-Do: Required Changes

- [ ] **Shield the pre-modal mint and give the startup check a timeout** — `issue_bot/intake.py`, `issue_bot/bot.py` — Wrap the check as `asyncio.wait_for(asyncio.shield(filing_check(target)), FILING_CHECK_TIMEOUT)` so a slow cold mint still warms the cache. Wrap `_check_github_access`'s call in `asyncio.wait_for(…, STARTUP_CHECK_TIMEOUT)` (for example 10 s) and log `timeout` by type only. Add a test for each.
- [ ] **Briefly cache a failed access check** — `issue_bot/github.py` or `issue_bot/intake.py` — Remember a failed check for 10–30 s so repeated commands during an outage don't each mint a token; add a test.
- [ ] **Collapse the repeated except tails** — `issue_bot/intake.py` (pre-modal check), `issue_bot/bot.py` (`_check_github_access`) — Keep the `GitHubError` branch for its stage and status; fold TimeoutError into the generic branch; send the reply once; use try/except/else.
- [ ] **Test the refusal reply failing, and the no-check startup** — `tests/test_intake.py`, `tests/test_bot.py` — Cover `send_message` raising after a failed check, and assert that `setup_hook` with `filing_check=None` logs no "github access" line.
- [ ] **Assert behavior, not bound-method internals** — `tests/test_bot.py` `test_main_runs_bot_with_token` — Patch `GitHubClient.check_access` with an AsyncMock and assert that calling `filing_check` awaits it.
- [ ] **Docstrings and line length** — `issue_bot/bot.py` (`_sync_commands`, `_check_github_access`), `issue_bot/github.py` (`check_access`) — Add one-line docstrings stating the log-only, keep-running contract, and shorten `check_access`'s docstring to at most 100 columns.
- [ ] **Note the slow-GitHub refusal in README Known limits** — `README.md` — "If GitHub takes over 2 s to answer the access check, the command refuses; try again."
- [x] **Correct the Step 8 Done line's `example.env` claim** — `plans/feature/slash-command-intake/slash-command-intake.md` — Fixed in this push.

6b: 0 misses. Review 2's findings are all on Step 8 code and docs, which were outside Review 1's diff.
