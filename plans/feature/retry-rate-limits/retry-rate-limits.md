# Retry and rate limits (F13)

## Summary
Transient GitHub failures (transport errors, 5xx, 429, primary and secondary rate limits) are
retried with bounded backoff that honors `Retry-After` / `x-ratelimit-reset`, and the bot's
outcome posts in Discord are retried the same way. When filing still fails after the last
attempt, the thread's error post carries a **Retry** button that re-runs filing for that report
through F12's `file_candidate` (idempotent), replacing `FILING_ERROR_REPLY`'s "run the command
again". Source: `plans/META-PLAN.md` § *F13 — Retry and rate limits*; F12's kept contract
(retries of one report sequential, re-file only through `file_candidate`).

## Research Findings
- **No headers today.** The `Transport` alias in `issue_bot/github.py` returns `(status, json)`;
  `aiohttp_transport` drops `resp.headers`, so `Retry-After` and
  `x-ratelimit-*` are unreadable. `GitHubClient._request` is the single HTTP
  choke point (callers: `_installation_token`, `ensure_label`, `create_issue`, `find_issue`,
  `_graphql`). It raises `GitHubError(stage, None) from None` *outside* the except block so
  `__context__` is None (frames hold the bearer token; pinned by
  `test_transport_error_raises_status_none`). The client injects `transport` and `clock` but no
  `sleep`; there is no `asyncio.sleep`, backoff or lock anywhere in `issue_bot/`, and no
  pytest-timeout, so an un-injected real sleep would hang the suite.
- **Only `create_issue` is unsafe to repeat.** Token mint, `ensure_label` (422 = exists),
  `find_issue` (GET), `addProjectV2ItemById` (returns the existing item) and the Status, Effort
  and Track field sets are idempotent. A timed-out or 5xx `POST /issues` may have landed, and
  F12's dedup sits one level up in `file_candidate` (`issue_bot/issues.py`, sole caller
  `filing_hook`'s `file_and_report` in `issue_bot/bot.py`).
  GraphQL rate limits can arrive as HTTP 200 with `errors[].type == "RATE_LIMITED"`. Today
  `GitHubClient._graphql` collapses them into `GitHubError(stage, 200)`.
- **Filing runs inline in the File-press callback.** `PreviewView.file_button`
  (`issue_bot/intake.py`) acks with `edit_message`, then `_post_and_file` posts the summary and
  awaits `on_candidate` = `filing_hook(github)`'s `file_and_report` (`issue_bot/bot.py`). That
  hook catches only `GitHubError` and posts through `_post_outcome` (which catches only
  `discord.HTTPException` and has no `view=`). `SUBMITTED_REPLY` goes through the File-press
  followup token (15 min) only after filing returns. `check_access` and `track_lookup` run under
  `asyncio.wait_for(..., FILING_CHECK_TIMEOUT)` (`intake_command`'s `report` and
  `IntakeModal._track_choices`), which cancels an in-flight backoff sleep.
- **Thread and summary posts are outside DD-7's retry (pass2-DD-4, accepted).** `open_thread`
  (`issue_bot/threads.py`) and `_post_and_file`'s summary post catch only
  `discord.HTTPException`, so an `aiohttp.ClientError` or `TimeoutError` that discord.py
  re-raises there escapes before `file_candidate` runs: the report is not filed, there is no
  Retry button, and the reporter gets `INTAKE_ERROR_REPLY` through `PreviewView.on_error`. This
  is today's behaviour, needs a Discord transport failure at that moment, and is out of DD-7's
  scope (`_post_outcome` only).
- **Retry state is in memory only.** The candidate (answers, band, Track, display name) exists
  only in `file_and_report`'s locals. The summary message holds just the type, mention and escaped
  title (`summary_text`, `issue_bot/intake.py`), so a restart-surviving button could not rebuild
  it. No persistent views exist (no `add_view`, `custom_id` or `DynamicItem`); README *Known
  limits* documents dead preview buttons after a restart. `Report.filed` marks the File press, not
  success, so it cannot gate a Retry.
- **discord.py already retries.** discord.py 2.7.1 retries REST 429 and 500/502/504/524 up to 5
  tries (`HTTPClient.request` in `.venv/.../discord/http.py`). What escapes is `DiscordServerError` after those
  tries, plus `aiohttp.ClientError` / `TimeoutError`, which `_post_outcome` does not catch today.
  Its 429 WARNING in `discord.http` (`_log.warning(fmt, method, url, retry_after)`) logs the route
  URL, but no `discord.http` route carries a token: interaction and webhook-token routes
  (`/interactions/<id>/<token>`, `/webhooks/<id>/<token>`) go through `discord.webhook.async_`,
  whose 429 WARNING (`'Webhook ID %s is rate limited. Retrying in %.2f seconds.'`) logs only the
  webhook id. So Standing invariant 2 (tokens are never logged) already holds in 2.7.1 and F13
  adds no log filter (pass1-DD-1).
- **A long filing can outlive the File press's followup token (pass1-DD-4, accepted).**
  `SUBMITTED_REPLY` is sent through that 15-minute token only after `on_candidate` returns
  (`intake.py`, `_post_and_file`). If the automatic retries push filing past it, only
  `SUBMITTED_REPLY` is lost: `_reply` catches the `discord.HTTPException` and logs it as an ERROR
  (type, status, code). The thread still gets the issue link or the error post, which go through
  the bot token, not the followup token.
- Tests: `.venv/bin/pytest` (CLAUDE.md, META-PLAN *Verification*), pytest-asyncio auto mode. GitHub is faked by `AsyncMock` transports that script `(status, json)`
  tuples (`tests/test_github.py` helpers `token_response`, `issue_response`, …). Discord objects
  are `SimpleNamespace` + `AsyncMock` factories in `tests/conftest.py` (`make_message`,
  `make_interaction`, `make_candidate`, `fake_github`); `recording_github` (`tests/test_bot.py`)
  is the stateful fake for idempotent re-filing. View buttons are invoked as
  `await view.<button>.callback(interaction)` or `await view._scheduled_task(item, interaction)`.
  `assert_no_member_text(caplog)` enforces invariant 2.
- **Accepted residual risks (C3; prose only, no guard).**
  - A `TimeoutError` or `aiohttp.ClientError` from a Discord send may follow a post that did
    land, so `_post_outcome`'s retry can post the same issue link or error message twice. The
    harm is a duplicate bot message, never a duplicate issue.
  - A create that times out at `REQUEST_TIMEOUT` (30 s) may land on GitHub after the re-filing's
    lookup has run (`FILING_RETRY_DELAY` later), so a duplicate issue is still possible, though
    much rarer than with no lookup; members close it by hand.
  - `setup_hook`'s startup GitHub access and Project checks go through `_request`, so during a
    GitHub outage they now retry with backoff before failing, which delays startup by at most
    the retry window.
  - A `RetryView` lives `RETRY_TIMEOUT` (a day) in memory; its `on_timeout` edit may fail if the
    thread was archived by then, and `on_timeout` logs and swallows that failure.
- Research done by 4 parallel subagents (architecture, dependencies, request chain, tests); the
  META-PLAN Per-feature session contract defines no Sizing re-score or split check.

## Design decisions

- **DD-1 — Retry button persistence (risk a).** Options: an in-memory view, dead after a restart
  and documented like the preview / a persistent `DynamicItem` with persisted report state.
  **Chosen:** in-memory, non-persistent view (asked; dd-261117-024). After a restart the button is
  dead; README *Known limits* says to run the command again.
- **DD-2 — Who may press Retry (risk b).** Options: reporter only / anyone in the channel.
  **Chosen:** anyone in the channel (asked; dd-261117-025). Re-filing is idempotent through F12,
  so there is no author check and no refusal reply.
- **DD-3 — Retries vs interaction deadlines (risk c).** Options: one uniform retry in
  `_request` / turn retries off on deadline-bound paths. **Chosen:** one uniform retry in
  `GitHubClient._request` (asked; dd-261117-026). The 2 s `wait_for` around `check_access` and
  `track_lookup` cancels the backoff and keeps today's replies.
- **DD-4 — Lookup failure on a re-filing (risk d).** Options: fail closed on re-filings / keep
  F12's fail-open everywhere. **Chosen:** fail closed on re-filings (asked; dd-261117-027).
  `file_candidate(..., refiling=True)` re-raises a lookup `GitHubError` instead of creating; the
  first attempt keeps F12 DD-3's fail-open.
- **DD-5 — Lookup author-line trust (F12 pass2-DD-1).** **Chosen:** keep as is (asked;
  dd-261117-028). `reports_link` is unchanged.
- **DD-6 — Where `create_issue` is retried.** **Chosen:** `_request` never re-sends a
  non-idempotent request after a transport error or 5xx; the filing-level retry re-runs
  `file_candidate` (lookup first) (asked; dd-261117-029). Rate-limited responses (GitHub
  rejected the request) are retried in `_request` for every stage, `issue` included.
- **DD-7 — Bot-level Discord retry.** **Chosen:** a bounded retry inside `_post_outcome` for
  `discord.DiscordServerError`, `aiohttp.ClientError` and `TimeoutError` only. It never re-sleeps
  a 429, which discord.py already handles (asked; dd-261117-030).
- **DD-8 — Where the tunables live.** **Chosen:** UPPER_SNAKE module constants (in `github.py`
  next to `REQUEST_TIMEOUT`, and in `bot.py`), with no config keys, so Standing invariant 3 is
  untouched (asked; dd-261117-031).
- **DD-9 — Transport shape.** **Chosen:** a 3-tuple `(status, data, headers)` with
  lowercase-keyed headers. Every test fake changes (asked; dd-261117-032).
- **DD-10 — Wait longer than the cap.** **Chosen:** stop retrying and surface the error, so
  filing posts the Retry button (asked; dd-261117-033).
- **DD-11 — Retry button scope.** **Chosen:** filing failures only. Roadmap writes get the
  automatic `_request` retries inside `place_on_roadmap`'s never-raise policy, and a roadmap
  failure still posts the link plus `ROADMAP_FAILED_NOTE` with no button (asked; dd-261117-034).
- **DD-12 — Token in discord.py's 429 log.** **Chosen:** filter it in F13, with a logging filter
  that redacts the token segment of webhook and interaction route URLs on the `discord.http`
  logger (asked; dd-261117-035). Revised at review (pass1-DD-1): premise false for discord.py
  2.7.1; Step dropped.

## Steps

### 1. Widen `Transport` to return headers and inject `sleep` (no behavior change) - COMPLETE (2026-11-17)
This step adds response headers and an injectable sleep to the GitHub client, so later steps can
honor `Retry-After` and tests never sleep for real.

**To-do:**
- [x] In `issue_bot/github.py`, change the `Transport` alias to
  `Callable[[str, str, Mapping[str, str], object], Awaitable[tuple[int, Any, Mapping[str, str]]]]`
  and update its comment: the third element is the response headers with **lowercased** keys.
- [x] Change `aiohttp_transport` to return
  `resp.status, data, {k.lower(): v for k, v in resp.headers.items()}`, built inside the
  `async with` block. Keep the `ValueError` → `data = None` handling and `REQUEST_TIMEOUT`.
  Change its return annotation from `tuple[int, Any]` to `tuple[int, Any, dict[str, str]]` and
  its docstring to "Send one JSON request in its own session; return the status, parsed JSON
  (or None) and the response headers with lowercased keys."
- [x] Add a keyword-only `sleep: Callable[[float], Awaitable[None]] = asyncio.sleep` parameter to
  `GitHubClient.__init__` after `clock`, stored as `self._sleep`
  (add `import asyncio` before `import time`; `Awaitable` is already imported from
  `collections.abc`).
- [x] In `GitHubClient._request`, unpack the 3-tuple. Keep the `(status, data)` return to
  callers for now (step 2 changes the loop) and keep the raise-outside-except pattern.
- [x] In `tests/test_github.py`, make every scripted transport response a 3-tuple by appending
  `{}`:
  - the builders `token_response`, `issue_response`, `project_response`, `add_response`,
    `set_response`, `track_project_response` and `set_track_response`, changing each one's
    return annotation from `tuple[int, dict[str, Any]]` to
    `tuple[int, dict[str, Any], dict[str, str]]`, and the module constant `ERRORS_RESPONSE`;
  - the `@pytest.mark.parametrize` value lists of `test_bad_token_shape_raises` (a
    `return_value`), `test_bad_success_shape_raises`, `test_project_fields_bad_response_raises`,
    `test_add_to_project_bad_add_raises`, `test_add_to_project_bad_set_raises` and
    `test_set_track_failure_raises_and_drops_cached_ids`, and each `response: tuple[int, Any]`
    parameter annotation (to `tuple[int, Any, dict[str, str]]`) plus
    `test_set_track_without_option_raises_before_request`'s `lookup: tuple[int, dict[str, Any]]`
    (to `tuple[int, dict[str, Any], dict[str, str]]`);
  - every other inline `(status, body)` in a `side_effect`/`return_value` list, e.g.
    `(status, error_body)`, `(401, None)`, `(201, {})`, `(200, listing)`.

  A missed 2-tuple fails on unpacking in `_request`, so the test run below catches it. Update
  `make_client(...)` to accept and pass an optional
  `sleep: Callable[[float], Awaitable[None]] | None = None` (when None, an `AsyncMock()` that
  records delays; add `Awaitable` to the file's `from collections.abc import Callable`), so no
  GitHub test can sleep for real. Grep `tests/` for other `transport=` users (`grep -rn "transport=" tests/`) and update
  them the same way.
- [x] Add `test_aiohttp_transport_returns_lowercased_headers`: monkeypatch `aiohttp.ClientSession`
  with a fake whose response has `status=200`, `json()` → `{}` and
  `headers={"Retry-After": "3"}`. Assert the result `== (200, {}, {"retry-after": "3"})`. The
  autouse `no_live_github` fixture monkeypatches the module attribute
  `issue_bot.github.aiohttp_transport` at test time. A module-top
  `from issue_bot.github import aiohttp_transport as real_aiohttp_transport` in
  `tests/test_github.py` binds the real function at collection, before any fixture runs, so call
  that, with a one-line comment saying why. The fake `ClientSession` keeps the test offline.
- [x] Run `.venv/bin/pytest tests/test_github.py` and then `.venv/bin/pytest`. All must pass.

### 2. Retry loop in `GitHubClient._request` (TDD)
This step makes `_request` retry rate-limited responses for every stage, and transport errors and
5xx for idempotent stages, with bounded backoff that honors the headers (DD-3, DD-6, DD-8, DD-10);
a rate limit with no usable wait fails at once (pass1-DD-3).

**To-do:**
- [ ] Add module constants in `github.py` beside `REQUEST_TIMEOUT`, with unit comments:
  `MAX_ATTEMPTS = 3  # per request, first try included`, `BACKOFF_BASE = 1.0  # seconds`,
  `BACKOFF_CAP = 8.0  # seconds`, `MAX_RETRY_WAIT = 60.0  # seconds; a longer requested wait fails at once (DD-10)`,
  `RETRY_STATUSES = frozenset({500, 502, 503, 504})`.
- [ ] Extend `GitHubError.__init__(self, stage: str, status: int | None, *, rate_limited: bool = False)`.
  Store `self.rate_limited` and keep the message `f"{stage} request failed status={status}"` (no
  header values, no response text). Add a property
  `transient -> bool: return self.status is None or self.status in RETRY_STATUSES or self.rate_limited`.
  Existing positional constructions (`GitHubError("issue", None)`) keep working.
- [ ] **Red:** in `tests/test_github.py` add, each with an injected recording `sleep` mock and a
  fixed `clock`. A client starts with no cached token, so every scripted `side_effect` list
  starts with `token_response()` (the token mint to `TOKEN_URL` is always the first transport
  call) and the scripted responses below follow it. Count requests by URL from
  `[c.args[1] for c in transport.call_args_list]`, since `await_count` includes the mint:
  - `test_request_retries_5xx_then_succeeds`: `find_issue` gets `(502, None, {})` and then a
    200 list. One sleep of `BACKOFF_BASE` is recorded, and the result is returned.
  - `test_request_retries_transport_error_for_idempotent_stage`: `ensure_label` sees
    `aiohttp.ClientConnectionError("Secret error words")` and then `(201, {}, {})`. It succeeds
    after one sleep.
  - `test_request_gives_up_after_max_attempts`: three 503s raise `GitHubError(stage="lookup", status=503)`
    with `transient` True. The transport URLs are `[TOKEN_URL] + [LOOKUP_URL] * MAX_ATTEMPTS`,
    and there are two sleeps (`BACKOFF_BASE`, `2*BACKOFF_BASE`, each capped at `BACKOFF_CAP`).
  - `test_request_honors_retry_after`: `(429, None, {"retry-after": "7"})` then success. The
    sleep is called with `7.0`.
  - `test_request_honors_ratelimit_reset`: `(403, None, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(int(clock()) + 12)})`
    then success. The sleep is called with `12.0`.
  - `test_request_rate_limit_without_wait_fails_at_once` (parametrized, pass1-DD-3): a bare
    `(429, None, {})` (no usable wait header) and `(403, None, {"retry-after": "0"})` (rate
    limited, since a present `retry-after` header marks a secondary limit, with a wait ≤ 0) each
    raise `GitHubError(status=<that status>, rate_limited=True)` after **one** request to the
    stage's URL (after the token mint) and no sleep.
  - `test_request_rate_limit_over_cap_fails_at_once`: `(429, None, {"retry-after": "3600"})`
    raises `GitHubError(status=429, rate_limited=True)` after **one** request to the stage's URL
    (after the token mint) and no sleep.
  - `test_request_rate_limit_exhausted_raises_rate_limited`: three 429s with `retry-after: 1`
    raise with `rate_limited=True`, `status=429`.
  - `test_plain_403_is_not_retried`: `(403, None, {})` (permission) is returned to the caller
    unchanged after one `LABEL_URL` request (after the token mint), so `ensure_label` raises
    `GitHubError("label", 403)` with `rate_limited` False.
  - `test_create_issue_not_resent_after_transport_error`: `create_issue` sees
    `TimeoutError()`. It raises `GitHubError("issue", None)` after **one** `ISSUE_URL` POST
    (the URLs are `[TOKEN_URL, ISSUE_URL]`), with no sleep (DD-6).
  - `test_create_issue_not_resent_after_5xx`: `(502, None, {})` on POST /issues raises
    `GitHubError("issue", 502)` after one `ISSUE_URL` POST (URLs `[TOKEN_URL, ISSUE_URL]`).
  - `test_create_issue_retried_when_rate_limited`: `(429, None, {"retry-after": "2"})` then
    `issue_response()` gives one sleep of `2.0` and the issue is returned.
  - `test_retry_errors_keep_no_context`: for the exhausted transport-error case, assert
    `__cause__ is None`, `__context__ is None`, `__suppress_context__ is True`, and that
    `"Secret error words"` and `"ghs_secret_token"` are absent from `str(exc)`/`repr(exc)`.

  No new 401 test (pass2-DD-3): the existing `test_*_401_drops_*` tests in
  `tests/test_github.py` script `[token_response(), (401, None, {}), token_response(), <success>]`
  and pin the URL list, so a retried 401 would consume the second token reply and fail them;
  they pin that a 401 is not retried inside `_request` and the caller still drops the token.

  Run them and confirm they fail for the right reason, except the regression guards
  `test_create_issue_not_resent_after_transport_error`, `test_create_issue_not_resent_after_5xx`
  and `test_retry_errors_keep_no_context`: today's `_request` already behaves as they assert, so
  they pass at Red and must stay green after Green.
- [ ] **Green:** give `_request` a keyword-only `idempotent: bool = True` and implement the loop:
  for `attempt` in `1..MAX_ATTEMPTS`, first set `transport_failed = False`, then call the
  transport and unpack `status, data, headers` from its reply. On
  `(aiohttp.ClientError, TimeoutError)` (never bound with `as`) set
  `status, data, headers = None, None, {}` and `transport_failed = True` inside the except and do
  nothing else there (no raise, no reference to the exception). So every attempt starts from
  fresh values, and a transport failure never reuses an earlier attempt's `data` or headers.
  Then compute the wait with a new module function
  `_retry_wait(status, data, headers, attempt, now, idempotent) -> tuple[float | None, bool]`,
  called with `now = self._clock()` read after the transport returns (never `time.time()`, so a
  test's fixed `clock` governs `x-ratelimit-reset`), which returns `(wait, rate_limited)`:
  - Rate limited when `status in (403, 429)` and (`"retry-after" in headers` or
    `headers.get("x-ratelimit-remaining") == "0"`), or `status == 429`, or (`status == 200` and
    `isinstance(data, dict)` and any `e.get("type") == "RATE_LIMITED"` for `e` in
    `data.get("errors") or []` that is a dict). The wait is `float(retry-after)` if parseable,
    else `float(x-ratelimit-reset) - now` if parseable, else unknown. An unknown wait or one
    ≤ 0 is returned as `math.inf` (add `import math` after step 1's `import asyncio`, before
    `import time`), so the caller fails at once with no sleep,
    exactly as for a wait over `MAX_RETRY_WAIT` (pass1-DD-3: GitHub asks for at least a minute
    when it gives no wait, so the bot never backs off 1 s/2 s on a rate limit). This applies
    regardless of `idempotent`. `BACKOFF_BASE`/`BACKOFF_CAP` are never used for a rate limit.
  - Transient when `status is None or status in RETRY_STATUSES`, and only if `idempotent`. The
    wait is `min(BACKOFF_BASE * 2 ** (attempt - 1), BACKOFF_CAP)`.
  - Otherwise `(None, False)`.

  If the wait is `None`, return `(status, data)`, or for a transport failure
  `raise GitHubError(stage, None) from None`. If `wait > MAX_RETRY_WAIT` or
  `attempt == MAX_ATTEMPTS`, `raise GitHubError(stage, status, rate_limited=rl) from None` (a
  transport failure gives `status=None`). Both raises sit outside any except block and use
  `from None`, as every raise in `github.py` does today, so `__context__` stays None and
  `__suppress_context__` is True (`test_retry_errors_keep_no_context`). Otherwise
  `await self._sleep(wait)` and loop. Never read or format response text.
- [ ] Pass `idempotent=False` from `GitHubClient.create_issue`'s `_request` call only. The
  token mint, `ensure_label`, `find_issue` and every `_graphql` call keep the default `True`.
- [ ] In `GitHubClient._installation_token`, build `app_jwt(...)` before the request as
  today. With `MAX_ATTEMPTS=3` and `MAX_RETRY_WAIT=60` the worst-case retry window (≈ 2×60 s +
  3×`REQUEST_TIMEOUT`) stays inside `JWT_LIFETIME` 540 s, so no per-attempt rebuild is needed.
  Add a one-line comment saying so.
- [ ] Update the `GitHubError` docstring to mention `rate_limited` and `transient` (still no
  response text), and the module docstring's "carry the request stage and HTTP status only" to
  "carry the request stage, HTTP status and a rate-limited flag only".
- [ ] **Rework the existing single-failure tests.** These existing `tests/test_github.py` tests
  script one 5xx or transport error on an idempotent stage, which the loop now retries: the
  retry either consumes the success scripted for a later call (so nothing raises) or runs out
  of `side_effect` entries (`StopAsyncIteration`, which `_request` does not catch). One rule for
  all of them: script that failure `MAX_ATTEMPTS` times (import `MAX_ATTEMPTS` from
  `issue_bot.github`), so the raise path is still what each test pins, keep any later call's
  responses after the repeated failures, and rely on `make_client`'s default recording `sleep`
  (step 1), so nothing sleeps for real.
  - `test_ensure_label_500_raises_and_is_not_cached`:
    `[token_response(), *[(500, error_body, {})] * MAX_ATTEMPTS, (201, {}, {})]`; the URL list
    becomes `[TOKEN_URL] + [LABEL_URL] * (MAX_ATTEMPTS + 1)`.
  - `test_ensure_label_transport_error_raises_status_none`:
    `[token_response(), *[error] * MAX_ATTEMPTS, (201, {}, {})]`; `await_count == MAX_ATTEMPTS + 2`.
  - `test_find_issue_non_200_raises_lookup_error`: `[token_response(), *[(500, error_body, {})] * MAX_ATTEMPTS]`.
  - `test_find_issue_transport_error_raises_lookup`: `[token_response(), *[error] * MAX_ATTEMPTS]`.
  - `test_project_fields_non_200_raises`:
    `[token_response(), *[(502, {"message": "Secret detail"}, {})] * MAX_ATTEMPTS]`.
  - `test_add_to_project_transport_error_raises_status_none` (all three cases): `side_effect=`
    `responses[:failing_call] + [aiohttp.ClientConnectionError("Secret error words")] * MAX_ATTEMPTS`.
  - `test_set_track_failure_raises_and_drops_cached_ids`: with
    `repeats = MAX_ATTEMPTS if status is None else 1` (only the `transport` case is retried),
    script `*[response] * repeats` in place of `response`, and replace `len(calls) == 5`,
    `calls[3]` and `calls[4]` with `len(calls) == 4 + repeats`, `calls[-2]` and `calls[-1]`.

  Unchanged: the `issue`-stage 5xx and transport cases (`create_issue` is non-idempotent), the
  tests whose `side_effect` is a single exception that repeats on every call
  (`test_check_access_transport_error_raises_status_none`, the `token` cases of
  `test_transport_error_raises_status_none`), and the `ERRORS_RESPONSE` cases (no
  `RATE_LIMITED`). Never loosen the retry to make one of these pass.
- [ ] **Refactor:** keep `_retry_wait` pure (no `self`, no logging; `github.py` never logs) and
  type-annotated. Run `.venv/bin/pytest tests/test_github.py`, then `.venv/bin/pytest`.

### 3. GraphQL rate limits surface as rate-limited errors
This step makes a `RATE_LIMITED` GraphQL reply that runs out of retries raise
`GitHubError(stage, 200, rate_limited=True)` instead of a schema-mismatch error, without logging
or carrying the errors text.

**To-do:**
- [ ] **Red:** as in step 2, each `side_effect` list starts with `token_response()` and requests
  are counted by URL. Each rate-limited reply carries a usable wait, since one without a wait
  fails at once (pass1-DD-3): with `make_client`'s default `clock` (`1_000_000.0`), the reply is
  `(200, {"errors": [{"type": "RATE_LIMITED", "message": "Secret error words"}]}, {"x-ratelimit-reset": "1000001"})`
  (the reset is one second after the clock).
  Add `test_graphql_rate_limited_retries_then_succeeds` (`project_fields` gets one such reply,
  then a valid project response; one sleep of `1.0`) and
  `test_graphql_rate_limited_exhausted_is_rate_limited` (`MAX_ATTEMPTS` such replies raise
  `GitHubError(stage="project", status=200, rate_limited=True)` with `"Secret error words"` absent
  from `str`/`repr`; the URLs are `[TOKEN_URL] + [GRAPHQL_URL] * MAX_ATTEMPTS` and the sleeps are
  `[call(1.0)] * (MAX_ATTEMPTS - 1)`). Also add
  `test_graphql_rate_limited_without_wait_fails_at_once`: the same reply with `{}` headers raises
  `GitHubError(stage="project", status=200, rate_limited=True)` after one `GRAPHQL_URL` request
  (URLs `[TOKEN_URL, GRAPHQL_URL]`) and no sleep. Also add
  `test_graphql_other_errors_not_retried`: an `errors` list without `RATE_LIMITED` raises
  `GitHubError("project", 200)` after one `GRAPHQL_URL` request (URLs `[TOKEN_URL, GRAPHQL_URL]`),
  as today. Step 2's `_retry_wait` already classifies the body, so these tests are expected to
  pass on their first run: this step confirms Step 2's behaviour rather than driving new code.
- [ ] **Green:** confirm `GitHubClient._graphql` still raises `GitHubError(stage, status)` for non-rate-limit `errors` and
  drops the token on 401 as before. Fix anything the tests expose.
- [ ] Run `.venv/bin/pytest tests/test_github.py`.

### 4. `file_candidate` fails closed on a re-filing (DD-4)
This step lets a re-filing refuse to create when the existing-issue lookup fails, so a create
that timed out but landed is never duplicated.

**To-do:**
- [ ] **Red:** in `tests/test_issues.py` add
  `test_file_candidate_refiling_lookup_failure_raises`: `fake_github` with
  `find_issue=AsyncMock(side_effect=GitHubError("lookup", 502))`. Then
  `await file_candidate(github, candidate, refiling=True)` raises that `GitHubError`, and
  `create_issue` and `ensure_label` are never awaited. Keep the existing
  `test_file_candidate_lookup_failure_still_files` (first attempt, fail-open) green.
- [ ] **Green:** change `file_candidate(github, candidate)` in `issue_bot/issues.py` to
  `file_candidate(github: GitHubClient, candidate: IssueCandidate, *, refiling: bool = False) -> FiledIssue`.
  In its lookup `except GitHubError` branch, `raise` when `refiling` (after the
  existing WARNING log, unchanged), else proceed as today. Update the docstring (DD-3 fail-open on
  the first attempt, fail-closed on a re-filing, F13 DD-4).
- [ ] Run `.venv/bin/pytest tests/test_issues.py`.

### 5. Filing-level retry, `_post_outcome` retry and `view=` (DD-6, DD-7)
This step makes `filing_hook` re-run `file_candidate` once on a transient failure, and makes
`_post_outcome` retry escaped Discord failures, accept a view and return the sent message.

**To-do:**
- [ ] Add constants in `issue_bot/bot.py` with unit comments:
  `FILING_ATTEMPTS = 2  # file_candidate runs; the re-run is a re-filing (DD-4, DD-6)`,
  `FILING_RETRY_DELAY = 2.0  # seconds`, `POST_ATTEMPTS = 3`, `POST_BACKOFF = 1.0  # seconds, doubled per attempt`.
- [ ] **Red (`_post_outcome`)** in `tests/test_bot.py`, driven through the public hook
  (pass2-DD-2; no test imports the private `_post_outcome`), as
  `test_filing_error_send_failure_logged_without_text` already does: a successful filing,
  `github = fake_github(FiledIssue(7, ISSUE_URL, "I_node7"))`, scripted failures on the
  issue-link post `message.create_thread.return_value.send`, and
  `await filing_hook(github, sleep=recording_sleep)(message, secret_candidate(make_candidate))`
  with `recording_sleep = AsyncMock()`. A successful filing never sleeps, so every recorded
  sleep is a post retry (Step 5 Green passes `sleep=sleep` to every `_post_outcome` call):
  - `test_link_post_retries_server_error`: `send.side_effect = [discord.DiscordServerError(SimpleNamespace(status=503, reason="x"), {"code": 0, "message": "Secret error words"}), None]`.
    `send` is awaited twice, `recording_sleep.await_args_list == [call(POST_BACKOFF)]`, no ERROR
    is logged, and `"Secret error words"` is in no `record_texts(caplog)` entry.
  - `test_link_post_retries_transport_error`: `send.side_effect = [aiohttp.ClientConnectionError("Secret error words"), None]`;
    the same assertions.
  - `test_link_post_gives_up_and_logs`: `send.side_effect = TimeoutError()` (raised on every
    call). `send` is awaited `POST_ATTEMPTS` times, no exception escapes the hook, one ERROR
    `could not send issue link for message_id=99 thread_id=1234: TimeoutError status=None code=None`
    is logged, and the sleeps are exactly `[call(POST_BACKOFF), call(2 * POST_BACKOFF)]` (no
    sleep after the last attempt).
  - `test_link_post_does_not_retry_forbidden`: `send.side_effect = forbidden(50013, "Secret error words")`
    gives one send, one ERROR (as today) and no sleep.

  The `view=` pass-through (thread and no-thread) is pinned by Step 6's
  `test_filing_error_post_has_retry_button`; the sent-message return value by Step 6's
  `test_retry_view_timeout_removes_button`.
- [ ] **Green:** change `_post_outcome` to
  `async def _post_outcome(message, thread, text, what, *, view: discord.ui.View | None = None, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> discord.Message | None`.
  Loop `POST_ATTEMPTS` times. Build the send kwargs as
  `allowed_mentions=NO_MENTIONS, suppress_embeds=True` plus `view=view` **only when `view` is not
  None**, so the existing `assert_awaited_once_with(text, allowed_mentions=..., suppress_embeds=True)`
  assertions stay valid. Retry on `discord.DiscordServerError`, `aiohttp.ClientError` and
  `TimeoutError` with `POST_BACKOFF * 2 ** (attempt-1)`; catch `DiscordServerError` before the
  generic `discord.HTTPException` branch. Any other `discord.HTTPException` logs as today and
  returns `None` at once. After the last attempt, log the existing ERROR format (for non-HTTP
  errors, `status` and `code` are `None`) and return `None`. On success return the sent message.
  In `bot.py`, add `import asyncio` as the first stdlib import (before `import logging`) and
  `import aiohttp` as the first third-party import (before `import discord`). Update the
  `_post_outcome` docstring: it retries Discord server and transport errors up to
  `POST_ATTEMPTS` times and returns the sent message, or None when the post failed.
- [ ] **Red (filing retry)** in `tests/test_bot.py`, with `filing_hook(github, sleep=recording_sleep)`:
  - Rework `test_retry_after_timed_out_create_finds_the_issue` (`tests/test_bot.py`): with
    `recording_github(fail_first_create=True)`, **one** `filing_hook(...)(message, candidate)`
    call now re-files automatically. `create_issue` is awaited once, `find_issue` twice, the
    thread gets `filed_reply(...)` once, one sleep of `FILING_RETRY_DELAY` is recorded, and a
    WARNING `retrying filing bug message_id=99 after GitHubError stage=issue status=None` is
    logged.
  - `test_filing_retry_lookup_failure_fails_closed`: the first `create_issue` raises
    `GitHubError("issue", None)`, the re-filing's `find_issue` raises `GitHubError("lookup", 502)`,
    and `create_issue` is never awaited a second time. The error post is made (step 6 adds its
    button).
  - `test_filing_not_retried_on_permanent_error`: `GitHubError("issue", 422)` (not transient)
    gives no sleep, one `create_issue` and the error post.
  - `test_filing_retry_reruns_once_when_rate_limited` (pass1-DD-2):
    `fake_github(GitHubError("issue", 429, rate_limited=True))` (every create is rejected, every
    lookup finds nothing). One `filing_hook(github, sleep=recording_sleep)(message, candidate)`
    call re-files once: `find_issue.await_count == FILING_ATTEMPTS`,
    `create_issue.await_count == FILING_ATTEMPTS`, one sleep of `FILING_RETRY_DELAY`, the WARNING
    `retrying filing bug message_id=99 after GitHubError stage=issue status=429`, one ERROR
    `could not file …` and one `FILING_ERROR_REPLY` post (step 6 adds its button).
  - `test_filing_retry_logs_no_member_text`: `assert_no_member_text(caplog)` over the retry path.
  - Update `test_filing_hook_failure_without_thread_replies_error_on_summary`: its
    `fake_github(GitHubError("token", None))` is transient (status None), so it now re-files.
    Call `filing_hook(github, sleep=AsyncMock())` so it never sleeps for real, and also assert
    one sleep of `FILING_RETRY_DELAY` and `github.create_issue.await_count == FILING_ATTEMPTS`
    (its one-ERROR and `message.reply` assertions stay; the retry log is a WARNING). Every other
    existing `filing_hook(...)` caller in `tests/test_bot.py` and `tests/test_intake.py` is fed a
    success, a non-transient `GitHubError` (`issue` 422, `label` 403, or a roadmap-stage 200) or
    a non-`GitHubError`, so none sleeps.
    Any test added later that feeds `filing_hook` a transient `GitHubError` injects `sleep` too.
- [ ] **Green:** change `filing_hook(github: GitHubClient) -> CandidateHook` to
  `filing_hook(github: GitHubClient, *, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> CandidateHook`.
  Split `file_and_report` into an inner
  `async def attempt(message, candidate, thread, *, refiling: bool) -> None` that loops
  `FILING_ATTEMPTS` times over `file_candidate(github, candidate, refiling=refiling or n > 1)`.
  On a `GitHubError` with `exc.transient` and attempts left, log the WARNING
  `"retrying filing %s message_id=%s after %s stage=%s status=%s"` (type, ids, exc type, stage,
  status only), `await sleep(FILING_RETRY_DELAY)` and loop. `transient` includes `rate_limited`
  (pass1-DD-2), so an exhausted or over-cap rate limit from `_request` also re-runs filing once:
  it costs one extra (fail-closed) re-filing lookup, and a second create when that lookup finds
  nothing, before the error post and its Retry button. Otherwise log the existing ERROR and
  post the error (step 6 adds the view). On success it does exactly today's success path (INFO
  `filed …`, `place_on_roadmap`, `_post_outcome(filed_reply(...))`). `file_and_report` keeps
  `open_thread` and calls `attempt(..., refiling=False)`. Pass `sleep=sleep` to every
  `_post_outcome` call. Update the `filing_hook` docstring: a transient `GitHubError` re-runs
  filing once, as a re-filing, after `FILING_RETRY_DELAY`; a final failure posts
  `FILING_ERROR_REPLY` (Step 6 adds the Retry button and extends this docstring).
- [ ] Check `issue_bot/__main__.py`'s `on_candidate=filing_hook(github)`. The default `sleep`
  needs no change, and `test_main_builds_github_client` (`tests/test_bot.py`, positional-only
  `record_client`) still passes because `GitHubClient(...)` in `__main__.py` is unchanged.
- [ ] Run `.venv/bin/pytest tests/test_bot.py tests/test_intake.py`, then `.venv/bin/pytest`.

### 6. Retry button on the filing-error post (DD-1, DD-2, DD-11)
This step attaches an in-memory **Retry** button to the error post. Any member may press it once.
It re-runs filing as a re-filing, strictly after the automatic retries, never overlapping one.

**To-do:**
- [ ] In `issue_bot/threads.py`, change `FILING_ERROR_REPLY` to fixed text with no member or
  response text:
  `"Sorry, I couldn't file this as a GitHub issue. Press **Retry** to try again; if the button no longer works, check the repo before running the command again."`.
  Update the exact-text pin `test_filing_error_reply_is_fixed_text` (`tests/test_threads.py`).
- [ ] Add `RETRY_TIMEOUT = 24 * 60 * 60  # seconds; the Retry button lives a day, in memory only (DD-1)`
  and `RETRY_ALREADY_REPLY = "This report is already being retried."` (fixed text) to `bot.py`,
  with `RETRYING_REPLY = "Retrying…"` (fixed text, the press's ack, pass1-DD-7) next to it.
- [ ] **Red** in `tests/test_bot.py`. Every test except `test_roadmap_failure_has_no_retry_button`
  (which files successfully) starts from a first filing that fails with a non-transient error, `github = fake_github(GitHubError("issue", 422))` (no automatic re-run, so
  the error post with its `RetryView` is made). Where the press must then succeed, set
  `github.create_issue.side_effect = [GitHubError("issue", 422), FiledIssue(7, ISSUE_URL, "I_node7")]`.
  Never use `recording_github(fail_first_create=True)` here: its only failure,
  `GitHubError("issue", None)`, is transient, so Step 5's automatic re-run finds the recorded
  issue and no error post or Retry button is ever made.
  - `test_filing_error_post_has_retry_button`: the error post is
    `send(FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True, view=<RetryView>)`.
    The view has one enabled button labelled `Retry`, `timeout == RETRY_TIMEOUT`, and
    `view.retry_button.is_persistent()` is False (no `custom_id` set by the code; discord.py
    2.7.1 generates a random one and `Item.is_persistent()` returns whether one was provided).
    `view.is_persistent()` is False too, but only because a timeout is set, so it is not the
    custom_id check. With no thread (`message.create_thread.side_effect = forbidden(50013, "x")`),
    the same post is `message.reply(FILING_ERROR_REPLY, allowed_mentions=NO_MENTIONS, suppress_embeds=True, view=<RetryView>)`.
  - `test_retry_press_refiles_once`: grab the view from
    `message.create_thread.return_value.send.await_args.kwargs["view"]` and run
    `await view.retry_button.callback(make_interaction())`. The press is acked with
    `interaction.response.edit_message(content=RETRYING_REPLY, view=None)`, `file_candidate` runs with `refiling=True`
    (assert `find_issue` ran before `create_issue` on this run), `filed_reply(...)` is posted in
    the thread, and `view.is_finished()` is true.
  - `test_retry_press_ignored_after_first`: a second `callback` on the same view gets
    `response.send_message(RETRY_ALREADY_REPLY, ephemeral=True)` and files nothing more.
    Also cover `asyncio.gather(view.retry_button.callback(first), view.retry_button.callback(second))`
    of two presses, where the **first** press's `response.edit_message.side_effect` is an `ack`
    that does `await asyncio.sleep(0)` and then sets `first.response.is_done.return_value = True`
    (as in `test_file_only_once`, `tests/test_intake.py`). The second press runs while the first
    is suspended in its ack, so it gets `RETRY_ALREADY_REPLY` only if `pressed` was set before
    that await: exactly one re-filing.
  - `test_retry_failure_posts_new_retry_button`: the re-filing fails again, so a **new** error
    post with a **new** `RetryView` is sent, and the old view is finished.
  - `test_retry_press_lookup_failure_fails_closed` (pass1-DD-5): `fake_github(GitHubError("issue", 422))`
    with `github.find_issue = AsyncMock(side_effect=[None, GitHubError("lookup", 422)])`, and
    `filing_hook(github, sleep=AsyncMock())`. The first filing's lookup finds nothing and its
    create fails (422, not transient, so no automatic re-run). On the Retry press the re-filing's
    lookup raises, and `file_candidate(..., refiling=True)` re-raises it instead of creating:
    `create_issue.await_count == 1` in total, a second `FILING_ERROR_REPLY` post is sent with a
    **new** `RetryView` (not the pressed one), and the last ERROR is
    `could not file bug message_id=99 … GitHubError stage=lookup status=422`.
  - `test_retry_press_by_any_member`: a press from a user whose id differs from
    `candidate.author_id` re-files (DD-2, no author check).
  - `test_retry_view_on_error_logs_safely`: the first filing fails with
    `fake_github(GitHubError("issue", 422))`, so the error post carries the view; grab it as in
    `test_retry_press_refiles_once`, then set
    `github.find_issue.side_effect = RuntimeError("Secret exception words")` so only the press's
    re-filing raises, and run `await view._scheduled_task(view.retry_button, interaction)`. The
    log is `unhandled RuntimeError in bug retry interaction_id=4242 status=None code=None` (via
    `intake.report_error`, on the `issue_bot.intake` logger, so read it with
    `record_texts(caplog)`, not `bot_records`), `interaction.followup.send` is awaited once with
    `(INTAKE_ERROR_REPLY, ephemeral=True)` (the press's edit ack already marked the response
    done), and `assert_no_member_text(caplog)` passes.
  - `test_retry_view_timeout_removes_button`: `await view.on_timeout()` edits the stored error
    message with `view=None`. An `HTTPException` there is logged by type/status/code and
    swallowed.
  - `test_roadmap_failure_has_no_retry_button`: filing succeeds, `place_on_roadmap` returns
    `False`, and the link post has no `view` kwarg (DD-11).
- [ ] **Green:** add `class RetryView(discord.ui.View)` in `issue_bot/bot.py`, with
  `__init__(self, retry: Callable[[], Awaitable[None]], issue_type: IssueType)` calling
  `super().__init__(timeout=RETRY_TIMEOUT)`, and attributes `self._retry = retry`,
  `self.issue_type = issue_type`, `self.pressed = False` and
  `self.message: discord.Message | None = None`. Its button is
  `@discord.ui.button(label="Retry", style=discord.ButtonStyle.primary) async def retry_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None`
  (annotated as `PreviewView`'s buttons are):
  if `self.pressed`, send `RETRY_ALREADY_REPLY` ephemerally and return. Otherwise set
  `self.pressed = True` **with no `await` before it** (the F12 sequencing guard, like
  `PreviewView.file_button`), call `self.stop()`, ack with
  `await interaction.response.edit_message(content=RETRYING_REPLY, view=None)` (like
  `file_button`'s `FILING_REPLY` ack, so the pressed post no longer says "Press **Retry**"), then
  `await self._retry()`. Note (pass2-DD-1, accepted): `stop()` removes the view from
  discord.py's `ViewStore`, so a press Discord delivers after it gets no reply from the bot and
  Discord shows "This interaction failed". Nothing files twice; `RETRY_ALREADY_REPLY` covers
  presses dispatched before `stop()` ran (the same ordering as `PreviewView.file_button`).
  `async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item, /) -> None`
  (signature and docstring as `PreviewView.on_error`) calls
  `await report_error(interaction, error, self.issue_type, "retry")`. First rename `intake.py`'s
  `_report_error` to public `report_error` (pass1-DD-6, the `discord_error_fields` precedent):
  its definition and its two call sites, `PreviewView.on_error` (`"preview"`) and
  `IntakeModal.on_error` (`"modal"`); `grep -rn "_report_error" issue_bot tests || true` then
  prints nothing (no test imports or patches it). In `bot.py`, add `report_error` to the
  `from issue_bot.intake import (...)` block right after `intake_command` (the block stays
  alphabetized: constants, classes, then functions). `on_timeout`
  edits `self.message` with `view=None` when set, catching `discord.HTTPException` (ERROR with
  type, status, code, message id) and `Exception` (type only).
- [ ] In `filing_hook`'s `attempt`, on the final failure build
  `view = RetryView(lambda: attempt(message, candidate, thread, refiling=True), candidate.type)`,
  then `sent = await _post_outcome(message, thread, FILING_ERROR_REPLY, "filing error", view=view, sleep=sleep)`
  and `view.message = sent`. If `sent is None` (the post failed), call `view.stop()`. Retries stay
  sequential: the button exists only after the automatic retries end, each view files at most once,
  and a new button appears only after that re-filing has failed. Extend the `filing_hook`
  docstring: the final `FILING_ERROR_REPLY` post carries a **Retry** button (`RetryView`).
- [ ] Update the existing assertions that pin the filing-error send kwargs (the error-post pins
  in `tests/test_bot.py`, including Step 5's filing-retry tests, and
  `test_github_error_still_posts_filing_error_reply` in `tests/test_intake.py`;
  `test_retry_after_timed_out_create_finds_the_issue` no longer posts an error after Step 5) to expect
  `view=ANY` (from `unittest.mock`) or to assert the view's type. Grep for every
  `FILING_ERROR_REPLY` use in `tests/` and update each one.
- [ ] Run `.venv/bin/pytest tests/test_bot.py tests/test_threads.py tests/test_intake.py`, then
  `.venv/bin/pytest`.

### 7. Documentation
This step records the new behavior where operators read it.

**To-do:**
- [ ] `README.md`: describe automatic retries (GitHub: up to `MAX_ATTEMPTS` per request, honoring
  `Retry-After`/`x-ratelimit-reset` up to `MAX_RETRY_WAIT`, and failing at once on a rate limit
  with no usable wait; a create is never re-sent blindly, and
  filing re-runs once with the lookup first, failing closed; Discord outcome posts retried
  `POST_ATTEMPTS` times) and the **Retry** button (any member, once per post, in memory). In
  *Known limits*:
  - Rewrite the bullet that starts "No automatic retry until F13: a timeout can leave an issue
    filed after an error reply." to the F13 behaviour: a timeout can still leave an issue filed
    after an error, so filing re-runs automatically once, and each re-run (automatic or
    **Retry**) first looks for an issue already linking the same summary message among the
    repo's 100 newest issues and pull requests; if that lookup fails, the first attempt logs a
    WARNING and files anyway, while a re-filing stops and posts the error with a **Retry**
    button. Keep "Running the command again is a new report, so check the repo first."
  - In the bullet that starts "A report is filed once", change "so after a failed filing run
    the command again (check the repo first)" to "so after a failed filing press **Retry** on
    the error post, or, once that button no longer works, check the repo and run the command
    again".
  - Add: the Retry button is dead after a restart or after `RETRY_TIMEOUT` (a day). Then run the
    command again after checking the repo.
- [ ] `CLAUDE.md`, *Project rules*, the "Logs never contain members' message text or names"
  bullet: change "the command, modal and preview-view error handlers" to "the command, modal,
  preview-view and Retry-view error handlers" (wording otherwise unchanged).
- [ ] `docs/SMOKE-TEST.md`, *Troubleshooting*, the row for "The log shows `could not look up an
  existing issue for … stage=lookup status=…`": change "that lookup failed, and the bot filed
  anyway." to "that lookup failed, and on a first attempt the bot filed anyway.", and replace
  the row's last sentence, "After `stage=lookup` the issue is filed normally, but once F13
  retries filings, a retry would not be deduplicated while the lookup fails.", with "After
  `stage=lookup` on a first attempt the issue is filed normally; on a re-filing (the automatic
  re-run or a **Retry** press) the bot stops instead and posts the error with a **Retry**
  button, so check the repo before pressing it." Afterwards
  `grep -n "once F13 retries filings" docs/SMOKE-TEST.md || true` prints nothing.
- [ ] Do not edit `plans/META-PLAN.md` here. The fold-back happens after merge (`/run-feature`
  Phase C).

### 8. Verify All Tests Pass
Run the full suite and check the Expected end state.

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm all tests pass.
- [ ] Check Standing invariant 1:
  `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot || true`
  prints nothing (the `|| true` keeps grep's exit 1 on no match from reading as a failure; the
  pass condition is empty output).
- [ ] Check invariant 2 by grep: no new log call in `issue_bot/` passes `candidate.title`,
  `candidate.answers`, `author_name`, an interaction object, response `data`, `exc_info=True`,
  or a header value (`git diff main -- issue_bot | grep -nE 'logger\.(debug|info|warning|error|exception)' || true`
  and read each hit). `github.py` still has no logger.
- [ ] Check invariant 3: `git diff main -- issue_bot/config.py example.env example.routes.toml`
  is empty (no new config keys).
- [ ] Investigate and fix any failure before marking the plan finished.

## Status
finished: false
