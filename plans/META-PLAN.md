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

**★FOCUS: `F4` — Complexity triage (S/M/L/XL)** (runnable; branch `feature/complexity-triage`).

Phases 1, 1.5 and 2 are complete on `main`: each route's `/bug`/`/feature` modal asks that route's
questions, the reporter files from a private preview, and the issue's body has one section per
answer (F3). F4 is runnable now and opens Phase 3. F6 is gated on creating the new chores4irl
roadmap Project.

<!-- Two or three sentences at most: what is runnable today, what is gated and on what.
Shipped work is git's record (`gh pr list --state merged`), not this file's. -->

### Shortest path to the focus feature

F4 has no open prerequisites: F3's answers (`IssueCandidate.answers`) and private preview
(`PreviewView`) are what it builds on.

1. **Run F4** (`/run-feature F4`, effort M). Rules rate each report S/M/L/XL from its answers; the
   preview shows the rating and files it as a label.

A live run needs the bot invited with the `bot` and `applications.commands` scopes and View
Channel, Read Message History, Send Messages, Create Public Threads and Send Messages in Threads
on each route's intake channel, plus F5's GitHub App (README § Discord setup and § GitHub App setup; runbook
`docs/SMOKE-TEST.md`, which uses a separate test server).

---

## Feature list (intake record)

> Written only by `/new-feature`; `/run-feature` removes a line at fold-back.

**Next F-ID:** `F11`

- [ ] **F4** (added 2026-10-16): Evaluate the issue's complexity (triage).
- [ ] **F6** (added 2026-10-16): Add the created issue to the chores4irl roadmap (split from "create the issue in the 4IRL/chores4irl GitHub repo and add it to its roadmap").

---

## Backlog summary (remaining work only)

| Order | Feature | Effort | Depends on | Phase |
|---|---|---|---|---|
| ★ 1 | **F4** — Complexity triage (S/M/L/XL) **[FOCUS]** | M | F3 | 3 |
| 2 | **F6** — Add the issue to the chores4irl roadmap Project | M | F5; soft: F8; couples: F4; cond: new chores4irl roadmap Project created (owner-approved) | 3 |

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

**Effort tally (remaining).** 4 pts (S=1 / M=2 / L=3 / XL=5).

---

## Status ledger

> Maintained by `/run-feature` (`pending` → `in-progress` → `in-review`; a verified-merged
> row is deleted at fold-back). Never hand-delete a row. Git wins any conflict.

| Feature | Status | Branch | PR |
|---|---|---|---|
| **F4 — Complexity triage (S/M/L/XL)** ★FOCUS | in-progress | `feature/complexity-triage` | — |
| **F6 — Add the issue to the chores4irl roadmap Project** | pending | `feature/roadmap-project` | — |

---

## Baseline: the codebase as it exists today (`main` at PR #19, `338bf7b`)

> The Assumed starting state for every remaining feature unless its section says
> otherwise. Describe what *is*, never what changed.

**Repo.** `4IRL/discord-github-issue-bot`, checked out at
`~/Code/discord-github-issue-bot`. `.claude/settings.json`'s sandbox `allowWrite` still also
lists the pre-rename folder path.

**Stack.** Python 3.12 + discord.py (Gateway client), aiohttp for the GitHub REST API and
PyJWT + cryptography for GitHub App auth, packaged as a Docker image. Clarifying questions are
per-route, per-type data in the route file; triage is planned as documented rules.

**Domain model.** `issue_bot/issue_type.py`: `IssueType` (`bug`, `feature`), a leaf module;
each type is one slash command and one target label. `issue_bot/handler.py`: frozen
`IssueCandidate` (type, title, `answers`, author id/name, message id/url, target), built only by
`candidate_from_submission(issue_type, title, answers, reporter, message, target)` with the
bot's summary message as `message`. `answers` is a tuple of `(question label, answer)` pairs in
question order, blanks included. Member text and names are `repr=False`. Adding or changing a
type's questions is route-file data; a new issue type still needs an `IssueType` member (it is a
slash command and a required label).

**Interfaces.** `issue_bot/config.py`: `Config.from_env(env)` reads, in order, `DISCORD_TOKEN`,
`DISCORD_GUILD_ID`, `UNROUTED_COMMANDS` (`UnroutedCommands` `refuse`/`ignore`), `GITHUB_ORG`
(an owner name), `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY_PATH`
(an `RSAPrivateKey` loaded from that PEM file) and `ROUTES_PATH`; the token and key are
`repr=False`. `Config.routes` is a read-only `Mapping[int, TargetConfig]` keyed by channel id in
file order (frozen again in `__post_init__`), built by `load_routes(path, org)`: a TOML file of
`[routes.<name>]` tables (name `[a-z0-9][a-z0-9_-]*`), each with exactly the `ROUTE_KEYS`
`channel_id`, `channel_name`, `category`, `repo` (`owner/name`, owner equal to `GITHUB_ORG`
case-insensitively), `repo_id`, a `labels` table mapping `bug` and `feature`, and `questions`:
one `[[routes.<name>.questions.<type>]]` array per type, each with 1–4 (`MAX_QUESTIONS`) tables of
exactly `label` (1–45 characters, unique within the type), `style` (`short`/`paragraph`) and
`required` (a TOML boolean). It rejects an
empty file, unknown keys, non-positive or non-int ids, blank strings and a `channel_id` two routes
share. `TargetConfig` is `name`, `channel_id`, `channel_name`, `category`, `github_repo`,
`github_repo_id`, `labels` (one per `IssueType`, checked in `__post_init__` and read-only) and
`questions` (`Mapping[IssueType, tuple[Question, ...]]`, frozen `Question(label, style: QuestionStyle,
required)`, one entry per type, read-only).
Every `ConfigError` names the key (env key or `routes.<name>.<key>`), never the value; an
unreadable file or a TOML syntax error is `ROUTES_PATH must name a readable TOML route file`
(no parser text). The 4irl/chores4irl values appear outside tests only in `example.env`
(`GITHUB_ORG=4IRL`) and `example.routes.toml` (one `[routes.c4i]` route, placeholder ids 0); both
are pinned by drift tests in `tests/test_config.py`. chores4irl's `bug` and `enhancement` labels
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
`Draft(title, answers)` when one is given, and a 30-minute timeout. A fresh `on_submit` defers
privately (`thinking=True`), normalizes the title (no letter or digit gets `BLANK_TITLE_REPLY`)
and sends a private preview (`PREVIEW_REPLY`, an embed from `preview_embed`, cut past 4096
characters with `PREVIEW_SHORTENED_NOTE`) with a `PreviewView`; nothing is posted or filed
(logged `previewed <type> interaction_id=…`). `PreviewView` (fixed `PREVIEW_TIMEOUT` 600 s
deadline from the submit; each button press trims the view's timeout back to it):
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
filing_check=None)` registers the two commands (with `config.routes` and `config.unrouted`) on `IntakeTree` (a `CommandTree` whose `on_error`
logs type, command, interaction id, status and code) with `guild=` always set. `setup_hook`
runs once per process. It syncs the commands to the configured guild (`synced N commands to
guild …`; a failure is logged and the bot keeps running), then runs the startup GitHub check for
each route in file order, one after another (`github access ok for repo_id=…` or
`github access check failed …`; a failure moves on to the next route). `on_ready` sanity-checks
every route's channel once per process (Gateway reconnects refire it) with
`channel_problems(channel, route, guild_id)`: a missing channel logs at ERROR, a guild, name or
category mismatch at WARNING (`channel <id> name is …, expected …`); neither stops the bot.
`on_error` logs the exception type and event name only.

Thread helpers live in `issue_bot/threads.py`: `thread_name` (title cut to 100 characters with
`…`) and `open_thread(message, name)`. `open_thread` reuses `message.thread`, else calls
`create_thread(name=…)` (channel-default auto-archive), recovers a 160004 "already created"
with `message.fetch_thread()`, and logs any other `HTTPException` by type, status and code,
returning `None`. `filed_reply(issue, title)` formats the link message,
`Filed as GitHub issue #<number>: <escaped title>` with the `html_url` on the next line
(`FILED_REPLY`).

The bot needs the `bot` and `applications.commands` invite scopes and View Channel, Read
Message History, Send Messages, Create Public Threads and Send Messages in Threads on each
route's intake channel. Read Message History also covers replying to the summary message. Guild commands persist on Discord after the bot stops; a redeploy re-syncs
them.

GitHub filing: `issue_bot/github.py` `GitHubClient(app_id, installation_id, private_key)`
mints an App JWT, then an installation token scoped to the target's repo id with
`issues: write`, cached per repo id until 5 minutes before expiry (dropped on a 401).
`create_issue(target, title, body, labels)` POSTs to `repos/<target.github_repo>/issues` and
returns `FiledIssue(number, html_url)`, or raises `GitHubError(stage, status)` (`stage` is
`token` or `issue`; `status` is None on a transport failure). `check_access(target)` mints (or
reuses) the target's token and raises `GitHubError` on failure; it is the `filing_check`. The module never logs, and the
HTTP transport is injectable (tests pass a fake). `issue_bot/issues.py` builds the issue:
`issue_title` (cut to 256 characters with `…`), `issue_body` (the only body formatter: an
author line ``` Reported by `<author>` in Discord: <summary message url> ```, `---`, then one
`### <label>` section per non-blank answer, or `_No description given._`, with every `@` defanged
by a zero-width space in labels and answers; it calls `render_body(author_name, link, answers)`,
which the preview calls with `PREVIEW_LINK` in place of the URL), `issue_labels` (the target's
label for the type) and `file_candidate(github, candidate)`. `bot.filing_hook(github)` is the
production `on_candidate`: it opens the issue's thread, files the issue even if no thread
opened, and on success logs `filed … issue=<html_url>` and then posts `filed_reply`. On a
`GitHubError` it logs type, stage and status and posts the fixed `threads.FILING_ERROR_REPLY`
(which says to run the command again). Both posts go through `bot._post_outcome(message,
thread, text, what)`: in the thread, or as a reply to the summary message when no thread
opened, always with `AllowedMentions.none()` and `suppress_embeds=True`. A
`discord.HTTPException` on that post is logged as `could not send <issue link|filing error> …`
by type, status, code and ids. Any other exception reaches `PreviewView.on_error`. `issue_bot/__main__.py` builds the client, wires `filing_hook` and
`filing_check=github.check_access`, and runs at INFO with `log_handler=None` (discord loggers never at DEBUG).

**Tests & CI.** `.venv/bin/pytest` from the repo root (`pyproject.toml`): 333 tests across
`tests/test_{handler,config,bot,intake,threads,github,issues,smoke}.py`, with Discord
interactions and the GitHub transport fully mocked (`make_interaction`, `make_candidate`,
`make_message` fixtures, plus `routes_file`, `route`, `two_route_config` and `write_routes` with
`ONE_ROUTE_TOML`/`TWO_ROUTE_TOML`, both with question sets, in `tests/conftest.py`). Button tests
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
files must add `questions` tables (or the bot exits 2). The owner's live smoke-test runbook is
`docs/SMOKE-TEST.md` (it uses a separate test server, never the live one). The owner's smoke
run of F10 passed before PR #13 merged (2026-10-21). The owner confirmed F7 works on its branch
before PR #15 merged (2026-10-21), F8 before PR #17 merged (2026-10-25), and F3 before PR #19
merged (2026-10-26). Before PR #9 merged, the owner's run filed issues #1 and #2 in a private
scratch repo, torn down on 2026-10-18 (recorded in PR #9's description).
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
3. Every config key, in the environment and the route file, is required and validated at
   startup; a bad config exits with code 2 before connecting (F1; route file F8, PR #17).

### Assumptions to revisit at planning time

1. ~~`!bug` → `bug`, `!feature` → `enhancement`~~ verified by F5 (PR #9); now in Baseline.
2. The roadmap is a **new** chores4irl roadmap Project, not the existing org Project #2
   "chores4irl fold" (owner's choice, 2026-10-16). F6 verifies the new Project exists.

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

*Kept because F4 and F6 build on it.*
- `IssueBot(config, on_candidate=...)`: the `on_candidate(message, candidate)` hook is the
  single seam for candidates; F5's `filing_hook`, with F7's link post, plugs in there.
  Don't add a second candidate dispatch path. F3's File button feeds it (`_post_and_file`) with
  the bot's summary message as `message`.
- `IssueCandidate` carries the `TargetConfig` (route) it came from. Filing reads the repo, repo
  id and labels from `candidate.target`, never from a constant.

## F5 — File the issue in 4IRL/chores4irl · merged (#9)

*Kept because F4 and F6 build on it.*
- `issue_bot/issues.py` is the only place an issue body is formatted (`render_body`, which
  `issue_body` and F3's preview share); later features extend it rather than formatting a
  second body.
- `GitHubClient.create_issue` returns `FiledIssue(number, html_url)`; the posted link is that
  `html_url`, never a URL built from config. Failures surface only as
  `GitHubError(stage, status)`, which callers log by type, stage and status.
- `filing_hook(github)` is the one production `on_candidate`: it opens the thread first and
  files even when no thread opened. It runs only after F3's File press; F4's label rides the
  same `create_issue` call and F6 adds roadmap placement after filing, both inside this hook.
- Auth is one GitHub App installation (instance-wide `GITHUB_APP_*` config); each token is
  scoped to one route's repo id with `issues: write` and cached per repo id. Every route's repo
  joins that one installation (which is why each must be in `GITHUB_ORG`); F6 widens the token
  request's `permissions` for Projects.

## F3 — Per-tag modal questions with preview and confirm · merged (#19)

*Kept because F4 builds on it.*
- `PreviewView` (issue_bot/intake.py) is the one pre-filing step: F4 shows its rating and the
  reporter's override there, before File. The preview body comes from `preview_embed`, i.e.
  `issues.render_body` with `PREVIEW_LINK`, so preview and filed body never diverge.
- The reporter's answers reach filing as `IssueCandidate.answers` (`(label, answer)` pairs in
  question order); a `Draft(title, answers)` carries them between the modal, the preview and
  Edit. Both are `repr=False` member text.
- The modal is full at Title plus four questions (Discord's five-field cap), so F4 adds no modal
  field; its override lives in the preview.

## F7 — Post the issue link in the thread · merged (#15)

*Kept because F6 builds on it.*
- `bot._post_outcome(message, thread, text, what)` is the one path that posts a filing
  outcome: in the thread, else as a reply to the summary message, always with
  `AllowedMentions.none()` and `suppress_embeds=True`, logging a Discord failure by type,
  status, code and ids. Any new outcome message (e.g. F6's roadmap result) reuses it rather than
  adding a second send path. F3's private preview is not an outcome: it is the interaction's own
  ephemeral response (`followup.send`, `edit_message`, `edit_original_response`).
- The link message is `threads.filed_reply(issue, title)`, built from the route's own
  `FiledIssue.html_url`. It is posted after the
  `filed … issue=<url>` log line, so a failed post never hides the issue URL.

## F8 — Multi-target routes and multi-instance deployment · merged (#17)

*Kept because F6 builds on it.*
- A route is a `TargetConfig` whose first field is `name`, its `[routes.<name>]` table name. F6
  keys its per-route Project config off `route.name`, adding its own keys under
  `[routes.<name>]` by extending `ROUTE_KEYS` and `load_routes` (as F3's `questions` did), never
  a second config file or per-route env keys. Today every `ROUTE_KEYS` key is required and
  `test_example_routes_shape` checks each route for exactly that set; a key a route may omit
  (F6: a route with no Project) changes both.
- `Config.routes` (channel id → route, read-only, file order) is the only route lookup, and
  `intake_command(issue_type, routes, unrouted, on_candidate, filing_check=None)` is the
  registration seam: the route is looked up by `interaction.channel_id` at call time, and
  outside the routes the command refuses or, with `UnroutedCommands.IGNORE`, returns without
  responding (in shared-token mode every container receives every command, so a reply would
  race the right container).
- Command payloads stay route-agnostic: every container on one token syncs the same guild
  command set, and the last sync wins. Commands sync only with `guild=`.

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
- **`--clear-commands`.** A one-shot empty guild sync for a rollback or retirement. Until then,
  removing `/bug` and `/feature` from a server means an empty sync for that guild or removing
  the app from the server; neither is verified (the Server Settings → Integrations path didn't
  list the bot in the owner's test, 2026-10-21).
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
- **Drop the pre-rename `allowWrite` path.** `.claude/settings.json` still lists
  `/home/rmila/Code/c4i-issue-bot`; removing it is an optional owner edit in its own small
  PR (agents can't write that file).

---

# REMAINING FEATURES

## F4 — Complexity triage (S/M/L/XL) · Phase 3 · Effort M · (added 2026-10-16)

**Goal.** From the tag and F3's modal answers, documented rules assign an S/M/L/XL
complexity (S=1, M=2, L=3, XL=5 points). The rating appears in F3's private preview, where
the reporter can override it before filing, and it is filed as a `complexity:<band>` label.
Feature-list line F4.

**Rank rationale.** It reads F3's answers, so it can't come earlier.

**Dependencies.** F3.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F3's modal answers and preview. Verify:
- F3's preview step exists and is where the rating is shown.

**Expected end state** (repo-checkable):
- The rating rules are data or one documented module, and members can read them (linked
  from a help reply or the README).
- Filed issues carry exactly one `complexity:S|M|L|XL` label, created if it doesn't exist.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Rule unit tests for each band, plus override tests.

**Open risks / decisions.** (a) The owner sets the rules themselves (which answers raise
the band); draft them at planning for approval. (b) Creating labels needs the
issues/metadata write permission on chores4irl. (c) F3's preview is ephemeral, so only the
reporter overrides before filing; other members change the label on GitHub afterwards.

**Session.** `/run-feature F4` on branch `feature/complexity-triage`; plan at
`plans/feature/complexity-triage/complexity-triage.md`.

## F6 — Add the issue to the chores4irl roadmap Project · Phase 3 · Effort M · (added 2026-10-16)

**Goal.** Each filed issue is added to the new chores4irl roadmap Project (GitHub Projects
v2), with its Status set and its complexity field matching F4's rating.
Feature-list line F6.

**Rank rationale.** Phase 3. It's blocked by the Project, which doesn't exist yet, and its
complexity field shares a contract with F4.

**Dependencies.** F5; soft: F8; couples: F4; cond: new chores4irl roadmap Project created
(owner-approved). The gate is checked by finding the Project in
`gh api graphql` `organization(login:"4IRL"){projectsV2}` and recording its number in
config. Per F8's kept contract, the Project number and field IDs are per-route config under
`[routes.<name>]` (a route may have no Project).

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F5's GitHub client. Verify:
- The new roadmap Project exists and is linked to chores4irl (Assumption 2).

**Expected end state** (repo-checkable):
- The Project number and field IDs are config, never hardcoded.
- Filing adds the issue to the Project and sets Status (and, once F4 has merged, the
  complexity field), with all GraphQL calls mocked in tests.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** GraphQL mutation tests (add item, set single-select field) against a
mocked transport.

**Open risks / decisions.** (a) Org Projects need the `organization_projects` write
permission (App) or a classic `project` scope; this widens F5's auth, so confirm at
planning. (b) The Project's own fields (Status values, a Complexity single-select with
S/M/L/XL) are designed when it is created.

**Session.** `/run-feature F6` on branch `feature/roadmap-project`; plan at
`plans/feature/roadmap-project/roadmap-project.md`.

---

## Dependencies & couplings (remaining work)

```
Phase 1:    done       (F1 #2; F9 rename #5; F2 threads #7; F5 filing #9; F10 intake #13; F7 link #15)
Phase 1.5:  done       (F8 routes #17)
Phase 2:    done       (F3 questions + preview #19)
Phase 3:    F3 ──► ★ F4
            F5 ──► F6   [cond: new roadmap Project] (couples F4; soft: after F8)
```

- **Hard chains:** F3 → F4, F5 → F6. F1, F2, F3, F5, F7, F8, F9 and F10 have shipped; refs to
  them stay valid, so F4 is runnable and F6 waits on its roadmap-Project gate.
- **Soft preferences:** F8 (shipped) before F6, so Project config is per-route from the start.
  F6 could start any time after F5 once its Project exists; the ROADMAP keeps it in Phase 3 so
  the Project fields are designed alongside F4.
- **Couplings to honor:** F4 ↔ F3: F4 reads `IssueCandidate.answers` and shows its rating in
  F3's `PreviewView` (F3's kept contract). F6 puts its per-route settings under `[routes.<name>]`
  (F8's kept contract). F4 ↔ F6: both use the same S/M/L/XL band names, one as a label and one
  as a Project field.

---

## History policy

Forward-looking: merged work is pruned by `/run-feature`'s fold-back and `/new-feature`'s
reconcile; git is the history.
