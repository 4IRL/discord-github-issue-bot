# Push Review: feature/file-issue

## Review 1
Generated: 2026-10-18 16:52
Comparison: origin/main 7d8056160383bad462af099cc7a9c9a7082ded2e..ac148712cd8d77004ba7221ab3413bda7f3ca9b0
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No secrets and no 4irl code defaults. Error paths log type, stage and status only. The installation token is scoped to one repo with `issues: write`.
- (minor) `issue_bot/issues.py` `issue_body`: a Discord display name containing a backtick ends the single-backtick code span early. Mentions stay defanged, so the effect is cosmetic spoofing only.

#### 2. Correctness — PASS
Token caching and expiry, 401 handling, truncation and config parsing are correct.
- (minor) The same backtick-in-display-name issue.
- (minor) `issue_bot/bot.py` `filing_hook` catches only `GitHubError`. Any other exception leaves the member without a reply, though `on_error` logs it by type.

#### 3. Simplicity & Conciseness — PASS
- (minor) `raise GitHubError(...) from None` outside any `except` block in `_installation_token` and `create_issue` is redundant. It is kept deliberately so the test can assert `__suppress_context__` (DD-13).
- (minor) `issue_labels` is a one-line wrapper. It mirrors `issue_title` and `issue_body`.

#### 4. Test Coverage — PASS
- (minor) `issue_title` has no exact-boundary test: 256 stays as is, and 257 becomes 256 characters ending in `…`.
- (minor) No test checks that a non-201 2xx status (200/202) with a valid body still raises.

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs, stubs or stray fixtures.

#### 6. Consistency & Style — PASS
- (minor) `issue_bot/threads.py` `FILING_ERROR_REPLY` is a 152-character line. The file already has long lines.

#### 7. Integration Risk — PASS
No breaking changes. The new required keys and pins are documented, and the bot isn't deployed yet.
- (minor) `example.env` `GITHUB_APP_PRIVATE_KEY_PATH` holds a container-only path. The README documents the local override, but the env file itself has no comment saying so.
- (minor, for information) F7 will extend `filing_hook`/`file_and_report` to post the link. That is an expected extension, not a second dispatch path.

#### 8. Error Handling & Silent Failures — PASS
- (minor) `file_and_report` gives no member-facing reply for an unexpected exception other than `GitHubError`, such as a JWT signing error.
- (minor) When no thread opened and filing fails, the member sees nothing. A `message.reply(...)` fallback is possible.

#### 9. Type Design — PASS
- (minor) `GitHubError.stage` is a plain `str`. A `Literal["token", "issue"]` annotation would let a type checker catch typos.
- (minor) The token cache value is an anonymous `tuple[str, float]`. It is private and used in only two places.

### To-Do: Required Changes

- [ ] **Neutralize backticks in the author name** — `issue_bot/issues.py` `issue_body`, `tests/test_issues.py` — Replace or strip backticks in `candidate.author_name` before wrapping it in the code span (or use a fence longer than any run in the name), and add a test with a display name containing a backtick.
- [ ] **Reply on unexpected filing errors** — `issue_bot/bot.py` `file_and_report`, `tests/test_bot.py` — Consider a second handler for `Exception` that logs `type(exc).__name__` with message and thread ids, sends `FILING_ERROR_REPLY` (sharing the send helper with the `GitHubError` branch), and never logs exception text. Today `test_filing_hook_unexpected_error_reaches_on_error` pins the opposite behavior, so this is an owner design choice.
- [ ] **Fall back to a message reply when no thread opened** — `issue_bot/bot.py` `file_and_report` — Optionally `message.reply(FILING_ERROR_REPLY)` when `thread is None` and filing failed, guarded by the same `discord.HTTPException` handler.
- [ ] **Pin the title-truncation boundary** — `tests/test_issues.py` — Assert that a 256-character title stays unchanged and a 257-character title becomes 256 characters ending in `…`.
- [ ] **Reject non-201 2xx issue responses in a test** — `tests/test_github.py` `test_bad_success_shape_raises` — Add a `(200, {"number": 7, "html_url": "u"})` case that raises `GitHubError` with stage `issue` and status 200.
- [ ] **Type `GitHubError.stage` as a Literal** — `issue_bot/github.py` — Annotate `stage: Literal["token", "issue"]`.
- [ ] **Name the token cache entry** — `issue_bot/github.py` — Optionally replace `tuple[str, float]` with a small frozen dataclass or `NamedTuple` (`token`, `expires_at`).
- [ ] **Comment the container-only key path** — `example.env` — Add one line saying a local run must point `GITHUB_APP_PRIVATE_KEY_PATH` at the key's host path.
- [ ] **Split `FILING_ERROR_REPLY` across lines** — `issue_bot/threads.py` — Optional: use implicit string concatenation inside parentheses.
- [ ] **Decide on the redundant `from None` and `issue_labels` wrapper** — `issue_bot/github.py`, `issue_bot/issues.py` — Leave as-is (deliberate per DD-13 and symmetry), or drop them.
