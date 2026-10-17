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

**★FOCUS: `F1` — Channel listener and tag parsing** (runnable; branch `feature/channel-listener`).

Nothing is built yet. F1 is the only feature with no prerequisites, and every other feature
builds on it. F6 is additionally gated on creating the new chores4irl roadmap Project.

<!-- Two or three sentences at most: what is runnable today, what is gated and on what.
Shipped work is git's record (`gh pr list --state merged`), not this file's. -->

### Shortest path to the focus feature

F1 has no prerequisites. It needs a Discord application with a bot token, the Message
Content intent enabled, and the bot invited to the 4irl server with permission to read the
channel. The owner sets that up; the token goes in `.env`. After F1, the Phase 1 skeleton
runs F2 and F5 (independent of each other), then F7.

---

## Feature list (intake record)

> Written only by `/new-feature`; `/run-feature` removes a line at fold-back.

**Next F-ID:** `F8`

- [ ] **F1** (added 2026-10-16): Listen to the 'c4i-github-issues' channel in the 'C4I' category of the 4irl server and parse messages from any member for a type tag such as #feature or #bug, ignoring untagged messages.
- [ ] **F2** (added 2026-10-16): For each tagged message, create a thread for the issue.
- [ ] **F3** (added 2026-10-16): In the thread, ask the clarifying questions needed to flesh out the idea (rule-based, per tag).
- [ ] **F4** (added 2026-10-16): Evaluate the issue's complexity (triage).
- [ ] **F5** (added 2026-10-16): Create the issue in the 4IRL/chores4irl GitHub repo (split from "create the issue in the 4IRL/chores4irl GitHub repo and add it to its roadmap").
- [ ] **F6** (added 2026-10-16): Add the created issue to the chores4irl roadmap (split from "create the issue in the 4IRL/chores4irl GitHub repo and add it to its roadmap").
- [ ] **F7** (added 2026-10-16): Post a direct link to the newly created issue in the same thread.

---

## Backlog summary (remaining work only)

| Order | Feature | Effort | Depends on | Phase |
|---|---|---|---|---|
| ★ 1 | **F1** — Channel listener and tag parsing **[FOCUS]** | L | — | 1 |
| 2 | **F2** — Thread per tagged message | S | F1 | 1 |
| 3 | **F5** — File the issue in 4IRL/chores4irl | M | F1 | 1 |
| 4 | **F7** — Post the issue link in the thread | S | F2, F5 | 1 |
| 5 | **F3** — Rule-based clarifying questions | L | F2, F5 | 2 |
| 6 | **F4** — Complexity triage (S/M/L/XL) | M | F3 | 3 |
| 7 | **F6** — Add the issue to the chores4irl roadmap Project | M | F5; couples: F4; cond: new chores4irl roadmap Project created (owner-approved) | 3 |

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

**Effort tally (remaining).** 14 pts (S=1 / M=2 / L=3 / XL=5).

---

## Status ledger

> Maintained by `/run-feature` (`pending` → `in-progress` → `in-review`; a verified-merged
> row is deleted at fold-back). Never hand-delete a row. Git wins any conflict.

| Feature | Status | Branch | PR |
|---|---|---|---|
| **F1 — Channel listener and tag parsing** ★FOCUS | in-progress | `feature/channel-listener` | — |
| **F2 — Thread per tagged message** | pending | `feature/issue-thread` | — |
| **F3 — Rule-based clarifying questions** | pending | `feature/clarifying-questions` | — |
| **F4 — Complexity triage (S/M/L/XL)** | pending | `feature/complexity-triage` | — |
| **F5 — File the issue in 4IRL/chores4irl** | pending | `feature/file-issue` | — |
| **F6 — Add the issue to the chores4irl roadmap Project** | pending | `feature/roadmap-project` | — |
| **F7 — Post the issue link in the thread** | pending | `feature/post-issue-link` | — |

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

1. `#bug` maps to chores4irl's existing `bug` label and `#feature` to its existing
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

## F1 — Channel listener and tag parsing · Phase 1 · Effort L · ★FOCUS · (added 2026-10-16)

**Goal.** The bot runs, connects to the Discord Gateway, listens only to the configured
channel, and turns a tagged message into a parsed issue candidate (type, title, author,
message link); untagged, bot and other-channel messages are ignored. Feature-list line F1.

**Rank rationale.** Every other feature consumes its parsed candidate and runtime, so it goes
first. It also stands up the project's code skeleton: package layout, config, Docker image
and the pytest harness that sets META-PLAN's Verification.

**Dependencies.** —

**Sizing.** unscored (intake estimate L); split check pending.

**Assumed starting state** = **Baseline**. Verify:
- `git ls-files` lists only the scaffold files (no `*.py`, no `Dockerfile`).

**Expected end state** (repo-checkable):
- The guild ID, category, channel and target repo are read from config/env, not hardcoded
  (`grep -rn 1137236302358659185 --include='*.py'` hits only config defaults or tests).
- A pure tag parser recognizes `#bug` and `#feature` (case-insensitive, anywhere in the
  text). It returns the type and the title with the tag stripped, or nothing for untagged
  text. Unit tests use the ROADMAP's two acceptance examples.
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
messages are captured). (d) Requires the privileged Message Content intent.

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
- All suites green; Standing invariants untouched.

**Test-suite deltas.** Handler tests for thread creation, name truncation and the
no-duplicate guard.

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

**Dependencies.** F2, F5.

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

**Goal.** The bot creates a GitHub issue in the configured repo (default `4IRL/chores4irl`)
from the candidate. The title comes from the message; the body holds the original text, the
Discord author and a link to the message; the type label is `bug` or `enhancement`.
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
(recommended: short-lived tokens and a bot identity on issues) or a fine-grained PAT with
Issues read/write. (b) What the bot does with the message if GitHub rejects the issue;
full retry is Phase 4, so recommend a visible error reply for now.

**Session.** `/run-feature F5` on branch `feature/file-issue`; plan at
`plans/feature/file-issue/file-issue.md`.

## F6 — Add the issue to the chores4irl roadmap Project · Phase 3 · Effort M · (added 2026-10-16)

**Goal.** Each filed issue is added to the new chores4irl roadmap Project (GitHub Projects
v2), with its Status set and its complexity field matching F4's rating.
Feature-list line F6.

**Rank rationale.** Phase 3. It's blocked by the Project, which doesn't exist yet, and its
complexity field shares a contract with F4.

**Dependencies.** F5; couples: F4; cond: new chores4irl roadmap Project created
(owner-approved). The gate is checked by finding the Project in
`gh api graphql` `organization(login:"4IRL"){projectsV2}` and recording its number in
config.

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

**Goal.** After F5 files the issue, the bot posts its direct URL
(`https://github.com/4IRL/chores4irl/issues/<n>`) in the message's thread, which completes
the Phase 1 skeleton. Feature-list line F7.

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

---

## Dependencies & couplings (remaining work)

```
Phase 1:  ★ F1 ──► F2 ──────┐
              └──► F5 ──────┴──► F7
Phase 2:  {F2, F5} ──► F3
Phase 3:  F3 ──► F4
          F5 ──► F6   [cond: new roadmap Project] (couples F4)
```

- **Hard chains:** F1 → F2, F1 → F5, {F2, F5} → F7, {F2, F5} → F3 → F4, F5 → F6.
- **Soft preferences:** F7 before F3, so the skeleton is end-to-end usable before the
  conversation work; F3 doesn't need F7. F6 could start any time after F5 once its Project
  exists; the ROADMAP keeps it in Phase 3 so the Project fields are designed alongside F4.
- **Couplings to honor:** F3 ↔ F5: F3 reuses F5's single issue-body builder rather than
  formatting a second body. F4 ↔ F6: both use the same S/M/L/XL band names, one as a
  label and one as a Project field.

---

## History policy

Forward-looking: merged work is pruned by `/run-feature`'s fold-back and `/new-feature`'s
reconcile; git is the history.
