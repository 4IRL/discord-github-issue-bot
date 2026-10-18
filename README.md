# discord-github-issue-bot

A Discord bot that turns tagged messages (`!bug`, `!feature`) in a configured intake channel of a Discord server into fleshed-out GitHub issues in a configured repo of the 4IRL GitHub org, and onto that repo's roadmap. It asks clarifying questions in a thread, then posts the new issue's link back there. Its first target (an example) is `#c4i-github-issues` in the 4irl server → `4IRL/chores4irl`.

The code itself is target-agnostic: it holds no 4irl values (never as a code default), and their config home is the committed [`example.env`](example.env).

## Status

F1 (channel listener and tag parser), F2 (thread per tagged message) and F5 (issue filing) exist: the bot connects to Discord, watches the intake channel and turns each new `!bug` / `!feature` message into an issue candidate. Each candidate gets a public thread on its message, named from the title (truncated to 100 characters), and is then filed as an issue in the target repo with the tag's label. A message that already has a thread reuses it. A filed issue is logged by issue type, message id, message URL, thread id and issue URL. If filing fails, the bot posts a fixed error reply in the thread, when the thread was opened. Posting the issue's link back in the thread comes with F7.

- The intake channel is matched by `DISCORD_CHANNEL_ID`; its name, category and guild are only checked at startup (a mismatch logs a warning; a channel the bot cannot see logs an error).
- Edited messages are ignored, and so are messages inside threads, from bots or webhooks, and system messages.
- The first recognized tag decides the issue type; every tag is stripped from the title and body.

### Message format

A message files an issue only in this structured form. The tag can go anywhere; the labels are case-insensitive and may be bolded.

```text
!feature
Title: Sharing/Inviting to UTubs
Body: allow easy sharing/inviting to UTubs for members outside the UTub
```

- `Title:` is required and is one line.
- `Body:` is optional and keeps its line breaks. It runs to the end of the message, or to a later `Title:` line while the title is still missing or blank.
- Lines outside the two fields are ignored.
- A blank `Title:` (one with no letter or digit) or a blank `Body:` yields to a later line with the same label. Once a label has text, a repeated label is ordinary text inside the Body and is ignored elsewhere.
- A tagged message with no usable `Title:` line files no issue: the bot opens a `Format help: !<tag>` thread on it, replies with the expected format, and logs it by issue type, message id, message URL and thread id.

Direction: [`plans/ROADMAP.md`](plans/ROADMAP.md). Next work: [`plans/META-PLAN.md`](plans/META-PLAN.md).

### Known limits

- No retry or dedup until Phase 4, so a timeout can leave an issue filed after an error reply.
- Messages sent while the bot is down are not filed.
- An edit after filing does not update the issue.

## Getting started

### Prerequisites

- Python 3.12
- Docker (for the container run)

### Discord setup

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and add a bot to it. Copy the bot token.
2. Under **Bot → Privileged Gateway Intents**, enable **Message Content Intent**. Without it the bot sees empty message text and never finds a tag.
3. Invite the bot to the server with the **View Channel**, **Read Message History**, **Create Public Threads** and **Send Messages in Threads** permissions on the intake channel. Threads use the channel's default auto-archive duration.

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
| `GITHUB_LABEL_BUG` | target | string | Label for `!bug` |
| `GITHUB_LABEL_FEATURE` | target | string | Label for `!feature` |

Each `GITHUB_LABEL_*` label must already exist in the target repo: a label an App requests that doesn't exist may be dropped or auto-created depending on its permissions _(unverified)_. The scratch-repo smoke test in the F5 plan's **Manual checks** confirms the label was applied.

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

The container runs as uid 10001, so the host key file must be readable by that uid: prefer `sudo chown 10001 key.pem && chmod 0400 key.pem`; use `chmod 0444` only on a file inside a `0700` directory you own.

The image contains only the code and its pinned dependencies; no credentials or target config are baked in.

## Tests

```sh
.venv/bin/pytest
```

Tests mock Discord: they never connect to the Gateway, post to a channel or create GitHub issues. GitHub is mocked through an injected transport, and a conftest guard fails any test that would make a live GitHub call.
