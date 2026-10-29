# Push Review: feature/preview-track

## Review 1
Generated: 2026-10-29 12:10
Comparison: origin/main afdcfea8ef7e4ef472e8b781c2966567caf39457..ce76ed9a34260805ee125bfd4b5ebacfbdea660d
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
GraphQL uses variables; option ids come from the cached lookup, never member input; new log lines carry type, stage, status, ids and counts only.
- minor: `_pick_track` indexes `track_options` with `int(values[0])`; an out-of-range value would raise into the view error handler (Discord validates values, so not realistic).

#### 2. Correctness — PASS
Config parsing, option caching, select/draft handling across band/Edit/File and the post-add `set_track` are consistent. No findings.

#### 3. Simplicity & Conciseness — PASS
- minor: `_track_choices` has three except branches; `TimeoutError` could fold into the generic one.
- minor: the preview embed is built with the same `track_row` derivation in three places; a `PreviewView` helper would remove it.

#### 4. Test Coverage — PASS
- minor: no test for `set_track` when the Project lookup itself fails (original stage kept, no mutation sent).
- minor: no load test for `track_field` alone (no `track_default`).
- minor: no test that an Edit of a row-less preview (failed lookup) stays row-less and doesn't re-query.
- minor (accepted): tests set `Select._values` (discord.py 2.7.1 internals), as existing tests do for modal `_value`.

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs or stale docstrings; docs match the code. No findings.

#### 6. Consistency & Style — PASS
- minor: `_pick_track` passes `track_row=True` while siblings derive `bool(self.track_options)`.

#### 7. Integration Risk — PASS
Every new parameter and field has a default; existing route files and callers keep working.
- minor (no change needed): "rollback undocumented" — README § Adding a roadmap Project already says a rollback needs `track_field` and the `track_default` tables removed.

#### 8. Error Handling & Silent Failures — PASS
- minor: `_track_choices`' broad `except Exception` logs at WARNING with the type only, so a wiring bug looks like a transient lookup failure.
- minor: `set_track`'s `stage=project-track status=200` covers both a missing option and a malformed response; the docstring could say so.

#### 9. Type Design — PASS
- minor: `ProjectFields.track_field_id`/`track_option_ids` are set as a pair by the only constructor but not enforced in `__post_init__`.
- minor (accepted): `ProjectConfig` with `track_defaults` but no `track_field` is rejected only by the loader, matching the other config types.

### To-Do: Required Changes

- [ ] **Add a `set_track` lookup-failure test** — `tests/test_github.py` — make the transport fail on the Project query and assert `set_track` raises the lookup's own stage and never sends `SET_TRACK_MUTATION`
- [ ] **Add a `track_field`-only load test** — `tests/test_config.py` — a project table with `track_field = "Track"` and no `track_default` loads `track_field == "Track"`, `track_defaults == ()`
- [ ] **Add a row-less Edit test** — `tests/test_intake.py` — first lookup raises, then `edit_submit_with`; assert the lookup was awaited once and the new view has no Track row
- [ ] **Unify the preview embed call** — `issue_bot/intake.py` — add a `PreviewView` helper that builds `preview_embed(..., track_row=bool(self.track_options))` and use it from `_choose`, `_pick_track` and the submit path
- [ ] **Fold the timeout branch** — `issue_bot/intake.py` `_track_choices` — decide whether `TimeoutError` keeps its own `: timeout` line (it matches the filing check's form, review pass 1 DD-3) or folds into the generic branch
- [ ] **Ignore an out-of-range pick** — `issue_bot/intake.py` `_pick_track` — treat a value outside `range(len(self.track_options))` as no change instead of raising
- [ ] **Document `stage=project-track status=200`** — `issue_bot/github.py` `set_track` docstring — say it means a missing option/field or a malformed response
- [ ] **Decide the broad-except log level** — `issue_bot/intake.py` `_track_choices` — keep WARNING (owner's pass-1 choice) or log a non-`GitHubError`, non-timeout failure at ERROR
- [ ] **Optionally pair the Track members** — `issue_bot/github.py` `ProjectFields.__post_init__` — normalise to `(None, {})` when only one of `track_field_id`/`track_option_ids` is set

6b: skipped (Review 1)
