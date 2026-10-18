# CLAUDE.md — discord-github-issue-bot

A Discord bot that turns tagged messages (`!bug`, `!feature`) in a configured intake channel of a Discord server into fleshed-out GitHub issues in a configured repo of the 4IRL GitHub org, and onto that repo's roadmap. It asks clarifying questions in a thread, then posts the new issue's link back there. Its first target (an example) is `#c4i-github-issues` in the 4irl server → `4IRL/chores4irl`.

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

<!-- Keep these in sync with .claude/skill-config.md's test fields. -->

- Test: `.venv/bin/pytest` (repo-root venv; install with `.venv/bin/pip install -r requirements-dev.txt`)

## Project rules

- **Never create real GitHub issues or post to the live Discord channel from tests or agent sessions.** Tests mock the Discord and GitHub clients; a live smoke test needs the user's explicit go-ahead each time.
- **Identifiers are config, not code.** Guild `1137236302358659185`, category `C4I`, channel `c4i-github-issues` and target repo `4IRL/chores4irl` (repo id `969373970`) come from configuration, so the bot can point at a test channel or repo. The code holds no 4irl values (never a code default); their config home is `example.env`.
- The Discord bot token and GitHub credentials live only in `.env` / the container environment; agents never read them. `example.env` is the committed, secret-free template (`.env` itself stays unread).
- **Logs never contain members' message text or names.** Log the issue type, message id and message URL only; message content stays in Discord and the filed issue. Exceptions escaping event handlers and hooks are logged by type and event name only. Never run the `discord` loggers at DEBUG: discord.py logs full gateway payloads (message text, member names) at that level.
