# Channel Listener and Tag Parsing (F1)

## Summary
Stand up the bot's code skeleton and its first behavior: a discord.py client that connects
to the Gateway, listens only to the configured intake channel, and turns a new message
carrying `#bug` or `#feature` into an `IssueCandidate` (type, title, raw content, author,
message link, target). Untagged, bot, webhook, system, edited, in-thread and other-channel messages
are ignored. The code is portable: the package has the generic name `issue_bot`, every
identifier comes from the environment, per-target values sit in one `TargetConfig` object
separate from instance-wide values, and no 4irl/chores4irl literal is a code default (no
`*.py` outside tests holds one; the config home for the 4irl values is the committed
`example.env`).
F1 also adds the test harness (META-PLAN Verification: `.venv/bin/pytest`), the Docker image
and the README/CLAUDE.md run and test docs. Later features (F2 thread, F5 filing) consume
candidates through a single `on_candidate(message, candidate)` hook.

## Research Findings
- Research was done inline: the repo holds only scaffold files (`CLAUDE.md`, `README.md`,
  `.gitignore`, `.claudeignore`, `.claude/settings.json`, `plans/`), no `*.py` and no
  `Dockerfile`. Host Python is 3.12.11.
- `.claude/settings.json` already has the project sandbox block (Discord, GitHub, PyPI
  domains; `allowUnsandboxedCommands: true` for Docker), so no sandbox step is needed.
- `.gitignore` covers `.venv/`, `__pycache__/`, `.pytest_cache/`, `data/`, `.env` and
  `.env.*`; `.claudeignore` lists `.env` and `.env.*`; the global `~/.claude/settings.json`
  denies `Read(**/.env*)` and the sandbox read-denies `**/.env*`. The example file is named
  `example.env`, which matches none of those rules, so agents read, stage and diff it
  normally while `.env` stays ignored and unread (checked at the portability-revision DD
  pass in the repo: `git check-ignore -q example.env; echo $?` → `1`,
  `git check-ignore -q .env; echo $?` → `0`).
- Latest stable on PyPI (2026-10-17): `discord.py==2.7.1`, `pytest==9.1.1`,
  `pytest-asyncio==1.4.0`. Verified at the pass-1 review in a scratch venv: `discord.Client`
  constructs without a running loop; on first construction in a process it logs two
  WARNINGs from logger `discord.client` (PyNaCl / davey not installed: voice unsupported),
  which are expected and harmless.
- Owner decisions (planning and pass-1 review, 2026-10-17; portability revision same day):
  channel matched by **ID from config**, name/category/guild checked only at startup
  (warning log); **first recognized tag wins**, every recognized tag is stripped from the
  title; **edited messages are ignored**; the hook receives **the message and the
  candidate**; **logs carry ids and URLs only**; the parser reads `message.content` (F5
  cleans mention markup). Portability revision: package **`issue_bot`**; **all config from
  env, every key required, no code defaults**; the 4irl example values go in a committed
  **`example.env`**, never a TOML file. Decision note (portability-revision review, DD-1):
  the owner chose `example.env` over `.env.example` because the sandbox and the global read
  deny mask `**/.env*`, so agents could write a `.env.example` but never read it back; the
  rejected route needed `!.env.example` un-ignore lines plus a global settings change.
  Open risk (d): the privileged Message Content intent must be enabled in the Developer
  Portal; the README documents it.

## Prerequisites
Host tools for `/run-plan` Phase 0: `python3` (3.12; `python3 --version` → 3.12.11), `git`,
and `docker` with Docker Desktop running and WSL integration on for this distro
(`docker info` needs the sandbox disabled). `.venv/bin/pytest` and `.venv/bin/pip` are **not**
host prerequisites: Step 1 creates them, and every test command in this plan uses those
venv paths, never a bare host pytest. `/run-plan` Phase 0 runs `docker info` before any
step and halts the whole run if it fails, so start Docker first (or run Steps 1–5 one at a
time with `/next-step-taker`). Step 6's UNRESOLVED marker covers Docker failing after Phase 0
passed. To the `/run-plan` orchestrator: `ui_runner_cmd` is intentionally blank (no UI suite
exists); at `/run-plan` Step 3 (Completion), skip the UI test subagent and treat the UI suite
as N/A; the integration runner (`.venv/bin/pytest`) is the only suite.
Not Phase 0 tools: `set`, `export` and `.` in the `.env` shell-form spans are bash builtins
(`set --version` exits 2, so skip it); `awk`, `diff`, `grep`, `ls` and `cp` are host
utilities already present (`awk --version` → GNU Awk 5.2.1, `diff --version` → GNU
diffutils 3.10). Also skip: bare `pytest` (not on the host PATH; every run uses
`.venv/bin/pytest`); Python source spans such as `import issue_bot`, `from`, `class`, `raise`,
`async`, `await`, `try`, `except`, `if`, `assert`, `sys` and `hasattr` (code inside the package and tests, not shell
commands); the Dockerfile directives `FROM`, `ENV`, `WORKDIR`, `COPY`, `RUN`, `USER`,
`STOPSIGNAL` and `CMD`, which run inside `docker build`; the image name
`python:3.12.11-slim` (a Docker tag, not a command); and identifier or prose spans such as
`run`, `start`, `login`, `use`, `type` and `discord` (method, logger and field names).

## Design

Package `issue_bot/` at the repo root; tests in `tests/`.

| Module | Owns |
|---|---|
| `tags.py` | `IssueType` (`StrEnum`: `BUG = "bug"`, `FEATURE = "feature"`), `ParsedTag` (frozen dataclass: `type: IssueType`, `title: str`), `parse_tag(text: str) -> ParsedTag | None` |
| `config.py` | `ConfigError`, `TargetConfig` and `Config` (frozen dataclasses), each with `from_env(env: Mapping[str, str])` |
| `handler.py` | `IssueCandidate` (frozen dataclass), `candidate_from_message(message, config) -> IssueCandidate | None` |
| `bot.py` | `build_intents()`, `channel_problems(channel, config) -> list[str]`, `CandidateHook`, `log_candidate` (default hook), `IssueBot(discord.Client)` |
| `__main__.py` | `main()`: logging setup, `Config.from_env(os.environ)`, `IssueBot(...).run(token)` |

Environment keys (names only here; every key is required and has **no default in code**;
`example.env` carries the 4irl example values):

| Key | Scope | Type | Meaning |
|---|---|---|---|
| `DISCORD_TOKEN` | instance | str (secret) | Bot token |
| `DISCORD_GUILD_ID` | instance | positive int | Server the bot serves |
| `DISCORD_CHANNEL_ID` | target | positive int | Intake channel (matched by ID) |
| `DISCORD_CHANNEL_NAME` | target | str | Expected channel name (startup sanity check only) |
| `DISCORD_CATEGORY` | target | str | Expected category name (startup sanity check only) |
| `GITHUB_REPO` | target | `owner/name` | Output repo |
| `GITHUB_REPO_ID` | target | positive int | Output repo id |
| `GITHUB_LABEL_BUG` | target | str | Label for `#bug` |
| `GITHUB_LABEL_FEATURE` | target | str | Label for `#feature` |

Label keys are derived, not listed: `f"GITHUB_LABEL_{issue_type.name}"` for each `IssueType`,
so adding a tag type adds exactly one required key.

`TargetConfig` fields: `channel_id: int`, `channel_name: str`, `category: str`,
`github_repo: str`, `github_repo_id: int`, `labels: Mapping[IssueType, str]` (a
`types.MappingProxyType`, read-only). `Config` fields: `discord_token: str` (with
`field(repr=False)` so it never appears in logs), `guild_id: int`, `target: TargetConfig`.
F8 later turns `target` into a list of routes (and updates `candidate_from_message` and
`channel_problems`, which read `config.target`); F5 and F8 add their own required keys. Neither
`TargetConfig` nor `Config` is hashable (`labels` is a mapping, so the generated `__hash__`
raises `TypeError`): F8 keys routes by `channel_id`, never by the `TargetConfig` object.
`IssueCandidate` is not hashable either (it carries `target`); key per-message state by `message_id`.

Resolution order in `Config.from_env`: `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, then
`TargetConfig.from_env(env)` (keys in the table's order, labels last in `IssueType` order). So
an empty environment reports `DISCORD_TOKEN is required` (Step 6's Docker gate relies on it).
Validation messages: absent or blank (after `.strip()`) → `"<KEY> is required"`; not an
integer → `"<KEY> must be an integer"`; integer ≤ 0 → `"<KEY> must be a positive integer"`
(so the `example.env` channel placeholder `0` fails loudly); `GITHUB_REPO` not matching
`REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")` with `fullmatch` →
`"GITHUB_REPO must be owner/name"`.

`example.env` exact content (written in Step 6; plain `KEY=value` lines, no quotes, no
`export`; `docker run --env-file` takes each value literally, while the shell form
`set -a; . ./.env; set +a` reads the same values only when no value contains spaces or
quotes, so a value with spaces needs the Docker `--env-file` run or that key exported by
hand with quotes):

```
# Copy to .env and fill in. .env is gitignored; never commit a real token.
# Instance-wide
DISCORD_TOKEN=
DISCORD_GUILD_ID=1137236302358659185
# Target: intake channel -> output repo
# Channel ID: Discord Developer Mode, right-click #c4i-github-issues, Copy Channel ID. 0 is rejected.
DISCORD_CHANNEL_ID=0
DISCORD_CHANNEL_NAME=c4i-github-issues
DISCORD_CATEGORY=C4I
GITHUB_REPO=4IRL/chores4irl
GITHUB_REPO_ID=969373970
GITHUB_LABEL_BUG=bug
GITHUB_LABEL_FEATURE=enhancement
```

`IssueCandidate` fields: `type: IssueType`, `title: str`, `content: str` (raw
`message.content`, unmodified: F5 puts it in the issue body), `author_id: int`,
`author_name: str` (`message.author.display_name`), `message_id: int`, `message_url: str`
(`message.jump_url`), `target: TargetConfig` (the route the message arrived on; F1 sets it to
`config.target`). `title`, `content` and `author_name` are declared `field(repr=False)`, so
`repr(candidate)` (and any log or traceback that formats it) carries no member text or name.

Hook contract: `CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]`.
`IssueBot.on_message` awaits `self.on_candidate(message, candidate)`, so F2 can call
`message.create_thread(...)` and check `message.thread` directly, and F5 reads the output
repo and labels from `candidate.target`; when F8 turns `Config.target` into routes, the hook
signature stays the same because each candidate already carries its own target.

Tag grammar (verified at pass-1 review and re-verified at the portability-revision DD pass
against every test input in Step 2):
- ``TAG_PATTERN = re.compile(r"(?<![\w#/`])#(bug|feature)(?![\w`-])", re.IGNORECASE)``. So
  `#BUG` and `#Feature` match, as does a tag in a quoted line (`> #bug quoted`); `#bugfix`,
  `#bug-report`, `foo#bug`, `##bug`, URL fragments (`x.com/#bug`) and a tag touching a
  backtick (``use `#bug` here``) do not; a tag elsewhere inside a code span or fenced block
  still matches. The first match decides the type.
- Title: remove every match, then remove empty bracket pairs
  (`EMPTY_BRACKETS = re.compile(r"\(\s*\)|\[\s*\]|\{\s*\}")`), collapse whitespace runs to one
  space, then strip the edge characters `TITLE_EDGE = " .,:;-|/"` from both ends.
- A title with no letter or digit (`not any(ch.isalnum() for ch in title)`) returns `None`
  (tag-only messages such as `#bug`, `#bug.`, `#feature !`).

Messages in threads under the channel are **not** captured: a thread message's
`message.channel.id` is the thread's id, so the channel-ID filter drops it. F3's in-thread
answers containing `#bug` therefore never spawn new candidates.

Logging rule: log records never contain message text, titles or member names; log the
issue type, `message_id` and `message_url` only. Rejected config values and the token are
never logged (the startup check's WARNINGs name the expected non-secret ids and names on
purpose): a `ConfigError` names only the key, `_positive_int` raises it `from None` (so the
rejected value's `ValueError` is not chained into a traceback), and `main()` logs it without
`exc_info`. An exception escaping an event handler or the candidate hook is logged by its
type and event name only (`IssueBot.on_error`: no traceback, no message, no event
arguments). Never run the `discord` loggers at DEBUG:
discord.py logs full gateway payloads (message text, member names) at that level. Step 6 adds
this as a CLAUDE.md project rule.

Portability gate (META-PLAN F1 Expected end state), used in Steps 6 and 7:
`grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues|\bC4I\b|4[Ii][Rr][Ll]' --include='*.py' --include='Dockerfile' --include='pyproject.toml' --exclude-dir=.venv --exclude-dir=tests .`
prints nothing (exit 1), and `grep -rn 'DEFAULT_' issue_bot/` prints nothing. The first grep
also covers the `Dockerfile` (Step 6: no `ENV` line sets any config key) and
`pyproject.toml`.

## Contract for later features
What F2, F5 and F8 may rely on once F1 merges (Step 7 copies this section into the final
report):
- Modules: `issue_bot.tags` (`IssueType` `StrEnum` with `BUG = "bug"`, `FEATURE = "feature"`;
  `parse_tag`), `issue_bot.config` (`Config`, `TargetConfig`, `ConfigError`),
  `issue_bot.handler` (`IssueCandidate`, `candidate_from_message`), `issue_bot.bot`
  (`IssueBot`, `CandidateHook`, `log_candidate`); the entry point is `issue_bot/__main__.py`'s
  `main()`, run as a module.
- Hook: `CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]`, passed
  as `IssueBot(config, on_candidate=...)` and awaited once per new tagged message in the
  intake channel (default `log_candidate`, which logs ids and URLs only). An exception
  escaping the hook or any event handler is logged by `IssueBot.on_error` by type and event
  name only (no traceback, message or arguments); a hook that needs more detail logs it
  itself under the logging rule.
- `IssueCandidate` (frozen dataclass), eight fields: `type: IssueType`, `title: str`,
  `content: str`, `author_id: int`, `author_name: str`, `message_id: int`,
  `message_url: str`, `target: TargetConfig`. `title`, `content` and `author_name` are
  `field(repr=False)`. Not hashable (it carries `target`): key sets/dicts by `message_id`.
- `TargetConfig` (frozen): `channel_id`, `channel_name`, `category`, `github_repo`,
  `github_repo_id`, `labels: Mapping[IssueType, str]` (read-only `MappingProxyType`, one
  entry per `IssueType`). `Config` (frozen): `discord_token` (repr-hidden), `guild_id`,
  `target: TargetConfig` (F8 turns it into routes). Neither is hashable; key routes by
  `channel_id`.
- Environment: the nine keys in the Design table, every one required, no code defaults; a
  new `IssueType` adds one required `GITHUB_LABEL_<NAME>` key.
- `title` and `content` keep raw Discord mention markup (`<@id>`, `<#id>`, `<@&id>`): F2's
  thread name and F5's issue title and body must clean them.

## Steps

Commits: each step's commit stages explicit paths (the files the step created or changed plus
`plans/feature/channel-listener/channel-listener.md`); `git add .` fails in this sandbox on
placeholder device files. Step 1's commit is the first to include the (until then untracked)
plan file and its `reviews/` directory. `.claude/skill-config.md` is gitignored and never
staged. Never read `.env` (`example.env` is an ordinary committed file). Per-step review:
`git diff --name-only` omits new files, so give the review and fix subagents the step's new
files by name as well (the `??` paths from `git status --porcelain --untracked-files=all`
that this step created, excluding sandbox placeholder dotfiles). Never pass a `.env*` file.

### 1. Project skeleton, test harness and test-command registration
Create the package, dependency pins, pytest config and the repo-root venv so `.venv/bin/pytest`
runs, and register that command where the executing skills look for it.

**To-do:**
- [x] Create `requirements.txt` with `discord.py==2.7.1`, then create the venv:
  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. Run
  `.venv/bin/pip freeze` and add every transitive dependency it lists (aiohttp, yarl,
  multidict, frozenlist, aiosignal, attrs, propcache, idna, aiohappyeyeballs,
  typing_extensions, and whatever else appears) to `requirements.txt` at its installed
  version with `==`, one per line: `discord.py` first, then the rest sorted alphabetically.
- [x] Create `requirements-dev.txt` starting with `-r requirements.txt`, then
  `pytest==9.1.1` and `pytest-asyncio==1.4.0`. Install it
  (`.venv/bin/pip install -r requirements-dev.txt`), then pin each new transitive dependency
  (`iniconfig`, `packaging`, `pluggy`, `pygments`, … whatever `pip freeze` adds beyond
  `requirements.txt`) into `requirements-dev.txt` with `==`.
- [x] Create `pyproject.toml` with only tool config (no build backend):
  `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `pythonpath = ["."]`,
  `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"`.
- [x] Create `issue_bot/__init__.py` (one-line generic module docstring, e.g.
  `"""Discord intake channel to GitHub issue bot."""`, naming no server or repo) and
  `tests/__init__.py` (empty).
- [x] Create `tests/test_smoke.py` with `test_package_imports()` asserting
  `import issue_bot` succeeds. Run `.venv/bin/pytest` and confirm 1 passed.
- [x] Register the test command. In `CLAUDE.md` § Commands, replace the line
  `- Test: _not set up yet_` with
  `- Test: \`.venv/bin/pytest\` (repo-root venv; install with \`.venv/bin/pip install -r requirements-dev.txt\`)`,
  and replace the two-line `<!-- Fill in once code exists … -->` comment with the one-line
  `<!-- Keep these in sync with .claude/skill-config.md's test fields. -->`. In the
  gitignored `.claude/skill-config.md` § Tests, set `- test_run_cmd: .venv/bin/pytest` (the
  command `/next-step-taker` runs as `$TEST_RUN_CMD`; there are no markers, so it runs the
  whole suite) and `- integration_runner_cmd: .venv/bin/pytest` (leave `ui_runner_cmd`
  blank: no UI suite). Do not stage `.claude/skill-config.md`.

Done 2026-10-17: `.venv/bin/pytest` → 1 passed. Sandbox note: the sandbox read-denies `**/*.pem`, which blocks pip's vendored `certifi/cacert.pem` in an existing venv. So `.venv` was built with `--without-pip`, and the packages were installed through a throwaway helper venv (`<helper>/bin/pip --python .venv/bin/python install -r requirements-dev.txt`). To get `.venv/bin/pip`, run `.venv/bin/python -m ensurepip --upgrade` outside the sandbox.

**Verify:** `.venv/bin/pytest` → 1 passed; `grep -n 'Test: `.venv/bin/pytest`' CLAUDE.md`
prints the Commands line; `grep -n 'test_run_cmd: .venv/bin/pytest' .claude/skill-config.md`
and `grep -n 'integration_runner_cmd: .venv/bin/pytest' .claude/skill-config.md` each print
one line.

### 2. Tag parser (TDD)
A pure function recognizing `#bug` / `#feature` per the Design's tag grammar. It comes before
config because `TargetConfig.labels` is keyed by `IssueType`.

**To-do:**
- [x] Red: create `tests/test_tags.py`:
  - `test_roadmap_feature_example`: `"Display chore count next to Room tab name in parentheses when each Room tab is active #feature"`
    → `ParsedTag(IssueType.FEATURE, "Display chore count next to Room tab name in parentheses when each Room tab is active")`.
  - `test_roadmap_untagged_example`: `"anyone around tonight?"` → `None`.
  - `test_roadmap_bug_example`: `"Chore bars turn red on the due date instead of after it #bug"`
    → `BUG`, title without the tag.
  - `test_case_insensitive`: `#BUG`, `#Feature` recognized.
  - `test_tag_anywhere`: `"#bug login button broken"` and `"login #bug button broken"` →
    title `"login button broken"` (whitespace collapsed).
  - `test_first_tag_wins_and_all_stripped`: `"#feature dark mode #bug"` → `FEATURE`,
    title `"dark mode"`.
  - `test_not_a_tag` (parametrized): `"#bugfix for x"`, `"#bug-report x"`, `"foo#bug"`,
    `"##bug x"`, `"#chore something"`, `"see https://x.com/#bug for it"`, `"x/#bug y"`,
    ``"use `#bug` here"``, `""` → `None`.
  - `test_tag_only_returns_none` (parametrized): `"#bug"`, `"  #feature  "`, `"#bug."`,
    `"#feature !"` → `None`.
  - `test_title_cleanup` (parametrized): `"#bug: broken"` → `"broken"`; `"(#bug) x"` → `"x"`;
    `"[#feature] dark mode"` → `"dark mode"`; `"Why does it crash? #bug"` →
    `"Why does it crash?"`.
  - `test_multiline`: `"line one\n#bug\nline two"` → `BUG`, title `"line one line two"`.
  Run `.venv/bin/pytest tests/test_tags.py`; confirm it fails on the missing module.
- [x] Green: create `issue_bot/tags.py` with `IssueType(StrEnum)`, `ParsedTag`, module
  constants `TAG_PATTERN`, `EMPTY_BRACKETS` and `TITLE_EDGE` exactly as in the Design's tag
  grammar, and `parse_tag(text: str) -> ParsedTag | None`: the first `TAG_PATTERN.search`
  gives `IssueType(match.group(1).lower())` (no match → `None`); the title is
  `" ".join(EMPTY_BRACKETS.sub(" ", TAG_PATTERN.sub(" ", text)).split()).strip(TITLE_EDGE)`;
  a title with no alphanumeric character → `None`.
- [x] Refactor; `.venv/bin/pytest` green.

Done 2026-10-17: red confirmed (`ModuleNotFoundError: issue_bot.tags`), then `.venv/bin/pytest` → 27 passed.

**Verify:** `.venv/bin/pytest tests/test_tags.py` green.

### 3. Config from environment (TDD)
`Config.from_env` reads the instance-wide values and builds one `TargetConfig`; every key is
required and nothing has a code default.

**To-do:**
- [x] Red: create `tests/conftest.py` with a `test_env` fixture returning a **fresh** dict of
  neutral fixture values for all nine keys: `DISCORD_TOKEN="test-token"`,
  `DISCORD_GUILD_ID="111"`, `DISCORD_CHANNEL_ID="555"`, `DISCORD_CHANNEL_NAME="intake"`,
  `DISCORD_CATEGORY="Intake"`, `GITHUB_REPO="example-org/example-repo"`,
  `GITHUB_REPO_ID="222"`, `GITHUB_LABEL_BUG="bug"`, `GITHUB_LABEL_FEATURE="enhancement"`;
  and a `config` fixture returning `Config.from_env(test_env)`.
- [x] Red: create `tests/test_config.py` (each test passes a plain `dict`, never
  `os.environ`):
  - `test_full_env_loads(test_env)`: `guild_id == 111`; `config.target` is a `TargetConfig`
    with `channel_id == 555`, `channel_name == "intake"`, `category == "Intake"`,
    `github_repo == "example-org/example-repo"`, `github_repo_id == 222`, and
    `dict(labels) == {IssueType.BUG: "bug", IssueType.FEATURE: "enhancement"}`.
  - `test_each_key_required` (parametrized over the nine key names): deleting that key from
    `test_env` raises `ConfigError` whose message is `f"{key} is required"` (proves there is
    no default for any key).
  - `test_empty_env_names_token_first`: `Config.from_env({})` raises `ConfigError` with
    message `DISCORD_TOKEN is required`.
  - `test_blank_value_counts_as_missing`: `DISCORD_CHANNEL_NAME="  "` → `ConfigError`
    `DISCORD_CHANNEL_NAME is required`.
  - `test_non_integer_id_raises` (parametrized over `DISCORD_GUILD_ID`,
    `DISCORD_CHANNEL_ID`, `GITHUB_REPO_ID`): value `"abc"` → message
    `f"{key} must be an integer"`.
  - `test_non_positive_id_raises` (parametrized over the same three keys × `"0"`, `"-5"`) →
    message `f"{key} must be a positive integer"`.
  - `test_bad_repo_format` (parametrized: `"noslash"`, `"a/b/c"`, `"own er/repo"`) →
    `GITHUB_REPO must be owner/name`.
  - `test_token_not_in_repr`: with `DISCORD_TOKEN="secret-value"`,
    `"secret-value" not in repr(config)`.
  - `test_labels_read_only`: `config.target.labels[IssueType.BUG] = "x"` raises `TypeError`.
  Run `.venv/bin/pytest tests/test_config.py`; confirm it fails on the missing module.
- [x] Green: create `issue_bot/config.py` per the Design section, starting with
  `from __future__ import annotations` (so the self-referencing `-> Config` /
  `-> TargetConfig` annotations resolve on 3.12): `class ConfigError(Exception)`,
  `REPO_PATTERN`, `@dataclass(frozen=True) class TargetConfig` with
  `classmethod from_env(cls, env: Mapping[str, str]) -> TargetConfig`, and
  `@dataclass(frozen=True) class Config` with
  `classmethod from_env(cls, env: Mapping[str, str]) -> Config`. Private helpers
  `_required(env, key) -> str` (strips; blank or absent raises
  `ConfigError(f"{key} is required")`) and `_positive_int(env, key) -> int` (calls
  `_required`, turns a `ValueError` from `int()` into
  `raise ConfigError(f"{key} must be an integer") from None`, and
  raises `ConfigError(f"{key} must be a positive integer")` for values ≤ 0). Labels:
  `MappingProxyType({t: _required(env, f"GITHUB_LABEL_{t.name}") for t in IssueType})`.
  No module-level default constants and no literal identifier values.
- [x] Refactor if needed; confirm `.venv/bin/pytest` green and `grep -rn 'DEFAULT_' issue_bot/`
  prints nothing.

Done 2026-10-17: red confirmed (`ModuleNotFoundError: issue_bot.config` from conftest), then `.venv/bin/pytest` → 53 passed. Review hardening (minor findings): ID keys must be ASCII decimal integers (`ASCII_INTEGER_PATTERN`, so `"١٢٣"`, `"+5"`, `"1_000"` → `must be an integer`) and `GITHUB_REPO` rejects `.`/`..` segments (`DOT_SEGMENTS`); tests extended → 65 passed; `grep -rn 'DEFAULT_' issue_bot/` prints nothing.

**Verify:** `.venv/bin/pytest tests/test_config.py` green.

### 4. Message handler (TDD, mocked Discord)
`candidate_from_message` applies the filters and builds an `IssueCandidate`.

**To-do:**
- [ ] Red: add to `tests/conftest.py` a `make_message` fixture returning a factory
  `make_message(content="Fix it #bug", *, channel_id=555, author_bot=False, webhook_id=None,
  message_type=discord.MessageType.default, author_id=7, author_name="Alice", message_id=99)`
  that builds a `types.SimpleNamespace` with `content`, `channel=SimpleNamespace(id=channel_id)`,
  `author=SimpleNamespace(bot=author_bot, id=author_id, display_name=author_name)`,
  `webhook_id`, `type=message_type`, `id=message_id`,
  `jump_url=f"https://discord.com/channels/111/{channel_id}/{message_id}"`. No real Discord
  objects or network.
- [ ] Red: create `tests/test_handler.py`:
  - `test_tagged_message_becomes_candidate`: all eight `IssueCandidate` fields match:
    `type == IssueType.BUG`, `title == "Fix it"`, `content == "Fix it #bug"` (the raw text),
    `author_id == 7`, `author_name == "Alice"`, `message_id == 99`,
    `message_url == "https://discord.com/channels/111/555/99"`, and
    `candidate.target is config.target`.
  - `test_candidate_repr_hides_text`: for
    `make_message("Secret title words #bug", author_name="Alice")`, `repr(candidate)`
    contains none of `Secret title words`, `#bug` or `Alice`, and contains `message_id=99`.
  - `test_other_channel_ignored` (`channel_id=556`) → `None`.
  - `test_thread_message_ignored` (`make_message("#bug x", channel_id=777)`, 777 standing
    for a thread under the configured channel) → `None`.
  - `test_bot_author_ignored` (`author_bot=True`) → `None`.
  - `test_webhook_ignored` (`webhook_id=123`) → `None`.
  - `test_system_message_ignored` (`message_type=discord.MessageType.thread_created`) → `None`.
  - `test_reply_type_accepted` (`message_type=discord.MessageType.reply`) → candidate.
  - `test_untagged_ignored` (`"anyone around tonight?"`) → `None`.
- [ ] Green: create `issue_bot/handler.py` with `IssueCandidate` (the Design's eight fields,
  `title`, `content` and `author_name` as `field(repr=False)`) and
  `candidate_from_message(message, config: Config) -> IssueCandidate | None`. Order of
  checks: `message.channel.id != config.target.channel_id` → None; `message.author.bot` →
  None; `message.webhook_id is not None` → None;
  `message.type not in (discord.MessageType.default, discord.MessageType.reply)` → None;
  `parse_tag(message.content)` is None → None; else build the candidate with
  `content=message.content` and `target=config.target`. Annotate `message` as
  `discord.Message` (tests duck-type it).
- [ ] Refactor; `.venv/bin/pytest` green.

**Verify:** `.venv/bin/pytest tests/test_handler.py` green.

### 5. Bot client, startup channel check and entry point (TDD)
Wire the handler into a `discord.Client` with the Message Content intent; check the
configured channel at startup.

**To-do:**
- [ ] Red: create `tests/test_bot.py`:
  - `test_intents`: `build_intents().message_content is True`, `.guild_messages is True`,
    `.guilds is True`, `.members is False`, `.presences is False`.
  - `channel_problems` tests with `SimpleNamespace` channels
    (`id=555`, `name`, `guild=SimpleNamespace(id=...)`, `category=SimpleNamespace(name=...)`
    or `None`) against the `config` fixture (guild 111, channel 555, name `intake`, category
    `Intake`): matching channel → `[]`; `None` channel → one problem; wrong name, wrong
    category, no category, wrong guild → one problem each. Each test asserts the exact
    problem string from the Green to-do, e.g. `["channel 555 not found or not visible to the
    bot"]`, `["channel 555 is in guild 222, expected 111"]`, `["channel name is 'general',
    expected 'intake'"]`, `["channel category is 'Other', expected 'Intake'"]`,
    `["channel category is None, expected 'Intake'"]`.
  - `async def test_on_message_calls_hook_with_message_and_candidate`:
    `bot = IssueBot(config, on_candidate=hook)` where `hook = unittest.mock.AsyncMock()`;
    `msg = make_message()`; `await bot.on_message(msg)`; `hook.assert_awaited_once()`; the
    awaited args are `(msg, candidate)` with `candidate` an `IssueCandidate` of type `BUG`.
  - `async def test_on_message_ignores_untagged`: hook not awaited.
  - `async def test_default_hook_logs_ids_not_text(caplog)`: `bot = IssueBot(config)` (no
    hook); inside `caplog.at_level(logging.INFO)`, `await bot.on_message(make_message("Secret
    title words #bug"))`; among records with `record.name == "issue_bot.bot"`, one INFO
    record's message contains `bug`, `99` (the message id) and the factory's `jump_url`, and
    no record's message contains `Secret title words` or `Alice`.
  - `async def test_on_ready_logs_channel_problems(caplog)`: patch `bot.get_channel` to
    return `None` (`monkeypatch.setattr(bot, "get_channel", lambda _id: None)`);
    `await bot.on_ready()`; a WARNING record from `issue_bot.bot` names the channel ID.
    Also a matching-channel case logs no WARNING from `issue_bot.bot` (filter
    `caplog.records` by `record.name == "issue_bot.bot"`): discord.py logs two voice
    WARNINGs (PyNaCl, davey) from `discord.client` on the first Client constructed in a
    process, so an unfiltered check is order-dependent.
  - `async def test_on_error_hides_exception_text(caplog)`: `bot = IssueBot(config)`; inside
    `caplog.at_level(logging.INFO)`, `try: raise RuntimeError("Secret title words")` /
    `except RuntimeError: await bot.on_error("on_message")`; an ERROR record with
    `record.name == "issue_bot.bot"` has a `getMessage()` containing `RuntimeError` and
    `on_message`, and no record's `getMessage()` or `exc_text or ""` contains
    `Secret title words`.
  - `test_edits_not_handled`: `assert not hasattr(IssueBot, "on_message_edit")` (discord.py
    2.7.1's `discord.Client` defines no `on_message_edit`, so the attribute exists only if
    `IssueBot` adds one).
  - `test_main_exits_on_config_error(monkeypatch)`: with all nine config keys removed from
    `os.environ` (`monkeypatch.delenv(key, raising=False)` for each), `main()` raises
    `SystemExit` with code 2 and never constructs `IssueBot` (monkeypatch
    `issue_bot.__main__.IssueBot` to a stub that fails the test if called).
  - `test_main_config_error_hides_value(monkeypatch, test_env, caplog)`: `setenv` every key
    from `test_env`, then `DISCORD_GUILD_ID="secret-value"`; with `IssueBot` stubbed to fail
    if called, `main()` raises `SystemExit` with code 2, `caplog.records` is not empty, and
    no record's `getMessage()` or `exc_text or ""` contains `secret-value`.
  - `test_main_runs_bot_with_token(monkeypatch, test_env)`: `setenv` all nine keys from
    `test_env`; monkeypatch `issue_bot.__main__.IssueBot` to a stub class whose `__init__`
    records its `config` argument and whose `run(self, token, **kw)` records `token` and
    `kw`; `main()` returns; the stub got a `Config` with `guild_id == 111`, `run` got
    `"test-token"` and `kw == {"log_handler": None}`.
- [ ] Green: create `issue_bot/bot.py` with `logger = logging.getLogger(__name__)`:
  - `build_intents() -> discord.Intents`: `discord.Intents.none()`, then set
    `guilds = True`, `guild_messages = True`, `message_content = True` (least privilege).
  - `channel_problems(channel, config: Config) -> list[str]`: compares against
    `config.guild_id`, `config.target.channel_name` and `config.target.category`, emitting
    exactly these strings: a `None` channel yields only
    `f"channel {config.target.channel_id} not found or not visible to the bot"`; otherwise,
    per mismatch, `f"channel {channel.id} is in guild {channel.guild.id}, expected {config.guild_id}"`,
    `f"channel name is {channel.name!r}, expected {config.target.channel_name!r}"` and
    `f"channel category is {actual!r}, expected {config.target.category!r}"` with
    `actual = channel.category.name if channel.category else None`.
  - `CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]`;
    `async def log_candidate(message, candidate) -> None` ignores `message` and logs at INFO
    `"captured %s message_id=%s (%s)"` with `candidate.type`, `candidate.message_id`,
    `candidate.message_url` — never the title, content or author name.
  - `class IssueBot(discord.Client)`: `__init__(self, config: Config, on_candidate:
    CandidateHook = log_candidate)` calls `super().__init__(intents=build_intents())`, then
    sets `self.config = config` and `self.on_candidate = on_candidate`;
    `async def on_ready(self)` logs INFO `"connected as %s"` and a WARNING per
    `channel_problems(self.get_channel(self.config.target.channel_id), self.config)`;
    `async def on_message(self, message)` calls `candidate_from_message(message, self.config)`
    and, when a candidate is returned, awaits `self.on_candidate(message, candidate)`;
    `async def on_error(self, event_method: str, /, *args, **kwargs) -> None` (the discord.py
    2.7.1 `Client.on_error` signature) logs at ERROR `"unhandled %s in %s"` with
    `type(sys.exc_info()[1]).__name__` (`import sys`) and `event_method`, with no `exc_info`, no `args` and
    no exception message (the default `Client.on_error` calls `_log.exception`, whose
    traceback carries the exception text, which can quote member text). discord.py's
    `Client._run_event` awaits `on_error` inside its `except Exception:` block, so
    `sys.exc_info()` holds the exception there (verified at the DD-11 pass in a scratch venv
    with discord.py 2.7.1: a hook raising `RuntimeError` with member text, run through
    `bot._run_event(bot.on_message, "on_message", msg)` and through `bot.dispatch("message", msg)`,
    left only `unhandled RuntimeError in on_message` and no record containing the text). No
    `on_message_edit` handler (edits ignored by design).
- [ ] Green: create `issue_bot/__main__.py` importing `IssueBot` at module level
  (`from issue_bot.bot import IssueBot`, so the test can monkeypatch
  `issue_bot.__main__.IssueBot`) and a module `logger = logging.getLogger(__name__)`, with
  `main() -> None`:
  `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`;
  `config = Config.from_env(os.environ)` inside `try`, with
  `except ConfigError as exc: logger.error("configuration error: %s", exc); raise SystemExit(2) from None`
  (no `exc_info`, so no traceback and no config value reaches the log);
  then `IssueBot(config).run(config.discord_token, log_handler=None)` (logging already
  configured). Guard with `if __name__ == "__main__": main()`.
- [ ] Tests construct `IssueBot(config, ...)` directly (verified at pass-1 review: discord.py
  2.7.1's `Client.__init__` needs no running loop; the PyNaCl/davey WARNING log records on
  first construction are expected) and never call `run`/`start`/`login`, so no test reaches
  the network. Tick once the suite is green.
- [ ] Refactor; `.venv/bin/pytest` green.

**Verify:** `.venv/bin/pytest` green.

### 6. Example config, Docker image and docs
Commit the example env file, package the bot and document how to configure, run and test it.

**To-do:**
- [ ] Create `example.env` at the repo root with the Write tool, content exactly the lines
  inside the Design's `example.env` code block (no fence lines, ending with one newline).
  Verify it byte for byte against the plan:
  ``awk '/^`example.env` exact content/{f=1; next} f && /^```/{if (b) exit; b=1; next} b' plans/feature/channel-listener/channel-listener.md | diff - example.env; echo "exit=$?"``
  prints only `exit=0`, and read the file back to confirm `DISCORD_TOKEN=` has no value.
  Then `git check-ignore -q example.env; echo $?` prints `1` (not ignored),
  `git check-ignore -q .env; echo $?` prints `0` (still ignored), and
  `git ls-files --others --exclude-standard -- example.env` prints `example.env`. Stage it by
  explicit path in this step's commit.
- [ ] Create `.dockerignore` excluding `.env`, `.env.*`, `example.env`, `.git`, `.venv`, `__pycache__`,
  `*.pyc`, `.pytest_cache`, `data/`, `plans/`, `tests/`, `.claude/`, `*.pem`, `*.key`,
  `secrets/`, `credentials/` — the image must never contain credentials or a target
  config (all config arrives through the environment at run time).
- [ ] Create `Dockerfile`: `FROM python:3.12.11-slim` (tag verified to exist at pass-1
  review); `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`; `WORKDIR /app`;
  `COPY requirements.txt .`; `RUN pip install --no-cache-dir -r requirements.txt`;
  `COPY issue_bot/ issue_bot/`; create and switch to a non-root user
  (`RUN useradd --create-home --uid 10001 bot` then `USER bot`); `STOPSIGNAL SIGINT` (Python
  is PID 1 and ignores SIGTERM; SIGINT triggers discord.py's graceful shutdown);
  `CMD ["python", "-m", "issue_bot"]`. No `ENV` line sets any config key.
- [ ] Update `README.md`: keep the intro (it describes the 4irl deployment) and add one
  sentence that the code is target-agnostic: it holds no 4irl values (never a code default),
  and their config home is `example.env`. Replace "Getting started" with prerequisites (Python 3.12, Docker),
  Discord setup (create an application and bot, enable the **Message Content** privileged
  intent, invite with View Channel + Read Message History; F2 later adds thread
  permissions), configuration (`cp example.env .env`, set `DISCORD_TOKEN` and
  `DISCORD_CHANNEL_ID`; a table of the nine keys from this plan's Design section with
  **scope, type and meaning only, never values**; every key is required), local run
  (`python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`, then
  `set -a; . ./.env; set +a; .venv/bin/python -m issue_bot`) and Docker run
  (`docker build -t issue-bot .` and `docker run --rm --env-file .env issue-bot`), with the
  note that `.env` uses plain `KEY=value` lines (no quotes, no `export`): `--env-file` takes
  each value literally, while the shell form (`set -a; . ./.env; set +a`) works only for
  values without spaces or quotes, so a value with spaces needs the Docker `--env-file` run
  (or that key exported by hand with quotes): describe this in words, with no `KEY=value`
  example line, since Step 7's README gate rejects any `DISCORD_*=`/`GITHUB_*=` text; and that pointing the bot at another channel
  or repo means changing only `.env`. Replace "Tests" with `.venv/bin/pytest` and the note that
  tests mock Discord. Update "Status" to say F1 (listener + parser) exists and candidates
  are only logged (ids and URLs) until F2/F5. Note that edited messages and messages inside
  threads are ignored and the channel is matched by `DISCORD_CHANNEL_ID`.
- [ ] Update `CLAUDE.md` § Project rules: add
  `- **Logs never contain members' message text or names.** Log the issue type, message id and message URL only; message content stays in Discord and the filed issue. Exceptions escaping event handlers and hooks are logged by type and event name only. Never run the `discord` loggers at DEBUG: discord.py logs full gateway payloads (message text, member names) at that level.`
  In the existing "Identifiers are config, not code" rule, append that the code holds no
  4irl values (never a code default) and their config home is `example.env`, and in the existing credentials rule note that `example.env` is
  the committed, secret-free template (`.env` itself stays unread).
- [ ] Docker build check (needs `dangerouslyDisableSandbox: true`): `docker build -t
  issue-bot:dev .`, then `docker run --rm issue-bot:dev; echo "exit=$?"` with **no**
  env file; the output must contain the `DISCORD_TOKEN is required` log line and `exit=2`
  (proves the image starts the bot entry point without contacting Discord). Then remove the
  image: `docker image rm issue-bot:dev`. The pulled base image `python:3.12.11-slim` and
  build cache stay in the local daemon (reused by later builds); the owner can reclaim them
  with `docker image rm python:3.12.11-slim` and `docker builder prune`. Do not run either
  from the agent session. Never pass `--env-file .env` and never connect
  to the live server. If Docker is not available or the daemon is not running, leave this
  box unticked, write directly under it
  `UNRESOLVED — requires user decision/action: docker build could not run: <error>`, end
  your final report with that same line, and stop. On a later run where the gate passes,
  delete that marker line before ticking the box.

**Verify:** `.venv/bin/pytest` green; the Design's portability gate prints nothing for both
greps.

### 7. Verify All Tests Pass
Run the full suite and the Expected-end-state checks from META-PLAN § F1.

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm all tests pass (skill-config's `test_run_cmd` and
  `integration_runner_cmd` both name this same command; `ui_runner_cmd` is intentionally
  blank, per the Prerequisites note to the `/run-plan` orchestrator).
- [ ] Run the Design's portability gate:
  `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues|\bC4I\b|4[Ii][Rr][Ll]' --include='*.py' --include='Dockerfile' --include='pyproject.toml' --exclude-dir=.venv --exclude-dir=tests .; echo "exit=$?"`
  prints only `exit=1`, and `grep -rn 'DEFAULT_' issue_bot/; echo "exit=$?"` prints only
  `exit=1`. Confirm the gate is not vacuous: `ls issue_bot/*.py` lists `__init__.py`,
  `__main__.py`, `bot.py`, `config.py`, `handler.py`, `tags.py`.
- [ ] Confirm `grep -nE '(DISCORD|GITHUB)_[A-Z_]+=' README.md || true`
  prints nothing (keys by name only), and
  `grep -nE '1137236302358659185|969373970' README.md; echo "exit=$?"` prints only `exit=1`
  (no ID values in the README), `git ls-files example.env` prints `example.env`
  after the Step 6 commit, `grep -n 'example.env' .dockerignore` prints the exclusion line, `grep -nF '| Verification | `.venv/bin/pytest` |' plans/META-PLAN.md`
  prints the Project-facts row, and `grep -n 'Test: `.venv/bin/pytest`' CLAUDE.md` prints the
  Commands line.
- [ ] Copy the *Contract for later features* section verbatim into this step's final report
  for the `/run-plan` orchestrator; the durable carrier for `/run-feature` Phase C is this
  section of the plan file, which merges to main with the PR. Phase C's rule
  reads "If a *remaining* feature still targets this one's implemented contract, add/update
  it under 'COMPLETED-FEATURE CONTRACTS STILL IN FORCE'" (F2 and F5 depend on F1). Tick once
  copied.
- [ ] Investigate and fix any failures before marking the plan finished. If every check above
  passed, tick this box with `— N/A: no failures`.

## Status
finished: false
