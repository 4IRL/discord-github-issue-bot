# c4i-issue-bot

A Discord bot for the 4irl server that turns tagged messages in `#c4i-github-issues` (`!bug`, `!feature`) into fleshed-out issues on the `4IRL/chores4irl` GitHub repo and its roadmap. It asks clarifying questions in a thread, then posts the new issue's link back there.

The code itself is target-agnostic: it holds no 4irl values (never as a code default), and their config home is the committed [`example.env`](example.env).

## Status

F1 (channel listener and tag parser) exists: the bot connects to Discord, watches the intake channel and turns each new `!bug` / `!feature` message into an issue candidate. Until F2 (clarifying thread) and F5 (issue filing) land, candidates are only logged, by issue type, message id and message URL.

- The intake channel is matched by `DISCORD_CHANNEL_ID`; its name, category and guild are only checked at startup (a mismatch logs a warning).
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
- `Body:` is optional. It runs to the end of the message and keeps its line breaks.
- Lines outside the two fields are ignored.
- A blank `Title:` (one with no letter or digit) or a blank `Body:` yields to a later line with the same label. Once a label has text, a repeated label is ordinary text.
- A tagged message with no usable `Title:` line is dropped, and the drop is logged by issue type, message id and message URL. F2 will reply in the thread with a format hint.

Direction: [`plans/ROADMAP.md`](plans/ROADMAP.md). Next work: [`plans/META-PLAN.md`](plans/META-PLAN.md).

## Getting started

### Prerequisites

- Python 3.12
- Docker (for the container run)

### Discord setup

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and add a bot to it. Copy the bot token.
2. Under **Bot → Privileged Gateway Intents**, enable **Message Content Intent**. Without it the bot sees empty message text and never finds a tag.
3. Invite the bot to the server with the **View Channel** and **Read Message History** permissions on the intake channel. (F2 will add the thread permissions.)

### Configuration

All configuration comes from the environment, and every key is required: there are no defaults in code. Copy the template and fill it in:

```sh
cp example.env .env
```

Then set the bot token and the intake channel's ID in `.env` (enable Developer Mode in Discord, right-click the channel, **Copy Channel ID**). `.env` is gitignored; never commit a real token.

| Key | Scope | Type | Meaning |
|---|---|---|---|
| `DISCORD_TOKEN` | instance | string (secret) | Bot token |
| `DISCORD_GUILD_ID` | instance | positive integer | Server the bot serves |
| `DISCORD_CHANNEL_ID` | target | positive integer | Intake channel (matched by ID) |
| `DISCORD_CHANNEL_NAME` | target | string | Expected channel name (startup sanity check only) |
| `DISCORD_CATEGORY` | target | string | Expected category name (startup sanity check only) |
| `GITHUB_REPO` | target | `owner/name` | Output repo |
| `GITHUB_REPO_ID` | target | positive integer | Output repo id |
| `GITHUB_LABEL_BUG` | target | string | Label for `!bug` |
| `GITHUB_LABEL_FEATURE` | target | string | Label for `!feature` |

Pointing the bot at another channel or repo (for example a test channel) means changing only `.env`.

`.env` uses plain key-equals-value lines, with no quotes and no `export`. Docker's `--env-file` takes each value literally. The shell form below reads the same file correctly only when no value contains spaces, quotes, `$`, backticks or backslashes (the shell expands them); for such a value, use the Docker run, or export that key by hand with single quotes before starting the bot. The shell form runs in a subshell so the token is not left exported in your terminal.

### Run locally

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
(set -a; . ./.env; set +a; exec .venv/bin/python -m issue_bot)
```

### Run with Docker

```sh
docker build -t issue-bot .
docker run --rm --env-file .env issue-bot
```

The image contains only the code and its pinned dependencies; no credentials or target config are baked in.

## Tests

```sh
.venv/bin/pytest
```

Tests mock Discord: they never connect to the Gateway, post to a channel or create GitHub issues.
