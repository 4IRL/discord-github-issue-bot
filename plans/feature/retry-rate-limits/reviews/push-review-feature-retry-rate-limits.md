# Push Review: feature/retry-rate-limits

## Review 1
Generated: 2026-11-17 14:28
Comparison: origin/main 986aea21592086bf4cec75e1a6927652ee2216e6..56d530e505eecacc8ebd3e3dd164b8f8a907ac80
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No secrets, injection or logging-rule violations; GitHubError raises stay outside except blocks (from None), header values and response text are never logged.
- minor: any member may press Retry (accepted as DD-2); bounded to one idempotent, fail-closed re-filing per press.

#### 2. Correctness — PASS
Retry/backoff, the fail-closed re-filing, create_issue never re-sent after transport/5xx, _post_outcome retries and RetryView are correct.
- minor: a Retry press whose ack (edit_message) raises never re-files (accepted known limit, dd-261117-074; README Known limits).
- minor: filing_hook docstring paragraph is badly wrapped.

#### 3. Simplicity & Conciseness — PASS
Proportionate; minor tidy-ups.
- minor: RetryView.on_timeout has two near-identical except branches; collapse via discord_error_fields.
- minor: _post_outcome's failure temp + trailing AssertionError; _retry_wait's nested header parsing could use a small helper.
- minor: filing_hook docstring wrap.

#### 4. Test Coverage — PASS
Behavior-level coverage of retries, rate limits, the Retry button, fail-closed re-filing and log safety; minor gaps.
- minor: no direct parametrized test of GitHubError.transient.
- minor: _post_outcome backoff schedule [1.0, 2.0] and the aiohttp.ClientError branch not asserted directly.
- minor: secondary-limit 403 with retry-after on create_issue (non-idempotent, still retried) untested.
- minor: error-post send failure + RetryView stop covered only via test_filing_error_send_failure_logged_without_text (already asserts the view is stopped).

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs or stubs; docs match behavior.
- minor: filing_hook docstring wrap.

#### 6. Consistency & Style — PASS
- minor: single-letter names k/v in aiohttp_transport's header comprehension and c in a test_github.py comprehension.
- minor: aiohttp_transport docstring summary split over two lines; filing_hook docstring wrap.

#### 7. Integration Risk — PASS
All internal API changes (Transport 3-tuple, report_error public, GitHubError rate_limited, file_candidate refiling) are backward compatible or fully updated; no external consumers.

#### 8. Error Handling & Silent Failures — PASS
- minor: Retry ack failure (accepted known limit, dd-261117-074).
- minor: the 'retrying filing' WARNING and 'could not file' ERROR don't record rate_limited, so a rate-limited 403/200 reads like a permission or schema error in logs.

#### 9. Type Design — PASS
- minor: GitHubError isn't picklable/copyable (pre-existing; no action).
- minor: RetryView.message is assigned by the caller, as PreviewView does (consistent; no action).

### To-Do: Required Changes

- [ ] **Re-wrap the filing_hook docstring** — `issue_bot/bot.py` — re-wrap the paragraph containing "never logs member text or GitHub response text: only the type, ids, URLs," to the file's docstring width.
- [ ] **Rename single-letter comprehension variables** — `issue_bot/github.py` (aiohttp_transport: `k, v` → `name, value`), `tests/test_github.py` (`c` → `recorded`, matching the file's existing rename).
- [ ] **Give aiohttp_transport a one-line docstring summary** — `issue_bot/github.py` — one-line summary, blank line, then the lowercased-header detail.
- [ ] **Collapse RetryView.on_timeout's two except branches** — `issue_bot/bot.py` — one `except Exception as exc` using `discord_error_fields(exc)` to log type, status, code and message id.
- [ ] **Log rate_limited on filing retry/failure** — `issue_bot/bot.py` `filing_hook.attempt` — add `rate_limited=%s` (bool) to the 'retrying filing' WARNING and the 'could not file' ERROR; update the asserting tests in `tests/test_bot.py`.
- [ ] **Add a parametrized GitHubError.transient test** — `tests/test_github.py` — None, 500/502/503/504, rate_limited=True → True; 400/401/404/422 → False.
- [ ] **Assert _post_outcome's backoff schedule and ClientError branch** — `tests/test_bot.py` — in the link-post retry/give-up tests, assert sleeps equal [call(POST_BACKOFF), call(2 * POST_BACKOFF)] and cover aiohttp.ClientConnectionError.
- [ ] **Cover a rate-limited 403 on create_issue** — `tests/test_github.py` — create_issue gets (403, None, {"retry-after": "2"}) then issue_response(); assert one sleep of 2.0 and two ISSUE_URL requests.
- [ ] **Simplify _retry_wait header parsing and _post_outcome's failure temp (optional)** — `issue_bot/github.py`, `issue_bot/bot.py` — extract `_requested_wait(headers, now) -> float | None`; restructure the retry loop so the trailing AssertionError isn't needed. Behavior unchanged.

6b: skipped (Review 1)
