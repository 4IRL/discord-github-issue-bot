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

**★FOCUS: `F10` — Slash-command intake** (runnable; branch `feature/slash-command-intake`).

F1's listener, F2's threads and F5's issue filing are on `main`. F10 and F7 are runnable now
(F10 first, owner's choice 2026-10-18); F8 needs both. F6 is also gated on creating the new
chores4irl roadmap Project.

<!-- Two or three sentences at most: what is runnable today, what is gated and on what.
Shipped work is git's record (`gh pr list --state merged`), not this file's. -->

### Shortest path to the focus feature

F10 has no open prerequisites: F1's `on_candidate` seam, F2's `open_thread` and F5's
`filing_hook` are what its modal submit feeds.

1. **Run F10** (`/run-feature F10`, effort L). It replaces the `!bug`/`!feature` tags with
   `/bug` and `/feature` modals.
2. **Run F7** (effort S) on F10's intake. It completes the Phase 1 skeleton.

A live run needs F1's external setup (Discord application, bot token in `.env`, bot invited;
F10 adds the `applications.commands` invite scope and drops the Message Content intent),
F2's thread permissions (Create Public Threads, Send Messages in Threads) and F5's GitHub
App (README § GitHub App setup; runbook `docs/SMOKE-TEST.md`).

---

## Feature list (intake record)

> Written only by `/new-feature`; `/run-feature` removes a line at fold-back.

**Next F-ID:** `F11`

- [ ] **F3** (added 2026-10-16): In the thread, ask the clarifying questions needed to flesh out the idea (rule-based, per tag). (amended 2026-10-18: the per-tag questions become the fields of F10's modal, then a private preview with File/Edit; no thread conversation.)
- [ ] **F4** (added 2026-10-16): Evaluate the issue's complexity (triage).
- [ ] **F6** (added 2026-10-16): Add the created issue to the chores4irl roadmap (split from "create the issue in the 4IRL/chores4irl GitHub repo and add it to its roadmap").
- [ ] **F7** (added 2026-10-16): Post a direct link to the newly created issue in the same thread.
- [ ] **F8** (added 2026-10-17): Multiple instances of the bot should be deployable: spool up multiple bots, or have multiple listeners that port issues to different repos based on the bot's instantiation settings/parameters; all channels come from the same Discord server and all issues go to repos in the 4IRL GitHub org (both a route table in one process and multi-container deployment).
- [ ] **F10** (added 2026-10-18): Adapt or potentially replace `!bug` and `!feature` tags in Discord messages with slash commands (slash-command options, or a modal popup form for longer structured input); owner's choice: replace the tags outright with `/bug` and `/feature` opening a modal.

---

## Backlog summary (remaining work only)

| Order | Feature | Effort | Depends on | Phase |
|---|---|---|---|---|
| ★ 1 | **F10** — Slash-command intake: `/bug` and `/feature` open a modal **[FOCUS]** | L | F2, F5 | 1 |
| 2 | **F7** — Post the issue link in the thread | S | F2, F5; soft: F10 | 1 |
| 3 | **F8** — Multi-target routes and multi-instance deployment | L | F5, F7, F10 | 1.5 |
| 4 | **F3** — Per-tag modal questions with preview and confirm | M | F5, F10; soft: F8 | 2 |
| 5 | **F4** — Complexity triage (S/M/L/XL) | M | F3 | 3 |
| 6 | **F6** — Add the issue to the chores4irl roadmap Project | M | F5; soft: F8; couples: F4; cond: new chores4irl roadmap Project created (owner-approved) | 3 |

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

**Effort tally (remaining).** 13 pts (S=1 / M=2 / L=3 / XL=5).

---

## Status ledger

> Maintained by `/run-feature` (`pending` → `in-progress` → `in-review`; a verified-merged
> row is deleted at fold-back). Never hand-delete a row. Git wins any conflict.

| Feature | Status | Branch | PR |
|---|---|---|---|
| **F3 — Per-tag modal questions with preview and confirm** | pending | `feature/clarifying-questions` | — |
| **F4 — Complexity triage (S/M/L/XL)** | pending | `feature/complexity-triage` | — |
| **F6 — Add the issue to the chores4irl roadmap Project** | pending | `feature/roadmap-project` | — |
| **F7 — Post the issue link in the thread** | pending | `feature/post-issue-link` | — |
| **F8 — Multi-target routes and multi-instance deployment** | pending | `feature/multi-target` | — |
| **F10 — Slash-command intake** ★FOCUS | pending | `feature/slash-command-intake` | — |

---

## Baseline: the codebase as it exists today (`main` at PR #10, `ba53e2c`)

> The Assumed starting state for every remaining feature unless its section says
> otherwise. Describe what *is*, never what changed.

**Repo.** `4IRL/discord-github-issue-bot`, checked out at
`~/Code/discord-github-issue-bot`. `.claude/settings.json`'s sandbox `allowWrite` still also
lists the pre-rename folder path.

**Stack.** Python 3.12 + discord.py (Gateway client), aiohttp for the GitHub REST API and
PyJWT + cryptography for GitHub App auth, packaged as a Docker image. Clarification and triage
are planned as rule-based templates.

**Domain model.** `issue_bot/tags.py`: `IssueType` (`bug`, `feature`); `parse_tag(text)`
returns `ParsedTag(type, title, body)`, `MalformedTag(type)` (tagged, no usable `Title:`), or
`None` (untagged). Tags are `!bug`/`!feature`, case-insensitive, anywhere in the text, first
tag wins. `issue_bot/handler.py`: frozen `IssueCandidate` (type, title, body, content,
author id/name, message id/url, target). Member text and names are `repr=False`.

**Interfaces.** `issue_bot/config.py`: `Config` (instance-wide: `discord_token`, `guild_id`,
`github_app_id`, `github_installation_id`, and `github_private_key`, an `RSAPrivateKey` loaded
at startup from the PEM file at `GITHUB_APP_PRIVATE_KEY_PATH`; the token and key are
`repr=False`) holds one `TargetConfig` (`channel_id`, `channel_name`, `category`, `github_repo`,
`github_repo_id`, `labels`: one per `IssueType`, checked in `__post_init__` and read-only),
both built by `from_env` with every key required
and validated (`ConfigError`; an unreadable or non-RSA key names only the env key). The env
keys are listed in `example.env`, the only place the 4irl/chores4irl values appear outside
tests. chores4irl's `bug` and `enhancement` labels exist (checked by F5, 2026-10-18).
`candidate_from_message(message, config)`
accepts only new, human, non-webhook default/reply messages in the target channel (thread
messages are dropped). For a tagged message without a usable title it logs the type, message
id and URL (`malformed …`) and returns the `MalformedTag`; otherwise it returns the
`IssueCandidate` or `None`.

**Key modules / UI.** `issue_bot/bot.py`: `IssueBot(discord.Client)` with Message Content
intent. `on_ready` sanity-checks the channel once per process (Gateway reconnects refire
it): a missing channel logs at ERROR, a name/category mismatch at WARNING; neither stops the
bot. `IssueBot(config, on_candidate=open_issue_thread, on_malformed=reply_format_hint)`:
`on_message` hands each candidate to `on_candidate` (default: opens the issue's thread and
logs type, message id, URL and thread id) and each `MalformedTag` to `on_malformed` (default:
opens a `Format help: !<tag>` thread and posts the format hint). Thread helpers live in
`issue_bot/threads.py`: `thread_name` (title cut to 100 characters with `…`), `format_hint`,
and `open_thread(message, name)`, which reuses `message.thread`, else calls
`create_thread(name=…)` (channel-default auto-archive), recovers a 160004 "already created"
with `message.fetch_thread()`, and logs any other `HTTPException` by type, status and code,
returning `None`. The bot needs Create Public Threads and Send Messages in Threads on the
intake channel. `on_error` logs the exception type and event name, plus the message id
for `on_message`.

GitHub filing: `issue_bot/github.py` `GitHubClient(app_id, installation_id, private_key)`
mints an App JWT, then an installation token scoped to the target's repo id with
`issues: write`, cached per repo id until 5 minutes before expiry (dropped on a 401).
`create_issue(target, title, body, labels)` POSTs to `repos/<target.github_repo>/issues` and
returns `FiledIssue(number, html_url)`, or raises `GitHubError(stage, status)` (`stage` is
`token` or `issue`; `status` is None on a transport failure). The module never logs, and the
HTTP transport is injectable (tests pass a fake). `issue_bot/issues.py` builds the issue:
`issue_title` (cut to 256 characters with `…`), `issue_body` (the only body formatter: an
author line ``` Reported by `<author>` in Discord: <message url> ```, `---`, then the member's `Body:` or a
placeholder, with every `@` defanged by a zero-width space), `issue_labels` (the target's
label for the type) and `file_candidate(github, candidate)`. `bot.filing_hook(github)` is the
production `on_candidate`: it opens the issue's thread, files the issue even if no thread
opened, logs `filed … issue=<html_url>` on success (posting nothing in the thread), and on a
`GitHubError` logs type, stage and status and sends the fixed `threads.FILING_ERROR_REPLY` in
the thread. Any other exception reaches `on_error`. `issue_bot/__main__.py` builds the client,
wires `filing_hook`, and runs at INFO with `log_handler=None` (discord loggers never at DEBUG).

**Tests & CI.** `.venv/bin/pytest` from the repo root (`pyproject.toml`): 246 tests across
`tests/test_{tags,handler,config,bot,threads,github,issues,smoke}.py`, with Discord and the
GitHub transport fully mocked. No CI workflow.

**Deployment.** `Dockerfile` (`python:3.12.11-slim`, non-root uid 10001, `STOPSIGNAL SIGINT`,
`python -m issue_bot`), built and run as image `discord-github-issue-bot` (README). The env comes from `.env` (gitignored; `example.env` is the template).
The App private key is mounted read-only at `GITHUB_APP_PRIVATE_KEY_PATH`
(`/run/secrets/github-app-key.pem` in the container). The owner's live smoke-test runbook is
`docs/SMOKE-TEST.md`. Before PR #9 merged, the owner's run filed issues #1 and #2 in a private
scratch repo, torn down on 2026-10-18 (recorded in PR #9's description).
Not deployed anywhere yet.

### Standing invariants (must not regress)

<!-- Number once, never renumber; strike through a retired one and say where it went. -->

1. No target identifier is a code default:
   `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot`
   prints nothing (F1).
2. Logs and `repr`s never carry member message text or names: type, ids (message, thread)
   and message URL only; a caught Discord API error is logged by exception type, HTTP status
   and Discord error code, never its text (F2, PR #7); `on_error` logs the exception type,
   event name and (for `on_message`) the integer message id only (F1, PR #4; CLAUDE.md rule).
   A GitHub API error is logged by exception type, request stage and HTTP status, never its
   response text; tokens, JWTs and the App private key are never logged (F5, PR #9). The
   filed issue's URL may be logged.
3. Every config key is required and validated at startup; a bad config exits with code 2
   before connecting (F1).

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

*Kept because F7, F8 and F10 build on it, and F10 removes its tag path.*
- `IssueBot(config, on_candidate=...)`: the `on_candidate(message, candidate)` hook is the
  single seam for candidates; F5's `filing_hook` plugs in there and F7's link extends it.
  Don't add a second candidate dispatch path (F2's `on_malformed` handles only malformed tags).
  F10's modal submit feeds this same seam, with the bot's summary message as `message`.
- `IssueCandidate` carries the `TargetConfig` it came from. Filing reads the repo, repo id
  and labels from `candidate.target`, never from a constant.
- `candidate_from_message` returns the `MalformedTag` for a tagged message without a usable
  title; `IssueBot`'s `on_malformed` hook (default `reply_format_hint`) answers it. F10
  removes the tag parsing, `MalformedTag` and `on_malformed`.
- `Config` keeps instance-wide values apart from its single `target`; F8 turns `target` into
  a list of routes.

## F2 — Thread per tagged message · merged (#7)

*Kept because F7, F8 and F10 build on it, and F10 removes its format-hint path.*
- The default `on_candidate` (`open_issue_thread`) returns nothing. A hook that replaces or
  wraps it (F5's `filing_hook`, F7's link) gets the thread by calling
  `open_thread(message, thread_name(candidate.title))` again: its duplicate guard returns the
  existing thread instead of creating a second one. F10 opens it on the bot's summary
  message; the `Format help` thread and `format_hint` go away with the tags.
- Caught Discord API errors are logged by exception type, HTTP status and code, never their
  text (Standing invariant 2); new thread sends follow the same pattern as
  `reply_format_hint`.
- The 160004 code and fetch-by-message-id recovery are documentation-derived; the owner's
  duplicate-path check (archived thread via `PartialMessage`, steps in
  `plans/feature/issue-thread/issue-thread.md` § Manual checks) confirms them.

## F5 — File the issue in 4IRL/chores4irl · merged (#9)

*Kept because F3, F6, F7, F8 and F10 build on it.*
- `issue_bot/issues.py` `issue_body` is the only place an issue body is formatted; F3 extends
  it (one section per answered question) rather than formatting a second body.
- `GitHubClient.create_issue` returns `FiledIssue(number, html_url)`; F7 posts that
  `html_url`, never a URL built from config. Failures surface only as
  `GitHubError(stage, status)`, which callers log by type, stage and status.
- `filing_hook(github)` is the one production `on_candidate`: it opens the thread first and
  files even when no thread opened. Today it posts nothing on success and the fixed
  `FILING_ERROR_REPLY` on a `GitHubError`; F7 adds the success message there.
- Auth is one GitHub App installation (instance-wide `GITHUB_APP_*` config); each token is
  scoped to one target repo id with `issues: write` and cached per repo id. F8's extra target
  repos join that installation; F6 widens the token request's `permissions` for Projects.

## Deferred follow-ups (confirmed, unscheduled, no F-ID yet)

<!-- Promote an item with `/new-feature`. -->

- **F9 push-review polish.** The unticked minor to-dos in
  `plans/chore/rename-repo/reviews/push-review-chore-rename-repo.md`, Review 1: restore
  `.claude/settings.json`'s trailing newline (owner edit), stricter zero-count and `ok`
  wording in the plan's Owner checks, a one-sentence CLAUDE.md intro, and a ROADMAP
  Sequencing reflow. The "rename F9's title" item was resolved by this fold-back. None blocks
  a remaining feature.
- **F2 push-review polish.** The unticked minor to-dos in
  `plans/feature/issue-thread/reviews/push-review-feature-issue-thread.md`, Review 1: one
  shared API-error log helper with distinct create/fetch/send wording, `format_hint` split
  under 100 columns, a distinct log line when no thread opened, a decision on posting the hint
  into a human-started thread, two test tightenings (101-character name, no false "format
  hint" line after a failed send) and a one-line `candidate_from_message` docstring summary.
  The META-PLAN and PR-description items were resolved by this fold-back and PR #7. None
  blocks a remaining feature. The `format_hint` and hint-posting items lapse when F10
  removes the tags.
- **F2 accepted risk: emoji thread names.** `thread_name` counts Python code points; if a
  `could not open thread … code=50035` ERROR ever appears, count as Discord does.
- **F5 push-review polish.** The unticked minor to-dos in
  `plans/feature/file-issue/reviews/push-review-feature-file-issue.md`, Reviews 1–4: an
  owner decision on replying to unexpected (non-`GitHubError`) filing errors, which a test
  currently pins as reaching `on_error`; a message-reply fallback when filing fails and no
  thread opened; title-boundary (256/257) and non-201 2xx tests; a `Literal` stage type and a
  named token-cache entry; whether to keep the redundant `from None` and the `issue_labels`
  wrapper; an empty-author placeholder and a separator assertion in
  `issue_body`'s tests; `example.env`, `FILING_ERROR_REPLY` and `.dockerignore` tidies; and
  `docs/SMOKE-TEST.md` / README runbook tidies (one home for the container-key command, more
  troubleshooting rows). The plan's § Manual checks can be cut to a link to the runbook. None
  blocks a remaining feature; F7 may take the no-thread fallback since it touches the same
  hook.
- **Drop the pre-rename `allowWrite` path.** `.claude/settings.json` still lists
  `/home/rmila/Code/c4i-issue-bot`; removing it is an optional owner edit in its own small
  PR (agents can't write that file).

---

# REMAINING FEATURES

## F3 — Per-tag modal questions with preview and confirm · Phase 2 · Effort M · (added 2026-10-16; amended 2026-10-18)

**Goal.** Each tag's questions become the fields of F10's modal: Title plus up to four
per-tag questions (Discord caps a modal at five fields), loaded from a data file. After
submit the reporter gets a private (ephemeral) preview of the issue body with **File** and
**Edit** buttons: File files it, and Edit reopens the modal prefilled. There is no thread
conversation; members can still comment in the thread. Feature-list line F3 (amended
2026-10-18, replacing the one-question-at-a-time thread conversation).

**Rank rationale.** This is Phase 2's whole scope, now built on F10's modal. It changes the
filing path from "file on submit" (F10) to "file after preview".

**Dependencies.** F5, F10; soft: F8. Landing after F8 means the question sets are keyed per
target from the start.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F10's `/bug` and `/feature` modals. Verify:
- F5's issue-body builder exists and is the only place that formats an issue body.
- F10 builds each tag's modal in one place, from `IssueType`.

**Expected end state** (repo-checkable):
- The question sets for each tag live in a data file (for example `questions.yaml`): each
  question has a label, a style (short or paragraph) and a required flag. Loading rejects a
  tag with more than four questions at startup. Adding a tag or a question needs no code
  change.
- The preview is ephemeral, shows the body exactly as `issue_body` formats it, and offers
  File and Edit. An expired preview files nothing and says so.
- The filed issue body has one section per answered question; blank optional answers are
  left out.
- All suites green; Standing invariants untouched (modal answers are never logged).

**Test-suite deltas.** Question-file loading tests (valid, too many questions, missing
label), modal build per tag, preview → File files once, Edit reopens prefilled, timeout
files nothing, body sections.

**Open risks / decisions.** (a) An ephemeral preview's view dies with the process and its
interaction token lasts 15 minutes; recommend a timeout within that and a "submit again"
note, with no persisted conversation state (the old `data/` store is dropped unless
planning finds a need). (b) Prefilled Edit needs `TextInput` default values; confirm the
pinned discord.py supports them. (c) Whether F10's Description field stays as a catch-all
field per tag. (d) Only the reporter answers now; the earlier "any member" answer rule is
replaced by members commenting in the thread.

**Session.** `/run-feature F3` on branch `feature/clarifying-questions`; plan at
`plans/feature/clarifying-questions/clarifying-questions.md`.

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
config. After F8, the Project number and field IDs are per-target config (a target may
have no Project).

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

## F7 — Post the issue link in the thread · Phase 1 · Effort S · (added 2026-10-16)

**Goal.** After F5 files the issue, the bot posts its direct URL (the `html_url` GitHub
returns, e.g. `https://github.com/4IRL/chores4irl/issues/<n>`, never built from a
hardcoded repo) in the message's thread, which completes the Phase 1 skeleton.
Feature-list line F7.

**Rank rationale.** It closes the Phase 1 loop and is tiny once F2 and F5 exist. It runs
after F10 (owner's choice, 2026-10-18) so the link is posted in the thread on the bot's
summary message rather than reworked later.

**Dependencies.** F2, F5; soft: F10.

**Sizing.** unscored (intake estimate S); split check pending.

**Assumed starting state** = **Baseline** plus F2's thread, F5's returned issue and F10's
slash-command intake. Verify:
- F5's client returns the created issue's `html_url`.
- F10's modal submit reaches `filing_hook` through `on_candidate`.

**Expected end state** (repo-checkable):
- The handler test shows one thread message containing the mocked issue URL. A failed
  filing still posts F5's `FILING_ERROR_REPLY` and no link.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** End-to-end handler test (message → thread → mocked issue → link
posted) and a failure-path test.

**Open risks / decisions.** (a) Recommend a short confirmation that includes the issue
number and title, not only the bare URL.

**Session.** `/run-feature F7` on branch `feature/post-issue-link`; plan at
`plans/feature/post-issue-link/post-issue-link.md`.

## F8 — Multi-target routes and multi-instance deployment · Phase 1.5 · Effort L · (added 2026-10-17)

**Goal.** One bot process serves several targets: a route table in a config file maps each
intake channel (all in the configured guild) to its target repo in the 4IRL org, with its
own tag → label map. The same image can also run as several containers, each with its own
route file, and the deployment docs show both. Feature-list line F8.

**Rank rationale.** It comes right after the Phase 1 skeleton (owner's choice, 2026-10-17)
so F3, F4 and F6 build per-target question sets and config from the start instead of being
refactored later. It needs F5's GitHub client, F7's end-to-end flow and F10's
interaction intake to generalize (F10 first, so routes dispatch slash commands from the
start; owner's choice, 2026-10-18).

**Dependencies.** F5, F7, F10.

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline** plus Phase 1 (F1, F2, F5, F7, F10) and F1's
target config object. Verify:
- F1's config has one target object, separate from instance-wide values, and
  `grep -rnE 'chores4irl|969373970' --include='*.py' .` outside `tests/` prints nothing.
- F10's `/bug` and `/feature` interaction intake exists: the commands open their modals,
  and a submit reaches `filing_hook` through `on_candidate`.

**Expected end state** (repo-checkable):
- A route file (format chosen at planning, e.g. YAML or TOML, path from env) lists one or
  more targets: intake channel ID, target repo and repo ID, tag → label map. Secrets stay in
  env, never in the route file. The single-target env config of F1 still works, or is
  migrated with a documented one-route example.
- The handler dispatches each `/bug` or `/feature` interaction by channel ID to its route;
  one in an unrouted channel gets F10's ephemeral refusal. Filing, labels and the posted link use that route's repo.
- Startup validation rejects duplicate channel IDs and a repo outside the configured org,
  and runs F1's name/category sanity check for every route.
- A compose file (or documented `docker run` set) runs two instances from the same image
  with different route files.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Route-file loading and validation tests (empty, duplicate channel,
foreign org), dispatch tests with two mocked routes filing to two mocked repos, and an
unrouted-channel test.

**Open risks / decisions.** (a) Credentials across targets: one GitHub App installed on
each target repo (recommended) versus a credential per route; one Discord bot token per
process. (b) Two containers sharing one bot token both receive every Gateway event; each
must ignore channels outside its own routes, and the docs must warn against overlapping
routes (or recommend one Discord application per container). (c) Per-target question-set
keys for F3 (no persisted state; F3's risk (a) drops its `data/` store), and per-target
Project config for F6, are set here as the contract those features build on. (d) Hot
reload of the route file: recommend restart-only.

**Session.** `/run-feature F8` on branch `feature/multi-target`; plan at
`plans/feature/multi-target/multi-target.md`.

## F10 — Slash-command intake: `/bug` and `/feature` open a modal · Phase 1 · Effort L · (added 2026-10-18)

**Goal.** Members report through `/bug` and `/feature` slash commands in the intake
channel instead of `!bug`/`!feature` message tags, which are removed outright. Each command
opens a modal with a required **Title** and an optional paragraph **Description**. On
submit, the bot posts a public summary message in the intake channel (type, title,
reporter), opens the issue's thread on it, and files the issue through F5's
`filing_hook`. Feature-list line F10.

**Rank rationale.** It is ★FOCUS ahead of F7 (owner's choice, 2026-10-18), so F7's link and
F8's routes are built on the final intake rather than reworked. Discord validates the
modal's fields, which removes F1's `Title:` parsing and F2's format-hint path. It splits
the intake swap out of F3, which keeps the per-tag questions.

**Dependencies.** F2, F5.

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline**. Verify:
- `on_candidate(message, candidate)` is the single candidate seam (F1's kept contract), and
  `filing_hook` opens the thread with `open_thread(message, …)` (F2, F5).

**Expected end state** (repo-checkable):
- The bot registers `/bug` and `/feature` application commands, synced to the configured
  guild only (no global commands), with command names derived from `IssueType`.
- Submitting the modal posts one summary message, opens its thread, and files the issue
  with the reporter and that message's URL in `issue_body`'s author line.
- A command used outside the intake channel gets an ephemeral refusal and files nothing.
- `parse_tag`, `MalformedTag`, `on_malformed`/`reply_format_hint` and `format_hint` are
  gone, `on_message` no longer creates candidates, and the Message Content intent is no
  longer requested; `grep -rnE '!bug|!feature' --include='*.py' issue_bot` prints nothing.
- README's setup covers the `applications.commands` invite scope and drops the Message
  Content intent.
- All suites green; Standing invariants untouched (invariant 2 covers modal text and
  interaction payloads as member text).

**Test-suite deltas.** Mocked `Interaction` tests: the command opens the modal; submit →
summary message → thread → filed issue; a wrong channel is refused; a `GitHubError` still
posts `FILING_ERROR_REPLY`; commands sync to the guild only. The tag-parsing and
format-hint tests are removed.

**Open risks / decisions.** (a) `IssueCandidate`'s message id and URL now point at the bot's
summary message, and the author comes from `interaction.user`; decide whether the summary
mentions the reporter (`<@id>` with mentions suppressed) or names them. (b) The submit
must be acknowledged within 3 seconds: defer ephemerally, then follow up once the summary
is posted. (c) Command sync runs once per process (`setup_hook`), not on every `on_ready`.
(d) `plans/ROADMAP.md` capabilities 1–2 and Phases 1, 1.5 and 2 still describe the
`!tag`/`Title:` intake and a thread conversation; update them (owner-approved) with or
before F10. (e) A five-field modal cap leaves four fields for F3's per-tag questions;
F10's Description field is the slot F3 replaces.

**Session.** `/run-feature F10` on branch `feature/slash-command-intake`; plan at
`plans/feature/slash-command-intake/slash-command-intake.md`.

---

## Dependencies & couplings (remaining work)

```
Phase 1:    ★ F10 ┄┄► F7       (soft; F1 shipped #2; F9 rename #5; F2 threads #7; F5 filing #9)
Phase 1.5:  {F7, F10} ──► F8
Phase 2:    {F5, F10} ──► F3       (soft: after F8)
Phase 3:    F3 ──► F4
            F5 ──► F6   [cond: new roadmap Project] (couples F4; soft: after F8)
```

- **Hard chains:** {F2, F5} → F10, {F2, F5} → F7, {F5, F7, F10} → F8, {F5, F10} → F3 → F4,
  F5 → F6. F1, F2, F5 and F9 have shipped; refs to them stay valid, so F10 and F7 are
  runnable, and {F7, F10} → F8, F10 → F3 → F4 and F6's roadmap-Project gate still wait.
- **Soft preferences:** F10 before F7, so the link is posted on the final intake. F7 before
  F3, so the skeleton is end-to-end usable before the question work. F8 before F3 and F6,
  so question sets and Project config are per-target from the start. F6 could start any
  time after F5 once its Project exists; the ROADMAP keeps it in Phase 3 so the Project
  fields are designed alongside F4.
- **Couplings to honor:** F3 ↔ F5: F3 reuses F5's single issue-body builder rather than
  formatting a second body. F3 ↔ F10: F3's per-tag questions fill F10's modal (five-field
  cap) and replace its Description field. F10 removes F1's tag path and F2's format-hint
  path but keeps the `on_candidate` seam (F1's and F2's kept contracts). F8 turns F1's
  single `TargetConfig` into a list (F1's kept contract) and routes F10's interactions by
  channel. F4 ↔ F6: both use the same S/M/L/XL band names, one as a label and one as a
  Project field.

---

## History policy

Forward-looking: merged work is pruned by `/run-feature`'s fold-back and `/new-feature`'s
reconcile; git is the history.
