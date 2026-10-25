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
configured intake channels in the 4irl Discord server and turns members' reported ideas into
well-formed issues in configured repos of the 4IRL GitHub org and their roadmaps. Its first
target is `#c4i-github-issues` in the `C4I` category (guild `1137236302358659185`) →
`4IRL/chores4irl` (repo id `969373970`).
Any member reports an idea with a `/bug` or `/feature` slash command, which opens a modal
asking for a title and the questions that type needs to flesh the idea out, such as
"/bug, Title: Chore bars turn red on the due date". The bot never reads ordinary chatter. On
submit it posts a summary message in the channel and opens a thread on it, rates the idea's
complexity, then files a labeled issue, adds it to the roadmap and posts the issue's direct
link in the thread. Capture, triage and filing happen without anyone leaving Discord.

chores4irl is the first target, not the only one. The bot is portable: which channel it
listens to and which repo it files into are settings, and one deployment (or several
instances of the same image) can route different channels in the 4irl server to different
repos in the 4IRL GitHub org.

### Capabilities

The numbered capabilities define "done". Each is a user-observable outcome, never a
component.

1. **Slash-command capture.** Any member runs `/bug` or `/feature` in
   `#c4i-github-issues`, fills in the modal (a required Title and an optional Description)
   and submits it; the bot posts a public summary message and opens a thread on it. The
   same command in any other channel is refused privately. *Acceptance example:* `/feature`
   submitted with "Title: Sharing/Inviting to UTubs" and "Description: allow easy
   sharing/inviting to UTubs for members outside the UTub" is captured as a `feature` with
   that title and body; "anyone around tonight?" produces no response.
2. **Per-type questions.** Each type's modal asks the rule-based questions that type
   requires, and the reporter sees a private preview of the issue with File and Edit before
   anything is filed. *Acceptance example:* the `/bug` modal asks for steps to reproduce,
   expected behavior and actual behavior, and nothing is filed until the reporter picks File.
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
   target is a settings change, not a code change. *Acceptance example:* a report in a
   second configured channel files its issue in that channel's repo, while
   `#c4i-github-issues` keeps filing in chores4irl.

### Out of scope

- LLM-written questions or triage: clarification and complexity are rule-based by choice.
- Editing, closing or syncing existing issues from Discord; the bot only creates.
- Channels in other Discord servers, or repos outside the 4IRL GitHub org.

## Current state

<!-- Capability-level only: one row per capability above. Code-level detail (what files
exist, what the schema is) is META-PLAN's Baseline; do not restate it here. Update the
"as of" date whenever a row changes, which is normally at a phase-status change. -->

*As of 2026-10-25.*

| # | Capability | State | Delivered by |
|---|---|---|---|
| 1 | Slash-command capture | done — `/bug` and `/feature` modals in each routed channel | Phases 1, 1.5 |
| 2 | Per-type questions | none — not started | Phase 2 |
| 3 | Complexity rating | none — not started | Phase 3 |
| 4 | Issue filed and on the roadmap | partial — filed with its type label; structured body and roadmap placement pending | Phases 1 (filed), 2 (structured body), 3 (roadmap) |
| 5 | Link posted back | done — issue number, title and link in the thread (or a reply on the summary) | Phase 1 |
| 6 | Multiple targets | done — a route file maps channels to repos, from one process or several containers | Phases 1 (portable config), 1.5 (routes, instances) |

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
  in the thread rather than silently dropped (retry added in Phase 4). A command needs the
  bot online: one run while the bot or Discord is unreachable fails in Discord, and nothing
  is queued. It runs on `c4i` (Phase 4): while that Pi is down the bot is offline, and
  members report again once it is back.

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

### Phase 1: Walking skeleton (command → issue → link) · done (2026-10-21) — `/bug` and `/feature` modals in one configured channel post a summary, open a thread on it, file a labeled issue and post its link back (F1, F2, F5, F10, F7).

### Phase 1.5: Multi-target and rename · done (2026-10-25) — a TOML route file maps each intake channel to its own repo in the org, from one process or several containers on one token, and the project carries the `discord-github-issue-bot` name (F9, F8).

### Phase 2: Per-type questions · planned

**Goal.** Each type's modal asks the questions that type needs, and the bot files an issue
whose body is built from the answers after the reporter confirms a preview. **Advances
capabilities:** 2, 4.

- Question sets for each type are data rather than code (for example `/bug`: steps to
  reproduce, expected, actual, device/browser; `/feature`: who it is for, the problem it
  solves, what "done" looks like), so adding a type or question needs no code change. They
  become the modal's fields: the Title plus up to four questions (Discord's five-field cap).
- After submit the reporter gets a private (ephemeral) preview of the issue with **File**
  and **Edit**: File files it with a structured body (sections per question), and Edit
  reopens the modal prefilled.
- There is no thread conversation and no persisted conversation state; members can still
  comment in the thread.

**Exit criteria.** In the test channel, a `/bug` and a `/feature` report each show their
questions in the modal and a private preview, an Edit reopens the modal prefilled, and the
filed issue's body has one section per answered question.

**Why here.** The value of the bot over a plain form is the fleshed-out idea; it needs the
Phase 1 modal, thread and filing path to exist first.

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
- A command needs the bot online, and nothing is queued while it is down; a report is
  never filed twice.
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
