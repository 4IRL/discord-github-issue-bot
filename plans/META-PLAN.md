# META-PLAN — c4i-issue-bot feature rollout

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
| PR link form | `[#N](https://github.com/4IRL/c4i-issue-bot/pull/N)` |
| Merge strategy | `squash` |
| Worktree prefix | `none` |
| Install command | `none` |
| Port caveats | `none` |

---

## Where the work stands

**★FOCUS: `F9` — Rename to discord-github-issue-management-bot** (blocked on F1's merge;
branch `chore/rename-repo`).

F1 is built and in review ([#2](https://github.com/4IRL/c4i-issue-bot/pull/2)); `main` is
still the scaffold. F9 is pulled ahead of the rest of Phase 1 (owner's choice, 2026-10-17) so
the next `/stronghold-sweep` indexes the project under its new name and portable function.
F6 is additionally gated on creating the new chores4irl roadmap Project.

<!-- Two or three sentences at most: what is runnable today, what is gated and on what.
Shipped work is git's record (`gh pr list --state merged`), not this file's. -->

### Shortest path to the focus feature

1. **Merge F1** ([#2](https://github.com/4IRL/c4i-issue-bot/pull/2)) and fold it back
   (`/run-feature F1`). That is F9's only hard prerequisite; F1 already created the package
   under the generic name `issue_bot`, so nothing gets renamed twice.
2. **Run F9** (`/run-feature F9`, effort M). In-repo: docs, titles, *PR link form*, image
   name, and README/ROADMAP describing the portable function. Owner steps: the GitHub repo
   rename, the local folder move, `.claude/settings.json` and `.claude/skill-config.md`
   (agent sessions can't write these), and the Claude project-history directory move.
3. **Then run `/stronghold-sweep`** from `~/Code`, which re-indexes the project under the new
   name.

After F9, the Phase 1 skeleton resumes: F2 and F5 (independent of each other), then F7. F1's
external setup (Discord application, bot token in `.env`, Message Content intent, bot
invited) is only needed for a live run, not for F9.

---

## Feature list (intake record)

> Written only by `/new-feature`; `/run-feature` removes a line at fold-back.

**Next F-ID:** `F10`

- [ ] **F1** (added 2026-10-16): Listen to the 'c4i-github-issues' channel in the 'C4I' category of the 4irl server and parse messages from any member for a type tag such as #feature or #bug, ignoring untagged messages. (amended 2026-10-17: portability, "the resulting Discord bot should have readily tunable parameters to easily adjust its pointed intake Discord channel and its pointed output GitHub repo … able to plug into different endpoints, not just the currently planned for chores4irl"; per-target values live in one target config object with no chores4irl defaults in code, and the package takes the new generic name.) (amended 2026-10-17: structured messages, "require users structure their message for easier parsing by the bot … a diff block for issue title and body"; a tagged message carries a required one-line `Title:` and an optional multi-line `Body:`, and one without a usable `Title:` is dropped with an ids-only log line.) (amended 2026-10-17: the tag prefix is `!` (`!bug`, `!feature`), not `#`, because `#` triggers Discord's channel autocomplete.)
- [ ] **F2** (added 2026-10-16): For each tagged message, create a thread for the issue.
- [ ] **F3** (added 2026-10-16): In the thread, ask the clarifying questions needed to flesh out the idea (rule-based, per tag).
- [ ] **F4** (added 2026-10-16): Evaluate the issue's complexity (triage).
- [ ] **F5** (added 2026-10-16): Create the issue in the 4IRL/chores4irl GitHub repo (split from "create the issue in the 4IRL/chores4irl GitHub repo and add it to its roadmap").
- [ ] **F6** (added 2026-10-16): Add the created issue to the chores4irl roadmap (split from "create the issue in the 4IRL/chores4irl GitHub repo and add it to its roadmap").
- [ ] **F7** (added 2026-10-16): Post a direct link to the newly created issue in the same thread.
- [ ] **F8** (added 2026-10-17): Multiple instances of the bot should be deployable: spool up multiple bots, or have multiple listeners that port issues to different repos based on the bot's instantiation settings/parameters; all channels come from the same Discord server and all issues go to repos in the 4IRL GitHub org (both a route table in one process and multi-container deployment).
- [ ] **F9** (added 2026-10-17): Rename the repo to reflect its portability: c4i-issue-bot → discord-github-issue-management-bot (GitHub repo, local folder, docs and project facts; the Python package already takes the generic name in F1) (amended 2026-10-17: made ★FOCUS ahead of the rest of Phase 1 so the next `/stronghold-sweep` indexes the project under its new name; scope adds README/ROADMAP describing the portable function.)

---

## Backlog summary (remaining work only)

| Order | Feature | Effort | Depends on | Phase |
|---|---|---|---|---|
| 1 | **F1** — Channel listener and tag parsing (in review) | L | — | 1 |
| ★ 2 | **F9** — Rename to discord-github-issue-management-bot **[FOCUS]** | M | F1 | 1.5 |
| 3 | **F2** — Thread per tagged message | S | F1 | 1 |
| 4 | **F5** — File the issue in 4IRL/chores4irl | M | F1 | 1 |
| 5 | **F7** — Post the issue link in the thread | S | F2, F5 | 1 |
| 6 | **F8** — Multi-target routes and multi-instance deployment | L | F5, F7 | 1.5 |
| 7 | **F3** — Rule-based clarifying questions | L | F2, F5; soft: F8 | 2 |
| 8 | **F4** — Complexity triage (S/M/L/XL) | M | F3 | 3 |
| 9 | **F6** — Add the issue to the chores4irl roadmap Project | M | F5; soft: F8; couples: F4; cond: new chores4irl roadmap Project created (owner-approved) | 3 |

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

**Effort tally (remaining).** 19 pts (S=1 / M=2 / L=3 / XL=5).

---

## Status ledger

> Maintained by `/run-feature` (`pending` → `in-progress` → `in-review`; a verified-merged
> row is deleted at fold-back). Never hand-delete a row. Git wins any conflict.

| Feature | Status | Branch | PR |
|---|---|---|---|
| **F1 — Channel listener and tag parsing** | in-review | `feature/channel-listener` | [#2](https://github.com/4IRL/c4i-issue-bot/pull/2) |
| **F2 — Thread per tagged message** | pending | `feature/issue-thread` | — |
| **F3 — Rule-based clarifying questions** | pending | `feature/clarifying-questions` | — |
| **F4 — Complexity triage (S/M/L/XL)** | pending | `feature/complexity-triage` | — |
| **F5 — File the issue in 4IRL/chores4irl** | pending | `feature/file-issue` | — |
| **F6 — Add the issue to the chores4irl roadmap Project** | pending | `feature/roadmap-project` | — |
| **F7 — Post the issue link in the thread** | pending | `feature/post-issue-link` | — |
| **F8 — Multi-target routes and multi-instance deployment** | pending | `feature/multi-target` | — |
| **F9 — Rename to discord-github-issue-management-bot** ★FOCUS | pending | `chore/rename-repo` | — |

---

## Baseline: the codebase as it exists today (`main` at the root (scaffold) commit)

> The Assumed starting state for every remaining feature unless its section says
> otherwise. Describe what *is*, never what changed.

**Stack.** Python 3 + discord.py, a GitHub REST/GraphQL client, rule-based clarification
templates, packaged as a Docker container (chosen at scaffold; no code yet).

**Domain model.** None yet.

**Interfaces.** None yet.

**Key modules / UI.** None yet.

**Tests & CI.** None yet.

**Deployment.** None yet.

### Standing invariants (must not regress)

<!-- Number once, never renumber; strike through a retired one and say where it went. -->

None yet.

### Assumptions to revisit at planning time

1. `!bug` maps to chores4irl's existing `bug` label and `!feature` to its existing
   `enhancement` label (owner's choice, 2026-10-16); F5 verifies both still exist.
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

None yet.

## Deferred follow-ups (confirmed, unscheduled, no F-ID yet)

<!-- Promote an item with `/new-feature`. -->

None yet.

---

# REMAINING FEATURES

## F1 — Channel listener and tag parsing · Phase 1 · Effort L · (added 2026-10-16)

**Goal.** The bot runs, connects to the Discord Gateway, listens only to the configured
channel, and turns a tagged message into a parsed issue candidate (type, title, author,
message link); untagged, bot and other-channel messages are ignored. Everything that names
an intake channel or output repo is configuration, so the same code can point at any
channel in the server and any repo in the 4IRL org (amended 2026-10-17, portability).
Feature-list line F1.

**Rank rationale.** Every other feature consumes its parsed candidate and runtime, so it goes
first. It also stands up the project's code skeleton: package layout, config, Docker image
and the pytest harness that sets META-PLAN's Verification. Portability is folded in here
because the config shape and package name are cheapest to get right before any code exists.

**Dependencies.** —

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline**. Verify:
- `git ls-files` lists only the scaffold files (no `*.py`, no `Dockerfile`).

**Expected end state** (repo-checkable):
- The guild ID, category, channel and target repo are read from config/env, not hardcoded.
  Per-target values (intake channel ID, channel name/category for the sanity check, target
  repo, repo ID, tag → label map) sit in one target config object, separate from
  instance-wide values (guild, token), so F8 can turn one target into a list. No
  chores4irl- or 4irl-specific literal is a code default:
  `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' .`
  outside `tests/` prints nothing; the chores4irl values appear only in a documented example
  config (e.g. `.env.example` key names plus a non-secret example target file) and test
  fixtures.
- The Python package has the new generic name (chosen at planning to match F9's repo name,
  e.g. `issue_bot`), not `c4i_issue_bot`.
- A pure tag parser recognizes `!bug` and `!feature` (case-insensitive, anywhere in the
  text). It returns the type with the `Title:` (required, one line) and `Body:` (optional,
  multi-line) fields, tags stripped; a malformed result for a tagged message with no usable
  `Title:`; or nothing for untagged text (amended 2026-10-17). Unit tests use the
  ROADMAP's two acceptance examples.
- A `Dockerfile` builds an image that starts the bot. `README.md` documents the `.env` keys
  by name only.
- `.venv/bin/pytest` is green. META-PLAN's Verification row and CLAUDE.md's Test command
  are set.
- All suites green; Standing invariants none yet.

**Test-suite deltas.** New: parser unit tests, and a message-handler test with a mocked
Discord client (channel filter, bot-author filter, untagged message ignored).

**Open risks / decisions.** (a) Match the channel by ID or by name + category: recommend ID
from config, with name/category used only in a startup sanity check. (b) Tag parsing:
recommend a recognized tag anywhere in the message, with the first tag winning if there are
several; confirm at planning. (c) Edited messages: recommend ignoring them (only new
messages are captured). (d) Requires the privileged Message Content intent. (e) The F1 plan
on `feature/channel-listener` (written before the 2026-10-17 amendment) uses
`c4i_issue_bot/` and `DEFAULT_*` chores4irl constants in `config.py`; revise it (package
name, target object, no target defaults) and re-review before implementing.

**Session.** `/run-feature F1` on branch `feature/channel-listener`; plan at
`plans/feature/channel-listener/channel-listener.md`.

## F2 — Thread per tagged message · Phase 1 · Effort S · (added 2026-10-16)

**Goal.** For each parsed candidate, the bot starts a thread on the original message, named
from the title. All later conversation and the final link go there. Feature-list line F2.

**Rank rationale.** It's the cheapest step after F1, and F3 and F7 both need a thread.

**Dependencies.** F1.

**Sizing.** unscored (intake estimate S); split check pending.

**Assumed starting state** = **Baseline** plus F1's listener and candidate type. Verify:
- F1's handler and parser exist and their tests pass.

**Expected end state** (repo-checkable):
- A tagged message triggers exactly one `create_thread` on that message (mocked in tests).
  The thread name is the title truncated to Discord's 100-character limit.
- A message that already has a thread doesn't get a second one.
- A tagged message that F1 drops as malformed (no usable `Title:` line) gets a thread reply
  with the expected `!tag` / `Title:` / `Body:` format, and no candidate.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Handler tests for thread creation, name truncation, the
no-duplicate guard and the malformed-message format hint.

**Open risks / decisions.** (a) Needs the Create Public Threads and Send Messages in Threads
permissions. (b) Thread auto-archive duration: recommend the channel default.

**Session.** `/run-feature F2` on branch `feature/issue-thread`; plan at
`plans/feature/issue-thread/issue-thread.md`.

## F3 — Rule-based clarifying questions · Phase 2 · Effort L · (added 2026-10-16)

**Goal.** In the thread, the bot asks the questions for that tag one at a time, records
answers from any member, and supports skip, cancel and file-now. It previews the issue body
and files on confirmation. Feature-list line F3.

**Rank rationale.** This is Phase 2's whole scope. It changes the filing path from "file
immediately" (F5) to "file after the conversation".

**Dependencies.** F2, F5; soft: F8. Landing after F8 means the question sets and
conversation state are keyed per target from the start.

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline** plus F2's thread and F5's filing call. Verify:
- F5's issue-body builder exists and is the only place that formats an issue body.

**Expected end state** (repo-checkable):
- The question sets for each tag live in a data file (for example `questions.yaml`).
  Adding a tag or a question needs no code change.
- Conversation state is persisted under `data/` and survives a restart. An idle thread
  times out with a note.
- The filed issue body has one section per answered question.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Conversation state-machine tests (happy path, skip, cancel, timeout,
restart resume), plus tests that the question file loads.

**Open risks / decisions.** (a) State store: recommend a SQLite file under `data/`, which is
already gitignored and claudeignored. (b) Answer attribution: whether to accept replies from
any member or only the author; the owner said "any member". (c) Likely split candidate
(state machine vs persistence) at sizing.

**Session.** `/run-feature F3` on branch `feature/clarifying-questions`; plan at
`plans/feature/clarifying-questions/clarifying-questions.md`.

## F4 — Complexity triage (S/M/L/XL) · Phase 3 · Effort M · (added 2026-10-16)

**Goal.** From the tag and F3's answers, documented rules assign an S/M/L/XL complexity
(S=1, M=2, L=3, XL=5 points). The rating appears in the preview, members can override it,
and it is filed as a `complexity:<band>` label. Feature-list line F4.

**Rank rationale.** It reads F3's answers, so it can't come earlier.

**Dependencies.** F3.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F3's conversation and answers. Verify:
- F3's preview step exists and is where the rating is shown.

**Expected end state** (repo-checkable):
- The rating rules are data or one documented module, and members can read them (linked
  from a help reply or the README).
- Filed issues carry exactly one `complexity:S|M|L|XL` label, created if it doesn't exist.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Rule unit tests for each band, plus override tests.

**Open risks / decisions.** (a) The owner sets the rules themselves (which answers raise
the band); draft them at planning for approval. (b) Creating labels needs the
issues/metadata write permission on chores4irl.

**Session.** `/run-feature F4` on branch `feature/complexity-triage`; plan at
`plans/feature/complexity-triage/complexity-triage.md`.

## F5 — File the issue in 4IRL/chores4irl · Phase 1 · Effort M · (added 2026-10-16)

**Goal.** The bot creates a GitHub issue in the configured target repo (chores4irl in the
example config; no code default, per F1's 2026-10-17 portability amendment) from the
candidate. The title is the message's `Title:` field; the body holds its `Body:` field,
the Discord author and a link to the message; the type label is `bug` or `enhancement`.
Feature-list line F5.

**Rank rationale.** It's the core of the Phase 1 skeleton and proves GitHub auth early. It
needs only F1, so it can run alongside F2.

**Dependencies.** F1.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F1's candidate type. Verify:
- `gh api repos/4IRL/chores4irl/labels/bug` and `.../labels/enhancement` both return 200
  (Assumption 1).

**Expected end state** (repo-checkable):
- One GitHub client module owns auth and issue creation. Tests mock it, and no test calls
  the live API (CLAUDE.md rule).
- The type → label mapping is config (`bug→bug`, `feature→enhancement`).
- One issue-body builder function owns body formatting (F3 extends it).
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Client tests against a mocked HTTP transport (success, auth failure,
422), plus label-mapping tests.

**Open risks / decisions.** (a) Auth: a GitHub App installed only on chores4irl
(recommended: short-lived tokens and a bot identity on issues, and adding a target repo
later is one more installation repo, which suits F8) or a fine-grained PAT with Issues
read/write. The client takes the repo from the target config, never a constant. (b) What the bot does with the message if GitHub rejects the issue;
full retry is Phase 4, so recommend a visible error reply for now.

**Session.** `/run-feature F5` on branch `feature/file-issue`; plan at
`plans/feature/file-issue/file-issue.md`.

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

**Rank rationale.** It closes the Phase 1 loop and is tiny once F2 and F5 exist.

**Dependencies.** F2, F5.

**Sizing.** unscored (intake estimate S); split check pending.

**Assumed starting state** = **Baseline** plus F2's thread and F5's returned issue.
Verify:
- F5's client returns the created issue's `html_url`.

**Expected end state** (repo-checkable):
- The handler test shows one thread message containing the mocked issue URL. A failed
  filing posts an error message instead of a link.
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
so F3, F4 and F6 build per-target state and config from the start instead of being
refactored later. It needs F5's GitHub client and F7's end-to-end flow to generalize.

**Dependencies.** F5, F7.

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline** plus Phase 1 (F1, F2, F5, F7) and F1's target
config object. Verify:
- F1's config has one target object, separate from instance-wide values, and
  `grep -rnE 'chores4irl|969373970' --include='*.py' .` outside `tests/` prints nothing.

**Expected end state** (repo-checkable):
- A route file (format chosen at planning, e.g. YAML or TOML, path from env) lists one or
  more targets: intake channel ID, target repo and repo ID, tag → label map. Secrets stay in
  env, never in the route file. The single-target env config of F1 still works, or is
  migrated with a documented one-route example.
- The handler dispatches each message by channel ID to its route; a message in an
  unrouted channel is ignored. Filing, labels and the posted link use that route's repo.
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
routes (or recommend one Discord application per container). (c) Per-target persistence
keys for F3's state store, and per-target Project config for F6, are set here as the
contract those features build on. (d) Hot reload of the route file: recommend restart-only.

**Session.** `/run-feature F8` on branch `feature/multi-target`; plan at
`plans/feature/multi-target/multi-target.md`.

## F9 — Rename to discord-github-issue-management-bot · Phase 1.5 · Effort M · ★FOCUS · (added 2026-10-17)

**Goal.** The project's name matches its portable scope: the GitHub repo
`4IRL/c4i-issue-bot` becomes `4IRL/discord-github-issue-management-bot` (or the name the
owner settles on at planning), along with the local folder, README/CLAUDE.md, ROADMAP
title, META-PLAN title and *PR link form*, and the Docker image name. The Python package
already has the generic name from F1. Feature-list line F9.

**Rank rationale.** ★FOCUS (owner's choice, 2026-10-17): pulled ahead of F2, F5 and F7 so
the next `/stronghold-sweep` indexes the project under its new name and portable function.
It needs only F1 (the generic package name), not the rest of Phase 1, and the earlier it
lands, the fewer files mention the old name. Independent of F8.

**Dependencies.** F1.

**Sizing.** unscored (intake estimate M); split check pending.

**Assumed starting state** = **Baseline** plus F1 (generic package name). Verify:
- No open PR is mid-review (renaming the repo while a PR is open is safe because GitHub
  redirects, but confirm at planning).

**Expected end state** (repo-checkable):
- `gh repo view 4IRL/<new-name>` succeeds and `git remote get-url origin` points at it.
- `grep -rn 'c4i-issue-bot\|c4i_issue_bot' --exclude-dir=.git .` hits only historical
  plan/review files (or nothing).
- META-PLAN's *PR link form* uses the new repo URL.
- The README's opening and the ROADMAP's end state describe the portable function (any
  channel in the server → any repo in the 4IRL org), with chores4irl as the first, example
  target. The next sweep reads that description. The ROADMAP's sequencing rationale notes
  that the rename went ahead of the rest of Phase 1.
- All suites green; Standing invariants untouched.

**Test-suite deltas.** None beyond the full suite passing after the rename.

**Open risks / decisions.** (a) The GitHub rename is an outward-facing owner action (needs
repo admin) and gets the owner's go-ahead at the time. (b) Renaming the local folder moves
Claude Code's per-project history and memory directory
(`~/.claude/projects/-home-rmila-Code-c4i-issue-bot/`) and the stronghold's index entries.
The index is rewritten only by `/stronghold-sweep`, so run a sweep afterwards; the history
move is an owner step outside this repo. (c) Whether the Discord bot's display name and
`#c4i-github-issues` channel change too is out of this repo's scope; the channel name is
config after F1. (d) `.claude/settings.json` (sandbox `allowWrite` holds the old absolute
path) and the gitignored `.claude/skill-config.md` (`project_name`, `repo`) are write-denied
to agent sessions, so the owner edits them; the plan lists them as owner steps. (e) Rename
the folder between sessions: close the session in the old folder, move it, and reopen in
the new one.

**Session.** `/run-feature F9` on branch `chore/rename-repo`; plan at
`plans/chore/rename-repo/rename-repo.md`.

---

## Dependencies & couplings (remaining work)

```
Focus:      F1 (in review, #2) ──► ★ F9   (pulled ahead of the rest of Phase 1)
Phase 1:    F1 ──► F2 ──────┐
              └──► F5 ──────┴──► F7
Phase 1.5:  {F5, F7} ──► F8        F1 ──► ★ F9   (independent of each other)
Phase 2:    {F2, F5} ──► F3        (soft: after F8)
Phase 3:    F3 ──► F4
            F5 ──► F6   [cond: new roadmap Project] (couples F4; soft: after F8)
```

- **Hard chains:** F1 → F2, F1 → F5, {F2, F5} → F7, {F5, F7} → F8, F1 → F9,
  {F2, F5} → F3 → F4, F5 → F6.
- **Soft preferences:** F9 right after F1, ahead of F2/F5/F7 (owner's ★FOCUS choice,
  2026-10-17). F7 before F3, so the skeleton is end-to-end usable before the
  conversation work; F3 doesn't need F7. F8 before F3 and F6, so conversation state and
  Project config are per-target from the start. F6 could start any time after F5 once its Project
  exists; the ROADMAP keeps it in Phase 3 so the Project fields are designed alongside F4.
- **Couplings to honor:** F3 ↔ F5: F3 reuses F5's single issue-body builder rather than
  formatting a second body. F1 ↔ F8: F8 turns F1's single target config object into a
  list; F1 keeps per-target and instance-wide values apart so that is not a rewrite. F4 ↔ F6: both use the same S/M/L/XL band names, one as a
  label and one as a Project field.

---

## History policy

Forward-looking: merged work is pruned by `/run-feature`'s fold-back and `/new-feature`'s
reconcile; git is the history.
