# META-PLAN — discord-github-issue-bot feature rollout

> **What this file is.** The execution manifest: F-IDs, order, ★FOCUS, status, the
> code-level Baseline, Standing invariants, per-feature contracts and couplings. Each
> feature runs as its own session via `/run-feature`; features enter only via
> `/new-feature`. The git repository, not conversation memory, carries state between
> sessions.
>
> **What it does not own.** End state, capabilities and phases: [`ROADMAP.md`](ROADMAP.md)
> (rows cite a phase; this file never restates the vision). Implementation steps: each
> feature's plan file. Run/test commands: `README.md`.

---

## Project facts

<!-- Per-project values the global workflow skills read instead of hardcoding. Keep the
Fact names exactly as written; use `none` for an optional fact that does not apply.
Machine-local values go in `.claude/skill-config.md`.
Every row ships with a value, never bare template text. Merge strategy, Worktree prefix,
Install command and Port caveats default to the common small-project values below; change
one only when the project differs (`merge`/`rebase`/`n/a` with no PRs; a prefix when features
run in sibling worktrees, which then usually need an Install command and Port caveats).
Verification is stack-specific, e.g. Python venv `cd backend && .venv/bin/pytest`, Node
`npm test`, both `cd backend && .venv/bin/pytest && cd .. && npm test`. Until a test runner
exists, write `pending — set by F<n>` (or `pending — set by the first feature with tests`);
/run-feature stops on a `pending` Verification exactly as on a missing one.
With `Merge strategy` `n/a` (no PRs), `/run-feature` runs its no-PR mode and also requires
`Branch`, `Merge gate` and `Push`, and reads an optional `Backup before edit` (unset means git
is the backup). Add those rows (prose instructions, followed as written); `PR link form`,
`Worktree prefix` and `Port caveats` are then unused. -->

| Fact | Value |
|---|---|
| Verification | `.venv/bin/pytest` |
| PR link form | `[#N](https://github.com/4IRL/discord-github-issue-bot/pull/N)` |
| Merge strategy | `squash` |
| Worktree prefix | `none` |
| Install command | `none` |
| Port caveats | `none` |

---

## Where the work stands

**★FOCUS: `F17` — Track dropdown in the private preview** (runnable; branch `feature/preview-track`).

Phases 1, 1.5 and 2 are complete on `main`, and Phase 3's rating and roadmap placement have
shipped: each report is rated S/M/L/XL (F4) and, on a route with a `project` table, added to its
org Project with Status and Effort set (F6). F17 (the preview's Track pick), Phase 3's last
feature, is runnable. Phase 4 is pre-loaded as F11–F16; F11's live deploy waits on homelab's
`c4i` Docker stage (homelab Phase 3).

<!-- Two or three sentences at most: what is runnable today, what is gated and on what.
Shipped work is git's record (`gh pr list --state merged`), not this file's. -->

### Shortest path to the focus feature

F17's prerequisites have shipped (F6's Project client and per-route Project config, F4's
preview), and Project #2 already has the `Track` field it sets (Assumption 3).

1. **Run F17** (`/run-feature F17`, effort M): the reporter picks the item's Track in the
   private preview, and on File the bot sets it after F6 adds the item.

A live run needs the bot invited with the `bot` and `applications.commands` scopes and View
Channel, Read Message History, Send Messages, Create Public Threads and Send Messages in Threads
on each route's intake channel, plus F5's GitHub App (README § Discord setup and § GitHub App setup; runbook
`docs/SMOKE-TEST.md`, which uses a separate test server).

---

## Feature list (intake record)

> Written only by `/new-feature`; `/run-feature` removes a line at fold-back.

**Next F-ID:** `F18`

- [ ] **F11** (added 2026-10-28): Phase 4: deploy on `c4i` (the Pi 4) as a container with automatic restart, a memory limit, a health check and readable logs, deployed by one documented command over `ssh c4i`; folds in the deferred `--clear-commands` follow-up.
- [ ] **F12** (added 2026-10-28): Phase 4: a report is never filed twice.
- [ ] **F13** (added 2026-10-28): Phase 4: GitHub or Discord errors are reported in the thread with a retry, never silently dropped, and rate limits are respected (automatic retry first, then a Retry button).
- [ ] **F14** (added 2026-10-28): Phase 4 quality of life: a help command.
- [ ] **F15** (added 2026-10-28): Phase 4 quality of life: duplicate-issue hints.
- [ ] **F16** (added 2026-10-28): Phase 4 quality of life: more issue types, declared in the route file rather than in code.
- [ ] **F17** (added 2026-10-28): Track dropdown in the private preview. After F6 files each report onto the route's GitHub Project, let the reporter pick the item's Track in the private preview, alongside F4's S/M/L/XL band buttons, as an optional single-select row in PreviewView (not in the modal); options are the Project's own Track options read through GitHub's API, never a hardcoded list; each route and issue type can configure a pre-selected default by option name in the route file; the pick survives Edit; on File, after F6 adds the item, the bot sets Track (blank with no pick); a failed Track write is handled like F6's failed Project write; no dropdown for a route with no Project or a Project with no Track field; the bot still never sets ID, Order, Lane, Start date, Target date or Days.

---

## Backlog summary (remaining work only)

| Order | Feature | Effort | Depends on | Phase |
|---|---|---|---|---|
| ★ 1 | **F17** — Track dropdown in the private preview **[FOCUS]** | M | F6; couples: F4, F8 | 3 |
| 2 | **F12** — Never file a report twice | M | soft: F6, F17 | 4 |
| 3 | **F13** — Retry and rate limits (auto, then a Retry button) | L | F12; soft: F6 | 4 |
| 4 | **F11** — Deploy on `c4i` | M | homelab#P3 (c4i Docker stage) | 4 |
| 5 | **F14** — Help command | S | couples: F16 | 4 |
| 6 | **F15** — Duplicate-issue hints in the preview | M | soft: F13; couples: F17 | 4 |
| 7 | **F16** — Issue types from the route file | L | soft: F6, F17; couples: F4, F8 | 4 |

<!-- *Depends on* holds dependency edges in the grammar of
/home/rmila/Code/_STRONGHOLD/plans/roadmap.md §3.1 *Dependency edges and `NEXT.md`*, which is
the authority. Address: `<repo>#F<n>` or `<repo>#P<n>`. `<repo>` is the directory name under
`/home/rmila/Code` (`stronghold` for the stronghold); a bare `F<n>`/`P<n>` means this repo;
`P2.5` addresses an inserted phase. `P<n>` exists only for a repo whose ROADMAP has
`### Phase N:` headings (or, with no ROADMAP, a `STATUS.md` with `## Phase N` headings), never
for `stronghold`. Kinds: a bare ref blocks; `soft:` enables (never gates); `couples:` marks a
shared contract (never gates); `cond: <text>` is a manual gate with no address yet; `—` means
none. Parse rules: split the cell on `;` into groups, outside parentheses; a kind prefix at the
start of a group applies to every `,`-separated ref in that group (a prefix anywhere else is
not in the grammar); a `cond:` group is never split on `,`: its whole text, to the next `;`
outside parentheses or the cell end, is one gate; a `(note)` after a ref is ignored by readers
and never split (an IDEAS id goes in a note, e.g. `soft: meals4irl#F3 (X-004)`). Prefixes are
lowercase and exact, never bolded; an unbalanced `(` is reported, not guessed. A ref to a
shipped (folded-back) F-ID stays valid; whether it is done follows the §3.1 done rule. Only the
waiting feature declares an edge. `/new-feature` writes and checks refs.
A legacy `external:` or `**external:**` at the start of a `;` group reads as `cond:`
for that group until backfilled (`F3, F4; external: canary repo` = hard F3, F4 plus a manual
gate), unsplit like `cond:`; any other text not in the grammar is reported, never guessed. A
superseded row (Feature cell struck through with `~~`, *Depends on* starting `**superseded`)
holds its supersession note, not edges; readers skip it. -->

**Effort tally (remaining).** 15 pts (S=1 / M=2 / L=3 / XL=5): Phase 3 2 (F17), Phase 4
13 (F11–F16).

---

## Status ledger

> Maintained by `/run-feature` (`pending` → `in-progress` → `in-review`; a verified-merged
> row is deleted at fold-back). Never hand-delete a row. Git wins any conflict.

| Feature | Status | Branch | PR |
|---|---|---|---|
| **F17 — Track dropdown in the private preview** ★FOCUS | pending | `feature/preview-track` | — |
| **F12 — Never file a report twice** | pending | `feature/idempotent-filing` | — |
| **F13 — Retry and rate limits** | pending | `feature/retry-rate-limits` | — |
| **F11 — Deploy on `c4i`** | pending | `feature/deploy-c4i` | — |
| **F14 — Help command** | pending | `feature/help-command` | — |
| **F15 — Duplicate-issue hints** | pending | `feature/duplicate-hints` | — |
| **F16 — Issue types from the route file** | pending | `feature/route-issue-types` | — |

---

## Baseline: the codebase as it exists today (`main` at PR #24, `c579ab4`)

> The Assumed starting state for every remaining feature unless its section says
> otherwise. Describe what *is*, never what changed.

**Repo.** `4IRL/discord-github-issue-bot`, checked out at
`~/Code/discord-github-issue-bot`. `.claude/settings.json`'s sandbox `allowWrite` still also
lists the pre-rename folder path.

**Stack.** Python 3.12 + discord.py (Gateway client), aiohttp for the GitHub REST API and
PyJWT + cryptography for GitHub App auth, packaged as a Docker image. Clarifying questions are
per-route, per-type data in the route file; triage is documented rules in code
(`issue_bot/complexity.py`, members' copy `docs/COMPLEXITY.md`).

**Domain model.** `issue_bot/issue_type.py`: `IssueType` (`bug`, `feature`), a leaf module;
each type is one slash command and one target label. `issue_bot/complexity.py` (pure, imports
only `issue_type`): `Complexity` StrEnum `S`, `M`, `L`, `XL` in that order;
`rate(issue_type, answers)` starts at `STARTING_BAND` (bug S, feature M) and raises one step at
`RAISE_ONE_AT` (800) and two at `RAISE_TWO_AT` (2000) total stripped answer characters, capped at
XL; `complexity_label(band)` is `complexity:<band>`. `issue_bot/handler.py`: frozen
`IssueCandidate` (type, title, `answers`, `complexity`, author id/name, message id/url, target),
built only by `candidate_from_submission(issue_type, title, answers, complexity, reporter,
message, target)` with the bot's summary message as `message`. `answers` is a tuple of
`(question label, answer)` pairs in question order, blanks included. Member text and names are `repr=False`. Adding or changing a
type's questions is route-file data; a new issue type still needs an `IssueType` member (it is a
slash command and a required label).

**Interfaces.** `issue_bot/config.py`: `Config.from_env(env)` reads, in order, `DISCORD_TOKEN`,
`DISCORD_GUILD_ID`, `UNROUTED_COMMANDS` (`UnroutedCommands` `refuse`/`ignore`), `GITHUB_ORG`
(an owner name), `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY_PATH`
(an `RSAPrivateKey` loaded from that PEM file) and `ROUTES_PATH`; the token and key are
`repr=False`. `Config.routes` is a read-only `Mapping[int, TargetConfig]` keyed by channel id in
file order (frozen again in `__post_init__`), built by `load_routes(path, org)`: a TOML file of
`[routes.<name>]` tables (name `[a-z0-9][a-z0-9_-]*`), each with the `ROUTE_KEYS`
`channel_id`, `channel_name`, `category`, `repo` (`owner/name`, owner equal to `GITHUB_ORG`
case-insensitively), `repo_id`, a `labels` table mapping `bug` and `feature`, `questions`:
one `[[routes.<name>.questions.<type>]]` array per type, each with 1–4 (`MAX_QUESTIONS`) tables of
exactly `label` (1–45 characters, unique within the type), `style` (`short`/`paragraph`) and
`required` (a TOML boolean), and the one optional key `project`: a `[routes.<name>.project]` table
of exactly the `PROJECT_KEYS` `number` (positive int, the Project's number in the repo owner's
org), `status_field`, `status` (the Status option new items get) and `effort_field` (names, not
ids; read by `_route_project`, which returns `None` when the table is absent). It rejects an
empty file, unknown keys, non-positive or non-int ids, blank strings and a `channel_id` two routes
share. `TargetConfig` is `name`, `channel_id`, `channel_name`, `category`, `github_repo`,
`github_repo_id`, `labels` (one per `IssueType`, checked in `__post_init__` and read-only),
`questions` (`Mapping[IssueType, tuple[Question, ...]]`, frozen `Question(label, style: QuestionStyle,
required)`, one entry per type, read-only) and `project` (frozen `ProjectConfig(number,
status_field, status, effort_field)` or `None`; no code default, checked in `__post_init__`).
Every `ConfigError` names the key (env key or `routes.<name>.<key>`), never the value; an
unreadable file or a TOML syntax error is `ROUTES_PATH must name a readable TOML route file`
(no parser text). The 4irl/chores4irl values appear outside tests only in `example.env`
(`GITHUB_ORG=4IRL`) and `example.routes.toml` (one `[routes.c4i]` route, placeholder ids 0, with
a `[routes.c4i.project]` table for Project #2); both are pinned by drift tests in
`tests/test_config.py` (`test_example_routes_shape` also runs `_route_project`). chores4irl's `bug` and `enhancement` labels
exist (checked by F5, 2026-10-18). `DISCORD_GUILD_ID` is also the one guild the slash commands are
synced to.

**Key modules / UI.** Slash-command intake lives in `issue_bot/intake.py`.
`intake_command(issue_type, routes, unrouted, on_candidate, filing_check=None)` builds one guild
command per `IssueType` (`/bug`, `/feature`) and looks the route up with
`routes.get(interaction.channel_id)` at call time (a thread's own id is unrouted). With no route it
sends the private `INTAKE_REFUSAL` (logged `refused …`), or with `UnroutedCommands.IGNORE` returns
without responding (logged `ignored <type> outside this instance's routes interaction_id=…
channel_id=…`). Otherwise it runs `filing_check(target)` within
`FILING_CHECK_TIMEOUT` (2 s): on a `GitHubError`, a timeout or any other error it sends the
private `FILING_UNAVAILABLE_REPLY` and opens no modal. Then it opens `IntakeModal(issue_type,
target, on_candidate, draft=None, preview=None)`: a required Title (`ui.Label`-wrapped
`TextInput`, max 100 = `THREAD_NAME_LIMIT`), then one `TextInput` per
`target.questions[issue_type]` (`answer_inputs`, max `ANSWER_MAX_LENGTH` 4000), prefilled from a
`Draft(title, answers, suggested, complexity, overridden)` when one is given, and a 30-minute
timeout. `on_submit` rates the answers (`suggested`); the band is the previous draft's when that
draft was `overridden` (an override sticks across Edit), else `suggested`. A fresh `on_submit`
defers privately (`thinking=True`), normalizes the title (no letter or digit gets
`BLANK_TITLE_REPLY`) and sends a private preview (`PREVIEW_REPLY`, an embed from
`preview_embed(draft, author_name)`, its description cut past 4096 characters with
`PREVIEW_SHORTENED_NOTE`, plus a `COMPLEXITY_FIELD` field reading `COMPLEXITY_CHOSEN` when
overridden, else `COMPLEXITY_SUGGESTED`) with a `PreviewView`; nothing is posted or filed (logged
`previewed <type> interaction_id=…`). `PreviewView` (fixed `PREVIEW_TIMEOUT` 600 s deadline from
the submit; each button press trims the view's timeout back to it) has S/M/L/XL buttons on row 0
(the current band `primary`, set by `_paint`) and File and Edit on row 1:
- **S/M/L/XL** (`_choose`) sets the band and `overridden=True` before any `await`, then edits the
  preview in place (embed and view only); it logs nothing, and a closed view ignores it;
- **File** sets its close guard before any `await`, acks with `FILING_REPLY` (buttons removed,
  embed kept), then runs `_post_and_file`: post the public summary `**New <type>** from <@id>:
  <escaped title>` with `AllowedMentions.none()` and `suppress_embeds=True` (a missing channel or
  Discord error gets `SUMMARY_FAILED_REPLY` and files nothing), hand `(summary, candidate)` to
  `on_candidate`, confirm privately with `SUBMITTED_REPLY` and the summary link;
- **Edit** reopens the modal prefilled (`preview=` set). That submit answers with
  `response.edit_message` (a new preview and view in place, its own deadline, even after the old
  one expired); a blank title gets `BLANK_TITLE_EDIT_REPLY`; the old view closes only after the
  edit lands;
- expiry edits the preview to `PREVIEW_EXPIRED_REPLY`, buttons removed and embed kept, and files
  nothing (logged `preview expired <type> interaction_id=…`).

`IntakeModal.on_error` and `PreviewView.on_error` share `_report_error`: type, issue type,
`modal`/`preview`, interaction id, status and code (`discord_error_fields`), never `exc_info`,
and a private `INTAKE_ERROR_REPLY`. Every reply failure is caught and logged.

`issue_bot/bot.py`: `IssueBot(discord.Client)` with the guilds intent only (no message
intents, no `on_message`). `IssueBot(config, on_candidate=open_issue_thread,
filing_check=None, project_check=None)` registers the two commands (with `config.routes` and `config.unrouted`) on `IntakeTree` (a `CommandTree` whose `on_error`
logs type, command, interaction id, status and code) with `guild=` always set. `setup_hook`
runs once per process. It syncs the commands to the configured guild (`synced N commands to
guild …`; a failure is logged and the bot keeps running), then runs the startup GitHub check for
each route in file order, one after another (`github access ok for repo_id=…` or
`github access check failed …`; a failure moves on to the next route). After a route's access
check passes and when it has a `project`, `project_check(route)` (`ProjectCheck`, wired to
`GitHubClient.project_fields`) logs `github project ok for repo_id=… project=…` or ERROR
`github project check failed for repo_id=… project=…: <type> stage=… status=…` (type only for a
non-`GitHubError`); it never stops the bot. `on_ready` sanity-checks
every route's channel once per process (Gateway reconnects refire it) with
`channel_problems(channel, route, guild_id)`: a missing channel logs at ERROR, a guild, name or
category mismatch at WARNING (`channel <id> name is …, expected …`); neither stops the bot.
`on_error` logs the exception type and event name only.

Thread helpers live in `issue_bot/threads.py`: `thread_name` (title cut to 100 characters with
`…`) and `open_thread(message, name)`. `open_thread` reuses `message.thread`, else calls
`create_thread(name=…)` (channel-default auto-archive), recovers a 160004 "already created"
with `message.fetch_thread()`, and logs any other `HTTPException` by type, status and code,
returning `None`. `filed_reply(issue, title, complexity, roadmap)` formats the link message,
`Filed as GitHub issue #<number> (complexity <band>): <escaped title>` with the `html_url` on the
next line (`FILED_REPLY`), plus a third line when `roadmap` is `True` (`ROADMAP_ADDED_NOTE`,
"Added to the roadmap.") or `False` (`ROADMAP_FAILED_NOTE`, "Couldn't finish adding it to the
roadmap; the owner can fix it by hand."); `None` (no Project) adds nothing.

The bot needs the `bot` and `applications.commands` invite scopes and View Channel, Read
Message History, Send Messages, Create Public Threads and Send Messages in Threads on each
route's intake channel. Read Message History also covers replying to the summary message. Guild commands persist on Discord after the bot stops; a redeploy re-syncs
them.

GitHub filing: `issue_bot/github.py` `GitHubClient(app_id, installation_id, private_key)`
mints an App JWT, then an installation token scoped to the target's repo id with
`issues: write`, plus `organization_projects: write` only when the route has a `project`, cached
per `(repo id, has project)` until 5 minutes before expiry (dropped on a 401).
`create_issue(target, title, body, labels)` POSTs to `repos/<target.github_repo>/issues` and
returns `FiledIssue(number, html_url, node_id)`, or raises `GitHubError(stage, status)` (`stage` is
`token`, `label`, `issue`, `project`, `project-item` or `project-field`; `status` is None on a
transport failure, 200 for a GraphQL `errors` body or a lookup mismatch).
`project_fields(target)` (GraphQL `PROJECT_FIELDS_QUERY` on `GRAPHQL_URL`) resolves the
route's Project node id, Status field and option and Effort field and one option per
`Complexity` band by name into a frozen `ProjectFields`, cached per `(owner, ProjectConfig)` for
the process (never cached on failure; `ValueError` for a route with no project).
`add_to_project(target, issue, band)` runs `ADD_ITEM_MUTATION` (`addProjectV2ItemById`), then
`SET_FIELDS_MUTATION` (two aliased `updateProjectV2ItemFieldValue`, option ids as GraphQL
`String`), returns the item id, and on a `project-item`/`project-field` failure drops that
route's cached ids before re-raising.
`ensure_label(target, name)` POSTs `repos/<repo>/labels` (`LABEL_COLOR` `c5def5`); a 201 or any
422 counts as "exists" and is cached per (repo id, name) for the process; a 401 drops the cached
token. `check_access(target)` mints (or reuses) the target's token and raises `GitHubError` on
failure; it is the `filing_check`. The module never logs, and the
HTTP transport is injectable (tests pass a fake). `issue_bot/issues.py` builds the issue:
`issue_title` (cut to 256 characters with `…`), `issue_body` (the only body formatter: an
author line ``` Reported by `<author>` in Discord: <summary message url> ```, `---`, then one
`### <label>` section per non-blank answer, or `_No description given._`, with every `@` defanged
by a zero-width space in labels and answers; it calls `render_body(author_name, link, answers)`,
which the preview calls with `PREVIEW_LINK` in place of the URL), `issue_labels` (the target's
label for the type, then `complexity:<band>`) and `file_candidate(github, candidate)`, which
calls `ensure_label` first and, on a `GitHubError` there, logs a WARNING (`could not create
complexity label for <type> message_id=…: <exc type> stage=… status=…`) and files with the type
label only. `place_on_roadmap(github, candidate, issue)` returns `None` for a route with no
project, else awaits `add_to_project` and returns `True` (INFO `added <type> message_id=… to the
roadmap issue=…`) or, on any exception, `False` with a WARNING (`could not add <type>
message_id=… to the roadmap issue=…: <exc type> stage=… status=…`, type only for a
non-`GitHubError`). issues.py's log lines carry no member or response text. `bot.filing_hook(github)` is the
production `on_candidate`: it opens the issue's thread, files the issue even if no thread
opened, and on success logs `filed … issue=<html_url>`, runs `place_on_roadmap` and then posts
`filed_reply(…, roadmap)`; a roadmap failure never undoes or blocks filing. On a
`GitHubError` it logs type, stage and status and posts the fixed `threads.FILING_ERROR_REPLY`
(which says to run the command again). Both posts go through `bot._post_outcome(message,
thread, text, what)`: in the thread, or as a reply to the summary message when no thread
opened, always with `AllowedMentions.none()` and `suppress_embeds=True`. A
`discord.HTTPException` on that post is logged as `could not send <issue link|filing error> …`
by type, status, code and ids. Any other exception reaches `PreviewView.on_error`. `issue_bot/__main__.py` builds the client, wires `filing_hook` and
`filing_check=github.check_access` and `project_check=github.project_fields`, and runs at INFO with `log_handler=None` (discord loggers never at DEBUG).

**Tests & CI.** `.venv/bin/pytest` from the repo root (`pyproject.toml`): 448 tests across
`tests/test_{handler,config,bot,intake,threads,github,issues,complexity,smoke}.py`
(`test_complexity.py` also pins `docs/COMPLEXITY.md`'s thresholds and starting bands), with Discord
interactions and the GitHub transport fully mocked (`make_interaction`, `make_candidate`,
`make_message` fixtures, plus `routes_file`, `route`, `two_route_config` and `write_routes` with
`ONE_ROUTE_TOML`/`TWO_ROUTE_TOML`, both with question sets and no project, and the `PROJECT`
constant with `project_route`/`project_config` fixtures, in `tests/conftest.py`; `fake_github`
has `create_issue`, `ensure_label` and `add_to_project`). Button tests
call a view's button `.callback(...)` directly; `make_interaction` carries `data={}`,
`response.edit_message` and `edit_original_response`. No CI workflow.

**Deployment.** `Dockerfile` (`python:3.12.11-slim`, non-root uid 10001, `STOPSIGNAL SIGINT`,
`python -m issue_bot`), built and run as image `discord-github-issue-bot` (README). The env comes from `.env` (gitignored; `example.env` is the template).
The App private key is mounted read-only at `GITHUB_APP_PRIVATE_KEY_PATH`
(`/run/secrets/github-app-key.pem` in the container) and the route file at `ROUTES_PATH`
(`/run/config/routes.toml`), read once at startup (restart after an edit). README § Run several
instances documents several containers from one image on one bot token, each with its own route
file and `UNROUTED_COMMANDS=ignore`. README's *Upgrading from single-target config* maps the
old `.env` target keys to route fields, and *Upgrading to per-type questions* says existing route
files must add `questions` tables (or the bot exits 2), and *Adding a roadmap Project* gives the
order (grant the App's Organization permission **Projects: Read and write** first, then add the
table) and the revert. The `4irl-issue-bot` App has that permission (F6, 2026-10-29). The owner's live smoke-test runbook is
`docs/SMOKE-TEST.md` (it uses a separate test server, never the live one). The owner's smoke
run of F10 passed before PR #13 merged (2026-10-21). The owner confirmed F7 works on its branch
before PR #15 merged (2026-10-21), F8 before PR #17 merged (2026-10-25), F3 before PR #19
merged (2026-10-26), F4 before PR #21 merged (2026-10-28), and F6 before PR #24 merged
(2026-10-29). Before PR #9 merged, the owner's
run filed issues #1 and #2 in a private scratch repo, torn down on 2026-10-18 (recorded in PR
#9's description).
Not deployed anywhere yet; the target host is `c4i`, the Pi 4 (ROADMAP Phase 4).

### Standing invariants (must not regress)

<!-- Number once, never renumber; strike through a retired one and say where it went. -->

1. No target identifier is a code default:
   `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot`
   prints nothing (F1).
2. Logs and `repr`s never carry member message text or names; modal text and interaction
   payloads are member text too. Logs carry the type, ids (guild, channel, message, thread,
   interaction) and message URL only. A caught Discord API error is logged by exception type,
   HTTP status and Discord error code, never its text (F2, PR #7). `on_error` logs the exception
   type and event name only; the command, modal and preview-view error handlers log type,
   command, modal or view name, interaction id, status and code, never `exc_info` or an
   interaction's repr (F10, PR #13; preview view F3, PR #19; CLAUDE.md rule). A GitHub API error is logged by exception type, request stage and
   HTTP status, never its response text; tokens, JWTs and the App private key are never logged
   (F5, PR #9). The filed issue's URL may be logged.
3. Every config key, in the environment and the route file, is required and validated at startup, except the optional `[routes.<name>.project]` table, whose keys are then all required (F6); a bad config exits with code 2 before connecting (F1; route file F8, PR #17).

### Assumptions to revisit at planning time

1. ~~`!bug` → `bug`, `!feature` → `enhancement`~~ verified by F5 (PR #9); now in Baseline.
2. ~~The roadmap is the existing org Project #2 "chores4irl fold"~~ verified by F6 (PR #24):
   linked to `4IRL/chores4irl`, `Status` has `Todo`, `In Progress`, `Done`, `Effort` has `S`,
   `M`, `L`, `XL`; now in Baseline (`example.routes.toml`'s `[routes.c4i.project]`). The bot
   still leaves `ID`, `Order`, `Lane`, `Start date`, `Target date` and `Days` blank.
3. Project #2 has a `Track` single-select (e.g. an `A · Bugs` option) that the reporter picks in
   the preview (F17, owner's request 2026-10-28). F17 verifies it at planning.

---

## Per-feature session contract

Run `/run-feature <F-ID>`; it owns the contract (cold survey → plan → review → implement
→ commit → verify → PR → fold-back). With `Merge strategy` `n/a`, run the same skills by
hand: `/plan-creator`, `/plan-reviewer`, `/run-plan`, `/git-commit`, then verify.
Parallel features: `/worktree <F-ID>...`.

---

# COMPLETED-FEATURE CONTRACTS STILL IN FORCE

> Only a merged feature's contract that a **remaining** feature builds on, edits or must
> remove.

## F1 — Channel listener and tag parsing · merged (#2)

*Kept because F12 and F13 build on it.*
- `IssueBot(config, on_candidate=...)`: the `on_candidate(message, candidate)` hook is the
  single seam for candidates; F5's `filing_hook`, with F7's link post, plugs in there.
  Don't add a second candidate dispatch path. F3's File button feeds it (`_post_and_file`) with
  the bot's summary message as `message`.
- `IssueCandidate` carries the `TargetConfig` (route) it came from. Filing reads the repo, repo
  id and labels from `candidate.target`, never from a constant.

## F5 — File the issue in 4IRL/chores4irl · merged (#9)

*Kept because F12, F13, F15 and F17 build on it.*
- `issue_bot/issues.py` is the only place an issue body and its labels are formatted
  (`render_body`, which `issue_body` and the preview share; `issue_labels`); later features
  extend it rather than formatting a second body.
- `GitHubClient.create_issue` returns `FiledIssue(number, html_url, node_id)`; the posted link is that
  `html_url`, never a URL built from config. Failures surface only as
  `GitHubError(stage, status)`, which callers log by type, stage and status. Inside
  `file_candidate`, F4's `ensure_label` runs before `create_issue`; its `GitHubError` is caught
  there (a WARNING, then filing with the type label only) and never reaches `filing_hook`.
- `filing_hook(github)` is the one production `on_candidate`: it opens the thread first and
  files even when no thread opened. It runs only after the preview's File press; F6's roadmap
  placement (`place_on_roadmap`) runs after filing, inside this hook.
- Auth is one GitHub App installation (instance-wide `GITHUB_APP_*` config); each token is
  scoped to one route's repo id with `issues: write` (plus F6's `organization_projects: write`
  on a Project route) and cached per `(repo id, has project)`. Every route's repo joins that one
  installation (which is why each must be in `GITHUB_ORG`).

## F4 — Complexity triage (S/M/L/XL) · merged (#21)

*Kept because F17 extends its preview (a Track row beside the band buttons, kept across Edit
like the band override) and F16 must move its per-type `STARTING_BAND` into the route file.*
- `issue_bot.complexity.Complexity` (`S`, `M`, `L`, `XL`) is the one home of the band names.
  F6 sets the Project's `Effort` single-select to the option named `str(band)`, never a second list.
- The band to file is `IssueCandidate.complexity` (the reporter's override if they pressed one,
  else the rules' rating); F6 reads it inside `filing_hook`, never re-rates.
- The label is `complexity_label(band)` (`complexity:<band>`), created on demand by
  `GitHubClient.ensure_label`; a failed label create is non-fatal.
- The thread's link message shows the band and F6's roadmap line
  (`filed_reply(issue, title, complexity, roadmap)`), posted via `_post_outcome`.

## F7 — Post the issue link in the thread · merged (#15)

*Kept because F13 and F17 build on it.*
- `bot._post_outcome(message, thread, text, what)` is the one path that posts a filing
  outcome: in the thread, else as a reply to the summary message, always with
  `AllowedMentions.none()` and `suppress_embeds=True`, logging a Discord failure by type,
  status, code and ids. Any new outcome message reuses it rather than adding a second send path
  (F6's roadmap result is a line of the link message, not a second post). The private preview is not an outcome: it is the interaction's own
  ephemeral response (`followup.send`, `edit_message`, `edit_original_response`).
- The link message is `threads.filed_reply(issue, title, complexity, roadmap)` (F4 added the band, F6 the roadmap line), built from the route's own
  `FiledIssue.html_url`. It is posted after the
  `filed … issue=<url>` log line, so a failed post never hides the issue URL.

## F8 — Multi-target routes and multi-instance deployment · merged (#17)

*Kept because F17 and F16 add route keys, and F11 and F14 must keep commands route-agnostic.*
- A route is a `TargetConfig` whose first field is `name`, its `[routes.<name>]` table name.
  Per-route settings are keys under `[routes.<name>]`, added by extending `ROUTE_KEYS` and
  `load_routes` (as F3's `questions` and F6's `project` did), never a second config file or
  per-route env keys. Every `ROUTE_KEYS` key is required except F6's optional `project` table
  (`_route_project` returns `None` when absent); `test_example_routes_shape` checks each example
  route for exactly `ROUTE_KEYS` (the example's one route has a `project` table), so another
  optional key changes both.
- `Config.routes` (channel id → route, read-only, file order) is the only route lookup, and
  `intake_command(issue_type, routes, unrouted, on_candidate, filing_check=None)` is the
  registration seam: the route is looked up by `interaction.channel_id` at call time, and
  outside the routes the command refuses or, with `UnroutedCommands.IGNORE`, returns without
  responding (in shared-token mode every container receives every command, so a reply would
  race the right container).
- Command payloads stay route-agnostic: every container on one token syncs the same guild
  command set, and the last sync wins. Commands sync only with `guild=`.

## F6 — Add the issue to the roadmap Project · merged (#24)

*Kept because F17 writes through its Project client and config, F12 and F13 must cover its
Project writes, and F16 adds route keys beside its `project` table.*
- A route's Project is its optional `[routes.<name>.project]` table → `TargetConfig.project`
  (`ProjectConfig(number, status_field, status, effort_field)`): names, never ids; the owner is
  the route repo's owner. Ids are looked up by `GitHubClient.project_fields(target)` →
  `ProjectFields` and cached per `(owner, ProjectConfig)`, so **`ProjectConfig` must stay
  hashable** (F17's per-type Track defaults: a tuple of pairs, or `field(hash=False,
  compare=False)`, never a dict).
- `GitHubClient.add_to_project(target, issue, band)` adds the item and sets Status and Effort,
  and returns the item id (for F17's Track write); a `project-item`/`project-field` failure
  drops the route's cached ids before re-raising.
- The failed-write policy: `issues.place_on_roadmap` runs after the `filed …` log inside
  `filing_hook`, catches every exception (WARNING with type, stage and status, or type only)
  and returns `False`, so a Project failure never undoes or blocks filing; the link message then
  ends with `ROADMAP_FAILED_NOTE`. A route without a Project gets no roadmap line and its token
  never asks for `organization_projects`.
- Startup: `IssueBot(project_check=…)` checks each Project route once after its access check
  and never stops the bot.

## Deferred follow-ups (confirmed, unscheduled, no F-ID yet)

<!-- Promote an item with `/new-feature`. -->

- **F9 push-review polish.** The unticked minor to-dos in
  `plans/chore/rename-repo/reviews/push-review-chore-rename-repo.md`, Review 1: restore
  `.claude/settings.json`'s trailing newline (owner edit), stricter zero-count and `ok`
  wording in the plan's Owner checks and a ROADMAP Sequencing reflow (the CLAUDE.md intro
  item was done by F10, PR #13). The "rename F9's title" item was resolved by this
  fold-back. None blocks a remaining feature.
- **F2 push-review polish.** The unticked minor to-dos in
  `plans/feature/issue-thread/reviews/push-review-feature-issue-thread.md`, Review 1: one
  shared API-error log helper with distinct create/fetch/send wording, `format_hint` split
  under 100 columns, a distinct log line when no thread opened, a decision on posting the hint
  into a human-started thread, two test tightenings (101-character name, no false "format
  hint" line after a failed send) and a one-line `candidate_from_message` docstring summary.
  The META-PLAN and PR-description items were resolved by this fold-back and PR #7. None
  blocks a remaining feature. The `format_hint`, hint-posting, human-started-thread, false-hint
  test and `candidate_from_message` items lapsed when F10 removed the tags (PR #13).
- **F2 accepted risk: emoji thread names.** `thread_name` counts Python code points; if a
  `could not open thread … code=50035` ERROR ever appears, count as Discord does.
- **F5 push-review polish.** The unticked minor to-dos in
  `plans/feature/file-issue/reviews/push-review-feature-file-issue.md`, Reviews 1–4: an
  owner decision on replying to unexpected (non-`GitHubError`) filing errors, which a test
  currently pins as reaching `on_error`; title-boundary (256/257) and non-201 2xx tests; a `Literal` stage type and a
  named token-cache entry; whether to keep the redundant `from None` and the `issue_labels`
  wrapper; an empty-author placeholder and a separator assertion in
  `issue_body`'s tests; `example.env`, `FILING_ERROR_REPLY` and `.dockerignore` tidies; and
  `docs/SMOKE-TEST.md` / README runbook tidies (one home for the container-key command, more
  troubleshooting rows). The plan's § Manual checks can be cut to a link to the runbook. None
  blocks a remaining feature. The message-reply fallback with no thread was done by F7
  (PR #15).
- **F7 push-review polish.** The two unticked minor to-dos in
  `plans/feature/post-issue-link/reviews/push-review-feature-post-issue-link.md`, Review 1:
  a `filing_hook` test with a mention/URL title, and a test of the link post on the
  `fetch_thread` (160004) recovery path. Neither blocks a remaining feature.
- **F10 push-review polish.** The unticked minor to-dos in
  `plans/feature/slash-command-intake/reviews/push-review-feature-slash-command-intake.md`,
  Reviews 1–2, include:
  - reuse `discord_error_fields` and collapse the repeated except tails;
  - an on_ready-does-not-sync test;
  - drop the `DD-n` ids from source comments;
  - shorten over-long docstrings and constants;
  - README notes on the Message Content intent and on a slow-GitHub refusal;
  - a private reply from `IntakeTree.on_error`;
  - shield the pre-modal token mint, and give the startup check its own timeout;
  - briefly cache a failed access check;
  - a few test tightenings.

  None blocks a remaining feature.
- **F8 push-review polish.** The unticked minor to-dos in
  `plans/feature/multi-target/reviews/push-review-feature-multi-target.md`, Review 1: drop
  `load_routes`' redundant `seen` map; log the unrouted refuse/ignore line once; name the route in
  the startup access-check log lines; decide whether to split the route-file error into
  "cannot be read" and "is not valid TOML"; and decide whether `Config.__post_init__` checks that
  routes is non-empty and keyed by each route's `channel_id`. None blocks a remaining feature.
- **F3 push-review polish.** The unticked minor to-dos in
  `plans/feature/clarifying-questions/reviews/push-review-feature-clarifying-questions.md`,
  Review 1, include:
  - a `PreviewView.close()` method so `IntakeModal` stops touching `_closed`;
  - splitting `on_submit` into fresh and edit helpers, and one shared "could not send" log helper;
  - a private reply when the first preview send fails, and logging `previewed` only after it lands;
  - answering (or logging) a click on a closed preview;
  - a test that the superseded preview's File does nothing after an Edit submit;
  - deciding where `Question`'s invariants live (loader only, or `__post_init__` too);
  - two small tidies (a single-letter test variable, a precomputed style set).

  None blocks a remaining feature.
- **F3 accepted limits.** Recorded in README *Known limits*: a bot restart leaves an open
  preview's buttons dead (run the command again); a reporter who presses File in one Discord
  client while an Edit modal is open in another can file a second issue (close the duplicate).
  Question labels with control characters are rejected by Discord at modal send, not at startup;
  label uniqueness is case-sensitive (dd-261026-042, -043, -045).
- **F4 push-review polish.** The unticked minor to-dos in
  `plans/feature/complexity-triage/reviews/push-review-feature-complexity-triage.md`, Review 1:
  - name the labels in `file_candidate` instead of indexing `labels[1]` / `labels[:1]`;
  - an end-to-end override → Edit → File test;
  - parametrize the `ensure_label` raise test over 403/404/500;
  - explain or drop `docs/COMPLEXITY.md`'s Points column;
  - a test that `STARTING_BAND` covers every `IssueType`;
  - optional tidies: an explicit step count in `rate()`, loop-built band buttons, a `Draft`
    `__post_init__` check that `overridden or complexity == suggested`.

  None blocks a remaining feature.
- **F4 accepted limits.** Every 422 from the label endpoint counts as "already exists", and
  created labels stay cached until a restart (a label deleted on GitHub is re-created only then).
  A band press racing File, or the old preview's Edit submit, can briefly re-show dead buttons
  (code comments in `PreviewView._choose`; dd-261027-050, -051, -055, -058).
- **F6 push-review polish.** The unticked minor to-dos in
  `plans/feature/roadmap-project/reviews/push-review-feature-roadmap-project.md`, Review 1:
  - assert the posted reply ends with `ROADMAP_ADDED_NOTE` in the filing_hook Project-route
    success test;
  - replace `_project_key`'s bare `assert` with a `ValueError`;
  - rename `_route_project`'s `where_p`;
  - optional: a fixed reason token (`status-field`, `effort-band`, …) on a lookup mismatch in the
    startup log; non-`GitHubError` roadmap failures at ERROR; collapse `_check_project`'s two
    excepts; move `ProjectCheck` beside `FilingCheck`; `effort_option_ids` keyed by `Complexity`.

  The ProjectConfig-hashability item is in F6's kept contract; Review 2's "use the returned item
  id" is F17's. None blocks a remaining feature.
- **F6 accepted limits.** Project field and option ids are cached per process: a field or
  option deleted and re-created on GitHub is picked up after the next failed write (the cache is
  dropped) or a restart. Two first filings at once each run the lookup once (harmless). The
  Projects permission covers every Project in the org; staying off other Projects is procedure
  (README § GitHub App setup).
- **ROADMAP Current-state row 3** (Complexity rating) still reads "not started": its Maintaining
  rule refreshes Current-state rows only at a phase's close-out, which is now F17's fold-back
  (F17 joined Phase 3 on 2026-10-28). That close-out also adds Track to Phase 3's scope bullet.
- **Drop the pre-rename `allowWrite` path.** `.claude/settings.json` still lists
  `/home/rmila/Code/c4i-issue-bot`; removing it is an optional owner edit in its own small
  PR (agents can't write that file).

---

# REMAINING FEATURES

## F17 — Track dropdown in the private preview · Phase 3 · Effort M · (added 2026-10-28)

**Goal.** The reporter picks the Project item's Track in the private preview, and on File the
bot sets that Track after F6 adds the item. Feature-list line F17.

**Rank rationale.** Phase 3's last feature (owner's choice, 2026-10-28): it completes roadmap
placement, so Phase 3 closes at its fold-back, not F6's. It runs right after F6 because it
writes through F6's Project client and per-route Project config.

**Dependencies.** F6; couples: F4, F8. F6 supplies the Project add, the per-route Project
config and the failed-write policy (its Open risk (c)). F4's kept contract supplies
`PreviewView`, its band buttons and the `Draft` override that survives Edit. F8's kept
contract puts the per-route, per-type default under `[routes.<name>]`.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F6 merged. Verify:
- Project #2 has a `Track` single-select (Assumption 3), and F6's config shape for a route's
  Project (`ProjectConfig` names; ids looked up and cached, F6's kept contract).
- `PreviewView` has room for a select row: S/M/L/XL are row 0 and File/Edit row 1 (Discord
  allows 5 rows).

**Expected end state** (repo-checkable):
- `PreviewView` has an optional single-select Track row. Its options are the Project's `Track`
  options read through GitHub's GraphQL API, never a hardcoded list. No row when the route has
  no Project or the Project has no `Track` field.
- The route file can name a default Track option per issue type (e.g. `A · Bugs` for `bug` on
  chores4irl), validated at startup per Standing invariant 3. With no default, nothing is
  pre-selected.
- The pick is carried in `Draft` and survives Edit, as F4's band override does.
- On File, after F6 adds the item, the bot sets `Track` to the pick, or leaves it blank with no
  pick. A failed Track write is handled like F6's failed Project write. The bot never sets
  `ID`, `Order`, `Lane`, `Start date`, `Target date` or `Days`.
- README and `docs/COMPLEXITY.md`'s preview description show the Track row; `example.routes.toml`
  shows a default.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Mocked GraphQL for reading the field's options and for setting the field;
`PreviewView` tests for the row's presence or absence, the default, the pick and the pick kept
across Edit; config tests for the default key.

**Open risks / decisions.** (a) When options are read: at startup (stale until restart, like
the route file) or per preview (one API call per command, inside the 3-second interaction
window). (b) A configured default whose name isn't an option on the Project: a startup error,
a warning or a silent blank. (c) Discord's select is capped at 25 options. (d) Whether the
default lives with the route's `questions` or beside F6's Project keys; a key a route may omit
changes `test_example_routes_shape` (F8's kept contract).

**Session.** `/run-feature F17` on branch `feature/preview-track`; plan at
`plans/feature/preview-track/preview-track.md`.

---

## F12 — Never file a report twice · Phase 4 · Effort M · (added 2026-10-28)

**Goal.** Each report is filed at most once, even after a timeout, a retry or a File press in
a second Discord client. Feature-list line F12.

**Rank rationale.** Phase 4's first runnable item, and a hard prerequisite of F13: retrying
after a timeout that did file the issue would otherwise file it twice (README *Known limits*).

**Dependencies.** soft: F6, F17. After them, the dedup path covers the Project add and
the Track write as well.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F6 and F17 if merged. Verify:
- The issue body's author line already carries the summary message URL (`issue_body`), a
  candidate dedup key.

**Expected end state** (repo-checkable):
- Before creating an issue, filing checks for an existing issue for the same report (e.g. the
  summary message URL or id) and, if one exists, reuses it, posting the existing link.
- The F3 accepted limit (File in one client while an Edit is open in another files twice) is
  closed or narrowed and README *Known limits* updated.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** A repeated filing of the same candidate creates one issue; a timeout
after create then a retry finds the existing issue.

**Open risks / decisions.** (a) Dedup key and lookup: GitHub search (eventually consistent,
with its own rate limit) vs listing recent issues vs a local record (the bot keeps no state
today; homelab Phase 3 backs nothing up for it). (b) Scope of "a report": one summary message.

**Session.** `/run-feature F12` on branch `feature/idempotent-filing`; plan at
`plans/feature/idempotent-filing/idempotent-filing.md`.

---

## F13 — Retry and rate limits · Phase 4 · Effort L · (added 2026-10-28)

**Goal.** GitHub and Discord failures are retried automatically with backoff, rate limits are
respected, and a failure that persists is reported in the thread with a Retry button.
Feature-list line F13.

**Rank rationale.** Phase 4 hardening; needs F12 so a retry can't duplicate an issue.

**Dependencies.** F12; soft: F6. F6's Project writes join the retried calls.

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline** plus F12. Verify:
- `GitHubError(stage, status)` is the only GitHub failure surface; `_post_outcome` is the one
  outcome post path (F7's kept contract).

**Expected end state** (repo-checkable):
- Transient GitHub failures (transport errors, 5xx, 429 and secondary rate limits) are retried
  with bounded backoff, honoring `Retry-After` / `x-ratelimit-reset`; Discord posts likewise.
- After the last attempt, the thread's error post carries a Retry button that re-runs filing
  for that report (idempotently, via F12) and replaces `FILING_ERROR_REPLY`'s "run the command
  again".
- Logging stays within Standing invariant 2.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Backoff and `Retry-After` against the fake transport (no real sleeps);
the Retry button's callback re-files once and is ignored after success.

**Open risks / decisions.** (a) The Retry button must survive a restart (a persistent view
with a `custom_id` that encodes the report, rebuilt from the summary message), or be documented
as dead after one like the preview's. (b) Who may press Retry: the reporter only, or anyone.
(c) Retries must fit the interaction deadlines where an interaction is pending.

**Session.** `/run-feature F13` on branch `feature/retry-rate-limits`; plan at
`plans/feature/retry-rate-limits/retry-rate-limits.md`.

---

## F11 — Deploy on `c4i` · Phase 4 · Effort M · (added 2026-10-28)

**Goal.** The bot runs unattended on `c4i`, the Pi 4 (arm64), as a container with automatic
restart, a memory limit, a health check and readable logs, deployed by one documented command
over `ssh c4i`, with a verified way to clear the commands for a rollback. Feature-list line
F11.

**Rank rationale.** Phase 4's deploy work; ranked after F12 and F13 only because its live run
waits on homelab. Its repo-side work can be planned earlier (ROADMAP *Sequencing rationale*).

**Dependencies.** homelab#P3 (c4i Docker stage). This repo owns the image, its config and the
deploy command. The host side (Docker, the memory ceiling, root-only token and key files) is
homelab's Phase 3 (`homelab/plans/HOST-ROLES.md`).

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline**. Verify:
- homelab's `c4i` Docker stage exists, and where it puts the token and key files.
- The `Dockerfile`'s base image has an arm64 build.

**Expected end state** (repo-checkable):
- An arm64 image (built on `c4i` or cross-built), a compose file (or documented `docker run`)
  with `restart: unless-stopped`, a memory limit, a health check and log rotation, and one
  documented deploy command over `ssh c4i`.
- A `--clear-commands` one-shot (an empty guild sync) for a rollback or retirement, folded in
  from Deferred follow-ups. Until it is verified, removing the app from the server is the
  documented path; the Server Settings → Integrations path didn't list the bot in the owner's
  test (2026-10-21). README *Known limits* is updated.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** `--clear-commands` syncs an empty command set to the configured guild
only (mocked tree); the health signal's logic.

**Open risks / decisions.** (a) The bot has no HTTP port, so the health check needs a signal,
e.g. a heartbeat file touched while the Gateway is connected. (b) Build on the Pi or cross-build
with `buildx`. (c) The live deploy is a live side effect: it needs the owner's go-ahead
(CLAUDE.md). Phase 4's exit (two weeks of real use) is an owner gate after this ships.

**Session.** `/run-feature F11` on branch `feature/deploy-c4i`; plan at
`plans/feature/deploy-c4i/deploy-c4i.md`.

---

## F14 — Help command · Phase 4 · Effort S · (added 2026-10-28)

**Goal.** A member runs a help command and gets a private explanation of how to report: the
route's intake channel, the issue types, the preview and a link to `docs/COMPLEXITY.md`.
Feature-list line F14.

**Rank rationale.** Small quality-of-life addition; independent of the other Phase 4 work.

**Dependencies.** couples: F16. If F16 lands first, help lists the route's configured types.

**Sizing.** unscored (intake estimate S); split check pending.

**Assumed starting state** = **Baseline**.

**Expected end state** (repo-checkable):
- One more guild command (name decided at planning) that replies privately, route-aware, and
  honors `UNROUTED_COMMANDS` like `/bug` and `/feature` (F8's kept contract). Its payload stays
  route-agnostic.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Routed, unrouted-refuse and unrouted-ignore replies.

**Open risks / decisions.** (a) Command name (`/help` may clash with other bots). (b) Whether
help answers outside intake channels, since in shared-token mode only one container should reply.

**Session.** `/run-feature F14` on branch `feature/help-command`; plan at
`plans/feature/help-command/help-command.md`.

---

## F15 — Duplicate-issue hints in the preview · Phase 4 · Effort M · (added 2026-10-28)

**Goal.** The private preview lists a few existing issues in the route's repo whose titles look
like the report's, so the reporter can stop before filing a duplicate. Feature-list line F15.

**Rank rationale.** Quality of life, rule-based (no LLM, ROADMAP *Principles*).

**Dependencies.** soft: F13; couples: F17. The search call should go through F13's
rate-limit handling, and the hints share the preview with F17's Track row.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F13 and F17 if merged.

**Expected end state** (repo-checkable):
- The preview shows up to N likely duplicates (number, title, link) from a GitHub search
  scoped to the route's repo; a search failure shows no hints and never blocks the preview.
- Hint text from GitHub is member text for logging purposes (Standing invariant 2).
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Mocked search results, empty results and a failed search.

**Open risks / decisions.** (a) The match rule (title terms, open issues only) and N.
(b) The search API's own rate limit (30/min) and its time inside the interaction deadline.
(c) The embed space the hints take beside the 4096-character description.

**Session.** `/run-feature F15` on branch `feature/duplicate-hints`; plan at
`plans/feature/duplicate-hints/duplicate-hints.md`.

---

## F16 — Issue types from the route file · Phase 4 · Effort L · (added 2026-10-28)

**Goal.** Issue types (command name, label, questions, starting band) are declared in the route
file, so adding a type is a config change, not code. Feature-list line F16.

**Rank rationale.** Largest Phase 4 item; last because it reshapes `IssueType`, which every
other feature touches.

**Dependencies.** soft: F6, F17; couples: F4, F8. F6 and F17 add route keys first, so the
schema changes once more, not three times concurrently. F4's `STARTING_BAND` is per type, and
F8's commands must stay route-agnostic.

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline** plus F6 and F17. Verify:
- Every use of `IssueType` (commands, labels, questions, `STARTING_BAND`, F17's per-type Track
  default).

**Expected end state** (repo-checkable):
- The type set is read from the route file and validated at startup (Standing invariant 3); the
  hard-coded `IssueType` members become data. Existing route files with `bug` and `feature`
  keep working or get a documented upgrade (README *Upgrading* section).
- Synced commands stay identical across every container on one token (F8's kept contract), so
  the type set is instance-wide, or every route must declare the same set.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Config tests for type declarations; intake tests over a third,
config-declared type.

**Open risks / decisions.** (a) Instance-wide vs per-route types, given one guild command set
per token. (b) Whether `docs/COMPLEXITY.md`'s starting bands become per-route data too (its
drift test pins them today).

**Session.** `/run-feature F16` on branch `feature/route-issue-types`; plan at
`plans/feature/route-issue-types/route-issue-types.md`.

---

## Dependencies & couplings (remaining work)

```
Phase 1:    done       (F1 #2; F9 rename #5; F2 threads #7; F5 filing #9; F10 intake #13; F7 link #15)
Phase 1.5:  done       (F8 routes #17)
Phase 2:    done       (F3 questions + preview #19)
Phase 3:    F4 rating #21 (done)
            F5 ──► ★ F6 ──► F17   (F6 couples F4; F17 couples F4, F8)
Phase 4:    filing track:   (soft: F6, F17) ┄► F12 ──► F13 ┄► F15
            deploy track:   homelab#P3 (c4i Docker stage) ──► F11
            QoL track:      F14 ⇄ F16   (couples; F16 soft after F6, F17)
```

- **Hard chains:** F5 → F6 → F17; F12 → F13; homelab#P3 → F11 (external). F1, F2, F3, F4, F5,
  F7, F8, F9 and F10 have shipped; refs to them stay valid, so F6 is unblocked, and F12, F14,
  F15 and F16 have no unmet hard prerequisite.
- **Soft preferences:** F8 (shipped) before F6, so Project config is per-route from the start.
  F6 and F17 before F12, F13 and F16, so dedup, retry and the type schema cover the Project
  writes and route keys once. F13 before F15, so the search call is rate-limited.
- **Couplings to honor:** F6, F17 and F16 put per-route settings under `[routes.<name>]` (F8's
  kept contract). F4 ↔ F6: both use the same S/M/L/XL band names, one as a label and one as a
  Project field (F4's kept contract). F4 ↔ F17: the Track row sits in F4's `PreviewView` and
  its pick follows the band override's `Draft` pattern. F17 ↔ F15: both add to the private
  preview. F14 ↔ F16: help lists the types F16 makes configurable. F11, F14 and F16 keep the
  synced command set route-agnostic.

---

## History policy

Forward-looking: merged work is pruned by `/run-feature`'s fold-back and `/new-feature`'s
reconcile; git is the history.
