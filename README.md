# discord-github-issue-bot

A Discord bot that turns `/bug` and `/feature` reports, made through a modal in one of its configured intake channels of a Discord server, into GitHub issues in the 4IRL GitHub org. Each intake channel is a route, and each report is filed in that route's repo. Each report becomes a public summary message, a thread on it and a filed issue whose link is posted in the thread. Clarifying questions and roadmap placement are planned features. Its first target (an example) is `#c4i-github-issues` in the 4irl server → `4IRL/chores4irl`.

The code itself is target-agnostic: it holds no 4irl values (never as a code default), and their config home is the committed [`example.env`](example.env) and [`example.routes.toml`](example.routes.toml).

## Status

F2 (thread per report), F5 (issue filing), F7 (issue link in the thread), F8 (routes: several intake channels, each filing to its own repo, from the route file) and F10 (slash-command intake) exist: the bot registers `/bug` and `/feature` and files each report as described under [Reporting](#reporting). The thread is named from the title, and the issue gets its type's label. A filed issue is logged by issue type, message id, message URL, thread id and issue URL. On success the bot posts the issue number, title and link in the thread (`Filed as GitHub issue #<number>: <title>` with the link on the next line, no preview card); if filing fails it posts a fixed error reply there. With no thread, either goes as a reply to the summary message.

- The commands are synced to the `DISCORD_GUILD_ID` guild only, once per start. Outside a routed intake channel they are refused, or ignored with no reply when `UNROUTED_COMMANDS=ignore`.
- Each route's intake channel is matched by its `channel_id`; its name, category and guild are only checked at startup, per route (a mismatch logs a warning; a channel the bot cannot see logs an error).

### Reporting

1. Run `/bug` or `/feature` in an intake channel. A "New bug" or "New feature" form opens.
2. Fill in **Title** (required, up to 100 characters) and, optionally, **Description** (up to 4000 characters, line breaks kept), then submit.
3. The bot posts a public summary in the channel: the type, the title and you as a mention that pings nobody. It opens a thread on the summary, files the issue, then posts the issue's number, title and link in the thread.
4. You get a private confirmation linking the summary. Only you see it.

- A title with no letter or digit posts nothing; you get a private reply asking you to run the command again.
- If the summary can't be posted, nothing is filed, and you get a private reply saying so.
- Before the form opens, the bot checks it can reach the GitHub repo. If it can't (within 2 seconds), no form opens and you get a private reply: "Sorry, reports can't be filed to GitHub right now, so the form didn't open. Try again later."
- Run anywhere else, including inside a thread of an intake channel, the command gets a private refusal pointing to the intake channel. With `UNROUTED_COMMANDS=ignore` (see [Run several instances](#run-several-instances)), it gets no reply at all, and Discord shows "The application did not respond".

Direction: [`plans/ROADMAP.md`](plans/ROADMAP.md). Next work: [`plans/META-PLAN.md`](plans/META-PLAN.md).

### Known limits

- No retry or dedup until Phase 4, so a timeout can leave an issue filed after an error reply.
- `/bug` and `/feature` are registered on Discord's side and persist when the bot stops: a command run while the bot is down fails in Discord ("The application did not respond") and files nothing. A redeploy re-syncs them.
- An open modal expires after 30 minutes, and a bot restart drops every open modal: its submit fails in Discord, and nothing is filed or logged.
- The private confirmation means only that the summary was posted, not that the issue was filed. The filing outcome (link or error) appears in the thread, or as a reply to the summary when no thread opened; if that post fails too, the outcome shows only in the log (`could not send issue link …` or `could not send filing error …`).
- If GitHub filing fails, the Description typed in the modal is not kept anywhere in Discord; the reporter must type it again (F3's preview step addresses this).
- Route file changes need a restart.
- Rolling back to a build without slash commands leaves `/bug` and `/feature` registered in the guild but unanswered, until an empty command sync for the guild or removal of the app from the server. Neither path is verified yet; a `--clear-commands` flag is a deferred follow-up.

## Getting started

### Prerequisites

- Python 3.12
- Docker (for the container run)

### Discord setup

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and add a bot to it. Copy the bot token.
2. Invite the bot to the server with the `bot` and `applications.commands` scopes, and the **View Channel**, **Read Message History**, **Send Messages**, **Create Public Threads** and **Send Messages in Threads** permissions on each route's intake channel. Read Message History is kept for opening and fetching threads on the summary message, and for replying to the summary when no thread could be opened. Threads use the channel's default auto-archive duration.

### GitHub App setup

1. Create a GitHub App under the 4IRL org. Turn the webhook off. Grant the repository permissions **Issues: Read and write** and **Metadata: Read**.
2. Install it on every route's repo, and only those (**Only select repositories**). A route to a new repo means adding that repo to the installation.
3. Note the App ID (the App's settings page) and the installation ID (the number at the end of the installation's URL).
4. Generate a private key and keep the downloaded `.pem` outside the repo.

Issues filed to a public target repo are public, including the author's Discord display name. @mentions in the body and the author name are neutralized (a zero-width space after each `@`), so filing notifies no GitHub user.

### Configuration

Instance settings and secrets come from the environment, and the routes from the TOML file at `ROUTES_PATH`. Every key is required: there are no defaults in code. Copy the template and fill it in:

```sh
cp example.env .env
```

Then set the bot token, `GITHUB_ORG`, `ROUTES_PATH` and the `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID` and `GITHUB_APP_PRIVATE_KEY_PATH` values (see [GitHub App setup](#github-app-setup)) in `.env`. `.env` is gitignored; never commit a real token.

| Key | Scope | Type | Meaning |
|---|---|---|---|
| `DISCORD_TOKEN` | instance | string (secret) | Bot token |
| `DISCORD_GUILD_ID` | instance | positive integer | Server the bot serves |
| `UNROUTED_COMMANDS` | instance | `refuse` or `ignore` | A command outside the routes gets a private refusal (`refuse`) or no reply (`ignore`, for [several instances](#run-several-instances) on one bot token) |
| `GITHUB_ORG` | instance | owner name | The org the App is installed in; every route's repo must be in it |
| `GITHUB_APP_ID` | instance | positive integer | GitHub App ID |
| `GITHUB_APP_INSTALLATION_ID` | instance | positive integer | The App's installation ID |
| `GITHUB_APP_PRIVATE_KEY_PATH` | instance | path (secret file) | Path to the App's PEM private key |
| `ROUTES_PATH` | instance | path | Path to the route file |

The route file maps each intake channel to its repo. Copy the template outside the repo and fill it in:

```sh
mkdir -p ~/.config/discord-github-issue-bot && install -m 0644 example.routes.toml ~/.config/discord-github-issue-bot/routes.toml
```

Add one table per intake channel. For `channel_id`, enable Developer Mode in Discord, right-click the channel and **Copy Channel ID**.

| Field | Type | Meaning |
|---|---|---|
| `[routes.<name>]` | table | One route; the name is lowercase letters, digits, `-` or `_`, starting with a letter or digit |
| `channel_id` | positive integer | Intake channel (matched by ID; no two routes may share one) |
| `channel_name` | string | Expected channel name (startup sanity check only) |
| `category` | string | Expected category name (startup sanity check only) |
| `repo` | `owner/name` in `GITHUB_ORG` | Output repo |
| `repo_id` | positive integer | Output repo id |
| `labels.bug` / `labels.feature` | string | Label for `/bug` / `/feature` (a `[routes.<name>.labels]` table) |

Each `labels.*` label must already exist in its route's repo: a label an App requests that doesn't exist may be dropped or auto-created depending on its permissions _(unverified)_. The scratch-repo [smoke test](docs/SMOKE-TEST.md) confirms the label was applied.

Pointing the bot at another channel or repo (for example a test channel) means changing only the route file. The bot reads the file once at startup, so restart it after editing the file.

`.env` uses plain key-equals-value lines, with no quotes and no `export`. Docker's `--env-file` takes each value literally. The shell form below reads the same file correctly only when no value contains spaces, quotes, `$`, backticks or backslashes (the shell expands them); for such a value, use the Docker run, or export that key by hand with single quotes before starting the bot. The shell form runs in a subshell so the token is not left exported in your terminal.

#### Upgrading from single-target config

Configs from before the route file kept the target in `.env`; the bot no longer reads those keys. Move them into a `[routes.<name>]` table in the route file: `DISCORD_CHANNEL_ID` becomes `channel_id`, `DISCORD_CHANNEL_NAME` becomes `channel_name`, `DISCORD_CATEGORY` becomes `category`, `GITHUB_REPO` becomes `repo`, `GITHUB_REPO_ID` becomes `repo_id`, and `GITHUB_LABEL_BUG` / `GITHUB_LABEL_FEATURE` become `labels.bug` / `labels.feature`. Then add `UNROUTED_COMMANDS`, `GITHUB_ORG` and `ROUTES_PATH` to `.env` and delete the old keys.

### Run locally

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
(set -a; . ./.env; set +a; exec .venv/bin/python -m issue_bot)
```

For a local run, set `GITHUB_APP_PRIVATE_KEY_PATH` to the key's host path and `ROUTES_PATH` to the route file's host path (both outside the repo): `example.env`'s `/run/secrets/...` and `/run/config/...` paths exist only inside the container, through the Docker mounts.

### Run with Docker

```sh
docker build -t discord-github-issue-bot .
docker run --rm --env-file .env -v /path/to/key.pem:/run/secrets/github-app-key.pem:ro -v /path/to/routes.toml:/run/config/routes.toml:ro discord-github-issue-bot
```

The container runs as uid 10001, so the mounted key must be readable by that uid. Mount a copy owned by it (`sudo install -o 10001 -m 0400 key.pem key.container.pem`) rather than `chown`ing your own key, which would stop local runs from reading it. The route file is not secret: it needs only to be world-readable. In `.env`, set `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` and `ROUTES_PATH=/run/config/routes.toml` for the container run.

Before going live, run the owner-only [smoke test](docs/SMOKE-TEST.md) against a private scratch repo.

The image contains only the code and its pinned dependencies; no credentials or target config are baked in.

### Run several instances

Several containers from the same image can share one bot token, each serving its own intake channels. They share one `.env` (the same bot token and App), with `UNROUTED_COMMANDS=ignore` set in it, so each container stays silent on commands outside its own routes.

Each container mounts its own route file:

```sh
docker run -d --rm --name issue-bot-a --env-file .env -v /path/to/key.pem:/run/secrets/github-app-key.pem:ro -v /path/to/routes-a.toml:/run/config/routes.toml:ro discord-github-issue-bot
docker run -d --rm --name issue-bot-b --env-file .env -v /path/to/key.pem:/run/secrets/github-app-key.pem:ro -v /path/to/routes-b.toml:/run/config/routes.toml:ro discord-github-issue-bot
docker logs -f issue-bot-a
```

If `docker logs` says `No such container`, the container exited at startup (most often a `configuration error: …`) and `--rm` removed it: run the same command without `-d` to see the error.

```sh
docker stop issue-bot-a issue-bot-b
```

stops both: the image's `STOPSIGNAL SIGINT` triggers discord.py's graceful shutdown, and `--rm` removes them.

1. No channel may appear in two containers' route files. Nothing can check this across containers, and both would answer.
2. A command in a channel no container routes, including any thread (even one in an intake channel), gets Discord's "The application did not respond".
3. Run the same image version in every container: each one syncs the guild's `/bug`/`/feature` at start, and the last sync wins.

One process can also serve several channels from one route file, which is the simpler setup.

## Tests

```sh
.venv/bin/pytest
```

Tests mock Discord: they never connect to the Gateway, post to a channel or create GitHub issues. GitHub is mocked through an injected transport, and a conftest guard fails any test that would make a live GitHub call.
