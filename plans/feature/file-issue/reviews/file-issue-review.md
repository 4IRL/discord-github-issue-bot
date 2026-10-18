# Review: File the issue in the target repo (F5)

## Review — 2026-10-18
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/file-issue/file-issue.md blob b894b99a09d226ce4d4a411dd258ba3de1fb6335

### Summary
The plan is sound in structure. Steps are ordered so the suite stays green after each one, the import graph is acyclic, and library claims were verified in a throwaway venv (PyJWT 2.15.1 / cryptography 50.0.2 / aiohttp 3.14.5). Two problems need changes before implementation. A `__main__` test would start a real Discord client. Malformed GitHub success bodies would escape as non-`GitHubError`. There are also two safety decisions: the owner's live smoke-test writes, and @mentions in public issues.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 2 major, 6 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 1 major, 2 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 3 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 6 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 3 major, 12 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 2 major, 8 minor |

### Findings

#### Major (should fix)
- **[Step 5] `test_main_builds_github_client` doesn't stub IssueBot** _(Subagents #1, #3, #5)_: `main()` would run the real `discord.Client.run("test-token")`, which is a live Gateway login from a test. → mechanical fix F1.
- **[Step 4] Malformed 2xx GitHub bodies escape as ValueError/TypeError/KeyError** _(Subagents #1, #2, #5, #6)_: `filing_hook` catches only `GitHubError`, so a bad token or issue body skips the member-facing reply. → DD-1.
- **[Step 4] `aiohttp_transport` has no test** _(Subagent #5)_: it is the only network-touching code. → DD-2.
- **[Step 4] GitHub App request/response shapes are never exercised** _(Subagent #1, external)_: the `access_tokens` body with `repository_ids`/`permissions`, `expires_at` format, and labels set by an App. → DD-3.
- **[Manual checks] Live smoke-test writes aren't enumerated, recorded or reversible** _(Subagent #6, safety)_ → DD-4.
- **[Step 3] Member text and display name go verbatim into a public issue** _(Subagent #6, safety)_: `@user` notifies real GitHub accounts, `#N` creates cross-references, and `4IRL/chores4irl` is public (verified read-only). → DD-5.

#### Minor (nice to fix)
- **[Step 2] Missing `pathlib.Path` import; import grouping unstated** _(#1, #3, #4)_ → F2.
- **[Step 4] The transport must be called positionally, and `_request` has no method parameter** _(#1, #5, #6)_ → F3.
- **[Step 3] The label-mapping test needs a `!feature` message** _(#1)_ → F4.
- **[Step 1] The pin box hard-codes versions the previous box may change** _(#3)_ → F5.
- **[Design] github.py is said to have a logger but never logs** _(#4)_ → F6.
- **[Step 6] CLAUDE.md credentials and logging-"only" rules go stale** _(#4)_ → F7.
- **[Step 6] README local run: example.env's key path is a container path** _(#4, #6)_ → F8.
- **[Steps 2/5/7] "Prints nothing" greps exit 1 on success; the 4IRL grep is case-sensitive** _(#4, #5)_ → F9.
- **[Step 4] The transport-error test misses the issue stage and the sentinel check** _(#5)_ → F10.
- **[Step 2] The repr test can't fail without `repr=False`** _(#5)_ → F11.
- **[Step 2] Test key files have no neutral-name rule** _(#5, #6)_ → F12.
- **[Step 3] The truncation test needs a whitespace-free title** _(#5)_ → F13.
- **[Step 5] The send-failure test omits the filing failure it depends on** _(#5)_ → F14.
- **[Step 5] The grep gate on test contents may be unsatisfiable** _(#5)_ → F15.
- **[Step 1] META-PLAN Assumption 1 (labels exist) isn't checked in the plan** _(#6)_ → F16.
- **[Manual checks] The 256-char title limit is unverified** _(#1, external)_ → F17.
- **[Step 4] An issue-stage transport failure may mean the issue was created, yet the reply says "try again"; downtime messages are never filed** _(#2, #6)_ → DD-6.
- **[Step 2] `UnsupportedAlgorithm` escapes the ConfigError path** _(#2, #4)_ → DD-7.
- **[Step 4/2] Extra test coverage: refresh-margin boundary, more error statuses, encrypted key, the github module never logs** _(#5)_ → DD-8.
- **[Step 6] The missing-label behavior claim may be wrong** _(#6, external)_ → DD-9.

#### Descriptive (deferred to final cleanup)
- **[Steps 1, 7] Stored test-count totals ("171 passed")** _(#1, #3, #5, #6)_.
- Anchor lint: 5 `file:NNN` line citations in Research Findings.

### Verification Gaps
- **Step 4**: `aiohttp_transport` is unexercised (DD-2).
- **Step 6**: docs-only; verified by grep.

### To-Do: Mechanical Fixes (auto-applied)
- [x] F1: `test_main_builds_github_client` stubs `IssueBot` _(applied by fixing subagent)_
- [x] F2: `pathlib.Path` import and import grouping in `config.py` _(applied by fixing subagent)_
- [x] F3: positional POST transport call via `_request`, plus stage/status asserts _(applied by fixing subagent)_
- [x] F4: `!feature` label-mapping test case _(applied by fixing subagent)_
- [x] F5: the pin box uses the versions confirmed in the previous box _(applied by fixing subagent)_
- [x] F6: `github.py` has no logger _(applied by fixing subagent)_
- [x] F7: CLAUDE.md credentials and logging rules updated _(applied by fixing subagent)_
- [x] F8: README Configuration sentence and Run-locally key path _(applied by fixing subagent)_
- [x] F9: `!`-prefixed invariant greps and a case-insensitive `4irl` grep _(applied by fixing subagent)_
- [x] F10: transport-error test covers both stages and the sentinel _(applied by fixing subagent)_
- [x] F11: repr test asserts the field name is absent _(applied by fixing subagent)_
- [x] F12: neutral `.txt` test key file names _(applied by fixing subagent)_
- [x] F13: whitespace-free truncation titles _(applied by fixing subagent)_
- [x] F14: send-failure test files with a `GitHubError` _(applied by fixing subagent)_
- [x] F15: `grep -rln` file-list gate on test contents _(applied by fixing subagent)_
- [x] F16: META-PLAN Assumption 1 label check box in Step 1 _(applied by fixing subagent)_
- [x] F17: 256-char title manual check _(applied by fixing subagent)_

### Design Decisions (awaiting user input)

#### DD-1: [Step 4] Malformed GitHub success bodies
**Context:** Any malformed or non-JSON 201 body from the token or issue call (a missing or wrong-type `token`, a bad `expires_at`, a `None` body) raises a non-`GitHubError`. That error reaches `on_error`, and the member gets no reply.

| # | Option | Trade-off |
|---|---|---|
| 1 | Validate both bodies (dict, str token, str expires_at, `fromisoformat` in try; reject a naive timestamp; issue body dict + int number + str html_url, rejecting bool) → `GitHubError(stage, status) from None`; add `test_bad_token_shape_raises` (parametrized) and widen `test_bad_success_shape_raises` | The member always gets the reply; a few more lines and tests |
| 2 | Let a malformed 2xx escape to `on_error` and document it | Less code; the member sees nothing |

**Chosen:** Option 1 — validate both bodies (token: dict, str token, str expires_at, `fromisoformat` in try, naive rejected; issue: dict, `type(number) is int`, str html_url) → `GitHubError(stage, status) from None`; `test_bad_token_shape_raises` added and `test_bad_success_shape_raises` parametrized.

#### DD-2: [Step 4] Test `aiohttp_transport`
| # | Option | Trade-off |
|---|---|---|
| 1 | Local `aiohttp.test_utils.TestServer` on 127.0.0.1 (verified to work in the sandbox): 201 JSON, 204 empty, 200 text/plain → (201, {...}), (204, None), (200, None), plus a check of the received body | Real aiohttp behavior; localhost sockets |
| 2 | Monkeypatch `aiohttp.ClientSession` with a fake | No sockets; doesn't prove real aiohttp behavior |
| 3 | Accept the gap; only the owner's smoke test covers it | Zero cost; the adapter is unverified until live |

**Chosen:** Option 3 — accept the gap; `aiohttp_transport` is covered only by the owner's live smoke test (owner decision 2026-10-18).

#### DD-3: [Step 4] Unverified GitHub App request shapes
| # | Option | Trade-off |
|---|---|---|
| 1 | Owner-only probe in Manual checks (mint one token with the exact body; record the status, the `expires_at` format, and that the scoped repositories/permissions are right) and mark the shapes `_(unverified until owner probe)_` | Doesn't block agents |
| 2 | Owner-gated UNRESOLVED stop as the first box of Step 4 | Verified before building; blocks until the App exists |

**Chosen:** Option 1 — owner-only token probe in Manual checks, before the smoke test; request/response shapes marked _(unverified until the owner probe in Manual checks)_ in Design.

#### DD-4: [Manual checks] Live smoke-test writes (safety)
| # | Option | Trade-off |
|---|---|---|
| 1 | Scratch repo + test channel first; record the issue URL in the PR; close or delete it afterwards. Test the failure path only with a wrong `GITHUB_APP_INSTALLATION_ID` in `.env`, then restore it | Nothing written to the real target |
| 2 | Smoke-test once against the real target, record the URL, close it with a "smoke test" comment. Failure path via a wrong installation ID, then revert | Tests the real config; one throwaway issue in chores4irl |
| 3 | Keep "revoke access" but add an explicit restore step | Real intake fails until restored |

**Chosen:** Option 1 — scratch repo + test channel first, live writes listed, issue URL recorded in the PR, scratch issues closed/deleted and `.env` restored; failure path only via a wrong `GITHUB_APP_INSTALLATION_ID`; "revoke" wording removed.

#### DD-5: [Step 3] @mentions and public visibility (safety)
| # | Option | Trade-off |
|---|---|---|
| 1 | Neutralize `@` in the body and author name (U+200B after `@`, or the author name in backticks), test it, and add a README note that issues in a public target repo are public | No surprise notifications; text differs slightly from Discord |
| 2 | Keep verbatim; the README documents publication and that mentions notify GitHub users | Faithful text; can ping real people |

**Chosen:** Option 1 — `_defang_mentions` puts U+200B after every `@` in the body and author name, the author name is wrapped in backticks, `test_issue_body_neutralizes_mentions` added, README notes public visibility and neutralized mentions (a backtick in a display name is accepted).

#### DD-6: [Step 4/5] Ambiguous issue-stage failure, retry wording and downtime
| # | Option | Trade-off |
|---|---|---|
| 1 | Reword `FILING_ERROR_REPLY` to say "check the repo before reposting; to retry, post a new message (edits are ignored)", plus a README "Known limits" note | One reply, honest about duplicates |
| 2 | A second fixed reply for `stage == "issue"`, `status is None` ("couldn't confirm it was filed"), plus a README note | More precise; one more message and test |
| 3 | Keep the reply; add only the README "Known limits" note | Minimal |

**Chosen:** Option 1 — `FILING_ERROR_REPLY` reworded to "Sorry, I couldn't file this as a GitHub issue. Check the repo before reposting; to retry, post a new message (edits are ignored).", plus a README "Known limits" note.

#### DD-7: [Step 2] `UnsupportedAlgorithm` from `load_pem_private_key`
| # | Option | Trade-off |
|---|---|---|
| 1 | Catch it too (import from `cryptography.exceptions`), with no new test | Invariant 3 holds for every bad key |
| 2 | Leave it; GitHub App keys are always RSA | Simpler; a traceback on an exotic key |

**Chosen:** Option 1 — catch `UnsupportedAlgorithm` too (imported from `cryptography.exceptions`), no new test.

#### DD-8: [Steps 2/4] Extra tests (multi-select)
Options: (a) refresh-margin boundary at exactly `expires_at - 300`; (b) parametrize the issue error over 403/404/410/422/500/502, plus a 201 with no html_url, and check that a 404 keeps the cached token; (c) an encrypted-key → ConfigError test (the TypeError branch); (d) a test that `issue_bot.github` emits no log records.

**Chosen:** (b) more error statuses, (c) encrypted key; (a), (d) declined

#### DD-9: [Step 6] Missing-label behavior
| # | Option | Trade-off |
|---|---|---|
| 1 | Docs only: the README says the label must already exist (it may be dropped or auto-created depending on permissions); the manual check confirms the label is applied | No code |
| 2 | Runtime check: if the requested label is missing from the 201 response's `labels`, log a WARNING with the issue URL; add a test | Catches misconfiguration; a bit more code |

**Chosen:** Option 1 — docs only: the README says the label must already exist (dropped or auto-created depending on permissions, unverified); the scratch-repo smoke test confirms the label was applied.

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | #3 traced config→tags, handler→config, github→config, issues→handler/github, bot→all; acyclic |
| Type annotations | [x] | #1 checked signatures against issue_bot/*.py |
| Error handling (status codes, exceptions, user feedback) | [x] | #2 traced the full message→GitHub→reply chain |
| Test coverage (happy path, sad path, edge cases) | [x] | #5 read conftest and all test files |
| Breaking changes (API contracts, shared state, DB schema) | [x] | #6 read META-PLAN F3/F7/F8 consumers |
| Config consistency (env vars, requirements pins, lint rules) | [x] | #4 verified PyPI pins and transitive deps; the sandbox allows pypi hosts |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | #4 read CLAUDE.md, global CLAUDE.md, memory index |

## Review — 2026-10-18 (Pass 2)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/file-issue/file-issue.md blob 73a7109d0f26d76ab82b0ae7edd59799abffbe89

### Summary
Every Pass 1 fix and DD choice was re-verified and still holds in the plan as it stands. One major safety finding remains: the scratch repo used by the owner's smoke test had no stated location, visibility or teardown. The rest are minor fixes.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 2 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 4 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 2 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 3 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 1 major, 5 minor |

### Findings

#### Major (should fix)
- **[Manual checks] Scratch repo location, visibility and teardown are unstated** _(Subagent #6, safety)_: a scratch repo outside the org's installation would need a second installation (a different `GITHUB_APP_INSTALLATION_ID`), a public one publishes test issues, and nothing removes it from the installation afterwards. → DD-10.

#### Minor (nice to fix)
- **[Design, Step 3] Raw U+200B characters in the plan** _(#1, #2, #4, #5, #6)_: invisible in review and easily lost when copied; the test also never checks the defanged author. → P1.
- **[Design] `aiohttp_transport` shape and exception claims** _(#2)_: the body must be read inside both `async with` contexts, and `ContentTypeError` cannot occur with `content_type=None`. → P2.
- **[Design] The 401 path's keyed drop of the cached token** _(#2)_: a concurrent filing may already have dropped it, so a `del` raises `KeyError`. → P3.
- **[Step 5] The `aiohttp_transport` grep gate scans non-Python files** _(#2, #5)_ → P4.
- **[Step 1] The pin box appends instead of following `requirements.txt`'s layout** _(#3, #4)_ → P5.
- **[Step 4] `github.py` import list is unordered and ungrouped** _(#4)_ → P6.
- **[Step 6] The CLAUDE.md edits have no verify gate** _(#5)_ → P7.
- **[Manual checks] The failure-path run's live writes, re-run writes and thread cleanup are unstated** _(#6)_ → P8.
- **[Manual checks] Setup creates labels blindly instead of checking them first** _(#6)_ → P9.
- **[Step 1] The label-check marker asserts "missing" for any failure** _(#3, #6)_: a 404 means missing, while an auth or network error does not. → P10.
- **[Step 1] A failed PyPI lookup has no stated fallback** _(#3)_ → DD-11.
- **[Manual checks] The Docker run and the uid-10001 key-readability note are never exercised** _(#6)_ → DD-12.

#### Descriptive (deferred to final cleanup)
- **[Design] F7 hand-off wording**: the `file_candidate` / `FiledIssue` hand-off sentence for F7 could be tightened.
- **[Standing invariant 2] "message URL only" wording is stale** once Step 6 adds the filed issue's URL; note it for the META-PLAN fold-back.
- **[Step 6] README notes name no heading and repeat text**: the label, public-visibility and Known-limits notes give no target section, and two restate Design text.

### To-Do: Mechanical Fixes (auto-applied)
- [x] P1: U+200B written as the `\u200b` escape in Design and Step 3; the mentions test also asserts `"@\u200badmin"`; Step 3 Green forbids a literal U+200B _(applied by DD-application subagent)_
- [x] P2: `aiohttp_transport` prescribed as nested `async with` with the body read inside, `except ValueError` only, and the observed aiohttp 3.14.5 behavior recorded _(applied by DD-application subagent)_
- [x] P3: 401 drops the token with `self._tokens.pop(target.github_repo_id, None)` _(applied by DD-application subagent)_
- [x] P4: Step 5 gate is `grep -rln --include='*.py' "aiohttp_transport" tests` _(applied by DD-application subagent)_
- [x] P5: Step 1 pin box places direct and transitive pins per `requirements.txt`'s layout _(applied by DD-application subagent)_
- [x] P6: `github.py` imports in three ordered groups; Steps 3/4/5 Green boxes state the import convention _(applied by DD-application subagent)_
- [x] P7: Step 6 Verify greps CLAUDE.md for the two new phrases _(applied by DD-application subagent)_
- [x] P8: Manual checks list the failure-path writes, re-run writes and thread cleanup _(applied by DD-application subagent)_
- [x] P9: Setup confirms the labels with `gh api` and creates only missing ones _(applied by DD-application subagent)_
- [x] P10: Step 1 label marker reads "label check for <label> failed … a 404 means the label is missing" _(applied by DD-application subagent)_

### Design Decisions

#### DD-10: [Manual checks] Scratch repo location and teardown (safety)
**Context:** The smoke test writes to a scratch repo, but the plan never said where it lives, whether it is private, or how it is removed. An installation ID is per account, so a repo outside the 4IRL org would need a second installation and a changed `GITHUB_APP_INSTALLATION_ID`.

| # | Option | Trade-off |
|---|---|---|
| 1 | Private scratch repo in the 4IRL org, added to the existing org installation's selected repositories; installation ID unchanged; afterwards remove it from the selection, delete it and restore `.env` | Same installation as production; test issues stay private; one org repo exists briefly |
| 2 | Scratch repo under the owner's personal account with a second installation of the App | Nothing in the org; needs a second installation ID and doesn't exercise the org installation |

**Chosen:** Option 1 — private scratch repo in the 4IRL org added to the App's existing org installation (`GITHUB_APP_INSTALLATION_ID` unchanged); the token probe uses the scratch repo's id; afterwards the repo is removed from the installation's selection, deleted, and `.env` restored.

#### DD-11: [Step 1] PyPI lookup failure
**Context:** The version re-check box had no outcome for a failed `curl` lookup, so an executor could stall or guess.

| # | Option | Trade-off |
|---|---|---|
| 1 | Fall back to the expected versions and note "PyPI lookup failed; expected versions used"; the pip-install box still stops if the host is truly blocked | No stall; the install box remains the real gate |
| 2 | Stop with an UNRESOLVED marker | Strict; blocks on a transient lookup failure |

**Chosen:** Option 1 — fall back to the expected versions with the note under the box; the pip-install box still stops if the host is blocked.

#### DD-12: [Manual checks] Exercise the Docker run
**Context:** The README's Docker form and its uid-10001 key-readability note are documented but never run.

| # | Option | Trade-off |
|---|---|---|
| 1 | Owner manual check: build the image and run the scratch-repo smoke test through the README's Docker form with the key mounted read-only | Exercises the mount and the uid note; one more owner step |
| 2 | Leave the Docker path untested | Zero cost; a mount or permission error surfaces only in deployment |

**Chosen:** Option 1 — owner manual check: `docker build -t discord-github-issue-bot .`, then the README's `docker run --rm --env-file .env -v <host key path>:/run/secrets/github-app-key.pem:ro discord-github-issue-bot` with `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem`.

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes
[ ] Requires changes before proceeding

## Review — 2026-10-18 (Pass 3)
Plan snapshot: /home/rmila/Code/discord-github-issue-bot plans/feature/file-issue/file-issue.md blob dc8225fdeb29f1a41b361c7419880af436dd4993

### Summary
Every Pass 1 and Pass 2 fix and DD choice was re-verified and still holds. One major finding: the Step 1 pip install can never pass inside the agent sandbox, because pip's vendored CA bundle matches the sandbox's `**/*.pem` read deny. Reproduced from the repo root: `.venv/bin/pip install -r requirements-dev.txt` exits 1 and `.venv/bin/pip download PyJWT==2.15.1 --no-deps -d $TMPDIR/dl` ends in `PermissionError: [Errno 13] Permission denied` while loading `pip/_vendor/certifi/cacert.pem`. The rest are minor fixes.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 1 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 0 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 1 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 1 minor |
| 5 | Verification & Coverage | FAIL | 0 critical, 1 major, 2 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 3 minor |

### Findings

#### Major (should fix)
- **[Step 1] The in-sandbox pip install can never pass** _(Subagent #5)_: the old stop condition only covered blocked package hosts, but pip fails earlier, reading its CA bundle under the `**/*.pem` deny. → Q1.

#### Minor (nice to fix)
- **[Manual checks] Token probe expects `permissions` to be exactly `issues: write` plus `metadata: read`** _(#5)_: the check should be "`issues: write` and nothing broader". → Q2.
- **[Step 7] The last box is conditional with no tick-as-N/A form** _(#3)_ → Q3.
- **[Step 5] `FILING_ERROR_REPLY` placement** _(#4)_: `threads.py` keeps its constants together after `THREAD_ALREADY_CREATED`, not next to `format_hint`. → Q4.
- **[Step 6] The README heading and key mount have no verify gate** _(#5)_ → Q5.
- **[Manual checks] Issue URLs recorded in the PR stop resolving once the scratch repo is deleted** _(#6)_ → Q6.
- **[Manual checks] Two bots on one token, and `.env` changes without a restart** _(#6)_ → Q7.
- **[Step 4] `test_bad_token_shape_raises` does not assert `__suppress_context__`** _(#1)_ → DD-13.
- **[Manual checks] The smoke test exercises only one of the two labels** _(#6)_ → DD-14.

### To-Do: Mechanical Fixes (auto-applied)
- [x] Q1: Step 1 pip-install box names the `cacert.pem` read deny, forbids working around it, stops with `UNRESOLVED — requires user decision/action: pip install fails in the agent sandbox (<error line>); run \`! .venv/bin/pip install -r requirements-dev.txt\` in the session, then resume`, and clears the marker once `pip show PyJWT cryptography cffi pycparser` lists all four
- [x] Q2: token probe checks `permissions` holds `issues: write` and nothing broader (a `metadata: read` entry may also appear)
- [x] Q3: Step 7's last box ticks with "(none to fix)" when every check passed; no other conditional box lacked a tick form (the PyPI re-check box is always tickable through its fallback)
- [x] Q4: Step 5 puts `FILING_ERROR_REPLY` after `THREAD_ALREADY_CREATED` with the module's other constants
- [x] Q5: Step 6 Verify greps README for `### GitHub App setup` and `/run/secrets/github-app-key.pem:ro` (dry-run: both exit 1 on the current README, both print a line on a scratch copy with the prescribed additions)
- [x] Q6: Manual checks record the scratch repo name, issue numbers, what each check showed and the teardown date in the PR description
- [x] Q7: Container run starts by stopping the local bot; the failure path says to restart after each `.env` change

### Design Decisions

#### DD-13: [Step 4] Assert `__suppress_context__` on bad token shapes
**Context:** Design raises `GitHubError("token", status) from None` for every shape failure. `raise X from None` sets `__suppress_context__` to True whether or not it runs inside an `except` (checked with python3: outside an `except`, `__cause__` is None and `__suppress_context__` is True; inside one, the same, with `__context__` set but suppressed).

| # | Option | Trade-off |
|---|---|---|
| 1 | Assert `exc.__cause__ is None` and `exc.__suppress_context__ is True` | Proves no library text can surface through a chained traceback |
| 2 | Assert `__cause__` only | Misses an implicit `__context__` chain |

**Chosen:** Option 1 — `test_bad_token_shape_raises` asserts `exc.__cause__ is None` and `exc.__suppress_context__ is True`.

#### DD-14: [Manual checks] Exercise both labels
**Context:** The smoke test filed one tagged message, so only one `GITHUB_LABEL_*` mapping was confirmed live.

| # | Option | Trade-off |
|---|---|---|
| 1 | Post one `!bug` and one `!feature` message; confirm `bug` and `enhancement` respectively | Both mappings confirmed; one more issue and thread |
| 2 | One message only | Fewer writes; the second label stays unverified |

**Chosen:** Option 1 — the smoke test posts one `!bug` and one `!feature` message and confirms the `bug` and `enhancement` labels; the live-writes list names two issues and two threads (plus the 300-character-title check's one).

### Resolve During Implementation
- GitHub's installation-token request and response shape (`repository_ids` / `permissions` body, `expires_at` ending in `Z`, scoped `repositories`): confirmed only by the owner's token probe.
- Label apply / drop / auto-create behaviour for an App: confirmed only by the smoke test.
- Mention neutralization (`@` + U+200B) rendering on GitHub: confirmed only by the smoke test.
- `aiohttp_transport` has no unit test; covered only live, by owner decision (DD-2).
- Docker build and the read-only key mount (uid 10001): confirmed only by the owner's container run.
- Step 1's `pip show` all-four gate: its happy path cannot run in the sandbox (the packages are not installed; its negative path exits 1 with `Package(s) not found`).

### Descriptive cleanup: 10 fixed, 3 dropped
Fixed: five `file:NNN` citations in Research Findings turned into symbol citations; the F7 hand-off sentence now says `file_candidate` returns the `FiledIssue` F7 consumes; Step 6 notes that META-PLAN Standing invariant 2's "message URL only" wording is updated at fold-back; the CLAUDE.md credentials wording names a host path for a local run and a read-only mounted file in the container; the README notes name the heading each goes under; the token probe lists its own live write (one installation token, expiring in an hour). Dropped: the two stored "171" test counts (Steps 1 and 7) and "first" in "runs against a scratch repo first" (no real-target run follows).

---

### Verdict
[x] Ready to proceed as-is
[ ] Proceed after minor fixes
[ ] Requires changes before proceeding

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| [Step 1] In-sandbox `pip install` can never pass: pip's vendored `cacert.pem` matches the `**/*.pem` read deny (found Pass 3) | major | subagent-4:integration | verification_stopped_at_text | Passes 1–2 checked the sandbox `allowedDomains` for pypi hosts but never ran the install command in the sandbox | yes | not logged (review_due: critical only) |
| [Manual checks] Scratch-repo location, visibility and teardown unspecified (found Pass 2) | major | step-5f:dd-application | fix_regression | Pass 1's DD-4 application added a scratch repo without tracing the per-account installation and its teardown | yes | not logged (review_due: critical only) |
| [Step 3] Raw U+200B literal in prescribed code and test (found Pass 2) | minor | step-5f:dd-application | fix_regression | DD-5 application wrote an invisible literal instead of an escape | maybe | not logged (review_due: critical only) |
| [Manual checks] Recorded scratch-issue URLs become dead links (found Pass 3) | minor | step-5f:dd-application | fix_regression | DD-10 application deleted the repo the recorded URLs point at | maybe | not logged (review_due: critical only) |
| [Step 5] `grep -rln` gate also matches `__pycache__` `.pyc` files (found Pass 2) | minor | step-5b:mechanical-fix | fix_regression | F15's gate was dry-run only through the ugrep wrapper, which skips binaries | maybe | not logged (review_due: critical only) |

### Plan-Creator Misses
6b: 0 misses (Pass 1's major Correctness/Integration findings were about design and test setup, not wrong facts about existing code).
