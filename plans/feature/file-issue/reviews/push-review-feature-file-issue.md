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

- [x] **Neutralize backticks in the author name** — `issue_bot/issues.py` `issue_body`, `tests/test_issues.py` — Replace or strip backticks in `candidate.author_name` before wrapping it in the code span (or use a fence longer than any run in the name), and add a test with a display name containing a backtick. _(Done at the merge gate, 2026-10-18: backticks stripped and the author line moved above the member text; see `test_issue_body_strips_backticks_from_author` and `test_issue_body_author_line_comes_before_member_text`.)_
- [ ] **Reply on unexpected filing errors** — `issue_bot/bot.py` `file_and_report`, `tests/test_bot.py` — Consider a second handler for `Exception` that logs `type(exc).__name__` with message and thread ids, sends `FILING_ERROR_REPLY` (sharing the send helper with the `GitHubError` branch), and never logs exception text. Today `test_filing_hook_unexpected_error_reaches_on_error` pins the opposite behavior, so this is an owner design choice.
- [ ] **Fall back to a message reply when no thread opened** — `issue_bot/bot.py` `file_and_report` — Optionally `message.reply(FILING_ERROR_REPLY)` when `thread is None` and filing failed, guarded by the same `discord.HTTPException` handler.
- [ ] **Pin the title-truncation boundary** — `tests/test_issues.py` — Assert that a 256-character title stays unchanged and a 257-character title becomes 256 characters ending in `…`.
- [ ] **Reject non-201 2xx issue responses in a test** — `tests/test_github.py` `test_bad_success_shape_raises` — Add a `(200, {"number": 7, "html_url": "u"})` case that raises `GitHubError` with stage `issue` and status 200.
- [ ] **Type `GitHubError.stage` as a Literal** — `issue_bot/github.py` — Annotate `stage: Literal["token", "issue"]`.
- [ ] **Name the token cache entry** — `issue_bot/github.py` — Optionally replace `tuple[str, float]` with a small frozen dataclass or `NamedTuple` (`token`, `expires_at`).
- [ ] **Comment the container-only key path** — `example.env` — Add one line saying a local run must point `GITHUB_APP_PRIVATE_KEY_PATH` at the key's host path.
- [ ] **Split `FILING_ERROR_REPLY` across lines** — `issue_bot/threads.py` — Optional: use implicit string concatenation inside parentheses.
- [ ] **Decide on the redundant `from None` and `issue_labels` wrapper** — `issue_bot/github.py`, `issue_bot/issues.py` — Leave as-is (deliberate per DD-13 and symmetry), or drop them.

## Review 2
Generated: 2026-10-18 17:05
Comparison: origin/feature/file-issue b314ef24f705f258b105f419e9cdd3fb87409b59..31befd0 (+uncommitted)
Verdict: **PUSHED WITH MINOR FINDINGS**

Scope: the merge-gate change (author line first, backticks stripped). Type Design was not launched, because no types changed.

### Results by Reviewer

#### 1. Safety & Security — PASS
The reorder narrows the injection risk. There are no secrets or new boundary inputs.

#### 2. Correctness — PASS
The blank line before `---` avoids a setext heading. The placeholder and the mention defanging still apply.
- (minor) An author name made only of backticks becomes empty, which renders an empty code span. This is cosmetic.

#### 3. Simplicity & Conciseness — PASS

#### 4. Test Coverage — PASS
- (minor) No test covers a name made only of backticks.
- (minor) The hostile-body test doesn't assert that the member text sits after the `---` separator.

#### 5. Completeness & Cleanup — PASS
- (minor) The plan's `test_issue_body_has_body_author_and_link` spec still showed the old body-first string. It was fixed before this push.

#### 6. Consistency & Style — PASS
- (minor) The same stale plan line, fixed before this push.

#### 7. Integration Risk — PASS
`issue_body` has a single caller. F3 can still extend the one builder by appending below the header.
- (minor) The same stale plan line, fixed before this push.

#### 8. Error Handling & Silent Failures — PASS

### To-Do: Required Changes

- [x] **Update the stale test spec** — `plans/feature/file-issue/file-issue.md` — Make the `test_issue_body_has_body_author_and_link` bullet expect the header-first string. _(Done before the push.)_
- [ ] **Fall back when the stripped author is empty** — `issue_bot/issues.py` `issue_body`, `tests/test_issues.py` — Use a placeholder such as `unknown` when `author_name` with its backticks removed is empty, and test a name made only of backticks.
- [ ] **Assert the separator in the hostile-body test** — `tests/test_issues.py` `test_issue_body_author_line_comes_before_member_text` — Assert `body.split("\n\n---\n\n", 1)[1]` equals the member text.

6b: 0 misses (Review 1 never examined the new hunks; they were written after it).

## Review 3
Generated: 2026-10-18 21:12
Comparison: origin/feature/file-issue 2aea35ef4a6b90f6366bf19a3c6279582a6b9fb8..194f9610
Verdict: **BLOCKED**

Scope: `docs/SMOKE-TEST.md` (new) and the README's container-key advice. Docs only; Type Design was not launched.

### Results by Reviewer

#### 1. Safety & Security — PASS
- (minor) Teardown never deletes the container copy of the key.
- (minor) The probe puts the JWT in curl's argv. It is short-lived; accepted.
- (minor) The runbook says `.env` is literal, but the local commands source it with the shell.

#### 2. Correctness — PASS
Every claim was checked against the code.
- (minor) The `.env` block omits the other required keys. Say it overrides a `.env` copied from `example.env`.

#### 3. Simplicity & Conciseness — PASS
- (minor) Section 0's App steps and section 4's container commands repeat the README.

#### 4. Test Coverage — PASS (docs only)

#### 5. Completeness & Cleanup — PASS
- (minor) The plan's frozen Manual checks section and old `chown` advice predate the runbook. Add a pointer.

#### 6. Consistency & Style — PASS
- (minor) The README and the runbook both hold the App setup and container steps (CLAUDE.md's "one home" rule).

#### 7. Integration Risk — PASS
- (minor) `docs/` is not in `.dockerignore`. It is harmless, because the Dockerfile copies only `issue_bot/` and `requirements.txt`.

#### 8. Error Handling & Silent Failures — FAIL
- (major) The readability check sources `.env` with the shell, so it hides the quote, comment and `~` traps it lists. Those traps apply only to Docker's literal `--env-file`. The check and the trap list contradict each other.
- (minor) An empty `$JWT` from a failed key load turns into a misleading 401.
- (minor) The troubleshooting table lacks the silent Discord-side failure (no thread, no log) and probe 400/403.
- (minor) Add an `ls -ld` check to tell a Docker-created directory from a key file.

### To-Do: Required Changes

- [x] **Separate local and container `.env` rules** — `docs/SMOKE-TEST.md` § 0 `.env` — State that the local run sources `.env` through the shell (quotes stripped, `~` expanded), so the `test -r` check matches what the bot sees. State that Docker's `--env-file` is literal, so the container needs a bare `/run/secrets/github-app-key.pem`. Add a literal `grep` check and an in-container `test -r` check for the container.
- [x] **Catch a failed JWT** — `docs/SMOKE-TEST.md` § 1 — Add `test -n "$JWT"` after generating it, and mention it in the 401 row.
- [x] **Delete the container key copy at teardown** — `docs/SMOKE-TEST.md` § 5.
- [x] **Say the `.env` block overrides an `example.env` copy** — `docs/SMOKE-TEST.md` § 0.
- [x] **Add troubleshooting rows** — `docs/SMOKE-TEST.md` — Cover no thread and no log, probe 400/403, and `ls -ld` for a Docker-created directory.
- [x] **Keep one home for App setup** — `docs/SMOKE-TEST.md` § 0 — Link the README for App creation; keep only the key-storage steps.
- [x] **Point the plan at the runbook** — `plans/feature/file-issue/file-issue.md` § Manual checks — Add a one-line note that `docs/SMOKE-TEST.md` supersedes it.
- [ ] **(Optional) Add `docs/` to `.dockerignore`.** _(Not done: the Dockerfile copies only `issue_bot/` and `requirements.txt`.)_

6b: 0 misses (Review 2 never saw these files).

## Review 4
Generated: 2026-10-18 21:16
Comparison: origin/feature/file-issue 2aea35ef4a6b90f6366bf19a3c6279582a6b9fb8..cb76e48
Verdict: **PUSHED WITH MINOR FINDINGS**

Scope: `docs/SMOKE-TEST.md`, the README and the plan pointer after the Review 3 fixes. All 8 reviewers PASS. Error Handling confirmed that the Review 3 major finding is fixed.

### To-Do: Required Changes

- [ ] **Name `DISCORD_TOKEN` in the runbook's `.env` block** — `docs/SMOKE-TEST.md` § 0 — `example.env` leaves it blank, so it must also be set.
- [ ] **Make the empty-JWT guard stop the probe** — `docs/SMOKE-TEST.md` § 1 — Use `test -n "$JWT" || { echo 'JWT generation failed'; false; } && curl …`, or add "empty JWT" to the 401 troubleshooting row.
- [ ] **Add the remaining troubleshooting rows** — `docs/SMOKE-TEST.md` — Cover a curl/JSON decode error (no network), Discord `LoginFailure` or `PrivilegedIntentsRequired` at startup, and how the runtime `stage=token status=N` line maps to the probe rows. Also say GitHub-issued keys start with `BEGIN RSA PRIVATE KEY`, so a different header means the wrong file.
- [ ] **Keep one home for the container-key command** — `README.md`, `docs/SMOKE-TEST.md` § 4 and its troubleshooting rows — Keep the `sudo install` command in one place, link to it from the other, and shorten the troubleshooting rows to pointers.
- [ ] **Tidy the plan's superseded note** — `plans/feature/file-issue/file-issue.md` § Manual checks — Reword it to "Superseded by …" and add a blank line after it. At fold-back, cut the section down to a link.
- [ ] **Clarify `~` expansion** — `docs/SMOKE-TEST.md` § 0 — Say "an unquoted leading `~`".

6b: 0 misses (Review 3's findings were all re-reported or fixed; these are new lines).
