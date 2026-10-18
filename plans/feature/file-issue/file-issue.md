# File the issue in the target repo (F5)

## Summary
Each `IssueCandidate` becomes a GitHub issue in its target repo (`candidate.target.github_repo`, never a
constant). The title comes from `Title:`. The body holds `Body:`, the Discord author and a link to the
message. The label is `candidate.target.labels[candidate.type]`. The bot authenticates as a **GitHub App**
(RS256 JWT → installation token, down-scoped to the target repo id and cached until near expiry). On a
filing failure it posts a short, fixed error reply in the issue's thread. On success it posts nothing,
because F7 adds the link; the filer returns `FiledIssue(number, html_url)` for F7 to use.

Owner decisions (2026-10-18, F5 planning): GitHub App auth (not a PAT); on failure a visible error
reply only, nothing on success (F7 posts the link).

## Research Findings
- **Seam.** `IssueBot(config, on_candidate=open_issue_thread, on_malformed=reply_format_hint)`
  (`IssueBot.__init__` in `issue_bot/bot.py`). `CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]`
  (`issue_bot/bot.py`). `main()` in `issue_bot/__main__.py` runs `IssueBot(config).run(config.discord_token, log_handler=None)`. F5 plugs
  in through `on_candidate` (F1 contract: no second dispatch path). `__main__` passes a filing hook, and
  the class default `open_issue_thread` stays for tests and for a bot built without GitHub.
- **No session lifecycle needed.** Filing volume is a handful of issues a day, so the real transport opens
  a short-lived `aiohttp.ClientSession` per request (`async with`). That avoids `setup_hook`/`close`
  overrides, and `IssueBot`'s constructor stays side-effect free (tests build it with no running loop).
  aiohttp 3.14.5 is already pinned (`requirements.txt`).
- **Dependencies.** RS256 needs `cryptography` (+ `cffi`, `pycparser`). `PyJWT` is the conventional
  encoder. None is installed in `.venv`. Latest stable on PyPI: PyJWT 2.15.1, cryptography 50.0.2,
  cffi 2.1.1, pycparser 3.11. All ship manylinux / pure wheels, so `python:3.12.11-slim` needs no build
  tools.
- **Config keys appear in three test lists.** `tests/conftest.py` `test_env` (the single valid env),
  `tests/test_config.py` `ALL_KEYS` (must equal `from_env`'s **read order**) and `ID_KEYS`, and
  `tests/test_bot.py` `CONFIG_KEYS`. `test_main_runs_bot_with_token` (`tests/test_bot.py`) stubs
  `IssueBot` as `StubBot.__init__(self, config)`.
- **Privacy idiom.** Errors are logged as `type(exc).__name__`, status and code, never their text.
  Tests plant `Secret … words` / `Alice` sentinels and assert they are absent from `record_texts(caplog)`
  (helper in `tests/test_bot.py`). A GitHub 422 `message` can echo the submitted title, so GitHub errors are logged by
  type, stage and HTTP status only. The private key file is multi-line PEM and cannot travel through
  `docker --env-file` (README), so it is a **path** (`GITHUB_APP_PRIVATE_KEY_PATH`) to a read-only
  bind mount. Tests generate an RSA key in memory and write it under a neutral name (the agent sandbox
  denies `**/*.pem`).

## Design (contracts the steps build)

- `issue_bot/config.py` — `Config` gains, in read order after `DISCORD_GUILD_ID`:
  `github_app_id: int` (`GITHUB_APP_ID`, `_positive_int`), `github_installation_id: int`
  (`GITHUB_APP_INSTALLATION_ID`, `_positive_int`), and `github_private_key: RSAPrivateKey = field(repr=False)`
  (`GITHUB_APP_PRIVATE_KEY_PATH`, `_required`, then read and parsed). Field order: `discord_token, guild_id,
  github_app_id, github_installation_id, github_private_key, target`. Instance-wide: one App, one org
  installation (F8 adds repos to the installation). Error: `ConfigError("GITHUB_APP_PRIVATE_KEY_PATH must
  name a readable RSA private key")`, raised `from None` for `OSError`, `ValueError`, `TypeError`,
  `cryptography.exceptions.UnsupportedAlgorithm` (DD-7) and a non-RSA key. An encrypted key loaded with
  `password=None` raises `TypeError`. It names the key only: no path, no contents, no library text.
- `issue_bot/github.py` (new; no logger, since the module never logs):
  - Constants `API_URL = "https://api.github.com"`, `API_VERSION = "2022-11-28"`,
    `USER_AGENT = "discord-github-issue-bot"`, `TOKEN_REFRESH_MARGIN = 300  # seconds before expires_at`,
    `JWT_LIFETIME = 540  # GitHub rejects exp > 10 minutes ahead`, `REQUEST_TIMEOUT = 30  # seconds`.
  - `Transport = Callable[[str, str, Mapping[str, str], object], Awaitable[tuple[int, Any]]]`, which takes
    (method, url, headers, json payload) and returns (HTTP status, parsed JSON or `None`).
  - `async def aiohttp_transport(method, url, headers, payload) -> tuple[int, Any]`, one session per
    call, with the body read inside both contexts:
    ```python
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
        async with session.request(method, url, headers=headers, json=payload) as resp:
            try:
                data = await resp.json(content_type=None)
            except ValueError:
                data = None
            return resp.status, data
    ```
    Observed with the repo's aiohttp 3.14.5 against a local `TestServer`: an empty body (204, or 200 with
    no bytes) returns `None` without raising; a non-JSON body (`text/plain`, `text/html`, or malformed
    JSON under `application/json`) raises `json.JSONDecodeError`, a `ValueError`; with `content_type=None`
    the mimetype check is skipped, so `aiohttp.ContentTypeError` is never raised and needs no handler.
  - `@dataclass(frozen=True) class FiledIssue: number: int; html_url: str`.
  - `class GitHubError(Exception)` with attributes `stage: str` (`"token"` or `"issue"`) and
    `status: int | None` (`None` for a transport failure). `str()` is `f"{stage} request failed
    status={status}"`, never response text.
  - `def app_jwt(app_id: int, private_key: RSAPrivateKey, now: float) -> str` →
    `jwt.encode({"iat": int(now) - 60, "exp": int(now) + JWT_LIFETIME, "iss": str(app_id)}, private_key,
    algorithm="RS256")`.
  - `class GitHubClient`:
    `__init__(self, app_id: int, installation_id: int, private_key: RSAPrivateKey, *, transport:
    Transport | None = None, clock: Callable[[], float] = time.time)`. It resolves
    `self._transport = transport or aiohttp_transport` at init, so the conftest guard below can patch the
    module global. Tokens are cached in `self._tokens: dict[int, tuple[str, float]]`, keyed by repo id,
    holding (token, expires_at epoch). `__repr__` returns `f"GitHubClient(app_id={app_id},
    installation_id={installation_id})"` and never shows the key or a token.
    `async def create_issue(self, target: TargetConfig, title: str, body: str, labels: list[str]) ->
    FiledIssue` performs these steps:
    1. `token = await self._installation_token(target.github_repo_id)`.
    2. POST `f"{API_URL}/repos/{target.github_repo}/issues"` with headers `{"Accept":
       "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION, "User-Agent": USER_AGENT,
       "Authorization": f"Bearer {token}"}` and payload `{"title": title, "body": body, "labels": labels}`.
    3. Status 201 whose body passes `isinstance(data, dict)`, `type(data.get("number")) is int` (a bool
       is rejected) and `isinstance(data.get("html_url"), str)` → `FiledIssue`. Status 401 →
       `self._tokens.pop(target.github_repo_id, None)` (never a keyed `del`: a concurrent filing may
       already have dropped it) and raise `GitHubError("issue", 401)`. Any other status, or a 201 failing
       that shape check → `GitHubError("issue", status)`. A transport exception (`aiohttp.ClientError`,
       `TimeoutError`) → `GitHubError(stage, None) from None`. The 201 response shape (`number`,
       `html_url`, labels as applied by an App) is _(unverified until the owner probe in Manual checks)_.

    `_installation_token(repo_id)` reuses a cached token while `clock() < expires_at -
    TOKEN_REFRESH_MARGIN`. Otherwise it POSTs `f"{API_URL}/app/installations/{installation_id}/access_tokens"`
    with `Authorization: Bearer <app_jwt>` (same other headers) and payload `{"repository_ids":
    [repo_id], "permissions": {"issues": "write"}}`. It expects 201 `{token: str, expires_at: ISO-8601}`
    and validates the body: `isinstance(data, dict)`, `isinstance(data.get("token"), str)` and
    `isinstance(data.get("expires_at"), str)`; then `datetime.fromisoformat(data["expires_at"])` inside
    `try/except ValueError`, rejecting a naive result (`tzinfo is None`), and `.timestamp()` of it. Any
    other status, or a 201 failing any of these checks, raises `GitHubError("token", status) from None`.
    This request body and the response shape (`expires_at` ending in `Z`, the scoped `repositories` /
    `permissions`) are _(unverified until the owner probe in Manual checks)_.

    Both POSTs go through a private `_request(stage, url, headers, payload) -> tuple[int, Any]`, which
    calls `await self._transport("POST", url, headers, payload)` with all four arguments positional (both
    calls are POST; the tests assert `call_args.args`), and converts `(aiohttp.ClientError, TimeoutError)`
    into `raise GitHubError(stage, None) from None`.
  - The module never logs. Callers log `GitHubError` by type, stage and status.
- `issue_bot/issues.py` (new) — the **single issue-body builder** (F3 extends it):
  - `ISSUE_TITLE_LIMIT = 256  # GitHub's maximum issue-title length.`
  - `def issue_title(candidate: IssueCandidate) -> str`: the title cut to 256 code points with `…`
    (same shape as `threads.thread_name`).
  - `def _defang_mentions(text: str) -> str` → `text.replace("@", "@\u200b")`: every `@` is followed by
    U+200B (zero-width space), so GitHub renders no @mention and notifies nobody (DD-5).
  - `def issue_body(candidate: IssueCandidate) -> str` →
    ``f"{_defang_mentions(candidate.body) or '_No description given._'}\n\n---\nReported by `{_defang_mentions(candidate.author_name)}` in Discord: {candidate.message_url}"``.
    Member-supplied text (the body and the author name) is defanged; the author name is wrapped in
    backticks. A display name that itself contains a backtick still renders acceptably, so it is accepted
    as is.
  - `def issue_labels(candidate: IssueCandidate) -> list[str]` → `[candidate.target.labels[candidate.type]]`.
  - `async def file_candidate(github: GitHubClient, candidate: IssueCandidate) -> FiledIssue`, which calls
    `github.create_issue(candidate.target, issue_title(candidate), issue_body(candidate),
    issue_labels(candidate))` and returns the `FiledIssue`, which F7 consumes for the link.
- `issue_bot/threads.py` — `FILING_ERROR_REPLY = "Sorry, I couldn't file this as a GitHub issue. Check
  the repo before reposting; to retry, post a new message (edits are ignored)."` (fixed text, no member
  or GitHub text; an issue-stage timeout may still have filed the issue, hence "check the repo").
- `issue_bot/bot.py` — `def filing_hook(github: GitHubClient) -> CandidateHook` returns `async def
  file_and_report(message, candidate) -> None`, which performs these steps:
  1. `thread = await open_thread(message, thread_name(candidate.title))`.
  2. `issue = await file_candidate(github, candidate)`. On `GitHubError as exc`, log ERROR
     `"could not file %s message_id=%s (%s) thread_id=%s: %s stage=%s status=%s"` (type, message id, URL,
     thread id or None, `type(exc).__name__`, `exc.stage`, `exc.status`). If `thread` is not None, send
     `FILING_ERROR_REPLY` with `reply_format_hint`'s `try/except discord.HTTPException` pattern (log
     `"could not send filing error for message_id=%s thread_id=%s: %s status=%s code=%s"`). Then return.
  3. On success, log INFO `"filed %s message_id=%s (%s) thread_id=%s issue=%s"` with `issue.html_url`.

  The issue is filed even when the thread could not be opened.
- `issue_bot/__main__.py` — `github = GitHubClient(config.github_app_id, config.github_installation_id,
  config.github_private_key)`; `IssueBot(config, on_candidate=filing_hook(github)).run(config.discord_token,
  log_handler=None)`.

## Steps

### 1. Add and install the JWT dependencies
Pin PyJWT and cryptography (plus transitive cffi, pycparser) and install them into `.venv`.

**To-do:**
- [ ] Verify META-PLAN Assumption 1 (read-only): `gh api repos/4IRL/chores4irl/labels/bug --jq .name` prints `bug` and `gh api repos/4IRL/chores4irl/labels/enhancement --jq .name` prints `enhancement`. If either fails, leave this box unticked, write directly under it `UNRESOLVED — requires user decision/action: label check for <label> failed in the target repo (<output>; a 404 means the label is missing)`, end your final report with that same line, and stop. On a later run where the check passes, delete that marker line before ticking the box.
- [ ] Re-check the latest stable versions (`curl -s https://pypi.org/pypi/<pkg>/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"` for PyJWT, cryptography, cffi, pycparser). Expected PyJWT 2.15.1, cryptography 50.0.2, cffi 2.1.1, pycparser 3.11. If a newer stable exists, use it and note the change here. If a lookup fails, use the expected versions and note "PyPI lookup failed; expected versions used" under this box. The pip-install box below still stops if the host is truly blocked.
- [ ] Add to `requirements.txt`, at the versions confirmed in the previous box, each package not already pinned there, keeping its layout and exact-pin style: the direct dependencies `PyJWT` and `cryptography` go after `discord.py==2.7.1` at the top, and the transitive `cffi` and `pycparser` into the alphabetized transitive block (case-insensitive order). `requirements-dev.txt` inherits them through `-r requirements.txt`, so it needs no change.
- [ ] Run `.venv/bin/pip install -r requirements-dev.txt`, then `.venv/bin/pip show cryptography cffi PyJWT pycparser` and confirm each `Requires:` dependency is pinned in `requirements.txt`; add any missing one at its installed version. In the agent sandbox this install is expected to fail before any network call: pip's vendored CA bundle (`.venv/lib/python3.12/site-packages/pip/_vendor/certifi/cacert.pem`) matches the sandbox's `**/*.pem` read deny, so pip exits 1 with `PermissionError: [Errno 13] Permission denied`. If the install fails that way, or because a package host is blocked, do not work around the deny (no other CA bundle, env override or sandbox escape): leave this box unticked, write directly under it `UNRESOLVED — requires user decision/action: pip install fails in the agent sandbox (<error line>); run \`! .venv/bin/pip install -r requirements-dev.txt\` in the session, then resume`, end your final report with that same line, and stop. On a later run where the packages are installed (`.venv/bin/pip show PyJWT cryptography cffi pycparser` lists all four at the pinned versions), delete that marker line before ticking the box.
- [ ] Verify with `.venv/bin/python -c "import jwt, cryptography; print(jwt.__version__, cryptography.__version__)"` and `.venv/bin/pytest -q` (all tests pass).

### 2. Config: GitHub App keys (TDD)
Add the three instance-wide App keys to `Config`, load and validate the private key at startup, and update every test key list.

**To-do:**
- [ ] `tests/conftest.py`: add a `scope="session"` fixture `github_private_key_pem(tmp_path_factory) -> Path`. It generates `rsa.generate_private_key(public_exponent=65537, key_size=2048)`, serializes it with `serialization.Encoding.PEM` / `PrivateFormat.TraditionalOpenSSL` / `NoEncryption()`, and writes it to `tmp_path_factory.mktemp("github-app") / "app-key.txt"`. The neutral name keeps it outside the sandbox's `*.pem` deny; never commit a key file. Add a session fixture `github_private_key(github_private_key_pem) -> RSAPrivateKey` that loads it, so tests can verify JWTs. Make `test_env` depend on `github_private_key_pem` and add `"GITHUB_APP_ID": "333"`, `"GITHUB_APP_INSTALLATION_ID": "444"` and `"GITHUB_APP_PRIVATE_KEY_PATH": str(github_private_key_pem)`.
- [ ] `tests/test_config.py` (Red): insert `"GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID", "GITHUB_APP_PRIVATE_KEY_PATH"` into `ALL_KEYS` right after `"DISCORD_GUILD_ID"`, matching the new read order. Add `GITHUB_APP_ID` and `GITHUB_APP_INSTALLATION_ID` to `ID_KEYS`. Extend `test_full_env_loads` to assert `config.github_app_id == 333`, `config.github_installation_id == 444` and `isinstance(config.github_private_key, rsa.RSAPrivateKey)`. Add these tests:
  - `test_private_key_not_in_repr`: `"github_private_key"` and `"PrivateKey"` are not in `repr(config)`, and neither is the PEM's base64 body line.
  - `test_private_key_path_missing_raises`: a nonexistent path raises `ConfigError` with the exact message `"GITHUB_APP_PRIVATE_KEY_PATH must name a readable RSA private key"`.
  - `test_private_key_not_pem_raises`: a file holding `"Secret key words"` raises the same message, and `"Secret key words"` is not in `str(exc)`.
  - `test_private_key_not_rsa_raises`: an EC key from `ec.generate_private_key(ec.SECP256R1())` written as PEM raises the same message.
  - `test_private_key_error_hides_path`: the path string is not in the message.
  - `test_private_key_encrypted_raises`: an RSA key serialized with `serialization.BestAvailableEncryption(b"pw")` (PEM, `TraditionalOpenSSL`) and written to `tmp_path / "encrypted-key.txt"` raises the same `ConfigError` message (the `TypeError` branch: loading an encrypted key with `password=None` raises `TypeError`).

  Each test writes its files under `tmp_path` with neutral `.txt` names (e.g. `not-a-key.txt`, `ec-key.txt`, `missing-key.txt`, `encrypted-key.txt`), never `.pem`/`.key`.

  Run `.venv/bin/pytest tests/test_config.py` and confirm the new tests fail.
- [ ] `issue_bot/config.py` (Green): add `from pathlib import Path` to the stdlib import group (after `from dataclasses import dataclass, field`, before `from types import MappingProxyType`), and a new third-party group between the stdlib group and `from issue_bot.tags import IssueType` holding, alphabetized, `from cryptography.exceptions import UnsupportedAlgorithm`, then `from cryptography.hazmat.primitives import serialization`, then `from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey`. Add a private helper `_rsa_private_key(env, key) -> RSAPrivateKey`. It calls `path = _required(env, key)`, then `serialization.load_pem_private_key(Path(path).read_bytes(), password=None)`; on `(OSError, ValueError, TypeError, UnsupportedAlgorithm)` it raises `ConfigError(f"{key} must name a readable RSA private key") from None`, and raises the same error if the result is not an `RSAPrivateKey`. Add fields `github_app_id: int`, `github_installation_id: int` and `github_private_key: RSAPrivateKey = field(repr=False)` between `guild_id` and `target`. In `Config.from_env`, read `GITHUB_APP_ID` (`_positive_int`), `GITHUB_APP_INSTALLATION_ID` (`_positive_int`) and `GITHUB_APP_PRIVATE_KEY_PATH` (`_rsa_private_key`) after `DISCORD_GUILD_ID` and before `TargetConfig.from_env(env)`. Keep the docstring rule that every key is required.
- [ ] `tests/test_bot.py`: add the three keys to `CONFIG_KEYS` in read order. `test_main_config_error_hides_value` and `test_main_runs_bot_with_token` set every `test_env` key, so they need no change in this step.
- [ ] `example.env`: after the instance-wide Discord keys, add a `# GitHub App (instance-wide)` block with a one-line how-to comment above each key, in the file's existing comment style:
  - `GITHUB_APP_ID=0`, with the comment: App settings page → "App ID"; `0 is rejected`.
  - `GITHUB_APP_INSTALLATION_ID=0`, with the comment: org Settings → GitHub Apps → Configure; the number at the end of the URL.
  - `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem`, with the comment: a path, not the key; mount the downloaded `.pem` read-only.

  Extend the header line to "never commit a real token or key". Add no secret values.
- [ ] Verify: `.venv/bin/pytest -q` all green; `! grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot` exits 0 and prints nothing.

### 3. Issue title, body and labels builder (TDD)
Create `issue_bot/issues.py` with the single body builder. The `file_candidate` wrapper is added in step 4, once the client exists.

**To-do:**
- [ ] Create `tests/test_issues.py` (Red). Build candidates through `candidate_from_message(make_message(...), config)`, because tests never construct `IssueCandidate` directly. Add these tests:
  - `test_issue_title_is_message_title`.
  - `test_issue_title_truncated_to_256`: a title of `"x" * 300` gives length 256 ending in `…`, and `"x" * 256` stays unchanged (no spaces, because the `thread_name` shape rstrips before the `…`).
  - `test_issue_body_has_body_author_and_link`: for content `"!bug\nTitle: T\nBody: Steps here"` with author `"Alice"`, `issue_body` equals exactly ``"Steps here\n\n---\nReported by `Alice` in Discord: https://discord.com/channels/111/555/99"``.
  - `test_issue_body_neutralizes_mentions`: content `"!bug\nTitle: T\nBody: ping @someone"` with author `"@admin"` → the result contains neither `"@someone"` nor `"@admin"` as a literal substring, and contains `"@\u200bsomeone"` and `"@\u200badmin"`.
  - `test_issue_body_without_body_uses_placeholder`: the body starts with `"_No description given._\n\n---\n"`.
  - `test_issue_labels_follow_config`, parametrized `(content, expected)`: `("!bug\nTitle: T", ["bug"])` and `("!feature\nTitle: T", ["enhancement"])`, read from `test_env`'s `GITHUB_LABEL_*`.
  - `test_issue_labels_use_target_mapping`: a `test_env` with `GITHUB_LABEL_FEATURE="idea"` and content `"!feature\nTitle: T"` gives `["idea"]`.

  Run it and confirm the tests fail with an `ImportError`.
- [ ] Create `issue_bot/issues.py` (Green). Module docstring: "Turns a candidate into the GitHub issue's title, body and labels; the only place an issue body is formatted." Add `ISSUE_TITLE_LIMIT = 256  # GitHub's maximum issue-title length.` and `issue_title`, `_defang_mentions`, `issue_body` and `issue_labels` exactly as in **Design**. It imports `IssueCandidate` from `issue_bot.handler` only. Write U+200B only as the `\u200b` escape in source and tests, never as a literal character. New imports follow the convention of `config.py` and `bot.py`: stdlib, third-party and project groups separated by a blank line, plain `import x` lines before `from x import y` lines within a group, each alphabetized by module.
- [ ] Verify: `.venv/bin/pytest -q` all green.

### 4. GitHub client module (TDD)
Create `issue_bot/github.py` (App JWT, cached installation token, issue creation) behind an injected transport, guard tests against live calls, and add `file_candidate`.

**To-do:**
- [ ] Create `tests/test_github.py` (Red). Add helpers:
  - `make_client(github_private_key, transport, clock=lambda: 1_000_000.0) -> GitHubClient`, with app id 333 and installation id 444.
  - `token_response(expires_at="2026-10-18T13:00:00Z") -> tuple[int, dict]`, returning `(201, {"token": "ghs_secret_token", "expires_at": expires_at})`.
  - `issue_response() -> tuple[int, dict]`, returning `(201, {"number": 7, "html_url": "https://github.com/example-org/example-repo/issues/7"})`.

  The target comes from the `config` fixture (`config.target`: repo `example-org/example-repo`, id 222). Add these tests:
  - `test_create_issue_success`: `transport = AsyncMock(side_effect=[token_response(), issue_response()])`. The result is `FiledIssue(7, ".../issues/7")`. Call 1 is `("POST", "https://api.github.com/app/installations/444/access_tokens", headers, {"repository_ids": [222], "permissions": {"issues": "write"}})`, and its `Authorization` header is `Bearer <jwt>`. Call 2 is `("POST", "https://api.github.com/repos/example-org/example-repo/issues", headers, {"title": ..., "body": ..., "labels": ["bug"]})`, with `Authorization: Bearer ghs_secret_token`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28` and `User-Agent: discord-github-issue-bot`.
  - `test_app_jwt_claims`: decode with `jwt.decode(token, github_private_key.public_key(), algorithms=["RS256"], options={"verify_exp": False, "verify_iat": False})`; `iss == "333"`, `iat == now - 60`, `exp == now + 540`.
  - `test_token_reused_until_near_expiry`: with a clock at an epoch more than 300 s before `expires_at`, two `create_issue` calls make 3 transport calls (one token).
  - `test_token_refreshed_near_expiry`: move the clock to within 300 s of `expires_at` and the second call mints a new token (4 calls).
  - `test_token_request_401_raises`: `(401, {"message": "Secret error words"})` raises `GitHubError` with `stage == "token"`, `status == 401`, and `"Secret error words"` absent from `str(exc)`.
  - `test_issue_request_error_raises_without_text`, parametrized over status 403, 404, 410, 422, 500 and 502, each with the sentinel body `(status, {"message": "Validation Failed", "errors": [{"value": "Secret title words"}]})`: gives `stage == "issue"` and `exc.status == status`, and neither `"Secret title words"` nor `"ghs_secret_token"` is in `str(exc)` or `repr(exc)`.
  - `test_issue_request_401_drops_cached_token`: after a 401 on the issue POST, the next `create_issue` mints a new token.
  - `test_issue_request_404_keeps_cached_token`: after a 404 on the issue POST, the next `create_issue` makes no new token call (its only transport call is the issue POST).
  - `test_bad_token_shape_raises`, parametrized over `(201, None)`, `(201, {"expires_at": "2026-10-18T13:00:00Z"})`, `(201, {"token": 5, "expires_at": "2026-10-18T13:00:00Z"})`, `(201, {"token": "t", "expires_at": "not-a-date"})` and `(201, {"token": "t", "expires_at": "2026-10-18T13:00:00"})` (naive): each raises `GitHubError` with `stage == "token"`, `status == 201`, `exc.__cause__ is None` and `exc.__suppress_context__ is True`.
  - `test_transport_error_raises_status_none`, parametrized over `aiohttp.ClientConnectionError("Secret error words")` and `TimeoutError()`: covers both stages: `AsyncMock(side_effect=error)` (token stage, `exc.stage == "token"`) and `AsyncMock(side_effect=[token_response(), error])` (issue stage, `exc.stage == "issue"`). Each gives `GitHubError` with `status is None`, `exc.__cause__ is None`, `exc.__suppress_context__` is True, and `"Secret error words"` not in `str(exc)`.
  - `test_bad_success_shape_raises`, parametrized over the issue response `(201, {"number": "x", "html_url": "u"})`, `(201, None)`, `(201, {"number": True, "html_url": "u"})` and `(201, {"number": 7})` (each after a good `token_response()`): raises `GitHubError` with `stage == "issue"` and `status == 201`.
  - `test_client_repr_hides_secrets`: after a successful call, `repr(client)` contains neither `"ghs_secret_token"` nor any PEM text.

  `aiohttp_transport` itself gets no unit test: it is covered only by the owner's live smoke test (**Manual checks**), by owner decision 2026-10-18 (DD-2).

  Run it and confirm the tests fail.
- [ ] Create `issue_bot/github.py` (Green) exactly per **Design**. Its module docstring states the policy: never logs; errors carry stage and HTTP status only, never GitHub's response text or tokens. Imports, in three blank-line-separated groups: stdlib `import time`, `from collections.abc import Awaitable, Callable, Mapping`, `from dataclasses import dataclass`, `from datetime import datetime`, `from typing import Any`; third-party `import aiohttp`, `import jwt`, `from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey`; project `from issue_bot.config import TargetConfig`. Don't import `issue_bot.bot`; keep the dependency graph acyclic. In `GitHubClient`, wrap the two transport calls in a private `_request(stage, url, headers, payload) -> tuple[int, Any]` that calls `await self._transport("POST", url, headers, payload)` with all four arguments positional (both calls are POST; the tests assert `call_args.args`) and converts `(aiohttp.ClientError, TimeoutError)` into `raise GitHubError(stage, None) from None`.
- [ ] `tests/conftest.py` (now that `issue_bot.github` exists): add an `autouse=True` fixture `no_live_github(monkeypatch)`. It sets `issue_bot.github.aiohttp_transport` to `AsyncMock(side_effect=AssertionError("live GitHub call in a test"))` using `monkeypatch.setattr("issue_bot.github.aiohttp_transport", ...)`. Any client built without an explicit transport then fails loudly instead of reaching api.github.com (CLAUDE.md rule). Then add `test_default_transport_is_guarded` to `tests/test_github.py`: a client built without `transport=` raises `AssertionError` on `create_issue`.
- [ ] Add `async def file_candidate(github: GitHubClient, candidate: IssueCandidate) -> FiledIssue` to `issue_bot/issues.py` (import `FiledIssue` and `GitHubClient` from `issue_bot.github`; new imports follow the same three-group, alphabetized convention as `config.py` and `bot.py`, so this line goes before `from issue_bot.handler import IssueCandidate`). Add `test_file_candidate_passes_title_body_labels` to `tests/test_issues.py`: a fake with `create_issue = AsyncMock(return_value=FiledIssue(7, "u"))` is awaited once with `(candidate.target, issue_title(c), issue_body(c), ["bug"])`, and the `FiledIssue` is returned.
- [ ] Verify: `.venv/bin/pytest -q` all green.

### 5. Filing hook, error reply and entry-point wiring (TDD)
Wire filing into the `on_candidate` seam, post the fixed error reply on failure, and build the client in `__main__`.

**To-do:**
- [ ] `tests/test_threads.py` (Red, then Green in `issue_bot/threads.py`): add `test_filing_error_reply_is_fixed_text`, asserting `FILING_ERROR_REPLY == "Sorry, I couldn't file this as a GitHub issue. Check the repo before reposting; to retry, post a new message (edits are ignored)."`. Then add the constant to `threads.py` after `THREAD_ALREADY_CREATED`, with the module's other constants, with a one-line comment that it carries no member or GitHub text.
- [ ] `tests/test_bot.py` (Red): add a helper `fake_github(result: FiledIssue | Exception) -> SimpleNamespace` whose `create_issue` is an `AsyncMock` returning the result or raising it as `side_effect`. Construct `IssueBot(config, on_candidate=filing_hook(github))` and add these tests:
  - `test_filing_hook_files_issue_and_logs_url`: content `"!bug\nTitle: Secret title words\nBody: Secret body words"`. The thread is created once (named from the title), `create_issue` is awaited once with `config.target` and labels `["bug"]`, `create_thread.return_value.send` is **not** awaited, and one INFO `issue_bot.bot` line contains `"filed bug"`, `"message_id=99"`, `message.jump_url`, `"thread_id=1234"` and the html_url. No record text contains the title or body sentinels or `"Alice"`.
  - `test_filing_hook_failure_replies_and_logs_status`: with `GitHubError("issue", 422)`, the thread's `send` is awaited once with `FILING_ERROR_REPLY`, and one ERROR line contains `"could not file bug"`, `"message_id=99"`, `"thread_id=1234"`, `"GitHubError"`, `"stage=issue"` and `"status=422"`. No sentinel text appears.
  - `test_filing_hook_files_even_without_thread`: `create_thread.side_effect = forbidden(50013, "x")` → `create_issue` is still awaited, and the INFO line has `"thread_id=None"`.
  - `test_filing_hook_failure_without_thread_logs_only`: thread fails and filing fails → the ERROR line has `thread_id=None` and nothing is sent.
  - `test_filing_error_send_failure_logged_without_text`: with `fake_github(GitHubError("issue", 422))`, `message.create_thread.return_value.send.side_effect = forbidden(50001, "Secret error words")` → an ERROR line `"could not send filing error"` with `Forbidden`, `403` and `50001`, and `"Secret error words"` appears in no record text.
  - `test_filing_hook_unexpected_error_reaches_on_error`: `create_issue` raises `RuntimeError("Secret exception words")` through `bot._run_event(bot.on_message, "on_message", message)` → `on_error` logs `unhandled RuntimeError in on_message message_id=99` only. This confirms that only `GitHubError` is caught.

  Leave the five existing `test_default_hook_*` tests unchanged: they cover the class default `open_issue_thread`, which stays.
- [ ] `issue_bot/bot.py` (Green): import `GitHubClient`, `GitHubError` from `issue_bot.github`, `file_candidate` from `issue_bot.issues`, and `FILING_ERROR_REPLY` from `issue_bot.threads`. New imports follow the same three-group, alphabetized convention as `config.py` and `bot.py`: project modules in alphabetical order, and the names within a line ordered constants, then classes, then functions, as in the existing `from issue_bot.handler import IssueCandidate, candidate_from_message` (so `from issue_bot.threads import FILING_ERROR_REPLY, format_hint, open_thread, thread_name`). Add `def filing_hook(github: GitHubClient) -> CandidateHook` per **Design**. Its docstring says it opens the thread, files the issue, replies with the fixed error on `GitHubError`, and never logs member text or GitHub response text. Update the `IssueBot` class docstring to say production wires `filing_hook` in `__main__`.
- [ ] `tests/test_bot.py` `test_main_runs_bot_with_token`: change `StubBot.__init__` to `(self, config: Config, **kwargs: object)`, record `kwargs`, and assert `callable(calls["init_kwargs"]["on_candidate"])` alongside the existing assertions. Add `test_main_builds_github_client(monkeypatch, test_env)`: set every `test_env` key with `monkeypatch.setenv`, replace `entry_point.IssueBot` with the same kwargs-accepting `StubBot` shape (`__init__(self, config, **kwargs)`, a no-op `run`) so no real Discord client starts, and replace `entry_point.GitHubClient` with a recorder that stores its positional args and returns a sentinel object. Call `entry_point.main()`; assert the recorded args are `(333, 444, <an RSAPrivateKey>)` (check the third with `isinstance(..., rsa.RSAPrivateKey)`).
- [ ] `issue_bot/__main__.py`: import `GitHubClient` from `issue_bot.github` and `filing_hook` from `issue_bot.bot` (same alphabetized project-group convention: `from issue_bot.bot import IssueBot, filing_hook` first, `from issue_bot.github import GitHubClient` last); build the client and pass `on_candidate=filing_hook(github)` per **Design**.
- [ ] Verify: `.venv/bin/pytest -q` all green; Standing invariant 1: `! grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot` exits 0 and prints nothing; `grep -rln --include='*.py' "aiohttp_transport" tests` lists no file other than `tests/conftest.py` and `tests/test_github.py`.

### 6. Documentation
Document GitHub App setup, the new keys, the key mount and the logging rule.

**To-do:**
- [ ] `README.md`:
  - Update the Status section: tagged messages are now filed as issues in the target repo; a failure posts an error reply in the thread; the link post comes with F7.
  - Add `GITHUB_APP_ID` (instance, positive integer), `GITHUB_APP_INSTALLATION_ID` (instance, positive integer) and `GITHUB_APP_PRIVATE_KEY_PATH` (instance, path to the App's PEM private key, secret file) rows to the `### Configuration` table (under `## Getting started`).
  - In `### Configuration`, extend the sentence "Then set the bot token and the intake channel's ID in `.env`" to also name the three `GITHUB_APP_*` values.
  - In `### Run locally`, add one sentence: for a local run, `GITHUB_APP_PRIVATE_KEY_PATH` must be the key's host path (outside the repo), since `example.env`'s `/run/secrets/...` path exists only inside the container through the Docker mount.
  - Add a `### GitHub App setup` section with a numbered list, after `### Discord setup`:
    1. Create an App under the 4IRL org. Webhook off. Repository permission Issues: Read and write, plus Metadata: Read.
    2. Install it on the target repo(s) only.
    3. Note the App ID and the installation ID (from the installation URL).
    4. Generate a private key and keep the `.pem` outside the repo.
  - In `### Run with Docker`, add to the `docker run` line `-v /path/to/key.pem:/run/secrets/github-app-key.pem:ro`. The container runs as uid 10001, so the host file must be readable by that uid (for example `chmod 0444` on a file in a private directory, or `chown 10001`).
  - In `## Tests`, say tests mock GitHub through an injected transport and a conftest guard fails any live call.
  - Below the `### Configuration` table, note that each `GITHUB_LABEL_*` label must already exist in the target repo: a label an App requests that doesn't exist may be dropped or auto-created depending on its permissions _(unverified)_. The scratch-repo smoke test in **Manual checks** confirms the label was applied.
  - At the end of `### GitHub App setup`, note that issues filed to a public target repo are public, including the author's Discord display name, and that @mentions in the body and the author name are neutralized (a zero-width space after each `@`), so filing notifies no GitHub user.
  - Add a `### Known limits` subsection at the end of `## Status`: no retry or dedup until Phase 4, so a timeout can leave an issue filed after an error reply; messages sent while the bot is down are not filed; edits are ignored.
- [ ] `CLAUDE.md`: in the logging rule, add after the Discord-error clause: "a GitHub API error is logged by exception type, request stage and HTTP status, never its response text; tokens, JWTs and the App private key are never logged." In the same rule, change "Log the issue type, ids (message, thread) and message URL only" to "Log the issue type, ids (message, thread), the message URL and the filed issue's URL only". In the credentials rule, change "The Discord bot token and GitHub credentials live only in `.env` / the container environment" to "The Discord bot token and GitHub App ids live only in `.env` / the container environment, and the App private key in a file outside the repo: a host path for a local run, a read-only mounted file in the container (its path is the `GITHUB_APP_PRIVATE_KEY_PATH` env value)". In **Stack**, say the HTTP client is aiohttp with PyJWT for App auth. Keep the edit minimal. META-PLAN Standing invariant 2's "message URL only" wording is updated at the META-PLAN fold-back, not by this plan.
- [ ] Verify: `grep -n "GITHUB_APP_" README.md example.env` shows all three keys in both files; `grep -n "request stage and HTTP status" CLAUDE.md` and `grep -n "GITHUB_APP_PRIVATE_KEY_PATH" CLAUDE.md` each print the edited line; `grep -n "### GitHub App setup" README.md` and `grep -n "/run/secrets/github-app-key.pem:ro" README.md` each print a line; `.venv/bin/pytest -q` green.

### 7. Verify All Tests Pass
Run the full test suite to confirm nothing is broken.

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm all tests pass.
- [ ] UI runner: none configured for this project (`ui_runner_cmd` is empty); nothing to run.
- [ ] Run Standing invariant 1: `! grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot` exits 0 and prints nothing; also `! grep -rni "4irl" --include='*.py' issue_bot` exits 0 and prints nothing.
- [ ] Copy the **Manual checks** section below verbatim into your final report.
- [ ] Investigate and fix any failures before marking the plan finished. If every check above passed, tick this box with "(none to fix)".

## Manual checks (owner only, never automated)
- Create and install the GitHub App per the README's new section; put the three `GITHUB_APP_*` values in `.env` and mount the key.
- Token probe (owner runs it locally, never an agent; DD-3), after the smoke test's **Setup** below has created the scratch repo and added it to the installation. `<REPO_ID>` is the scratch repo's id (`gh api repos/4IRL/<scratch> --jq .id`): mint one installation token with the exact **Design** body and check the response. From the repo root, after Step 4 has landed:
  ```
  JWT=$(.venv/bin/python -c 'import sys, time; from cryptography.hazmat.primitives import serialization; from issue_bot.github import app_jwt; k = serialization.load_pem_private_key(open(sys.argv[2], "rb").read(), None); print(app_jwt(int(sys.argv[1]), k, time.time()))' <APP_ID> <KEY_PATH>)
  curl -s -X POST -D /dev/stderr -H "Authorization: Bearer $JWT" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" https://api.github.com/app/installations/<INSTALLATION_ID>/access_tokens -d '{"repository_ids": [<REPO_ID>], "permissions": {"issues": "write"}}' | python3 -c 'import json, sys; d = json.load(sys.stdin); d.pop("token", None); print(json.dumps(d, indent=1))'
  ```
  The headers go to stderr and the filter drops `token` from the body, so the token is never shown; if a token is ever printed, never paste it anywhere (it expires within an hour). Confirm the status line is 201, `expires_at` ends in `Z`, `repositories` lists only the scratch repo, and `permissions` holds `issues: write` and nothing broader (a `metadata: read` entry may also appear). If any of these differs from **Design**, file a fix before going live. Live write: the probe mints one installation token on GitHub (it expires in an hour); it creates nothing else.
- A live smoke test needs the owner's explicit go-ahead each time (CLAUDE.md rule) and runs against a scratch repo (DD-4):
  - Setup: create a **private** scratch repo in the 4IRL org and add it to the App's existing org installation's selected repositories (org Settings → GitHub Apps → Configure). Keep `GITHUB_APP_INSTALLATION_ID` unchanged: an installation ID is per account, so the org installation covers the scratch repo. Confirm the `bug` and `enhancement` labels exist there (`gh api repos/4IRL/<scratch>/labels/bug --jq .name`, likewise `enhancement`), creating any that are missing. In `.env`, point `GITHUB_REPO` / `GITHUB_REPO_ID` at the scratch repo and `DISCORD_CHANNEL_ID` / `DISCORD_CHANNEL_NAME` / `DISCORD_CATEGORY` at a test channel.
  - Live writes it performs: the label check posts one `!bug` and one `!feature` message, which file two issues in the scratch repo (each with the title from `Title:`, body = the Body text plus the footer with the author's display name and the message link, and the type's label) and open two public threads in the test channel. The 300-character-title check files one more issue and opens one more thread. The failure-path run writes one public thread and one bot reply (`FILING_ERROR_REPLY`) in the test channel and nothing on GitHub. Re-running any check repeats its writes.
  - Post one `!bug` and one `!feature` message. Check that each issue has the right title, body footer (author and message link) and the App's `[bot]` author, that the `!bug` issue carries the `bug` label and the `!feature` issue the `enhancement` label (confirms the labels were applied; DD-9, DD-14), and that nothing is posted in either thread on success. Also post a tagged message with a 300-character title once and confirm the filed title is 256 characters ending in `…` (confirms ISSUE_TITLE_LIMIT). Record in the PR description the scratch repo name, each filed issue number and what each check showed (title, footer, label, `[bot]` author, the 256-character title), plus the teardown date; the scratch repo is deleted afterwards, so its URLs stop resolving.
  - Failure path, only via a wrong `GITHUB_APP_INSTALLATION_ID` in `.env`: post one tagged message, confirm the thread gets the fixed error reply and the log shows an ERROR line with `stage=token status=…` and no message text, then restore the right value. Restart the bot after each `.env` change; configuration is read only at startup.
  - Container run: stop the local bot first: two processes on one bot token both file every tagged message. Build the image (`docker build -t discord-github-issue-bot .`) and run the scratch-repo smoke test once through the README's Docker form (`docker run --rm --env-file .env -v <host key path>:/run/secrets/github-app-key.pem:ro discord-github-issue-bot`, with `.env`'s `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem`). This also exercises the README's uid-10001 readability note: a startup log line `configuration error: GITHUB_APP_PRIVATE_KEY_PATH must name a readable RSA private key` (exit status 2) means the container user cannot read the mounted key, or the mount's host path is wrong.
  - Afterwards: remove the scratch repo from the installation's repository selection (org Settings → GitHub Apps → Configure), then delete the scratch repo, and restore `.env` (target repo, intake channel and key path) to its values from before the test. Delete the smoke-test threads in the test channel, or leave them if the channel is private to the owner.

## Status
finished: false
