# Review: Channel Listener and Tag Parsing (F1)

## Review — 2026-10-17
Plan snapshot: /home/rmila/Code/c4i-issue-bot plans/feature/channel-listener/channel-listener.md blob 9003174f07c00b48be6f8f4e07a679a241ce0ace

### Summary
Code-level design was sound (all discord.py 2.7.1 / pytest 9.1.1 / pytest-asyncio 1.4.0 API
claims verified in scratch venvs; a scratch build of the design passed 32 tests), but the
plan needed changes: the candidate/hook contract was too thin for F2/F5, `/run-plan` Phase 0
would halt before Step 1, the default hook logged members' message text, and punctuation
next to a tag leaked into titles. All resolved below.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 0 critical, 1 major, 5 minor |
| 2 | Full-Stack Trace | FAIL | 0 critical, 2 major, 2 minor |
| 3 | Ordering & Cleanup | FAIL | 0 critical, 1 major, 5 minor |
| 4 | Integration & Conventions | FAIL | 0 critical, 2 major, 1 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 5 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 3 major, 7 minor |

### Findings

#### Major (should fix)
- **[Step 4/5] IssueCandidate and hook lack the raw text (F5 body) and a message handle (F2/F7 thread)** _(Subagents #2, #6)_ → DD-1.
- **[Prerequisites] `/run-plan` Phase 0 health-checks `pytest`/`docker` before Step 1 creates the venv** _(Subagents #3, #4)_ → DD-2.
- **[Step 1/6] Test command not registered in skill-config; CLAUDE.md updated only in Step 6** _(Subagents #3, #4)_ → DD-3.
- **[Step 5] Default hook logs members' message text at INFO** _(Subagent #6)_ → DD-4.
- **[Step 3] Punctuation residue and URL fragments in titles (`#bug.` → `.`)** _(Subagents #1, #6)_ → DD-5.
- **[Step 5] "Matching channel logs no WARNING" test is order-dependent (discord.py voice WARNINGs on first Client)** _(Subagent #1)_ → mechanical.

#### Minor (nice to fix)
- **[Step 2] `-> Config` annotation needs `from __future__ import annotations`** _(#1)_ → mechanical.
- **[Step 2/6] Required-key order unspecified though Step 6's gate needs `DISCORD_TOKEN is required`** _(#1, #2, #3, #6)_ → mechanical (order pinned + test).
- **[Step 6/7] ID grep gates: `git grep` misses untracked; Step 7 grep did not exclude `.venv`; vacuous on zero hits** _(#1, #5, #6)_ → mechanical.
- **[Step 5] IssueBot `__init__` did not say it stores `config`/`on_candidate`** _(#2)_ → mechanical.
- **[Step 5/7] Conditional boxes without a tick-as-N/A form** _(#1, #3, #5)_ → mechanical.
- **[Steps] Per-step commits must stage explicit paths; plan file untracked** _(#3)_ → mechanical.
- **[Step 7] README "names only" and META-PLAN Verification row had no command gate** _(#5)_ → mechanical.
- **[Step 5] `__main__` import form needed for the monkeypatch; exit code 2 not asserted** _(#5)_ → mechanical.
- **[Step 6] Docker gate: no exact exit check, dev image left behind** _(#6)_ → mechanical.
- **[Step 6] `.env` quoting differs between shell sourcing and `--env-file`** _(#6)_ → mechanical.
- **[Step 6] Docker gate placed before doc to-dos** _(#3)_ → DD-6.
- **[Step 4] Raw mention markup in titles (content vs clean_content)** _(#6)_ → DD-7.
- **[Steps 2/4/5] Untested specified behaviors (default hook, edits, blank optional, thread messages)** _(#5, #6)_ → DD-8.
- **[Step 6] Floating base image tag** _(#4)_ → DD-9.
- **[Step 6] PID 1 ignores SIGTERM** _(#6)_ → DD-10.

### To-Do: Mechanical Fixes (auto-applied)
Applied inline by the orchestrator in one plan rewrite together with the DD choices (the plan
author's context already held the full plan; no fixer subagents).
- [x] Step 5 caplog WARNING assertions filtered to `c4i_issue_bot.bot`.
- [x] Step 5 conditional construction box replaced by a verified statement + tick rule.
- [x] Step 2 `from __future__ import annotations`.
- [x] Step 2 required-key order pinned (Design + Green) and `test_empty_env_names_token_first` added.
- [x] Step 6/7 ID grep uses `--exclude-dir=.venv` and requires the config.py hit.
- [x] Step 5 IssueBot stores `self.config` / `self.on_candidate`.
- [x] Step 7 last box gets a `— N/A: no failures` tick form.
- [x] Commit note under `## Steps` (explicit paths; plan file staged in Step 1).
- [x] Step 7 command gates for README, META-PLAN Verification row and CLAUDE.md Test line.
- [x] Step 5 `__main__` imports `IssueBot` at module level; test asserts code 2.
- [x] Step 6 Docker gate checks `exit=2` and removes the dev image.
- [x] Step 6 README `.env` plain `KEY=value` note.

### Design Decisions (awaiting user input)

#### DD-1: [Steps 4–5] Hook contract for F2/F5
| # | Option | Trade-off |
|---|---|---|
| 1 | Hook `(message, candidate)` + `content` field | F2 uses message.create_thread/.thread directly |
| 2 | Add `content` + `channel_id` fields | F2 rebuilds a PartialMessage; duplicate guard via API error |
| 3 | Keep minimal | Contract changes in two later features |

**Chosen:** 1 — hook `(message, candidate)`, `content: str` added.

#### DD-2: [Prerequisites] run-plan Phase 0
| # | Option | Trade-off |
|---|---|---|
| 1 | Prerequisites section, keep Docker box | Docker must be running; box stops UNRESOLVED otherwise |
| 2 | Prerequisites section, Docker check by hand | Run never depends on Docker |

**Chosen:** 1 (Docker Desktop confirmed working from WSL during review: server 29.5.3).

#### DD-3: [Step 1] Test-command registration
**Chosen:** CLAUDE.md Test command + gitignored skill-config `integration_runner_cmd: .venv/bin/pytest`, both in Step 1.

#### DD-4: [Step 5] What logs may contain (safety)
**Chosen:** ids and URLs only; CLAUDE.md project rule; test asserts no title/name in the record.

#### DD-5: [Step 3] Punctuation next to tags
**Chosen:** `(?<![\w#/])` lookbehind (no URL fragments), remove empty bracket pairs, strip `" .,:;-|/"` from title edges, `None` when no alphanumeric. Dry-run verified on all test inputs.

#### DD-6: [Step 6] Docker gate placement
**Chosen:** last box of Step 6.

#### DD-7: [Step 4] content vs clean_content
**Chosen:** keep `message.content`; F5 cleans mention markup.

#### DD-8: [Steps 4–5] Extra tests
**Chosen:** default hook log line (`test_default_hook_logs_ids_not_text`) and `test_thread_message_ignored`; edits and blank-optional tests not added.

#### DD-9: [Step 6] Base image
**Chosen:** `python:3.12.11-slim` (tag verified via `docker manifest inspect`, exit 0).

#### DD-10: [Step 6] Graceful stop
**Chosen:** `STOPSIGNAL SIGINT`.

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding (applied; Pass 2 re-checks)

### Coverage Checklist
| Area | Checked? | Notes |
|---|---|---|
| Imports (dead, missing, circular) | [x] | No deletions; new modules only |
| Type annotations | [x] | `-> Config` forward ref fixed |
| Error handling (status codes, exceptions, user feedback) | [x] | ConfigError → SystemExit(2); hook exceptions logged by discord.py on_error |
| Test coverage (happy path, sad path, edge cases) | [x] | Scratch build of design passed |
| Breaking changes (API contracts, shared state, DB schema) | [x] | Hook contract fixed for F2/F5/F7 |
| Config consistency (env vars, requirements pins, lint rules) | [x] | Pins latest; skill-config synced (DD-3) |
| Naming conventions (CLAUDE.md rules, project patterns) | [x] | No prior code; CLAUDE.md rules applied |

## Review — 2026-10-17 (Portability revision, Pass 1)
Plan snapshot: /home/rmila/Code/c4i-issue-bot plans/feature/channel-listener/channel-listener.md blob be1bfb5532df746f4f57920b2989ed30354eebd9

### Summary
The plan was revised for META-PLAN F1's portability amendment: package `issue_bot`, env-only config with every key required and no code defaults, `TargetConfig` kept separate from instance values, and a committed example env file. Reviewers rebuilt the design in scratch venvs with the pinned versions, and every prescribed test passed (48–71 tests per reviewer); `python -m issue_bot` with no env exits 2 with `DISCORD_TOKEN is required`. One blocker, found by five reviewers and verified in-repo: the sandbox bind-mounts /dev/null over every `**/.env*` path, so `.env.example` could not be staged, and once tracked it would break sandboxed git status/diff. Resolved by DD-1 (rename to `example.env`).

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | FAIL | 1 critical, 0 major, 2 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 4 minor |
| 3 | Ordering & Cleanup | FAIL | 1 critical, 0 major, 4 minor |
| 4 | Integration & Conventions | FAIL | 1 critical, 1 major, 3 minor |
| 5 | Verification & Coverage | FAIL | 1 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | FAIL | 0 critical, 4 major, 6 minor |

### Findings

#### Critical (must fix before proceeding)
- **[Step 6] Sandbox masks `.env.example`: `git add` fails, and once tracked every sandboxed git status/diff/stash breaks, while /git-commit and /git-push would print its content** _(#1, #3, #4, #5, #6)_ → DD-1.

#### Major (should fix)
- **[Step 6] `!.env.example` in .claudeignore has no defined meaning under the global "each entry is a hard deny" rule** _(#4)_ → moot under DD-1.
- **[Step 6] Unanchored `!.env.example` un-ignores nested copies; no revert path** _(#6)_ → moot under DD-1.
- **[Owner actions] Auto-mode environment text says `.env.*` files are gitignored and sensitive** _(#6)_ → moot under DD-1.
- **[Step 3/5] ConfigError logging can leak an env value through exception chaining** _(#6)_ → DD-2.

#### Minor (nice to fix)
- **[Prerequisites] Docker failure halts /run-plan Phase 0, contrary to the plan's claim** _(#3)_ → mechanical.
- **[Steps] Per-step review never sees new files** _(#3)_ → mechanical.
- **[Step 1] Fix subagent's `$TEST_RUN_CMD` is blank** _(#3, #5)_ → DD-4.
- **[Step 7] Owner hand-off has no carrier under /run-plan** _(#4)_ → moot under DD-1.
- **[Design/Step 6] discord.py DEBUG logs full gateway payloads** _(#6)_ → mechanical.
- **[Step 7] README key gate covered 4 of 9 keys; no ID-value check** _(#5, #6)_ → mechanical.
- **[Design] Portability gate missed `C4I`, `4IRL`, Dockerfile** _(#6)_ → mechanical.
- **[Step 5] channel_problems strings unspecified** _(#6)_ → mechanical.
- **[Step 2] Tags inside inline code captured** _(#6)_ → DD-9.
- **[Step 4] Candidate drops the matched target** _(#2)_ → DD-5.
- **[Step 3] Frozen configs unhashable** _(#2)_ → DD-6.
- **[Step 4] IssueCandidate repr carries member data** _(#2)_ → DD-3.
- **[Step 7] No carrier for F1's consumer contract** _(#2)_ → DD-7.
- **[Step 5] main() happy path untested** _(#5)_ → DD-8.
- **[Step 6] Shell vs `--env-file` equivalence false for values with spaces** _(#1)_ → DD-10.

#### Descriptive (deferred to final cleanup)
- pip freeze ordering wording (#1); Step 7 "runner not configured" wording (#3); Owner-actions sandbox wording (#4); "4irl values live only in .env.example" wording (#4, #6).

### To-Do: Mechanical Fixes (auto-applied)
- [x] Prerequisites: Phase 0 halts on `docker info` failure; start Docker first _(applied by fixing subagent)_
- [x] Commits note: give review/fix subagents the step's new `??` files by name; never a `.env*` file _(applied by fixing subagent)_
- [x] Design + Step 6 logging rule: never run `discord` loggers at DEBUG _(applied by fixing subagent)_
- [x] Step 7 README gates: `(DISCORD|GITHUB)_[A-Z_]+=` plus ID-value grep _(applied by fixing subagent)_
- [x] Portability gate extended to `\bC4I\b|4IRL`, Dockerfile, pyproject.toml _(applied by fixing subagent)_
- [x] Step 5 channel_problems exact strings; test channels get `id=555` _(applied by fixing subagent)_

### Design Decisions (awaiting user input)

#### DD-1: [Step 6] Example env file vs the sandbox `**/.env*` mask (safety)
| # | Option | Trade-off |
|---|---|---|
| 1 | Rename to `example.env` | No deny matches; no negations or owner action; agents can read/stage/diff it |
| 2 | Keep `.env.example`, gate on owner's global change | F1 blocks on a global change widening reads in every repo |
| 3 | Keep `.env.example`, owner commits by hand | Sandboxed git noisy/broken until global deny narrowed |

**Chosen:** 1 — rename to `example.env`.

#### DD-2: [Step 3/5] Config error logging (safety)
**Chosen:** `raise ConfigError(...) from None`; `logger.error("configuration error: %s", exc)` without exc_info; test that a secret-like value never reaches a log record.

#### DD-3: [Step 4] IssueCandidate repr (safety)
**Chosen:** `title`, `content`, `author_name` declared `field(repr=False)`; add `test_candidate_repr_hides_text`.

#### DD-4: [Step 1] Skill test-command variables
**Chosen:** also set `test_run_cmd: .venv/bin/pytest`, with a Verify grep.

#### DD-5: [Step 4] Candidate carries its matched target
**Chosen:** add `target: TargetConfig` to IssueCandidate; the test asserts `candidate.target is config.target`.

#### DD-6: [Step 3] Hashability
**Chosen:** document that TargetConfig/Config are not hashable; key routes by `channel_id`.

#### DD-7: [Step 7] Consumer contract carrier
**Chosen:** add a `## Contract for later features` section and a Step 7 box copying it into the final report.

#### DD-8: [Step 5] main() happy path
**Chosen:** add the stub-based `test_main_runs_bot_with_token`.

#### DD-9: [Step 2] Backticked tags
**Chosen:** add a backtick to the lookbehind/lookahead, plus a `test_not_a_tag` case "use `#bug` here" → None.

#### DD-10: [Step 6] Shell vs `--env-file`
**Chosen:** narrow the README claim: the shell form works only for values without spaces or quotes.

---

### Verdict
[ ] Ready to proceed as-is
[ ] Proceed after minor fixes
[x] Requires changes before proceeding (applied; Pass 2 re-checks)

## Review — 2026-10-17 (Portability revision, Pass 2)
Plan snapshot: /home/rmila/Code/c4i-issue-bot plans/feature/channel-listener/channel-listener.md blob 05985b8423c08b84c425141bd3d9b51184d04873

### Summary
All six reviewers PASS: 0 critical, 0 major. A scratch build of the design passed all 72 prescribed tests (including the DD-2 leak test, which fails under mutation). The Step 6 `example.env` awk|diff gate exits 0, 1 and 2 on its match, mismatch and missing paths. `example.env` is not ignored, is not sandbox-masked and can be staged. Remaining items are minor; this pass's design decisions resolve them.

### Subagent Results

| # | Subagent | Verdict | Findings |
|---|---|---|---|
| 1 | Correctness & Accuracy | PASS | 0 critical, 0 major, 3 minor |
| 2 | Full-Stack Trace | PASS | 0 critical, 0 major, 4 minor |
| 3 | Ordering & Cleanup | PASS | 0 critical, 0 major, 2 minor |
| 4 | Integration & Conventions | PASS | 0 critical, 0 major, 1 minor |
| 5 | Verification & Coverage | PASS | 0 critical, 0 major, 3 minor |
| 6 | Completeness & Risk | PASS | 0 critical, 0 major, 5 minor |

### Findings

#### Minor (nice to fix)
- **[Design/Contract] IssueCandidate unhashable via DD-5 × DD-6 (cross-fix interaction)** _(#1, #2, #6)_ → mechanical.
- **[Prerequisites] Phase 0 would `--version` non-tools from inline spans (`pytest`, `import`, Dockerfile directives)** _(#3)_ → mechanical.
- **[Design/Step 7] Portability gate misses lowercase `4irl`** _(#5)_ → mechanical.
- **[Step 6] DD-10 README note invites a `KEY=value` line Step 7's gate rejects (cross-fix)** _(#5)_ → mechanical.
- **[Step 6] Docker check leaves base image/cache with no reclaim note** _(#6)_ → mechanical.
- **[Step 5] Exceptions escaping on_message hit discord.py's default on_error (traceback + message)** _(#2)_ → DD-11.
- **[Step 1] Blank `ui_runner_cmd` vs /run-plan's unconditional UI subagent** _(#4)_ → DD-12.
- **[Step 5] No test pins "edits ignored"** _(#5)_ → DD-13.

#### Descriptive (deferred to final cleanup)
- Logging-rule wording vs channel_problems; tag-grammar wording; Step 7 contract-carrier wording; F8 sentence; Contract module list; "only in example.env" scoping.

### To-Do: Mechanical Fixes (auto-applied)
- [x] IssueCandidate unhashable note in Design and Contract _(applied by fixing subagent)_
- [x] Prerequisites Phase 0 exemptions for non-tool inline spans _(applied by fixing subagent)_
- [x] Portability gate `4[Ii][Rr][Ll]` in Design and Step 7 _(applied by fixing subagent)_
- [x] Step 6 README: describe the hand-export in words, no `KEY=value` line _(applied by fixing subagent)_
- [x] Step 6 Docker base-image/cache reclaim note (owner-only) _(applied by fixing subagent)_

### Design Decisions

#### DD-11: [Step 5] Exceptions escaping on_message (safety)
| # | Option | Trade-off |
|---|---|---|
| 1 | F1 `on_error` override logging only type + event | Rule enforced structurally; tracebacks need reproduction |
| 2 | Contract note only | Default traceback logging stays |

**Chosen:** 1 — `on_error` override + Red test.

#### DD-12: [Step 1] Blank `ui_runner_cmd`
**Chosen:** Prerequisites note telling the /run-plan orchestrator to skip the UI subagent (N/A).

#### DD-13: [Step 5] Edits-ignored test
**Chosen:** add `test_edits_not_handled` (`assert not hasattr(IssueBot, "on_message_edit")`).

---

### Verdict
[ ] Ready to proceed as-is
[x] Proceed after minor fixes (applied)
[ ] Requires changes before proceeding

### Descriptive cleanup: 8 fixed, 2 dropped

### Missed-Finding Root Causes
| Finding | Severity | Unit | cause_class | Root cause | Skill gap? | Ledger id |
|---|---|---|---|---|---|---|
| on_error logs exception text and traceback | minor | subagent-2:full-stack-trace | scoped_too_narrowly | Pass 1 traced only the hook's success path | yes (log sinks) | not logged |
| IssueCandidate unhashable (DD-5 × DD-6) | minor | step-5f:dd-application | fix_regression | No cross-DD property re-derivation | yes | not logged |
| DD-10 README note vs README gate | minor | step-5f:dd-application | fix_regression | New gates not run against DD-invited output | yes | not logged |

(`not logged`: the ledger is in `review_due`, which records critical misses only.)
