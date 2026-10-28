# CLAUDE.md — discord-github-issue-bot

A Discord bot that turns `/bug` and `/feature` reports, made through a modal in one of its configured intake channels of a Discord server, into fleshed-out GitHub issues in that channel's route repo in the 4IRL GitHub org and onto that repo's roadmap. Its first target (an example) is `#c4i-github-issues` in the 4irl server → `4IRL/chores4irl`.

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

Python 3 with discord.py (Gateway connection) and aiohttp for the GitHub REST/GraphQL APIs, with PyJWT for GitHub App auth, packaged as a Docker container. Clarifying questions are per-route, per-type question sets in the route file, and complexity ratings are rule-based (`issue_bot/complexity.py`, documented in `docs/COMPLEXITY.md`), with no LLM. Docker commands run with `dangerouslyDisableSandbox: true`.

## Commands

<!-- Keep these in sync with .claude/skill-config.md's test fields. -->

- Test: `.venv/bin/pytest` (repo-root venv; install with `.venv/bin/pip install -r requirements-dev.txt`)

## Project rules

- **Never create real GitHub issues or post to the live Discord channel from tests or agent sessions.** Tests mock the Discord and GitHub clients; a live smoke test needs the user's explicit go-ahead each time.
- **Identifiers are config, not code.** Guild `1137236302358659185`, category `C4I`, channel `c4i-github-issues` and target repo `4IRL/chores4irl` (repo id `969373970`) come from configuration, so the bot can point at a test channel or repo. The code holds no 4irl values (never a code default); their config homes are `example.env` and `example.routes.toml`.
- The Discord bot token and GitHub App ids live only in `.env` / the container environment, and the App private key in a file outside the repo: a host path for a local run, a read-only mounted file in the container (its path is the `GITHUB_APP_PRIVATE_KEY_PATH` env value); agents never read them. `example.env` is the committed, secret-free template (`.env` itself stays unread).
- **Logs never contain members' message text or names.** Log the issue type, ids (guild, channel, message, thread, interaction), the message URL and the filed issue's URL only; modal text and interaction payloads are member text too; a caught Discord API error is logged by exception type, HTTP status and Discord error code, never its text; a GitHub API error is logged by exception type, request stage and HTTP status, never its response text; tokens, JWTs and the App private key are never logged; message content stays in Discord and the filed issue. Exceptions escaping event handlers and hooks are logged by type and event name only, while the command, modal and preview-view error handlers log the exception type, the command, modal or view name, the interaction id and, for a Discord API error, its HTTP status and Discord error code, never `exc_info` or an interaction's repr. Never run the `discord` loggers at DEBUG: discord.py logs full gateway payloads (message text, member names) at that level.
