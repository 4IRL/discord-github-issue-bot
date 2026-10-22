# Push Review: feature/multi-target

## Review 1
Generated: 2026-10-22 11:40
Comparison: origin/main b570fa0b33d49db6bbc738f184047eab1a1ac9e7..71bf03a085ba1f58596be0f0c4e57dc1ca287b67
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
The route file is operator-controlled, and loader errors name the key only (raised `from None`). New log lines carry ids only. `example.env` and `example.routes.toml` hold no secrets. No findings.

#### 2. Correctness — PASS
Multi-route config loading, channel-keyed dispatch, the per-route startup checks and per-repo token caching are all sound. No findings.

#### 3. Simplicity & Conciseness — PASS
- (minor) `issue_bot/config.py` `load_routes`: the `seen` dict duplicates `routes` (each `TargetConfig` already carries `name`).
- (minor) `issue_bot/config.py` `Config.__post_init__` re-wraps routes that `load_routes` already proxied. This is intended (DD-8: a directly built `Config` stays read-only).
- (minor) `issue_bot/intake.py` `report`: the IGNORE and REFUSE branches log near-identical lines.

#### 4. Test Coverage — PASS
- (minor) Missing-`ROUTES_PATH` test. **Already covered:** `ALL_KEYS` includes `ROUTES_PATH`, and `test_each_key_required[ROUTES_PATH]` passes. No action.

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs or stale env-key references. No findings.

#### 6. Consistency & Style — PASS
Follows project conventions. No findings.

#### 7. Integration Risk — PASS
- (minor) The breaking env change is intentional and documented. No action beyond the PR notes, which carry the old-key → route-field mapping and the read-only route-file mount.

#### 8. Error Handling & Silent Failures — PASS
- (minor) `load_routes` folds unreadable files and malformed TOML into one message. That is deliberate (the message never quotes the path or parser text), and SMOKE-TEST's troubleshooting row gives the locator one-liner (plan DD-5).
- (minor) `bot._check_github_access` per-route lines name only `repo_id`, not the route name.

#### 9. Type Design — PASS
- (minor) `Config.__post_init__` doesn't check that each key equals `route.channel_id` or that routes is non-empty, so a directly built `Config` could skip the loader's invariants.
- (minor) `TargetConfig` field invariants other than labels are enforced only in `_route()`. That's acceptable while the loader is the only production constructor.

### To-Do: Required Changes

- [ ] **Drop the redundant `seen` map** — `issue_bot/config.py` `load_routes` — use `routes[route.channel_id].name` in the "share channel_id" error instead of a separate `seen` dict; keep the exact error text.
- [ ] **Log once in the unrouted branch** — `issue_bot/intake.py` `intake_command.report` — compute the verb (`ignored` / `refused`) and keep the two exact log lines that `tests/test_intake.py` asserts, or leave as is if merging hurts readability.
- [ ] **Name the route in startup access-check logs** — `issue_bot/bot.py` `_check_github_access` — add `route=<name>` to the `github access ok …` / `github access check failed …` lines and update the exact-string tests in `tests/test_bot.py`.
- [ ] **Decide whether to split the route-file error** — `issue_bot/config.py` `load_routes` — optionally separate "cannot be read" from "is not valid TOML" (still without path or parser text), updating the tests and the SMOKE-TEST troubleshooting row; otherwise record the decision to keep one message.
- [ ] **Decide whether `Config.__post_init__` checks route invariants** — `issue_bot/config.py` — optionally raise `ConfigError` when routes is empty or a key differs from its `route.channel_id`; skip if `Config` is only built via `from_env`.
