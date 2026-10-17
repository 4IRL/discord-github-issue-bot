# c4i-issue-bot Roadmap — Current State to End State

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

c4i-issue-bot is a Discord bot in the 4irl server (guild `1137236302358659185`). It watches
the `#c4i-github-issues` channel in the `C4I` category and turns members' ideas into
well-formed issues on the `4IRL/chores4irl` GitHub repo (repo id `969373970`) and its roadmap.
Any member posts a one-line idea ending in a type tag, such as "Chore bars turn red on the due
date instead of after it #bug". The bot ignores untagged chatter. For a tagged message it opens
a thread, asks the questions that tag needs to flesh the idea out, rates its complexity, then
files a labeled issue, adds it to the roadmap and posts the issue's direct link in the same
thread. Capture, triage and filing happen without anyone leaving Discord.

### Capabilities

The numbered capabilities define "done". Each is a user-observable outcome, never a
component.

1. **Tagged capture.** A message in `#c4i-github-issues` from any member that carries a
   known type tag is picked up; untagged messages and bot messages are ignored.
   *Acceptance example:* "Display chore count next to Room tab name in parentheses when each
   Room tab is active #feature" is captured as a `feature` with that title; "anyone around
   tonight?" produces no response.
2. **Clarifying thread.** For each captured message the bot opens a thread on it and asks
   the rule-based questions that tag requires, collecting the author's (or any member's)
   answers there. *Acceptance example:* a `#bug` thread asks for steps to reproduce, expected
   behavior and actual behavior before anything is filed.
3. **Complexity rating.** From the tag and the answers, the bot assigns a complexity rating
   that becomes part of the filed issue. <Rating scale and rules: set by the owner.>
4. **Issue filed and on the roadmap.** Once clarification is done, the bot creates the
   issue in `4IRL/chores4irl` with a title, a structured body, the type label and the
   complexity rating, and adds it to the repo's roadmap.
5. **Link posted back.** The bot posts the new issue's direct URL in the same thread.
   *Acceptance example:* the thread ends with a message containing
   `https://github.com/4IRL/chores4irl/issues/<n>`.

### Out of scope

- LLM-written questions or triage: clarification and complexity are rule-based by choice.
- Editing, closing or syncing existing issues from Discord; the bot only creates.
- Other channels, servers or target repos. The IDs are config, but only this one channel
  and repo are supported.

## Current state

<!-- Capability-level only: one row per capability above. Code-level detail (what files
exist, what the schema is) is META-PLAN's Baseline; do not restate it here. Update the
"as of" date whenever a row changes, which is normally at a phase-status change. -->

*As of 2026-10-16.*

| # | Capability | State | Delivered by |
|---|---|---|---|
| 1 | Tagged capture | none — not started | Phase <N> |
| 2 | Clarifying thread | none — not started | Phase <N> |
| 3 | Complexity rating | none — not started | Phase <N> |
| 4 | Issue filed and on the roadmap | none — not started | Phase <N> |
| 5 | Link posted back | none — not started | Phase <N> |

## Principles & constraints

<!-- Durable, project-wide rules that shape *every* phase, written as policy with a short
reason. Verified code facts that must not regress are META-PLAN Standing invariants, and
command-level operating rules (exact backup commands, test commands) belong in CLAUDE.md /
README. Keep each item to one or two sentences. -->

- **<Constraint name>.** <Rule.> *Why:* <reason.> (e.g. "Additive-only schema changes once
  real data exists. *Why:* there is no migration tool and the data is irreplaceable.")
- **Accepted risk: <name>.** <The risk the project deliberately carries, and the trigger
  that makes it no longer acceptable.> (e.g. "No auth while reachable only on the home
  network; auth becomes mandatory the moment it is reachable beyond it.")
- **External dependencies.** <Other repos, services or hardware this project relies on, and
  what happens if each one is unavailable.>

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

### Phase 1: <name> · <status>

**Goal.** <One sentence.> **Advances capabilities:** <#, #>.

- <Scope bullet: an outcome at user or system level, not a task. Name the cross-surface
  owner if relevant, e.g. "owns the mobile-first layout of its own feature".>
- <…>

**Exit criteria.** <Observable conditions, including any real-device or real-data
verification that tests alone cannot show.>

**Why here.** <What it unblocks, or why it must precede the next phase.>

### Phase 2: <name> · planned

<…same shape…>

### Phase <N>: <hardening / as needed> · planned

<Optional final phase for quality-of-life work ordered by impact rather than dependency.>

## Sequencing rationale

<!-- Phase-level dependencies only. Feature-level chains and couplings live in META-PLAN. -->

<State the true dependency shape, e.g. `{1, 2} → 3 → 4 → {5, 6}`, then separate hard
dependencies from preferences: "1 before 2 is a preference (…), not a dependency". Explain
any inserted N.5 phase.>

## Maintaining this file

- **Who updates it:** the `/run-feature` fold-back that merges a phase's last remaining
  feature flips that phase's status, refreshes the Current-state rows it changed, and collapses
  the finished phase to one line, in the same PR. Vision changes are made deliberately by
  the owner, never as a side effect of a feature session.
- **History policy:** this file is forward-looking. Pivots, superseded designs and the
  story of how the plan changed live in git history and decision records, not here.
