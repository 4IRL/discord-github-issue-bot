# Push Review: fix/channel-listener-review-followups

## Review 1
Generated: 2026-10-18 01:21
Comparison: origin/main dbe9569a71aff7a4e073b88b3b39414d94e94ac2..848e0c1035af62542018c18a8a17457de06e36a3
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No injection, secret leak or member-text log leak. `on_error` logs only the exception type, the event and an int-checked message id. The config changes keep the token hidden from repr and add no 4irl defaults.

#### 2. Correctness — PASS
No correctness defects in the `bot.py`, `config.py` and `tags.py` changes, and the docs match the code.

#### 3. Simplicity & Conciseness — PASS
No over-engineering or dead code. Three minor readability nits:
- `issue_bot/config.py:37`: `_positive_int` raises a bare `ValueError` inside the `try` only to catch it on the next line. It is fine to keep, since this avoids writing the message twice, or the regex check could run before the `try`.
- `issue_bot/bot.py:89`: `on_error` has two nearly identical `logger.error` calls. A suffix string would allow a single call.
- `issue_bot/tags.py:18`: the conditional-group regex in `BRACKETED_TAG` is compact but harder to read. Acceptable as it is.

#### 4. Test Coverage — PASS
The new behaviour is well covered, edge cases included. One minor gap:
- `tests/test_bot.py:191`: no test covers the `on_ready` docstring's promise that a check that raises is logged once and never retried. If the flag assignment moved after the check, nothing would fail.

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs, stubs or temp files, and the docstrings match the code. Two minor staleness notes:
- `plans/feature/channel-listener/reviews/push-review-feature-channel-listener.md`: Review 3 items 1–3 are ticked, but their META-PLAN edits are in PR #3, not on this branch or `main`. The ticks carry no note saying so.
- `plans/feature/channel-listener/channel-listener.md:348`: the Tag grammar code block still shows the old `#` `TAG_PATTERN` and `#bug` examples. The lead-in points to the amendment, so it doesn't contradict it.

#### 6. Consistency & Style — PASS
Naming, imports, type hints and comment density match the existing code. One trivial nit:
- `issue_bot/bot.py:66`: `self._startup_checked: bool = False` is annotated, but the attributes next to it are not.

#### 7. Integration Risk — PASS
No overlap with PR #3, which touches only `plans/META-PLAN.md` and its own review file. No env or dependency changes, and the public APIs remain compatible. One minor note:
- `issue_bot/bot.py:49`: the `log_candidate` rename (`message` → `_message`) would break a future caller that passes `message=` by keyword.

#### 8. Error Handling & Silent Failures — PASS
No empty or broad catches and no silent fallbacks. A missing channel now logs at ERROR, config errors name the failing key, and the labels check raises instead of falling back to a default.

#### 9. Type Design — PASS
The reshaped types are sound. Two minor notes:
- `issue_bot/config.py:59`: `TargetConfig.__post_init__` enforces only the labels rule. The positive ids, the owner/name repo and the non-blank strings are checked only in `from_env`, so validation is split across two ways of building the object.
- `issue_bot/tags.py:42`: a `ParsedTag` built directly can hold a title with no letters or digits; only `parse_tag` guarantees a usable title.

### To-Do: Required Changes

- [ ] **Annotate Review 3's fold-back ticks** — `plans/feature/channel-listener/reviews/push-review-feature-channel-listener.md` — Add "(META-PLAN edit made by the F1 fold-back, PR #3)" to Review 3 items 1–3, or untick them until PR #3 merges.
- [ ] **Update the F1 plan's Tag grammar block** — `plans/feature/channel-listener/channel-listener.md` (~line 348) — Change the `TAG_PATTERN` and the `#bug` examples to the `!` prefix so the block matches `issue_bot/tags.py`.
- [ ] **Test that a raising startup check is not retried** — `tests/test_bot.py` — Make `get_channel` raise, call `on_ready` twice (tolerating the first exception) and assert `get_channel` was called once.
- [ ] **Collapse on_error's two logger calls** — `issue_bot/bot.py` `on_error` — Build a suffix (`f" message_id={message_id}"` or `""`) and make one `logger.error` call. Keep `%d` formatting so an int subclass can't inject text.
- [ ] **Drop the lone attribute annotation** — `issue_bot/bot.py` `IssueBot.__init__` — Change `self._startup_checked: bool = False` to `self._startup_checked = False` to match the attributes beside it.
- [ ] **Decide on _positive_int's raise-to-catch** — `issue_bot/config.py` `_positive_int` — Either keep it (the comment already explains the digit limit) or move the regex check ahead of the `try` and catch `ValueError` only around `int()`, without changing the message.
- [ ] **Decide where TargetConfig validates its fields** — `issue_bot/config.py` `TargetConfig` — Either move the id/repo/blank-string checks into `__post_init__` and have `from_env` rely on them, or add a docstring line saying `from_env` is the validated constructor.
- [ ] **Note ParsedTag's title guarantee** — `issue_bot/tags.py` `ParsedTag` — Add a docstring line saying only `parse_tag` guarantees a usable title, or add a `__post_init__` that calls `_is_usable_title`.
- [ ] **Keep CandidateHook calls positional** — `issue_bot/bot.py` `CandidateHook` / `log_candidate` — Add a short note to the `CandidateHook` docstring saying hooks are called positionally, since `log_candidate`'s first parameter is `_message`.
- [ ] **Leave BRACKETED_TAG's conditional groups as is** — `issue_bot/tags.py` — No change unless readability complaints come up; tick once confirmed.
