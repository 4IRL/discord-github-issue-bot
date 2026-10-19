# discord-github-issue-bot Roadmap — Current State to End State

> **What this file owns.** The project's *intent*: the end state it is driving toward, the
> capabilities that define "done", the coarse phases that get there and why they are
> ordered that way. It changes rarely: when the vision, a phase boundary or a phase's
> status changes.
>
> **What it does not own.** Feature IDs, feature status, branches, PRs, effort points,
> code-level facts (files, routes, schemas) and per-phase close-out detail all live in
> [`META-PLAN.md`](META-PLAN.md), the execution manifest. Implementation detail lives in
> per-feature plan files. How to run and test the project lives in `README.md`, and agent
> operating rules live in the project's `CLAUDE.md` / `AGENTS.md`. This file never copies
> from those; it links to them.
>
> **Direction of reference.** META-PLAN rows cite a phase (`Phase N`). This file never
> lists F-IDs, so adding, splitting or renumbering features never touches it. "What is
> next?" is answered by META-PLAN's ★FOCUS, not here.

## End state (the north star)

discord-github-issue-bot is a Discord bot that watches
configured intake channels in the 4irl Discord server and turns members' tagged ideas into
well-formed issues in configured repos of the 4IRL GitHub org and their roadmaps. Its first
target is `#c4i-github-issues` in the `C4I` category (guild `1137236302358659185`) →
`4IRL/chores4irl` (repo id `969373970`).
Any member posts an idea as a type tag plus a `Title:` line and an optional `Body:`, such as
"!bug / Title: Chore bars turn red on the due date" (one field per line). The bot ignores
untagged chatter. For a tagged message it opens
a thread, asks the questions that tag needs to flesh the idea out, rates its complexity, then
files a labeled issue, adds it to the roadmap and posts the issue's direct link in the same
thread. Capture, triage and filing happen without anyone leaving Discord.

chores4irl is the first target, not the only one. The bot is portable: which channel it
listens to and which repo it files into are settings, and one deployment (or several
instances of the same image) can route different channels in the 4irl server to different
repos in the 4IRL GitHub org.

### Capabilities

The numbered capabilities define "done". Each is a user-observable outcome, never a
component.

1. **Tagged capture.** A message in `#c4i-github-issues` from any member that carries a
   known type tag is picked up; untagged messages and bot messages are ignored.
   Messages use the structured form `!feature` / `Title: …` / `Body: …` (Body optional).
   *Acceptance example:* "!feature / Title: Sharing/Inviting to UTubs / Body: allow easy
   sharing/inviting to UTubs for members outside the UTub" (one field per line) is captured
   as a `feature` with that title and body; "anyone around tonight?" produces no response.
2. **Clarifying thread.** For each captured message the bot opens a thread on it and asks
   the rule-based questions that tag requires, collecting the author's (or any member's)
   answers there. *Acceptance example:* a `!bug` thread asks for steps to reproduce, expected
   behavior and actual behavior before anything is filed.
3. **Complexity rating.** From the tag and the answers, the bot assigns a complexity rating
   that becomes part of the filed issue. The scale is S / M / L / XL; the owner approves the
   rules that pick the band.
4. **Issue filed and on the roadmap.** Once clarification is done, the bot creates the
   issue in `4IRL/chores4irl` with a title, a structured body, the type label and the
   complexity rating, and adds it to the repo's roadmap.
5. **Link posted back.** The bot posts the new issue's direct URL in the same thread.
   *Acceptance example:* the thread ends with a message containing
   `https://github.com/4IRL/chores4irl/issues/<n>`.
6. **Multiple targets.** Several intake channels in the server each file into their own
   repo in the 4IRL org, from one running bot or from several instances, and adding a
   target is a settings change, not a code change. *Acceptance example:* a tagged message
   in a second configured channel files its issue in that channel's repo, while
   `#c4i-github-issues` keeps filing in chores4irl.

### Out of scope

- LLM-written questions or triage: clarification and complexity are rule-based by choice.
- Editing, closing or syncing existing issues from Discord; the bot only creates.
- Channels in other Discord servers, or repos outside the 4IRL GitHub org.

## Current state

<!-- Capability-level only: one row per capability above. Code-level detail (what files
exist, what the schema is) is META-PLAN's Baseline; do not restate it here. Update the
"as of" date whenever a row changes, which is normally at a phase-status change. -->

*As of 2026-10-17.*

| # | Capability | State | Delivered by |
|---|---|---|---|
| 1 | Tagged capture | none — not started | Phase 1 |
| 2 | Clarifying thread | none — not started | Phase 2 |
| 3 | Complexity rating | none — not started | Phase 3 |
| 4 | Issue filed and on the roadmap | none — not started | Phases 1 (filed), 2 (structured body), 3 (roadmap) |
| 5 | Link posted back | none — not started | Phase 1 |
| 6 | Multiple targets | none — not started | Phases 1 (portable config), 1.5 (routes, instances) |

## Principles & constraints

<!-- Durable, project-wide rules that shape *every* phase, written as policy with a short
reason. Verified code facts that must not regress are META-PLAN Standing invariants, and
command-level operating rules (exact backup commands, test commands) belong in CLAUDE.md /
README. Keep each item to one or two sentences. -->

- **Rule-based only, no LLM.** Clarifying questions and complexity ratings come from
  per-tag rules and templates, never a language model. *Why:* the behavior stays
  predictable and free, with no external model to depend on.
- **No live side effects from tests or agent sessions.** Tests mock the Discord and GitHub
  clients, and a live smoke test needs the owner's go-ahead each time (operating rule:
  `CLAUDE.md`). *Why:* stray runs must never file spam issues on `4IRL/chores4irl` or post
  in the real channel.
- **Identifiers are config, not code.** The guild, category, channel and target repo (and
  its id) come from configuration, and no target's values are code defaults. *Why:* the
  bot can be pointed at a test channel or repo, or at any new target, without a code
  change.
- **Least-privilege access.** The GitHub credential gets issues write on the target repo
  only, plus from Phase 3 the narrowest org Projects permission roadmap placement needs, and
  the Discord bot asks only for the intents and channel permissions it uses; credentials
  live outside the repo (see `CLAUDE.md`). *Why:* it limits the damage if a credential leaks.
- **External dependencies.** The bot relies on the Discord Gateway and the GitHub REST and
  GraphQL APIs, and files nothing while either is unavailable. A GitHub failure is reported
  in the thread rather than silently dropped (retry added in Phase 4), and messages posted
  while Discord was unreachable are picked up on restart (Phase 4). It runs on `c4i`
  (Phase 4): while that Pi is down the bot is offline, and the restart catch-up covers
  the gap.

## Phases

<!--
One section per phase. A phase is a coherent milestone that delivers or advances one or
more capabilities, and is decomposed into features in META-PLAN when its turn comes.

Phase numbers are permanent. To insert a phase between N and N+1, use N.5; never renumber.

A phase section holds only: status, goal, capabilities advanced, scope bullets, exit
criteria, and why it sits where it does. When a phase finishes, collapse its section to a
single line (status + date + what it delivered). Anything it left unfinished becomes a
META-PLAN feature or deferred follow-up, never a "close-out" list here.

Status markers: `done (YYYY-MM-DD)`, `active`, `planned`. Exactly one phase is `active`
at a time unless the sequencing rationale says otherwise.
-->

### Phase 1: Walking skeleton (message → issue → link) · active

**Goal.** A tagged message in the channel becomes a minimal GitHub issue, and its link
appears in a thread, end to end. **Advances capabilities:** 1, 4 (filed only), 5.

- The bot runs in its Docker container, connects to the Gateway and listens only to the
  configured channel; guild, category, channel and target repo all come from config.
- Tag parsing recognizes `!bug` and `!feature` anywhere in the message, reads the required
  `Title:` and optional `Body:` fields, and ignores untagged, bot and edited messages.
- For each tagged message the bot opens a thread on it, creates an issue (the `Title:`, the
  `Body:` and author as the body, the type label) and posts the issue URL in the
  thread.
- The bot authenticates to GitHub with least privilege on the target repo only (issues
  write; GitHub App vs fine-grained token decided at planning).
- Tests drive the flow against mocked Discord and GitHub clients; no test touches the live
  channel or repo.

**Exit criteria.** In a test channel pointed at a test repo, posting
"!bug / Title: Chore bars turn red on the due date" (one field per line) produces a thread, a
`bug`-labeled issue and its link in the thread, and an untagged message produces nothing.
The test suite is green and runs as META-PLAN's Verification.

**Why here.** It proves every external integration (Gateway intents, thread permissions,
GitHub auth, labels) before any conversation logic is built on top, and is useful on its
own as a quick-capture tool.

### Phase 1.5: Multi-target and rename · planned

**Goal.** The same bot serves more than one intake channel and target repo, and the
project carries a name that matches. **Advances capabilities:** 6.

- A route table in a config file maps each intake channel in the server to its target repo
  in the 4IRL org (with its own tag → label map); messages are filed to their channel's
  repo, and unrouted channels are ignored.
- The same image runs as one process with several routes or as several containers, each
  with its own route file; the deployment docs show both.
- The repo, local folder, docs and image are renamed to `discord-github-issue-bot`.

**Exit criteria.** With two routes pointing two test channels at two test repos, a tagged
message in each channel files in its own repo and posts its link back, both from one
process and from two containers. The renamed repo's suite is green.

**Why here.** Phase 2 and 3 add per-conversation state and per-repo Project config. Making
the config multi-target before they start means they are built per target once, instead
of refactored later.

### Phase 2: Clarifying conversation · planned

**Goal.** The bot asks the questions each tag needs in the thread and files an issue whose
body is built from the answers. **Advances capabilities:** 2, 4.

- Question sets for each tag are data rather than code (for example `!bug`: steps to
  reproduce, expected, actual, device/browser; `!feature`: who it is for, the problem it
  solves, what "done" looks like), so adding a tag or question needs no code change.
- The bot asks one question at a time and accepts replies from any member in the thread,
  with commands to skip a question, cancel, or file now.
- Before filing, the bot posts a preview of the issue and waits for a confirmation, then
  files the issue with a structured body (sections per question).
- Conversation state survives a bot restart, and an abandoned thread times out with a note
  instead of hanging forever.

**Exit criteria.** In the test channel, a `!bug` and a `!feature` thread each run through
their questions (including a skip and a cancel), and the filed issue's body has one
section per answered question. Restarting the container mid-conversation resumes it.

**Why here.** The value of the bot over a plain form is the fleshed-out idea; it needs the
Phase 1 thread and filing path to exist first.

### Phase 3: Triage and roadmap placement · planned

**Goal.** Every filed issue carries a rule-based complexity rating and lands on its
target's roadmap (chores4irl's first). **Advances capabilities:** 3, 4.

- Complexity is computed by documented rules from the tag and the answers (the owner sets
  the scale), shown in the confirmation preview, and members can override it before filing.
- The issue gets the type and complexity labels (labels created if missing), and is added
  to the chores4irl GitHub Projects roadmap with its Status and complexity fields set.
- The thread's final message shows the issue link together with its rating and roadmap
  placement.

**Exit criteria.** A filed test issue appears on a test Project board with the correct
fields, and its labels match the rating shown in Discord. The rating rules are written
down where members can read them.

**Why here.** Rating needs the Phase 2 answers as input, and roadmap placement needs
Projects (GraphQL) access, a separate permission best added once filing is proven.

### Phase 4: Production and hardening · planned

**Goal.** The bot runs unattended for the 4irl server and recovers from failures without
losing ideas. **Advances capabilities:** 1–5 (reliability).

- The bot is deployed on `c4i`, the household's always-on Raspberry Pi 4 (arm64), as a
  container with automatic restart, a memory limit, a health check and logs an operator
  can read; deploying a new version is one documented command run over `ssh c4i`. This
  repo owns the image, its config and that command. The host side (Docker, the memory
  ceiling, root-only files for the token and App key) is homelab's: its
  `plans/HOST-ROLES.md` and ROADMAP Phase 3.
- GitHub or Discord errors are reported in the thread with a retry, never silently
  dropped, and rate limits are respected.
- Messages posted while the bot was down are picked up on start, and a message is never
  filed twice.
- Quality-of-life additions ordered by impact (more tags, duplicate-issue hints, a help
  command).

**Exit criteria.** Live in `#c4i-github-issues` for two weeks of real use with no lost or
duplicated issues, and a forced GitHub failure and a container restart each recover
visibly in the thread.

**Why here.** Hardening is ordered by what real use exposes. The bot can be deployed
earlier (see Sequencing rationale), but this phase makes it safe to leave running.

## Sequencing rationale

<!-- Phase-level dependencies only. Feature-level chains and couplings live in META-PLAN. -->

`1 → 1.5 → 2 → 3 → 4`. Phase 1.5 depends on Phase 1 hard (it generalizes the working
skeleton). Phases 2 and 3 depend on Phase 1.5 only softly: they could run without it, but
would then need refactoring to become per-target. Phase 2 depends on Phase 1 hard (it
extends the thread and filing path), and Phase 3 depends on Phase 2 hard (the rating reads
the answers). Phase 4's hosting
and deploy work depends only on Phase 1 here, plus homelab's `c4i` Docker stage (homelab
Phase 3, which needs only homelab's Phase 1); putting it last is a preference. If the server
wants the bot live sooner, its deploy features can be pulled forward after Phase 1 or 2
without reordering the phases. Phase 3's roadmap placement depends only on Phase 1 and
could run alongside Phase 2; it stays with the rating so the Projects fields and labels
are designed once. The Phase 1.5 rename went
ahead of the rest of Phase 1 (owner's choice, 2026-10-17), so the stronghold index lists
the project under its portable name early and later work never has to rename files.

## Maintaining this file

- **Who updates it:** the `/run-feature` fold-back that merges a phase's last remaining
  feature flips that phase's status, refreshes the Current-state rows it changed, and collapses
  the finished phase to one line, in the same PR. Vision changes are made deliberately by
  the owner, never as a side effect of a feature session.
- **History policy:** this file is forward-looking. Pivots, superseded designs and the
  story of how the plan changed live in git history and decision records, not here.
