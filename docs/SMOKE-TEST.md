# Live smoke test

The owner's procedure for checking the bot against real Discord and GitHub before going live, or after a change to filing or auth. Tests never do this: they mock both services. Only the owner runs these steps, by hand. Each live run needs the owner's explicit go-ahead (CLAUDE.md), and agents never run them.

The run happens against a **private scratch repo** and a **test channel**, never the real target.

## What it writes

- **Startup:** the bot registers `/bug` and `/feature` in the guild `DISCORD_GUILD_ID` names. It overwrites them on every start, and they stay after teardown (see section 5).
- **Probe:** one installation token on GitHub, which expires within an hour. Nothing else.
- **Success checks:** two issues in the scratch repo (three with the optional `@someone` check), and one summary message plus one public thread per submission in the test channel.
- **Failure check:** one private reply to you. It posts nothing in the test channel and writes nothing to GitHub.
- **Re-runs:** every re-run repeats its writes.

## 0. One-time setup

### GitHub App and private key

1. Create and install the App as in the README's [GitHub App setup](../README.md#github-app-setup). Create one App under the 4IRL org, named for the bot, since issues show its author as `<app-slug>[bot]`. That one App serves every target repo, so don't make one per repo. Install it with **Only select repositories**. The installation ID stays the same when repos are added or removed.
2. On the App's settings page, under **Private keys**, click **Generate a private key**. The browser downloads `<app-slug>.<date>.private-key.pem`. GitHub keeps only the public half, so a lost or leaked key is replaced by generating a new one and deleting the old.
3. Store the key outside the repo, in the Linux filesystem, readable only by you. On WSL, don't keep it under `/mnt/c/...`: `chmod` has no real effect on the Windows mount. Delete the downloaded copy afterwards.

   ```sh
   mkdir -p ~/.config/discord-github-issue-bot
   chmod 700 ~/.config/discord-github-issue-bot
   mv <downloaded>.private-key.pem ~/.config/discord-github-issue-bot/github-app.pem
   chmod 600 ~/.config/discord-github-issue-bot/github-app.pem
   ```

### Scratch repo and test channel

1. Create a **private** repo in the 4IRL org, for example `4IRL/issue-bot-scratch`.
2. Go to org **Settings → GitHub Apps → \<your App\> → Configure** and add the scratch repo to the selected repositories.
3. Get the repo ID and check the labels:

   ```sh
   gh api repos/4IRL/issue-bot-scratch --jq .id                         # REPO_ID
   gh api repos/4IRL/issue-bot-scratch/labels/bug --jq .name            # expect: bug
   gh api repos/4IRL/issue-bot-scratch/labels/enhancement --jq .name    # expect: enhancement
   ```

   Create any label that returns 404.
4. Pick a Discord test channel in a separate test guild, never the live server: the commands are registered in the whole guild and stay there after teardown. The bot needs View Channel, Send Messages, Create Public Threads and Send Messages in Threads there, and must have been invited with the `bot` and `applications.commands` scopes.

### `.env` for a local run

Start from a `.env` copied from `example.env`, which supplies the other required keys, and set these:

```
GITHUB_APP_ID=<App ID>
GITHUB_APP_INSTALLATION_ID=<installation ID>
GITHUB_APP_PRIVATE_KEY_PATH=/home/<you>/.config/discord-github-issue-bot/github-app.pem
GITHUB_REPO=4IRL/issue-bot-scratch
GITHUB_REPO_ID=<REPO_ID>
DISCORD_GUILD_ID=<the test channel's guild ID>
DISCORD_CHANNEL_ID=<test channel ID>
DISCORD_CHANNEL_NAME=<test channel name>
DISCORD_CATEGORY=<test channel's category>
```

The bot syncs `/bug` and `/feature` to the `DISCORD_GUILD_ID` guild, so leaving example.env's value would register them in the live server. Set it to the test guild's ID.

The two run modes read `.env` differently:

- **Local run.** The README's command loads `.env` through the shell: quotes are stripped, a leading `~` is expanded, and an unquoted space or `$` breaks the value. Write the full path with no spaces. Don't point it at `/run/secrets/...`, which exists only inside the container.
- **Container run.** Docker's `--env-file` takes every value literally. A `~`, quotes or a trailing comment become part of the path. The value must be exactly `/run/secrets/github-app-key.pem` (section 4).

To check the local run, which loads `.env` the same way the bot is started, without printing the key:

```sh
(set -a; . ./.env; set +a; test -r "$GITHUB_APP_PRIVATE_KEY_PATH" && echo readable || echo "NOT readable: $GITHUB_APP_PRIVATE_KEY_PATH")
```

This check doesn't cover the container run. Check that separately in section 4.

## 1. Token probe

The probe checks the App's permissions and the token request shape before the bot files anything. Run it from the repo root with the venv installed, replacing `<APP_ID>`, `<KEY_PATH>`, `<INSTALLATION_ID>` and `<REPO_ID>`:

```sh
JWT=$(.venv/bin/python -c 'import sys, time; from cryptography.hazmat.primitives import serialization; from issue_bot.github import app_jwt; k = serialization.load_pem_private_key(open(sys.argv[2], "rb").read(), None); print(app_jwt(int(sys.argv[1]), k, time.time()))' <APP_ID> <KEY_PATH>)
test -n "$JWT" || echo "JWT generation failed: fix the error above before running curl"
curl -s -X POST -D /dev/stderr -H "Authorization: Bearer $JWT" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" https://api.github.com/app/installations/<INSTALLATION_ID>/access_tokens -d '{"repository_ids": [<REPO_ID>], "permissions": {"issues": "write"}}' | python3 -c 'import json, sys; d = json.load(sys.stdin); d.pop("token", None); print(json.dumps(d, indent=1))'
```

The filter drops `token`, so the token is never printed. If one ever is, don't paste it anywhere.

**The probe passes when all of these hold:**

- The status line is `201`.
- `expires_at` ends in `Z`.
- `repositories` lists only the scratch repo.
- `permissions` holds `issues: write` and nothing broader. A `metadata: read` entry may also appear.

If any of these differs, stop and fix it before going on.

## 2. Local run

```sh
(set -a; . ./.env; set +a; exec .venv/bin/python -m issue_bot)
```

The log shows `synced 2 commands to guild <DISCORD_GUILD_ID>`. In the test channel:

1. Run `/bug` and submit the modal with a Title and a Description, then do the same with `/feature`. Then check the following:

   | Where | What to see |
   |---|---|
   | Discord summary | A message reading "New bug from @\<you\>: \<Title\>" ("New feature" for `/feature`), with the type in bold; the mention does not ping |
   | Discord thread | A thread on each summary, with **nothing** posted in it (the link post comes with F7) |
   | Discord confirmation | A private "Thanks! Your report is posted: <summary link>" that only you see |
   | Issue title | The modal's Title |
   | Issue body | Opens with ``Reported by `<display name>` in Discord: <summary message link>``, then `---`, then the Description |
   | Issue label | `bug` on the `/bug` issue, `enhancement` on the `/feature` one |
   | Issue author | `<app-slug>[bot]` |
   | Log | One `filed bug …` and one `filed feature …` INFO line with the issue URL, and no member text |

2. In the modal, type past 100 characters in the Title. The field stops at 100 characters. Cancel the modal.
3. Run `/bug` in another channel. You get a private refusal ("Reports go in the intake channel: run this command there."), no modal opens, and the log shows `refused bug outside the intake channel …`.
4. Optionally, a Description containing `@someone`. It files a third issue, and nobody is notified.

## 3. Failure path

1. Stop the bot, set a wrong `GITHUB_APP_INSTALLATION_ID` in `.env` and restart it. The startup log shows an ERROR `github access check failed for repo_id=…: GitHubError stage=token status=…`, and the bot keeps running.
2. Run one `/bug`. No form opens; you get the private reply "Sorry, reports can't be filed to GitHub right now, so the form didn't open. Try again later." The log shows `filing unavailable for bug interaction_id=…: GitHubError stage=token status=…` with no member text. Nothing is posted in the channel and nothing goes to GitHub.
3. Restore the right ID.

A filing failure after a submit (the thread's `FILING_ERROR_REPLY`) can't be triggered this way, since the check now stops the form first; the unit tests cover it.

Restart the bot after every `.env` change. It reads its configuration only at startup.

## 4. Container run

Stop the local bot first. Two processes on one bot token both receive each command: one opens the modal and the other's reply fails (logged by the command tree's error handler), so a report is filed once. Still, never run two.

The image runs as uid 10001, which can't read your `0600` key. Give the container its own copy rather than changing the original's owner, because a key `chown`ed to 10001 is no longer readable by you for local runs:

```sh
sudo install -o 10001 -m 0400 ~/.config/discord-github-issue-bot/github-app.pem ~/.config/discord-github-issue-bot/github-app.container.pem
```

Build the image first, from the branch you're testing. Rebuild after any code change: the image is a snapshot taken when it is built.

```sh
docker build -t discord-github-issue-bot .
```

Set `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` in `.env`. Before starting the bot, check the literal value and confirm the container can read the key:

```sh
grep '^GITHUB_APP_PRIVATE_KEY_PATH=' .env      # exactly: GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem
ls -l ~/.config/discord-github-issue-bot/github-app.container.pem   # a regular file (-r--------) owned by 10001, not a "d" directory
docker run --rm --entrypoint sh \
  -v ~/.config/discord-github-issue-bot/github-app.container.pem:/run/secrets/github-app-key.pem:ro \
  discord-github-issue-bot -c 'test -r /run/secrets/github-app-key.pem && echo readable || echo NOT-readable'
```

Then run:

```sh
docker run --rm --env-file .env \
  -v ~/.config/discord-github-issue-bot/github-app.container.pem:/run/secrets/github-app-key.pem:ro \
  discord-github-issue-bot
```

Submit one `/bug`. It is filed as in section 2. Set the key path back to the host path afterwards.

For a quick test, add `--user "$(id -u)"` instead and mount the original `github-app.pem`. The container then runs as you.

## 5. Record and tear down

1. In the PR description, record:
   - the scratch repo name
   - each filed issue number and what each check showed: title, author line, label, `[bot]` author and the 100-character Title cap
   - the teardown date

   Do this before deleting the repo, because the issue links stop working once it's gone.
2. Remove the scratch repo from the installation's selected repositories (org **Settings → GitHub Apps → Configure**), then delete the repo. Keep the App and its installation for the real target.
3. Restore `.env` to the real target repo, intake channel and host key path. Delete the container key copy unless you'll keep running the bot in Docker: `sudo rm ~/.config/discord-github-issue-bot/github-app.container.pem`.
4. Delete the smoke-test summary messages and threads, or leave them if the test channel is private to you.
5. The test guild keeps `/bug` and `/feature`, which is harmless (they answer "The application did not respond" while the bot is down), or you can delete the test guild. Restore `.env`, but don't start the bot with the real config until the owner approves the live deploy and has posted the cutover notice (step 6): that start syncs the commands to the live server.
6. Cutover: before the live deploy, the owner posts a notice in the live intake channel that `!bug` and `!feature` no longer work. Agents never post.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Unable to find image 'discord-github-issue-bot:latest' locally` | The image was never built. Run `docker build -t discord-github-issue-bot .` first. |
| `configuration error: GITHUB_APP_PRIVATE_KEY_PATH must name a readable RSA private key` (exit 2), local run | The `.env` path is wrong, often still the container path, or you can't read the file, for example after a `chown 10001`. Run the `test -r` check in section 0. |
| The same error, container run | Run the three checks in section 4. `.env` must say exactly `/run/secrets/github-app-key.pem`. The `-v` source must be a regular file owned by 10001: if it was missing, Docker created an empty directory there, so remove it with `sudo rmdir` and recreate the copy. The key file must start with `-----BEGIN RSA PRIVATE KEY-----`, which `sudo head -c 31 <file>` shows without printing the key. |
| `/bug` and `/feature` are missing | The commands weren't synced to this guild. The bot must be invited with the `applications.commands` scope, `DISCORD_GUILD_ID` must be the test channel's guild, and the startup log must show `synced 2 commands to guild …` (a `could not sync commands …` ERROR names the failure). If the log is right, reload the Discord client, which caches the command list. |
| The command is refused in the right channel | A command run inside a thread, including a summary's thread, is refused: run it in the channel itself. Otherwise `DISCORD_CHANNEL_ID` doesn't match the channel: copy the channel ID again and restart the bot. |
| `/bug` says reports can't be filed | The bot can't get a GitHub token for the repo. Check the startup log's `github access check failed …` line (its `status`) and the `filing unavailable …` lines, then the App ID, installation ID, `GITHUB_REPO_ID` and private key; the token probe in section 1 shows the same failure. Restart the bot after fixing `.env`. |
| A submit gets a private error and no summary | The bot can't post in the channel. Check the startup log for `connected as …` with no channel ERROR or WARNING after it, and that the bot has View Channel, Send Messages, Create Public Threads and Send Messages in Threads there. |
| The probe prints `JWT generation failed` | The key couldn't be loaded. Check the `<KEY_PATH>` argument and the Python error above that line. |
| The probe returns 401 | The JWT was rejected. The App ID may be wrong, the key may belong to another App, or the system clock may be off by more than a minute. |
| The probe returns 400 | A `<…>` placeholder was left in the command, or the JSON body is malformed. |
| The probe returns 403 | The App is suspended, or the org hasn't approved its permissions. |
| The probe returns 404 | The installation ID is wrong, or the installation belongs to another App. |
| The probe returns 422 | The scratch repo isn't in the installation's selected repositories, or the App lacks Issues: write. |
| An issue is filed without its label | The label doesn't exist in the repo. Create it. |
