# Multi-target routes and multi-instance deployment (F8)

## Summary

One bot process serves several intake channels. A TOML route file, whose path is in the
required `ROUTES_PATH` env key, maps each intake channel to its target repo in the configured
GitHub org, with that route's own type → label map. `/bug` and `/feature` dispatch by
`interaction.channel_id` to their route. Filing, labels and the posted link already follow
`candidate.target`, so they use that route's repo unchanged. The same image can also run as
several containers sharing one bot token, each with its own route file and
`UNROUTED_COMMANDS=ignore`, so a container stays silent on commands outside its routes. This
plan implements META-PLAN § F8 and opens ROADMAP Phase 1.5.

## Research Findings

- **The single-target coupling sits in five production places.** `Config.from_env` builds
  `Config.target` (via `TargetConfig.from_env`). `bot.py` reads it in `channel_problems`, in
  `IssueBot`'s registration `intake_command(issue_type, config.target, …)`, in
  `_check_github_access` and in `on_ready`'s `get_channel`. Everything downstream already
  takes a `TargetConfig`: the `intake_command` closure, `IntakeModal.target`,
  `candidate_from_submission`, `IssueCandidate.target`, `issues.issue_labels`/`file_candidate`,
  and `GitHubClient.check_access`/`create_issue`, whose token cache is already a
  `dict[int, …]` keyed per repo id (`GitHubClient._tokens`, with the 401 eviction in
  `create_issue`). So `handler.py`, `issues.py`, `github.py` and `threads.py` need no change.
- **Route selection.** Commands are guild-wide, so the callback looks its route up at call
  time. `interaction.channel_id` is the thread's own id inside a thread (discord.py's
  `Interaction.channel_id`), so threads stay unrouted, exactly as F10 refuses them today
  (`intake_command`'s `report` channel check, and
  `test_command_refused_outside_intake_channel` with `channel_id` 556 and `None`). A modal submit is container-local: discord.py's
  `dispatch_modal` (`discord/ui/view.py`) drops unknown custom ids. "Silent" means returning without calling
  `interaction.response.*`. With one shared token every container receives every interaction
  (SMOKE-TEST §4: "Two processes on one bot token both receive each command"), and every
  container's `setup_hook` bulk-overwrites the same guild's command set
  (`tree.sync(guild=…)`), which is harmless only while every container builds an identical,
  route-agnostic payload.
- **Config conventions** (`config.py`). All config objects are frozen dataclasses, and maps
  are frozen in `__post_init__` with `MappingProxyType(dict(…))` via `object.__setattr__`.
  `ConfigError` names the key, never the value, and wraps a lower-level error `from None`.
  Keys are read in a fixed order and tests assert the first bad key
  (`test_first_missing_key_in_order_is_reported` over `ALL_KEYS`). There is no org key today:
  the org is only the owner half of `GITHUB_REPO`. Python 3.12.11 (venv and
  `python:3.12.11-slim`) has stdlib `tomllib`. PyYAML is not installed. `tomllib.load` needs a
  binary handle and raises `TOMLDecodeError` (a `ValueError`), whose text can quote the file.
- **Test blast radius.** `tests/conftest.py`'s `test_env` (12 keys) and `config` fixtures feed
  about 100 tests, which reach about 60 `config.target` call sites in `test_bot.py`,
  `test_intake.py`, `test_github.py`, `test_handler.py` and `test_issues.py`. The key lists are
  duplicated in `test_config.ALL_KEYS`/`ID_KEYS` and `test_bot.CONFIG_KEYS`. Exact asserted log
  lines are `github access ok for repo_id=222`, `github access check failed for repo_id=222: …`,
  `channel 555 not found or not visible to the bot` and `refused bug outside the intake channel
  interaction_id=4242 channel_id=556`. Nothing tests `example.env` against the keys `Config`
  reads.
- **Docs.** README § Configuration has a Key | Scope | Type | Meaning table. README
  § Run with Docker mounts only the key (`-v …:/run/secrets/github-app-key.pem:ro`), and the
  image copies only `issue_bot/`, so the route file must be mounted too. SMOKE-TEST § 0's
  "`.env` for a local run" block lists the target env keys, § 4 says "never run two", and two
  Troubleshooting rows ("The command is refused in the right channel" and "`/bug` says
  reports can't be filed") name `DISCORD_CHANNEL_ID` and `GITHUB_REPO_ID`. CLAUDE.md's
  "Identifiers are config, not code" rule and README's "The code itself is target-agnostic"
  paragraph name `example.env` as the 4irl values' only config home.

## Design decisions (planning, 2026-10-22; all asked)

| DD | Question | Chosen | Ledger |
|---|---|---|---|
| DD-1 | How several containers avoid racing on `/bug` and `/feature` | **One shared bot token plus an opt-in silent mode.** A container set to ignore stays silent on commands outside its routes. Overrode the recommended one app per container, so the picker shows a single `/bug`. | dd-261022-001 |
| DD-2 | F1's single-target env keys | **Migrate.** The route file is required. The seven target keys leave `Config`, `example.env` and the docs, and a committed one-route example file replaces them. | dd-261022-002 |
| DD-3 | Route file format | **TOML** via stdlib `tomllib`, with no new dependency. | dd-261022-003 |
| DD-4 | Org check | **A required `GITHUB_ORG` env key** (instance-wide, never a code default). Each route's repo owner must match it case-insensitively. | dd-261022-004 |
| DD-5 | How silent mode is switched on | **A required `UNROUTED_COMMANDS` env key**, `refuse` or `ignore` (exact lowercase after strip). | dd-261022-005 |
| DD-6 | Route file shape | **`[routes.<name>]` tables.** The name matches `[a-z0-9][a-z0-9_-]*`. Each table has the fields `channel_id`, `channel_name`, `category`, `repo` and `repo_id`, plus a `[routes.<name>.labels]` table keyed `bug`/`feature`. Unknown keys are rejected. | dd-261022-006 |
| DD-7 | Reload | **Restart-only.** The file is read once by `Config.from_env`, and a bad file exits 2 before connecting (Standing invariant 3). | dd-261022-007 |
| DD-8 | Two-instance docs | **A documented `docker run` set** in README, with no compose file (Phase 4 decides deployment). | dd-261022-008 |

Settled by META-PLAN rather than asked:
- **Credentials (Open risk a).** One GitHub App installation covers every route's repo (F5's
  kept contract: "F8's extra target repos join that installation"). That is why every repo
  must sit in `GITHUB_ORG`.
- **Threads stay unrouted.** Routes match by exact channel id, as F10 does.

### Contract for later features (Open risk c; fold into META-PLAN at fold-back)

- A route is a `TargetConfig` whose first field is `name`, the `[routes.<name>]` table
  name. F3 keys its per-route question sets and F6 its per-route Project config off
  `route.name`. They add their own keys under `[routes.<name>]` by extending `ROUTE_KEYS` and
  the loader. F8 requires every `ROUTE_KEYS` key, and `test_example_routes_shape` checks each
  route for exactly that set. A later feature whose key a route may omit (F6: a route with no
  Project) changes both. They never add a second config file or env keys per route.
- `Config.routes` is a read-only `Mapping[int, TargetConfig]` keyed by channel id, in file
  order. It is the only route lookup.
- Command payloads stay route-agnostic, because in shared-token mode every container syncs
  the same guild command set and the last sync wins.
- `intake_command(issue_type, routes, unrouted, on_candidate, filing_check=None)` replaces
  F10's seam: the route is looked up by `interaction.channel_id` at call time, and outside
  the routes the command refuses or, with `UnroutedCommands.IGNORE`, returns without
  responding. `channel_problems(channel, route, guild_id)` takes one route. Fold-back
  replaces META-PLAN's F10 `intake_command(issue_type, target, …)` seam lines and F1's
  single-`TargetConfig` interface line with these and `Config.routes`.

## Steps

### 1. Route-file loader

Add a tested `load_routes(path, org)` to `config.py`, plus the `UnroutedCommands` enum and
`TargetConfig.name`, without changing `Config` yet.

**To-do:**
- [x] **Red.** Add a module helper to `tests/conftest.py`: (2026-10-22)
      `write_routes(directory: Path, text: str) -> Path`, which creates `directory`
      (`directory.mkdir(parents=True, exist_ok=True)`), writes `text` to
      `directory / "routes.toml"` and returns the path. Add module constants for later steps:
      `ONE_ROUTE_TOML`, a `[routes.intake]` table with `channel_id = 555`,
      `channel_name = "intake"`, `category = "Intake"`, `repo = "example-org/example-repo"`,
      `repo_id = 222` and `[routes.intake.labels]` `bug = "bug"`, `feature = "enhancement"`;
      and `TWO_ROUTE_TOML`, which is `ONE_ROUTE_TOML` plus a `[routes.other]` table with
      `channel_id = 556`, `channel_name = "other-intake"`, `category = "Other"`,
      `repo = "example-org/other-repo"`, `repo_id = 223` and labels `bug = "defect"`,
      `feature = "idea"`. Then add `load_routes` tests to `tests/test_config.py`, each
      asserting the exact `str(excinfo.value)`. Extend the file's import to
      `from issue_bot.config import Config, ConfigError, TargetConfig, load_routes` and add
      `from tests.conftest import ONE_ROUTE_TOML, TWO_ROUTE_TOML, write_routes` after the
      `issue_bot` imports, as `tests/test_bot.py` does (the test files have no
      `from __future__ import annotations`, so every name a test or annotation uses must be
      imported). Build each variant by editing the TOML text in
      place: `ONE_ROUTE_TOML` ends with `[routes.intake.labels]`, so an appended line lands in
      the labels table. A top-level key such as `extra = 1` goes before the first table
      header, a route key such as `chanel_id = 1` goes directly under `[routes.intake]`, and a
      changed value replaces its line rather than repeating the table.
  - `ONE_ROUTE_TOML` loads to a mapping `{555: TargetConfig(name="intake", channel_id=555,
    channel_name="intake", category="Intake", github_repo="example-org/example-repo",
    github_repo_id=222, labels={BUG: "bug", FEATURE: "enhancement"})}`.
    `TWO_ROUTE_TOML` loads to two routes whose keys are `[555, 556]` in file order. The
    mapping is read-only (assigning raises `TypeError`).
  - An unreadable path (missing file, or a directory) and malformed TOML both raise
    `ROUTES_PATH must name a readable TOML route file`. A file holding invalid UTF-8 raises
    the same error.
  - An empty (zero-byte) file, a comment-only file (`# no routes\n`, no `routes` table), an
    empty `[routes]`, or
    `routes = 1` raises
    `ROUTES_PATH must define at least one [routes.<name>] table`. An unknown top-level key
    `extra = 1` raises `ROUTES_PATH has unknown key 'extra'`.
  - A route name breaking `[a-z0-9][a-z0-9_-]*` (`[routes.Intake]`, `[routes."a b"]`) raises
    `route names must be lowercase letters, digits, - or _`. A non-table route
    (`routes.intake = 1`) raises `routes.intake must be a table`.
  - For each of the six route keys removed in file-key order (`channel_id`, `channel_name`,
    `category`, `repo`, `repo_id`, `labels`), the error is `routes.intake.<key> is required`.
    Removing all keys from position N onward reports the key at position N.
  - Unknown key `chanel_id = 1` raises `routes.intake has unknown key 'chanel_id'`.
  - `channel_id`/`repo_id` set to `0`, `-1`, `"555"`, `true` or `1.5` raises
    `routes.intake.<key> must be a positive integer`.
  - `channel_name`/`category`/`repo` set to `"  "` raises `routes.intake.<key> is required`,
    and set to `5` raises `routes.intake.<key> must be a string`. Padded strings are stored
    stripped.
  - Repo `"example-org"`, `"a/b/c"` or `"example-org/.."` raises
    `routes.intake.repo must be owner/name`. Repo `"other-org/example-repo"` raises
    `routes.intake.repo must be in GITHUB_ORG`, while `"EXAMPLE-ORG/example-repo"` with org
    `"example-org"` loads.
  - Labels missing `feature`, holding an extra `docs`, set to `labels = "bug"`, or holding a
    value that is blank or not a string each raise
    `routes.intake.labels must map bug and feature to label names`.
  - Two routes with `channel_id = 555` raise `routes.intake and routes.other share channel_id`.
- [x] Run `.venv/bin/pytest tests/test_config.py` and confirm collection of
      `tests/test_config.py` fails with `ImportError: cannot import name 'load_routes'`
      (pytest exits 2), since the file imports `load_routes` from `issue_bot.config` at the
      top. (2026-10-22: ImportError on `load_routes`, exit 2.)
- [x] **Green**, in `issue_bot/config.py`: (2026-10-22)
  - `import tomllib` (after `import re`) and `from enum import StrEnum` (between the
    `from dataclasses import …` and `from pathlib import Path` lines). New constants:
    `ROUTE_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")`,
    `OWNER_PATTERN = re.compile(r"[A-Za-z0-9_.-]+")` (used in Step 2 for `GITHUB_ORG`) and
    `ROUTE_KEYS = ("channel_id", "channel_name", "category", "repo", "repo_id", "labels")`.
  - `class UnroutedCommands(StrEnum)`: `REFUSE = "refuse"`, `IGNORE = "ignore"`, with a
    docstring saying what each does to a command run outside this instance's routes.
  - Add `name: str` as `TargetConfig`'s first field, and change its docstring to "One route:
    an intake channel and the GitHub repo its issues go to." Until Step 2 deletes it,
    `TargetConfig.from_env` passes `name="env"`. Update the `make_target` helper in
    `tests/test_config.py` to pass `name="intake"`.
  - Private helpers that take `(route: Mapping[str, object], where: str, key: str)`, where
    `where` is `routes.<name>`. `_route_int` requires an `int` that is not a `bool` and is
    above 0. `_route_str` requires a `str`, strips it, and raises `… is required` when it is
    blank. A missing key raises `f"{where}.{key} is required"`.
  - `_route(name: str, route: object, org: str) -> TargetConfig` checks that the route is a
    `dict`, rejects the first unknown key in sorted order, then reads the keys in `ROUTE_KEYS`
    order. The repo gets the existing `REPO_PATTERN`/`DOT_SEGMENTS` check, then
    `owner.casefold() != org.casefold()`. A missing `labels` key raises
    `f"{where}.labels is required"` (checked before the shape check); otherwise the labels
    must be a `dict` with
    `set(labels) == {t.value for t in IssueType}`, and each value must be a non-blank `str`,
    which is stripped. It builds `TargetConfig(name=name, …,
    labels={IssueType(k): v for k, v in …})`.
  - `load_routes(path: str, org: str) -> Mapping[int, TargetConfig]` reads the file
    inside `with open(path, "rb") as file:` with `tomllib.load(file)` (so the handle is
    closed, as `_rsa_private_key`'s `read_bytes()` closes its file), catching `(OSError, ValueError)` and raising the
    readable-file `ConfigError` `from None`, so the file text is never quoted. It checks the
    top-level keys and that `routes` is a non-empty `dict`. It validates the names with
    `ROUTE_NAME_PATTERN.fullmatch` (not `.match`, which accepts `"a b"`), builds
    each route, tracks `seen: dict[int, str]` channel → name for the duplicate error, and
    returns `MappingProxyType(dict_in_file_order)`. Give it a docstring naming the file shape
    and the "key, never the value" rule. `config.py` still never logs.
- [x] **Refactor.** Keep `config.py`'s style: no docstrings on the private helpers, as with
      `_required`. Run `.venv/bin/pytest` and confirm the whole suite is green.
      (2026-10-22: style kept, 272 passed. Left unticked for three review triage questions.)
      Review decisions: unknown-key errors keep naming the key (asked); no id upper bound and label characters accepted as planned (assumed: dd-policy dd-261022-020, -021).

### 2. Switch `Config` to routes and dispatch commands by channel

Replace `Config.target` with `Config.routes` and the new env keys, move every consumer and
test to routes, and add the `ignore` branch.

**To-do:**
- [x] **Red: config tests.** (2026-10-22) In `tests/conftest.py`, add a `routes_file(tmp_path: Path) -> Path`
      fixture that calls `write_routes(tmp_path, ONE_ROUTE_TOML)`. Make `test_env` take it,
      delete the seven target keys (`DISCORD_CHANNEL_ID`, `DISCORD_CHANNEL_NAME`,
      `DISCORD_CATEGORY`, `GITHUB_REPO`, `GITHUB_REPO_ID`, `GITHUB_LABEL_BUG`,
      `GITHUB_LABEL_FEATURE`) and add `"UNROUTED_COMMANDS": "refuse"`,
      `"GITHUB_ORG": "example-org"` and `"ROUTES_PATH": str(routes_file)`. Add a
      `route(config: Config) -> TargetConfig` fixture that returns the only route
      (`next(iter(config.routes.values()))`). In `tests/test_config.py`:
  - Set `ALL_KEYS` to `["DISCORD_TOKEN", "DISCORD_GUILD_ID", "UNROUTED_COMMANDS",
    "GITHUB_ORG", "GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID",
    "GITHUB_APP_PRIVATE_KEY_PATH", "ROUTES_PATH"]` and `ID_KEYS` to
    `["DISCORD_GUILD_ID", "GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID"]`.
  - Rewrite `test_full_env_loads` to assert `config.unrouted is UnroutedCommands.REFUSE`,
    `config.github_org == "example-org"` and `list(config.routes) == [555]` with the Step 1
    route.
  - Retarget `test_blank_value_counts_as_missing` to `GITHUB_ORG`. Point the padded-id test at
    `DISCORD_GUILD_ID` (`" 111 "` → 111). Delete `test_bad_repo_format`, which is now covered
    by the Step 1 route tests.
  - Add tests: `UNROUTED_COMMANDS` set to `"silent"` or `"Refuse"` raises
    `UNROUTED_COMMANDS must be refuse or ignore`, and `" ignore "` loads as
    `UnroutedCommands.IGNORE`. `GITHUB_ORG` set to `"a/b"` or `".."` raises
    `GITHUB_ORG must be an owner name`. A `ROUTES_PATH` file whose repo is outside
    `GITHUB_ORG` raises the Step 1 org error through `Config.from_env`. `config.routes` is
    read-only: item assignment raises `TypeError` both on the `config` fixture and on a
    `Config` built directly with `dataclasses.replace(config, routes={555: route})` (taking
    the `route` fixture), which only `Config.__post_init__` freezes, as
    `test_direct_construction_makes_labels_read_only` does for `TargetConfig.labels`.
  - Change `test_labels_read_only` to use the `route` fixture.
  - Imports: make the file's `issue_bot.config` import
    `Config, ConfigError, TargetConfig, UnroutedCommands, load_routes`, and
    `import dataclasses` to the stdlib group.
- [x] Run `.venv/bin/pytest tests/test_config.py` and confirm it fails (2026-10-22: 17 failed, 3 errors, 98 passed):
      `test_full_env_loads`, the new `UNROUTED_COMMANDS`/`GITHUB_ORG`/`config.routes` tests and
      every test that builds a `Config` from `test_env` fail (the old `Config` still reads
      `DISCORD_CHANNEL_ID`). Cases for keys the old `Config` reads before its target keys, such
      as `test_each_key_required[DISCORD_TOKEN]`, and Step 1's `load_routes` tests still pass.
- [x] **Green: `Config`.** (2026-10-22) In `issue_bot/config.py`:
  - Delete `TargetConfig.from_env` and its "keys are read in order" comment. `_required` and
    `_positive_int` keep their other callers.
  - Add `_owner(env, key) -> str`, which is `_required` plus `OWNER_PATTERN.fullmatch` and the
    `DOT_SEGMENTS` check, raising `f"{key} must be an owner name"`.
  - Add `_unrouted(env, key) -> UnroutedCommands`, which looks up
    `UnroutedCommands(_required(env, key))` and maps a `ValueError` to
    `f"{key} must be refuse or ignore"` `from None`.
  - `Config` fields in order: `discord_token` (`repr=False`), `guild_id`, `unrouted:
    UnroutedCommands`, `github_org: str`, `github_app_id`, `github_installation_id`,
    `github_private_key` (`repr=False`) and `routes: Mapping[int, TargetConfig]`.
    `from_env` reads them in exactly the `ALL_KEYS` order: it reads `discord_token`
    (`_required`), `guild_id` (`_positive_int`), `unrouted` (`_unrouted`) and `github_org`
    (`_owner`) into locals in that order, then calls `cls(...)` with those four, the three App
    keys in order (`GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`,
    `GITHUB_APP_PRIVATE_KEY_PATH`, read inline as today) and
    `routes=load_routes(_required(env, "ROUTES_PATH"), github_org)`, so no key is read ahead of
    an earlier `ALL_KEYS` entry.
  - Add `Config.__post_init__`, which does
    `object.__setattr__(self, "routes", MappingProxyType(dict(self.routes)))`, the same
    pattern as `TargetConfig.__post_init__` uses for `labels` (`dict()` keeps file order), so
    a directly built `Config` has read-only routes too.
  - Change the module docstring to say that instance config and secrets come from the
    environment, that the routes come from the TOML file at `ROUTES_PATH`, and that nothing
    has a code default. Change `Config`'s docstring to "Instance-wide settings plus the
    routes, keyed by intake channel id."
- [x] Run `.venv/bin/pytest tests/test_config.py` and confirm it passes (2026-10-22: 118 passed) (the other test files
      still read `config.target` until the migration below).
- [x] **Red: intake.** (2026-10-22: 11 failed before the green) In `tests/test_intake.py`, migrate every
      `intake_command(issue_type, config.target, hook[, check])` call to
      `intake_command(issue_type, config.routes, config.unrouted, hook[, check])`. Migrate
      every `IntakeModal(…, config.target, …)` and every `config.target` assertion to the
      `route` fixture. The `filled_modal` helper takes `route: TargetConfig` in place of
      `config: Config` and builds `IntakeModal(issue_type, route, hook)`, and every
      `filled_modal(config, …)` call becomes `filled_modal(route, …)`, with its test taking the
      `route` fixture. Add tests:
  - With `UnroutedCommands.IGNORE` and `channel_id` 556 or `None`: no `send_message`, no
    `send_modal`, no `defer`, the filing check and hook are not awaited, and exactly one INFO
    record `ignored bug outside this instance's routes interaction_id=4242 channel_id=<id>`
    is logged. The test also calls `assert_no_member_text(caplog)`.
  - With `IGNORE` in a routed channel (555), the modal still opens.
  - With `REFUSE`, the existing refusal tests (`INTAKE_REFUSAL`, log
    `refused bug outside the intake channel …`) stay as they are.
  - The file's config import becomes
    `from issue_bot.config import Config, TargetConfig, UnroutedCommands`.
- [x] **Green: `intake_command`.** (2026-10-22) In `issue_bot/intake.py`, the new signature is
      `intake_command(issue_type: IssueType, routes: Mapping[int, TargetConfig],
      unrouted: UnroutedCommands, on_candidate: CandidateHook, filing_check: FilingCheck |
      None = None)`. The imports become
      `from collections.abc import Awaitable, Callable, Mapping` and
      `from issue_bot.config import TargetConfig, UnroutedCommands`. In `report`:
  - `target = routes.get(interaction.channel_id)`.
  - When it is `None` and `unrouted is UnroutedCommands.IGNORE`, log the `ignored …` INFO
    line with `issue_type`, `interaction.id` and `interaction.channel_id`, and `return` with
    no response. Add the comment "another instance on this bot token may own the channel;
    any reply here would race it".
  - Otherwise, when it is `None`, keep the existing refusal log line and `INTAKE_REFUSAL`.
    `INTAKE_REFUSAL`'s text stays F10's ("Reports go in the intake channel: run this command
    there."), unchanged; only README § Reporting says "an intake channel".
  - The filing check and the modal use `target` as before.
  - Change the docstring to "…opens the report modal in a routed intake channel; elsewhere
    it refuses privately or, with ``UnroutedCommands.IGNORE``, stays silent." The modal and
    its callers stay unchanged.
- [x] **Red: bot.** (2026-10-22: 40 failed before the green) In `tests/test_bot.py`:
  - The config import becomes `from issue_bot.config import Config, TargetConfig`, for the
    migrated tests' `route: TargetConfig` parameters.
  - Set `CONFIG_KEYS` to the same eight keys as `ALL_KEYS`.
  - Change the `channel_problems` tests (`test_matching_channel_has_no_problems` through
    `test_no_category`) to call `channel_problems(channel, route, config.guild_id)`, keeping
    their exact messages.
  - Migrate the `config.target` uses in `test_filing_hook_files_issue_posts_link_and_logs_url`,
    `test_filing_hook_unexpected_error_reaches_modal_on_error`,
    `test_setup_hook_logs_github_access_ok` and
    `test_setup_hook_github_access_failure_logged_and_survived` to `route`.
  - Make the end-to-end tree test (`IssueBot(config)` with `tree.get_command("bug", …)`)
    still open the modal in channel 555.
  - Add `test_main_exits_on_bad_route_file(monkeypatch, test_env, tmp_path, caplog)`, shaped
    like `test_main_config_error_hides_value`: set every `test_env` key with
    `monkeypatch.setenv`, then set `ROUTES_PATH` to `str(tmp_path / "missing.toml")`, patch
    `entry_point.IssueBot` with `FailingBot`, and assert `SystemExit` with code 2, that some
    record in `record_texts(caplog)` is
    `configuration error: ROUTES_PATH must name a readable TOML route file`, and that no
    record contains the missing file's path, and calls `assert_no_member_text(caplog)`.
- [x] **Green: bot.** (2026-10-22) In `issue_bot/bot.py`:
  - The new signature is `channel_problems(channel: Any, route: TargetConfig, guild_id: int)`,
    with the same message strings, except that the name and category problems gain a `channel <id>`
    prefix (Step 3 review, dd-261022-023), reading `route.channel_id`/`channel_name`/`category` and
    `guild_id`. The import becomes `from issue_bot.config import Config, TargetConfig`
    (`IssueBot` still takes `Config`).
  - Registration becomes `intake_command(issue_type, config.routes, config.unrouted,
    self.on_candidate, self.filing_check)`.
  - `_check_github_access` loops `for route in self.config.routes.values():`, with the same
    per-route `try`/`except` and log lines using `route.github_repo_id`. A failure on one
    route logs and `continue`s to the next, never `return`s.
  - `on_ready` loops the routes. For each, it calls `channel = self.get_channel(
    route.channel_id)`, picks the same ERROR/WARNING choice, and logs
    `channel_problems(channel, route, self.config.guild_id)`.
  - Update the docstrings: `on_ready` checks "each route's intake channel once", and
    `IssueBot` posts the summary "in the route's intake channel".
- [x] **Migrate the remaining tests.** (2026-10-22: grep prints nothing, exit 1) In `tests/conftest.py`, `make_candidate` takes
      `route: TargetConfig` instead of `config`, and its default is `target or route`. In
      `tests/test_github.py`, the `create(client, config)` helper becomes
      `create(client, route: TargetConfig)` and every `create(client, config)` caller (with
      its `config: Config` fixture parameter) becomes `create(client, route)` with a
      `route: TargetConfig` parameter; `test_create_issue_success`'s direct
      `client.create_issue(config.target, …)` and the `check_access` tests'
      `client.check_access(config.target)` pass `route`, and those tests' `config: Config`
      parameters become `route: TargetConfig`; swap the file's
      `from issue_bot.config import Config` for `TargetConfig`. Change `tests/test_handler.py`
      (its `candidate_from_submission(…, config.target)` calls and `config.target` assertion)
      to use `route` too: its two tests take `route: TargetConfig`, and the file's
      `from issue_bot.config import Config` becomes `TargetConfig`. In `tests/test_issues.py`,
      rewrite `test_issue_labels_use_target_mapping` to build
      `dataclasses.replace(route, labels={IssueType.BUG: "bug", IssueType.FEATURE: "idea"})`
      in place of the env override, taking the `route` fixture instead of `test_env`; add
      `import dataclasses` at the top of the file and swap its
      `from issue_bot.config import Config` for `TargetConfig`. Then confirm
      `grep -rnE 'config\.target|TargetConfig\.from_env|DISCORD_CHANNEL_ID|DISCORD_CHANNEL_NAME|DISCORD_CATEGORY|GITHUB_REPO\b|GITHUB_REPO_ID|GITHUB_LABEL_' --include='*.py' issue_bot tests`
      prints nothing (no output; grep exits 1, which is the pass; `--include='*.py'` keeps
      stale `__pycache__` files out).
- [x] Run `.venv/bin/pytest` and confirm the whole suite is green. (2026-10-22: 255 passed;
      grep clean. Its one review triage question has been resolved.)
      Review decision: per-route startup checks stay sequential (asked, dd-261022-022).

### 3. Two-route behaviour and per-repo tokens

Pin the multi-route contract with two mocked routes filing to two mocked repos. These tests
exercise Step 2's generalization; if one fails, fix the code, not the test.

**To-do:**
- [x] (2026-10-22) In `tests/conftest.py`, add a `two_route_config(test_env, tmp_path) -> Config` fixture
      that writes `path = write_routes(tmp_path / "two", TWO_ROUTE_TOML)` (`write_routes`
      creates the directory, which keeps it clear of `routes_file`) and returns
      `Config.from_env({**test_env, "ROUTES_PATH": str(path)})`, leaving `test_env` unchanged.
- [x] (2026-10-22) `tests/test_intake.py`: dispatch tests with `two_route_config`.
  - `/bug` in channel 555 opens a modal whose `.target.name == "intake"`, and in 556 one
    whose target is `"other"`. The filing check is awaited with the matching route each time.
  - Channel 557 with `REFUSE` gets `INTAKE_REFUSAL`. Channel 557 with `IGNORE` gets no
    response.
  - A submit in 556, through `filing_hook(fake_github(…))`, calls `create_issue` with the
    `"other"` route and labels `["defect"]` for `/bug`. The interaction and its summary are
    both in channel 556: build it as
    `make_interaction(channel_id=556, summary=make_message(channel_id=556))` and submit
    `filled_modal(two_route_config.routes[556], filing_hook(fake_github(…)))` on it (the
    route dispatch itself is the first sub-bullet's). The test takes the `make_message`
    fixture; add `MessageFactory` to the file's `tests.conftest` import.
- [x] (2026-10-22) `tests/test_github.py`: one `GitHubClient` and two routes (repo ids 222 and 223).
      `create_issue` on each mints two tokens, with `repository_ids` `[222]` then `[223]`, and
      POSTs to `/repos/example-org/example-repo/issues` and
      `/repos/example-org/other-repo/issues`. A second `create_issue` for 222 reuses its
      cached token with no new mint. Build the client with the file's `make_client`; the
      transport `side_effect` is `[token_response(), issue_response(), token_response(),
      issue_response(), issue_response()]` (the file's helpers), and the call URLs in order
      are `TOKEN_URL`, `ISSUE_URL`, `TOKEN_URL`,
      `"https://api.github.com/repos/example-org/other-repo/issues"`, `ISSUE_URL`, with the two
      token payloads' `repository_ids` `[222]` then `[223]`. The two routes come from the
      `two_route_config: Config` fixture, so import `Config` again beside `TargetConfig`
      (Step 2 swapped it out).
- [x] (2026-10-22) `tests/test_bot.py`: `setup_hook` with `two_route_config` awaits the check for both
      routes in file order (`check.await_args_list`). Mock `bot.tree.sync` with
      `AsyncMock(return_value=[])`, as `test_setup_hook_logs_github_access_ok` does. When the
      first route's check raises, the second is still checked. Parametrize this over two
      cases; in each, the `bot_records(caplog)` messages starting with `github access` are
      exactly, in order (`setup_hook` also logs `synced 0 commands to guild 111` first,
      which this filter leaves out):
      - `GitHubError("token", 401)`:
        `github access check failed for repo_id=222: GitHubError stage=token status=401`,
        then `github access ok for repo_id=223`.
      - `RuntimeError("Secret exception words")`:
        `github access check failed for repo_id=222: RuntimeError`, then
        `github access ok for repo_id=223`; also, no `record_texts(caplog)` entry (the
        conftest helper, already imported) contains `Secret exception words`.
  - `on_ready` with `two_route_config` looks up `[555, 556]` once across two `on_ready` calls,
    and a missing 556 logs only `channel 556 not found or not visible to the bot` at ERROR
    (its recording `get_channel` stub returns `make_channel()` for 555 and `None` for 556, so
    the WARNING-or-higher `bot_records` are exactly
    `[(logging.ERROR, "channel 556 not found or not visible to the bot")]`; the all-`None` stub
    of `test_on_ready_checks_channel_once_across_reconnects` would also log 555).
    `IssueBot(two_route_config)` still registers exactly `["bug", "feature"]` for the guild and
    no global commands.
  - Silent mode through the real tree: build
    `IssueBot(Config.from_env({**test_env, "UNROUTED_COMMANDS": "ignore"}))`, get the `bug`
    command with `bot.tree.get_command("bug", guild=discord.Object(id=111))`, run its
    callback with `make_interaction(channel_id=557)` and assert `send_message`, `send_modal`
    and `defer` are not awaited; with `make_interaction()` (channel 555) assert the modal
    opens (`send_modal` awaited once).
  - Give the module helper `make_channel` a `channel_id: int = 555` keyword (it builds
    `id=channel_id` instead of the fixed `id=555`). An `on_ready` test with
    `two_route_config`, where `get_channel` returns `make_channel()` for 555 and
    `make_channel(channel_id=556)` for 556, asserts the WARNING-or-higher `bot_records` are
    exactly `[(logging.WARNING, "channel 556 name is 'intake', expected 'other-intake'"),
    (logging.WARNING, "channel 556 category is 'Intake', expected 'Other'")]`.
- [x] Run `.venv/bin/pytest` and confirm all green. Every new log test also calls
      `assert_no_member_text(caplog)` (Standing invariant 2). (2026-10-22: 268 passed, after
      prefixing the name and category problems with the channel id.)
      Review decision: channel name/category warnings prefixed with the channel id (asked, dd-261022-023).

### 4. Example config, drift tests and docs

Give the 4irl values their new config home and document the single-process route file and
the shared-token multi-container mode.

**To-do:**
- [x] **Red: drift tests** (2026-10-22) in `tests/test_config.py`, reading files relative to the repo root
      via `Path(__file__).resolve().parent.parent`:
  - `test_example_env_lists_every_key`: the `KEY` of every non-comment, non-blank `KEY=…` line
    in `example.env` equals `set(ALL_KEYS)`.
  - `test_example_routes_shape`: `tomllib.load` of `example.routes.toml` gives a `routes`
    table. Each route's keys equal `set(ROUTE_KEYS)` (imported from `issue_bot.config`), and
    each `labels` table's keys equal `{t.value for t in IssueType}`. The test doesn't load it
    through `load_routes`, because its placeholder ids are 0 by design.
  - Imports: add `import tomllib` to the file's stdlib group, and make its `issue_bot.config`
    import `ROUTE_KEYS, Config, ConfigError, TargetConfig, UnroutedCommands, load_routes`
    (constants, classes, functions, as the other test files order them).
- [x] Run `.venv/bin/pytest tests/test_config.py -k example_` and confirm both fail (2026-10-22: 2 failed, an AssertionError and a FileNotFoundError):
      `example.env` still has the old keys, and `example.routes.toml` doesn't exist.
- [x] **Green: `example.env`.** (2026-10-22) Drop the `# Target: …` section and its seven keys. Under
      `# Instance-wide`, add these, each with a one-line how-to comment in the file's style:
  - `UNROUTED_COMMANDS=refuse`, commented "refuse: a command outside the routes gets a
    private refusal; ignore: no reply (every container sharing a bot token, see README)".
  - `ROUTES_PATH=/run/config/routes.toml`, commented "A path: mount your route file
    read-only here; start from example.routes.toml".

  Under `# GitHub App (instance-wide)`, add `GITHUB_ORG=4IRL`, commented "The org the App is
  installed in; every route's repo must be in it".
- [x] **Green: `example.routes.toml`** (2026-10-22) (new, committed, secret-free). A header comment
      explains: copy it outside the repo, one `[routes.<name>]` table per intake channel,
      lowercase names that later per-route settings key off, read once at startup, and
      restart after a change. Then one route, `[routes.c4i]`:
  - `channel_id = 0`, commented "Discord Developer Mode, right-click #c4i-github-issues,
    Copy Channel ID. 0 is rejected.";
  - `channel_name = "c4i-github-issues"` and `category = "C4I"`, commented "startup sanity
    check only";
  - `repo = "4IRL/chores4irl"`;
  - `repo_id = 0`, commented "`gh api repos/4IRL/chores4irl --jq .id`. 0 is rejected.";
  - `[routes.c4i.labels]` with `bug = "bug"` and `feature = "enhancement"`.

  Add `example.routes.toml` beside `example.env` in `.dockerignore`, and change its second
  comment line, "# All config arrives through the environment at run time.", to
  "# All config arrives at run time: the environment, plus the route file mounted at
  ROUTES_PATH." (one line).
- [x] Run `.venv/bin/pytest` and confirm green. (2026-10-22: 270 passed)
- [x] **`README.md`.** (2026-10-22)
  - Intro paragraph ("made through a modal in a configured intake channel … in a configured
    repo"): one intake channel per route, each report filed in that route's repo.
  - The "The code itself is target-agnostic" paragraph: the 4irl values' config home is
    `example.env` and `example.routes.toml`.
  - § Status opening paragraph ("F2 (thread per report), … and F10 (slash-command intake)
    exist"): add F8 (routes: several intake channels, each filing to its own repo, from the
    route file) to the list of features that exist.
  - § Status bullets ("The commands are synced …" and "The intake channel is matched by
    `DISCORD_CHANNEL_ID` …"): the commands are refused outside a routed intake channel, or
    ignored when `UNROUTED_COMMANDS=ignore`. Each route's channel is matched by its
    `channel_id`, and its name, category and guild are checked at startup per route.
  - § Reporting: "in the intake channel" becomes "in an intake channel", and the last bullet
    names the `ignore` case.
  - § Discord setup: the channel permissions apply on each route's intake channel.
  - § GitHub App setup: "Install it on the target repo(s) only" becomes install it on every
    route's repo (**Only select repositories**); a route to a new repo means adding that repo
    to the installation.
  - § Configuration opening ("All configuration comes from the environment, and every key is
    required…"): instance settings and secrets come from the environment and the routes from
    the TOML file at `ROUTES_PATH`; every key is required, with no defaults in code. In the
    "Then set the bot token, the intake channel's ID (… **Copy Channel ID**) …" sentence, move
    the channel-ID how-to to the route-file part (`channel_id`).
  - § Configuration: env keys and route file get separate tables. The env table holds the
    eight keys, adding `UNROUTED_COMMANDS` (`refuse`/`ignore`), `GITHUB_ORG` (owner name) and
    `ROUTES_PATH` (path). The route file table (`mkdir -p ~/.config/discord-github-issue-bot
    && cp example.routes.toml ~/.config/discord-github-issue-bot/routes.toml`; README never
    creates that directory elsewhere) has the rows `[routes.<name>]`,
    `channel_id`, `channel_name`, `category`, `repo` (`owner/name` in `GITHUB_ORG`),
    `repo_id` and `labels.bug`/`labels.feature`. Rewrite the labels note for
    `labels.*`. "changing only `.env`" becomes "changing only the route file". Add a sentence
    saying the file is read once at startup, so restart after editing it.
  - § Run locally: set `ROUTES_PATH` to the host path, as for the key.
  - § Run with Docker: add `-v /path/to/routes.toml:/run/config/routes.toml:ro` to the
    `docker run` line, and note the file needs only to be world-readable (it is not secret),
    unlike the key. The section's closing `.env` sentence ("In `.env`, set
    `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` for the container run.")
    sets both `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` and
    `ROUTES_PATH=/run/config/routes.toml`.
  - New § **Run several instances**, after § Run with Docker:
    - Containers from the same image share one `.env` (the same bot token and App) and set
      `UNROUTED_COMMANDS=ignore` in it.
    - Each container mounts its own route file. Show two detached lines,
      `docker run -d --rm --name issue-bot-a --env-file .env -v /path/to/key.pem:/run/secrets/github-app-key.pem:ro -v /path/to/routes-a.toml:/run/config/routes.toml:ro discord-github-issue-bot`
      and the same with `issue-bot-b`/`routes-b.toml` (the key mount is § Run with Docker's),
      then `docker logs -f issue-bot-a` to follow one, followed by: "If `docker logs` says
      `No such container`, the container exited at startup (most often a
      `configuration error: …`) and `--rm` removed it: run the same command without `-d` to
      see the error." Then `docker stop issue-bot-a issue-bot-b` to stop both (the image's
      `STOPSIGNAL SIGINT` triggers discord.py's graceful shutdown, and `--rm` removes them).
    - Warnings:
      1. No channel may appear in two containers' route files. Nothing can check this across
         containers, and both would answer.
      2. A command in a channel no container routes, including any thread (even one in an
         intake channel), gets Discord's "The application did not respond".
      3. Run the same image version in every container: each one syncs the guild's
         `/bug`/`/feature` at start, and the last sync wins.
    - Close with: "One process can also serve several channels from one route file, which is
      the simpler setup."
  - § Known limits: add "Route file changes need a restart."
- [x] **`docs/SMOKE-TEST.md`.** (2026-10-22; locator one-liner run: outputs as documented)
  - §0 "`.env` for a local run" block: replace the five target lines with `GITHUB_ORG=4IRL`,
    `UNROUTED_COMMANDS=refuse` and
    `ROUTES_PATH=/home/<you>/.config/discord-github-issue-bot/routes.smoke.toml`, plus a
    `routes.smoke.toml` block with one `[routes.smoke]` table for the test channel and
    `4IRL/issue-bot-scratch` (`repo_id = <REPO_ID>`, `channel_id = <test channel ID>`, …,
    labels `bug`/`enhancement`). Add `ROUTES_PATH` to the local and container path notes.
  - §3: "Restart the bot after every `.env` change" becomes "after every `.env` or route-file
    change".
  - §4: the container run sets `ROUTES_PATH=/run/config/routes.toml` and adds
    `-v ~/.config/discord-github-issue-bot/routes.smoke.toml:/run/config/routes.toml:ro` to
    the `docker run`. The pre-run checks add
    `grep '^ROUTES_PATH=' .env   # exactly: ROUTES_PATH=/run/config/routes.toml`. "Set the key
    path back to the host path afterwards" becomes "Set the key path and `ROUTES_PATH` back to
    the host paths afterwards". Keep "Stop the local bot first … never run two" for the smoke
    test, and add "README § Run several instances covers deliberate multi-container runs".
  - §5 step 3: "Restore `.env` to the real target repo, intake channel and host key path"
    becomes "Restore `ROUTES_PATH` to the real route file and the host key path".
  - Troubleshooting: the "refused in the right channel" row says the route's `channel_id`
    doesn't match. Add a row "The application did not respond" in a thread or an unrouted
    channel: with `UNROUTED_COMMANDS=ignore` the bot stays silent there; run the command in
    the routed channel itself. The "can't be filed" row checks `repo_id` in the route file. Add a row for
    `configuration error: routes.<name>.repo must be in GITHUB_ORG` and one for
    `ROUTES_PATH must name a readable TOML route file` (a wrong path, or a TOML syntax error;
    in a container run, also a `-v` route-file mount left off, a `-v` source path that didn't
    exist (Docker then created an empty directory there: remove it with `sudo rmdir` and
    create the file), or a route file uid 10001 can't read). That row also gives a locator one-liner, run from
    the repo root, that prints only the parser's one-line position message, never a traceback
    or the file's lines (it has no `|`, so it sits in the table cell unescaped):
    `.venv/bin/python -c 'import sys, tomllib; sys.excepthook = lambda t, e, tb: print(f"{t.__name__}: {e}"); tomllib.load(open(sys.argv[1], "rb")); print("ok")' <route file>`.
    A syntax error prints e.g. `TOMLDecodeError: Invalid value (at line 2, column 14)` (exit
    1), a valid file prints `ok`, and a missing file prints a `FileNotFoundError: …` line.
    Note that a file saved with a UTF-8 BOM fails at line 1, column 1
    (`TOMLDecodeError: Invalid statement (at line 1, column 1)`): re-save it as UTF-8 without
    a BOM.
- [x] **`CLAUDE.md`** (2026-10-22), the "Identifiers are config, not code" rule: "their config home is
      `example.env`" becomes "their config homes
      are `example.env` and `example.routes.toml`". In the opening sentence, "in a configured
      intake channel of a Discord server, into fleshed-out GitHub issues in a configured repo
      of the 4IRL GitHub org" becomes "in one of its configured intake channels of a Discord
      server, into fleshed-out GitHub issues in that channel's route repo in the 4IRL GitHub
      org". Leave everything else unchanged.
- [x] Confirm `grep -nE 'DISCORD_CHANNEL_ID|DISCORD_CHANNEL_NAME|DISCORD_CATEGORY|GITHUB_REPO\b|GITHUB_REPO_ID|GITHUB_LABEL_' README.md docs/SMOKE-TEST.md example.env CLAUDE.md`
      prints nothing (no output; grep exits 1, which is the pass). Then confirm the new
      passages landed (each exits 0): `grep -n '^### Run several instances' README.md`
      prints the heading line; `grep -l ':/run/config/routes.toml:ro' README.md docs/SMOKE-TEST.md`
      lists both files; `grep -l 'example.routes.toml' CLAUDE.md .dockerignore` lists both
      files (in any order). A file missing from a `grep -l` listing is a missed edit, even
      though grep still exits 0 when the other file matches. (2026-10-22: stale-key grep exit 1;
      heading found; both `grep -l` listings name both files. Review fixes: the README route-file
      copy uses `install -m 0644` so uid 10001 can read it, the route-name rule says "starting
      with a letter or digit", and the `example.env` drift test also rejects duplicate keys and
      lines without `=`; 270 passed.)

### 5. Verify all tests pass

Run the full suite and the F8 Expected-end-state checks.

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm every test passes.
- [ ] Standing invariant 1:
      `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot`
      prints nothing (no output; grep exits 1, which is the pass).
- [ ] `grep -rnE 'chores4irl|969373970' --include='*.py' . | grep -v '^./tests/' | grep -v '^./.venv/'`
      prints nothing (no output; grep exits 1, which is the pass).
- [ ] Standing invariant 2: `grep -rnE 'exc_info *=|logger\.exception' --include='*.py' issue_bot` prints
      nothing (no output; grep exits 1, which is the pass): `on_error`'s `sys.exc_info()` and
      the "never exc_info" comment in `_sync_commands` are expected and not matched. The new
      `ignored …` line logs only the issue type and ids, and every Step 2–3 log test calls
      `assert_no_member_text`.
- [ ] Standing invariant 3: confirm `test_main_exits_on_config_error` (which deletes all
      eight `CONFIG_KEYS` at once and expects exit 2) and Step 2's
      `test_main_exits_on_bad_route_file` both pass:
      `.venv/bin/pytest tests/test_bot.py -v -k 'test_main_exits_on_config_error or test_main_exits_on_bad_route_file'`
      lists both `tests/test_bot.py::test_main_exits_on_config_error PASSED` and
      `tests/test_bot.py::test_main_exits_on_bad_route_file PASSED` (before Step 2 only the
      first is collected).
- [ ] Check each F8 Expected-end-state bullet against the code and docs: route file with
      env path and secrets only in env; dispatch by channel id with refusal outside routes;
      startup rejecting duplicate channels and foreign-org repos; per-route name/category
      check; documented two-instance `docker run` set.
- [ ] Investigate and fix any failure before marking the plan finished; when nothing failed,
      tick it as `(none to fix)`.
- [ ] Copy the **Owner checks** section below, verbatim, into the final report.
- [ ] Confirm the **PR notes** section below is present and matches the final env keys
      (`example.env`) and route fields (`ROUTE_KEYS` in `issue_bot/config.py`), and repeat it,
      verbatim, at the end of the final report.

### Owner checks (manual, not for the executor)

Instruction for the agent running `/run-feature`: put these checks, in order, in Phase B's
verification brief under **Still needs you** (no skill relays a step's final report there:
`/run-plan` reports only its fixed "Report final summary" block, and Phase B builds its brief
"from the change itself, not from a fixed checklist").

- Before: follow `docs/SMOKE-TEST.md` § 0 (One-time setup) and § 1 (Token probe).
  Re-create `4IRL/issue-bot-scratch` (META-PLAN Baseline: torn down on 2026-10-18), add it to
  the App installation's selected repositories, create every label the route files use
  (`gh label create <name> --repo 4IRL/issue-bot-scratch` for `defect` and `idea`,
  besides `bug`/`enhancement`), and re-run the token probe. Create a second and a third test
  channel in the test guild, giving the bot the five channel permissions § 0 lists (View
  Channel, Read Message History, Send Messages, Create Public Threads, Send Messages in
  Threads).
- Writes: each `/bug` files one scratch issue and posts one summary message, one thread and
  one link post in that channel. Every bot start re-syncs the test guild's `/bug` and
  `/feature`. A re-run repeats all of it.
- Single process, two routes (test server and the scratch repo only, per `docs/SMOKE-TEST.md`):
  - Put two `[routes.*]` tables in `routes.smoke.toml`, for two test channels, both pointing
    at `4IRL/issue-bot-scratch`, with labels `bug`/`enhancement` and `defect`/`idea`.
  - Start the bot. The log shows `github access ok for repo_id=…` twice and no channel
    ERROR/WARNING.
  - `/bug` in each channel files an issue carrying that route's label, with the link posted
    in that channel's thread.
  - `/bug` in a third, unrouted channel gets the private refusal.
- Shared token, two containers:
  - Build the image from this branch (`docker build -t discord-github-issue-bot .`, as in
    `docs/SMOKE-TEST.md` § 4). Stop the single-process bot first (§ 4: no other process on
    this token during the run). Set `UNROUTED_COMMANDS=ignore`,
    `ROUTES_PATH=/run/config/routes.toml` and
    `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` in `.env` (§ 4's pre-run
    checks apply). Split the two tables of the single-process `routes.smoke.toml` into
    `routes.a.toml` and `routes.b.toml` beside it, then start two containers from that image
    as README § Run several instances shows (`docker run -d --rm --name issue-bot-a` and
    `--name issue-bot-b`), each mounting its own one-route file at `/run/config/routes.toml`
    (`-v <route file>:/run/config/routes.toml:ro`), plus the key mount from § 4. If
    `docker logs` says `No such container`, follow README § Run several instances' note: the
    container exited at startup and `--rm` removed it, so rerun it without `-d` to see the
    error.
  - `/bug` in channel A opens exactly one modal and files once. Only container A logs its
    `filed bug message_id=… issue=…` line, while container B logs only
    `ignored bug outside this instance's routes interaction_id=… channel_id=<A>`. The same
    goes for B, mirrored.
  - A third, unrouted channel shows "The application did not respond" and logs
    `ignored bug outside this instance's routes …` in both containers.
- After the owner checks, stop both containers (`docker stop issue-bot-a issue-bot-b`;
  `--rm` removes them), then tear down per `docs/SMOKE-TEST.md` § 5 (Record and tear down):
  record the scratch issues, remove the scratch repo from the installation and delete it,
  and restore `.env` (`UNROUTED_COMMANDS=refuse`, `ROUTES_PATH` and the host key path) and
  the route file, restoring SMOKE-TEST's single-route `routes.smoke.toml` or removing the
  extra routes. Delete `routes.a.toml` and `routes.b.toml`, and delete the second and third
  test channels or keep them for later smoke runs.

### PR notes

The F1 target env keys moved into the route file. Old key → route field:
`DISCORD_CHANNEL_ID`→`channel_id`, `DISCORD_CHANNEL_NAME`→`channel_name`,
`DISCORD_CATEGORY`→`category`, `GITHUB_REPO`→`repo`, `GITHUB_REPO_ID`→`repo_id`,
`GITHUB_LABEL_BUG`/`GITHUB_LABEL_FEATURE`→`labels.bug`/`labels.feature` (each under the
route's `[routes.<name>]` table). New env keys: `UNROUTED_COMMANDS`, `GITHUB_ORG`,
`ROUTES_PATH`.

Instruction for the agent running `/run-feature`: when its Phase A `/git-push` opens the PR,
add this section to the PR description (no skill copies it on its own: `/git-push`'s
"PR Body Format" builds the body from the diff). It reaches reviewers through this committed
plan file regardless.

## Status
finished: false
