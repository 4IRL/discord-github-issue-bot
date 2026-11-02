# Push Review: feature/idempotent-filing

## Review 1
Generated: 2026-11-01 21:38
Comparison: origin/main ba17bec2bc14c6dff0774becc373e67b888aebf4..faff941289be1f3a3fc76a7abb7b21c67a7f7823
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No injection, secret leakage or destructive operations; the lookup logs only stage/status and validates response shapes.
- minor: `reports_link` matches any issue whose first line ends with the summary URL, whoever opened it (already accepted as plan pass2-DD-1; revisit in F13).

#### 2. Correctness — PASS
Dedup lookup, shared Report guard and Edit/timeout refusals are sound; no await between the filed check and set.

#### 3. Simplicity & Conciseness — PASS
- minor: `file_button` writes `self._closed = True; self.stop()` in both the refusal branch and the filing path.

#### 4. Test Coverage — PASS
- minor: no test shows a fresh modal submit starts its own `Report` (a shared/module-level Report regression would refuse every later report).
- minor: no hook-level test for a failed lookup followed by a normal create and reply (covered at `file_candidate` level).

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs or stubs; docstrings and docs match the code.

#### 6. Consistency & Style — PASS
Follows project conventions.

#### 7. Integration Risk — PASS
Defaulted params keep callers compatible; existing token covers the GET.

#### 8. Error Handling & Silent Failures — PASS
`find_issue` raises `GitHubError` on every failure path; `file_candidate` catches only `GitHubError`.

#### 9. Type Design — PASS
- minor: `Report.filed` is a public mutable one-way latch; optional `mark_filed()` (no change required).

### To-Do: Required Changes

- [ ] **Add a test that two fresh reports each file** — `tests/test_intake.py` — Submit two fresh modals (two `submitted_preview` calls), press File on the first then the second; assert the hook is awaited twice and the two views' `report` objects are distinct.
- [ ] **Add a hook-level failed-lookup test** — `tests/test_bot.py` — `filing_hook` with `find_issue` raising `GitHubError("lookup", 502)`: `create_issue` awaited once, `filed_reply` posted, the lookup WARNING present and `assert_no_member_text(caplog)`.
- [ ] **Deduplicate the close sequence in `file_button`** — `issue_bot/intake.py` — Set `_closed`/`stop()` once before branching on whether the report was already filed, keeping everything before the first await.
- [ ] **Optionally add `Report.mark_filed()`** — `issue_bot/intake.py` — Or leave as is (type reviewer: no change required).
- [ ] **(Accepted, no change) Lookup trusts the author line alone** — `issue_bot/issues.py`, `issue_bot/github.py` — Recorded as plan pass2-DD-1; revisit in F13.
