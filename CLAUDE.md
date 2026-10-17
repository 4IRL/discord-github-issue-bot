# CLAUDE.md — c4i-issue-bot

A Discord bot for the 4irl server that turns tagged messages in `#c4i-github-issues` (`#bug`, `#feature`) into fleshed-out issues on the `4IRL/chores4irl` GitHub repo and its roadmap. It asks clarifying questions in a thread, then posts the new issue's link back there.

<!-- Project-specific rules only. Global rules (secrets, branch guard, sandbox, env-var
parsing) come from ~/.claude/CLAUDE.md and are not repeated here. -->

## Where things live

| Question | Document |
|---|---|
| How do I run and test it? | `README.md` |
| What rules must an agent follow here? | this file |
| Where is the project going, and why in this order? | `plans/ROADMAP.md` |
| What is the next feature, and what does the code look like now? | `plans/META-PLAN.md` |
| How is a given feature being built? | `plans/<topic>/<slug>.md` |

Each fact has one home. Link to it from elsewhere; never copy it.

## Stack

Python 3 with discord.py (Gateway connection) and an HTTP client for the GitHub REST/GraphQL APIs, packaged as a Docker container. Clarifying questions and complexity ratings are rule-based (per-tag templates), with no LLM. Docker commands run with `dangerouslyDisableSandbox: true`.

## Commands

<!-- Fill in once code exists: install, dev server, test, build. Keep them in sync with
.claude/skill-config.md's test fields. -->

- Test: _not set up yet_

## Project rules

- **Never create real GitHub issues or post to the live Discord channel from tests or agent sessions.** Tests mock the Discord and GitHub clients; a live smoke test needs the user's explicit go-ahead each time.
- **Identifiers are config, not code.** Guild `1137236302358659185`, category `C4I`, channel `c4i-github-issues` and target repo `4IRL/chores4irl` (repo id `969373970`) come from configuration, so the bot can point at a test channel or repo.
- The Discord bot token and GitHub credentials live only in `.env` / the container environment; agents never read them.
