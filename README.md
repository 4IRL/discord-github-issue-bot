# discord-github-issue-bot

A Discord bot that turns `/bug` and `/feature` reports, made through a modal in a configured intake channel of a Discord server, into GitHub issues in a configured repo of the 4IRL GitHub org. Each report becomes a public summary message, a thread on it and a filed issue whose link is posted in the thread. Clarifying questions and roadmap placement are planned features. Its first target (an example) is `#c4i-github-issues` in the 4irl server → `4IRL/chores4irl`.

The code itself is target-agnostic: it holds no 4irl values (never as a code default), and their config home is the committed [`example.env`](example.env).

## Status

F2 (thread per report), F5 (issue filing), F7 (issue link in the thread) and F10 (slash-command intake) exist: the bot registers `/bug` and `/feature` and files each report as described under [Reporting](#reporting). The thread is named from the title, and the issue gets its type's label. A filed issue is logged by issue type, message id, message URL, thread id and issue URL. On success the bot posts the issue number, title and link in the thread (`Filed as GitHub issue #<number>: <title>` with the link on the next line, no preview card); if filing fails it posts a fixed error reply there. With no thread, either goes as a reply to the summary message.

- The commands are synced to the `DISCORD_GUILD_ID` guild only, once per start, and are refused outside the intake channel.
- The intake channel is matched by `DISCORD_CHANNEL_ID`; its name, category and guild are only checked at startup (a mismatch logs a warning; a channel the bot cannot see logs an error).

### Reporting

1. Run `/bug` or `/feature` in the intake channel. A "New bug" or "New feature" form opens.
2. Fill in **Title** (required, up to 100 characters) and, optionally, **Description** (up to 4000 characters, line breaks kept), then submit.
3. The bot posts a public summary in the channel: the type, the title and you as a mention that pings nobody. It opens a thread on the summary, files the issue, then posts the issue's number, title and link in the thread.
4. You get a private confirmation linking the summary. Only you see it.

- A title with no letter or digit posts nothing; you get a private reply asking you to run the command again.
- If the summary can't be posted, nothing is filed, and you get a private reply saying so.
- Before the form opens, the bot checks it can reach the GitHub repo. If it can't (within 2 seconds), no form opens and you get a private reply: "Sorry, reports can't be filed to GitHub right now, so the form didn't open. Try again later."
- Run anywhere else, including inside a thread of the intake channel, the command gets a private refusal pointing to the intake channel.

Direction: [`plans/ROADMAP.md`](plans/ROADMAP.md). Next work: [`plans/META-PLAN.md`](plans/META-PLAN.md).

### Known limits

- No retry or dedup until Phase 4, so a timeout can leave an issue filed after an error reply.
- `/bug` and `/feature` are registered on Discord's side and persist when the bot stops: a command run while the bot is down fails in Discord ("The application did not respond") and files nothing. A redeploy re-syncs them.
- An open modal expires after 30 minutes, and a bot restart drops every open modal: its submit fails in Discord, and nothing is filed or logged.
- The private confirmation means only that the summary was posted, not that the issue was filed. The filing outcome (link or error) appears in the thread, or as a reply to the summary when no thread opened; if that post fails too, the outcome shows only in the log (`could not send issue link …` or `could not send filing error …`).
- If GitHub filing fails, the Description typed in the modal is not kept anywhere in Discord; the reporter must type it again (F3's preview step addresses this).
- Rolling back to a build without slash commands leaves `/bug` and `/feature` registered in the guild but unanswered, until an empty command sync for the guild or removal of the app from the server. Neither path is verified yet; a `--clear-commands` flag is a deferred follow-up.

## Getting started

### Prerequisites

- Python 3.12
- Docker (for the container run)

### Discord setup

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and add a bot to it. Copy the bot token.
2. Invite the bot to the server with the `bot` and `applications.commands` scopes, and the **View Channel**, **Read Message History**, **Send Messages**, **Create Public Threads** and **Send Messages in Threads** permissions on the intake channel. Read Message History is kept for opening and fetching threads on the summary message, and for replying to the summary when no thread could be opened. Threads use the channel's default auto-archive duration.

### GitHub App setup

1. Create a GitHub App under the 4IRL org. Turn the webhook off. Grant the repository permissions **Issues: Read and write** and **Metadata: Read**.
2. Install it on the target repo(s) only.
3. Note the App ID (the App's settings page) and the installation ID (the number at the end of the installation's URL).
4. Generate a private key and keep the downloaded `.pem` outside the repo.

Issues filed to a public target repo are public, including the author's Discord display name. @mentions in the body and the author name are neutralized (a zero-width space after each `@`), so filing notifies no GitHub user.

### Configuration

All configuration comes from the environment, and every key is required: there are no defaults in code. Copy the template and fill it in:

```sh
cp example.env .env
```

Then set the bot token, the intake channel's ID (enable Developer Mode in Discord, right-click the channel, **Copy Channel ID**) and the `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID` and `GITHUB_APP_PRIVATE_KEY_PATH` values (see [GitHub App setup](#github-app-setup)) in `.env`. `.env` is gitignored; never commit a real token.

| Key | Scope | Type | Meaning |
|---|---|---|---|
| `DISCORD_TOKEN` | instance | string (secret) | Bot token |
| `DISCORD_GUILD_ID` | instance | positive integer | Server the bot serves |
| `GITHUB_APP_ID` | instance | positive integer | GitHub App ID |
| `GITHUB_APP_INSTALLATION_ID` | instance | positive integer | The App's installation ID |
| `GITHUB_APP_PRIVATE_KEY_PATH` | instance | path (secret file) | Path to the App's PEM private key |
| `DISCORD_CHANNEL_ID` | target | positive integer | Intake channel (matched by ID) |
| `DISCORD_CHANNEL_NAME` | target | string | Expected channel name (startup sanity check only) |
| `DISCORD_CATEGORY` | target | string | Expected category name (startup sanity check only) |
| `GITHUB_REPO` | target | `owner/name` | Output repo |
| `GITHUB_REPO_ID` | target | positive integer | Output repo id |
| `GITHUB_LABEL_BUG` | target | string | Label for `/bug` |
| `GITHUB_LABEL_FEATURE` | target | string | Label for `/feature` |

Each `GITHUB_LABEL_*` label must already exist in the target repo: a label an App requests that doesn't exist may be dropped or auto-created depending on its permissions _(unverified)_. The scratch-repo [smoke test](docs/SMOKE-TEST.md) confirms the label was applied.

Pointing the bot at another channel or repo (for example a test channel) means changing only `.env`.

`.env` uses plain key-equals-value lines, with no quotes and no `export`. Docker's `--env-file` takes each value literally. The shell form below reads the same file correctly only when no value contains spaces, quotes, `$`, backticks or backslashes (the shell expands them); for such a value, use the Docker run, or export that key by hand with single quotes before starting the bot. The shell form runs in a subshell so the token is not left exported in your terminal.

### Run locally

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
(set -a; . ./.env; set +a; exec .venv/bin/python -m issue_bot)
```

For a local run, set `GITHUB_APP_PRIVATE_KEY_PATH` to the key's host path (outside the repo): `example.env`'s `/run/secrets/...` path exists only inside the container, through the Docker mount.

### Run with Docker

```sh
docker build -t discord-github-issue-bot .
docker run --rm --env-file .env -v /path/to/key.pem:/run/secrets/github-app-key.pem:ro discord-github-issue-bot
```

The container runs as uid 10001, so the mounted key must be readable by that uid. Mount a copy owned by it (`sudo install -o 10001 -m 0400 key.pem key.container.pem`) rather than `chown`ing your own key, which would stop local runs from reading it. In `.env`, set `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` for the container run.

Before going live, run the owner-only [smoke test](docs/SMOKE-TEST.md) against a private scratch repo.

The image contains only the code and its pinned dependencies; no credentials or target config are baked in.

## Tests

```sh
.venv/bin/pytest
```

Tests mock Discord: they never connect to the Gateway, post to a channel or create GitHub issues. GitHub is mocked through an injected transport, and a conftest guard fails any test that would make a live GitHub call.
