# Push Review: feature/channel-listener

## Review 1
Generated: 2026-10-17 20:13
Comparison: origin/main 9f6ffa330ef6ae462aa235f4eb1b2f234de62a39..f59d3a5e53a1d14b4815d7b388d94926d760e1b7
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No secrets, injection or unsafe operations. The token is hidden from repr, config errors never echo values, GITHUB_REPO is validated, on_error and the default hook keep member text out of logs, and the Docker image runs non-root with secrets excluded.

#### 2. Correctness — PASS
- (minor) `issue_bot/bot.py` on_ready: fires again after Gateway reconnects, so the "startup" channel check and "connected as" log repeat on each reconnect.

#### 3. Simplicity & Conciseness — PASS
- (minor) `issue_bot/config.py`: from_env locals passed straight to the constructor could be inlined.
- (minor) `issue_bot/config.py` _positive_int: the try/except ValueError is only reachable for Python's >4300-digit int limit; merge or comment it.
- (minor) `issue_bot/bot.py`: the CandidateHook indirection has one implementation (justified by F2/F5).

#### 4. Test Coverage — PASS
- (minor) No end-to-end test that a raising hook dispatched through discord's `_run_event` is logged by on_error without member text.
- (minor) Padded numeric IDs (`" 123 "`) and `x/..` / `../x` repo rejection are not asserted explicitly.

#### 5. Completeness & Cleanup — PASS
- (minor) `plans/META-PLAN.md` "Where the work stands" still says "Nothing is built yet" (fixed at the F1 fold-back).

#### 6. Consistency & Style — PASS
- (minor) Only `config.py` uses `from __future__ import annotations`.
- (minor) `issue_bot/tags.py` puts constants after the classes; IssueType/ParsedTag lack docstrings.
- (minor) `log_candidate`'s unused `message` parameter could be `_message`.

#### 7. Integration Risk — PASS
Greenfield bot with no existing callers. Env keys are documented, dependencies pinned, Dockerfile and .dockerignore consistent.

#### 8. Error Handling & Silent Failures — PASS
- (minor) on_error's line carries no message id, so a failed capture can't be tied to its Discord message (an id is not member text).
- (minor) A missing intake channel at startup is only a WARNING. Consider ERROR, since the bot can't work in that state.

#### 9. Type Design — PASS
- (minor) TargetConfig invariants (a label per IssueType, read-only labels, owner/name repo) are enforced only in from_env, not in __post_init__.
- (minor) ParsedTag's non-empty-alphanumeric title invariant is enforced only by parse_tag.

### To-Do: Required Changes

- [ ] **Run the startup channel check once** — `issue_bot/bot.py` — Guard on_ready's channel_problems check and "connected as" log with a once-flag (or move to setup_hook-time state) so Gateway reconnects don't repeat it; add a test calling on_ready twice.
- [ ] **Escalate a missing intake channel to ERROR** — `issue_bot/bot.py` channel_problems/on_ready, `tests/test_bot.py` — Log the "not found or not visible" problem at ERROR (name/category/guild mismatches stay WARNING); update the on_ready test.
- [ ] **Add the message id to on_error for on_message** — `issue_bot/bot.py` on_error, `tests/test_bot.py` — When `args[0]` has an integer `id`, append `message_id=<id>`; keep no traceback/message/text. Test it.
- [ ] **Test a raising hook through discord dispatch** — `tests/test_bot.py` — Run a hook raising `RuntimeError("Secret title words")` via `await bot._run_event(bot.on_message, "on_message", msg)`; assert one ERROR from `issue_bot.bot` and no record containing the text.
- [ ] **Assert padded IDs and dot-segment repos** — `tests/test_config.py` — Add cases: `DISCORD_CHANNEL_ID=" 555 "` parses to 555; `GITHUB_REPO` `"x/.."` and `"../x"` raise `GITHUB_REPO must be owner/name` (if not already parametrized).
- [ ] **Enforce TargetConfig invariants at construction** — `issue_bot/config.py` — Add `__post_init__` checking `set(labels) == set(IssueType)` and wrapping labels in `MappingProxyType` (via object.__setattr__); add a test constructing TargetConfig directly with a missing label.
- [ ] **Simplify _positive_int** — `issue_bot/config.py` — Merge the regex and ValueError paths into one "must be an integer" branch, or add a one-line comment on why the try/except stays (int digit limit).
- [ ] **Inline from_env locals** — `issue_bot/config.py` — Pass simple lookups directly into the `cls(...)` calls; keep the validated github_repo local.
- [ ] **Align module layout** — `issue_bot/tags.py` — Move TAG_PATTERN/EMPTY_BRACKETS/TITLE_EDGE above the classes and add one-line docstrings to IssueType and ParsedTag.
- [ ] **Signal the unused hook parameter** — `issue_bot/bot.py` log_candidate — Rename `message` to `_message`.
- [ ] **Refresh META-PLAN's "Nothing is built yet"** — `plans/META-PLAN.md` — Reword "Where the work stands" during the F1 fold-back (Phase C).
