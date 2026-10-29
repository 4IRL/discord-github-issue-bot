# Live smoke test

The owner's procedure for checking the bot against real Discord and GitHub before going live, or after a change to filing or auth. Tests never do this: they mock both services. Only the owner runs these steps, by hand. Each live run needs the owner's explicit go-ahead (CLAUDE.md), and agents never run them.

The run happens against a **private scratch repo** and a **test channel**, never the real target.

## What it writes

- **Startup:** the bot registers `/bug` and `/feature` in the guild `DISCORD_GUILD_ID` names. It overwrites them on every start, and they stay after teardown (see section 5).
- **Probe:** one installation token on GitHub, which expires within an hour. Nothing else. With a Project route (a route with a `project` table) the token also carries `organization_projects: write`.
- **Success checks:** two issues in the scratch repo (three with the optional `@someone` check), and one summary message plus one public thread with one link post in it per report filed with **File** in the test channel; an expired or edited preview writes nothing. The first filing with each band also creates that `complexity:<band>` label in the scratch repo. Each report filed on a Project route also writes one item in the test Project, with Status `Todo` and Effort set to the filed band.
- **Failure check:** one private reply to you. It posts nothing in the test channel and writes nothing to GitHub.
- **Re-runs:** every re-run repeats its writes, except that a `complexity:<band>` label already in the repo is not created again. On a Project route each re-run adds a new test-Project item for each new issue.

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
4. Create a test Project in the 4IRL org (org **Projects → New project**), never Project #2. Its default `Status` field already has a `Todo` option; add an `Effort` single-select field with options `S`, `M`, `L` and `XL`. Link it to `4IRL/issue-bot-scratch` (the Project's **Settings → Manage access**, or the repo's **Projects** tab), and read its number from its URL (`github.com/orgs/4IRL/projects/<number>`).
5. Pick a Discord test channel in a separate test guild, never the live server: the commands are registered in the whole guild and stay there after teardown. The bot needs View Channel, Read Message History, Send Messages, Create Public Threads and Send Messages in Threads there, and must have been invited with the `bot` and `applications.commands` scopes.

### `.env` for a local run

Start from a `.env` copied from `example.env`, which supplies the other required keys, and set these:

```
GITHUB_APP_ID=<App ID>
GITHUB_APP_INSTALLATION_ID=<installation ID>
GITHUB_APP_PRIVATE_KEY_PATH=/home/<you>/.config/discord-github-issue-bot/github-app.pem
GITHUB_ORG=4IRL
UNROUTED_COMMANDS=refuse
ROUTES_PATH=/home/<you>/.config/discord-github-issue-bot/routes.smoke.toml
DISCORD_GUILD_ID=<the test channel's guild ID>
```

Then create `~/.config/discord-github-issue-bot/routes.smoke.toml` with one route for the test channel and the scratch repo:

```toml
[routes.smoke]
channel_id = <test channel ID>
channel_name = "<test channel name>"
category = "<test channel's category>"
repo = "4IRL/issue-bot-scratch"
repo_id = <REPO_ID>

[routes.smoke.labels]
bug = "bug"
feature = "enhancement"

[[routes.smoke.questions.bug]]
label = "Steps to reproduce"
style = "paragraph"
required = true

[[routes.smoke.questions.bug]]
label = "Expected"
style = "paragraph"
required = true

[[routes.smoke.questions.bug]]
label = "Actual"
style = "paragraph"
required = true

[[routes.smoke.questions.bug]]
label = "Device / browser"
style = "short"
required = false

[[routes.smoke.questions.feature]]
label = "Who is it for?"
style = "short"
required = true

[[routes.smoke.questions.feature]]
label = "What problem does it solve?"
style = "paragraph"
required = true

[[routes.smoke.questions.feature]]
label = 'What does "done" look like?'
style = "paragraph"
required = false

[routes.smoke.project]
number = <test Project number>
status_field = "Status"
status = "Todo"
effort_field = "Effort"
```

The `questions` tables are required: without them the bot exits at startup with code 2. The `[routes.smoke.project]` table makes the scratch route a Project route, pointed at the test Project; the roadmap checks in section 2 need it. It sets no `track_field` (and the test Project has no Track field), so the smoke run does not exercise the preview's Track dropdown or the Track write.

The bot syncs `/bug` and `/feature` to the `DISCORD_GUILD_ID` guild, so leaving example.env's value would register them in the live server. Set it to the test guild's ID.

The two run modes read `.env` differently:

- **Local run.** The README's command loads `.env` through the shell: quotes are stripped, a leading `~` is expanded, and an unquoted space or `$` breaks the value. Write the full paths (`GITHUB_APP_PRIVATE_KEY_PATH` and `ROUTES_PATH`) with no spaces. Don't point them at `/run/secrets/...` or `/run/config/...`, which exist only inside the container.
- **Container run.** Docker's `--env-file` takes every value literally. A `~`, quotes or a trailing comment become part of the path. The values must be exactly `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` and `ROUTES_PATH=/run/config/routes.toml` (section 4).

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

For a Project route, send `"permissions": {"issues": "write", "organization_projects": "write"}` in the body instead, which is what the bot asks for on that route.

The filter drops `token`, so the token is never printed. If one ever is, don't paste it anywhere.

**The probe passes when all of these hold:**

- The status line is `201`.
- `expires_at` ends in `Z`.
- `repositories` lists only the scratch repo.
- `permissions` holds `issues: write` and nothing broader (for a Project route, `issues: write` and `organization_projects: write`). A `metadata: read` entry may also appear.

If any of these differs, stop and fix it before going on.

## 2. Local run

```sh
(set -a; . ./.env; set +a; exec .venv/bin/python -m issue_bot)
```

The log shows `synced 2 commands to guild <DISCORD_GUILD_ID>`. In the test channel:

1. Run `/bug`. The form shows Title and the route's bug questions (Steps to reproduce, Expected, Actual, Device / browser). Fill in the Title and the required answers, leave **Device / browser** blank, and submit.
   - A private preview appears, reading "Here's your report as it will be filed. Pick a complexity if the suggested one is off; **File** posts it; **Edit** changes it. This preview expires in 10 minutes.", with the issue body below it, `(link added when filed)` in place of the summary link and a **Complexity** field showing the suggested band. Nothing is posted in the channel yet.
   - Press a band button other than the highlighted one (S, M, L or XL). The pressed button is now highlighted and the Complexity field shows your choice; note the band.
   - Press **Edit**. The form reopens with your Title and answers filled in. Change one answer and submit. The same preview message updates in place with the changed answer, and no second message appears.
   - Press **File**. The preview changes to "Filing your report…". The filed issue carries the `complexity:<band>` label you chose.

   Then do the same with `/feature` (Who is it for?, What problem does it solve?, What does "done" look like?), and check the following:

   | Where | What to see |
   |---|---|
   | Discord summary | A message reading "New bug from @\<you\>: \<Title\>" ("New feature" for `/feature`), with the type in bold; the mention does not ping |
   | Discord thread | A thread on each summary, with one bot message `Filed as GitHub issue #<n> (complexity <band>): <title>`, with the band the preview showed, and the issue link on the next line, and no preview card. On the Project route a third line reads "Added to the roadmap." (`ROADMAP_ADDED_NOTE` in `issue_bot/threads.py`) |
   | Discord confirmation | A private "Thanks! Your report is posted: <summary link>" that only you see |
   | Issue title | The modal's Title |
   | Issue body | Opens with ``Reported by `<display name>` in Discord: <summary message link>``, then `---`, then one `### <question>` section per answered question, with the edited answer; the blank optional question has no section |
   | Issue label | The type label (`bug` on the `/bug` issue, `enhancement` on the `/feature` one) plus exactly one `complexity:<band>` label, matching the band the preview showed |
   | Issue author | `<app-slug>[bot]` |
   | Test Project | Each filed issue appears as an item with Status `Todo` and Effort set to the band the preview showed (the scratch route points at the test Project, never Project #2 or the live channel) |
   | Log | At startup, `github project ok for repo_id=… project=…`; then `previewed bug …` and `previewed feature …` lines (one per submit, including each Edit submit), then one `filed bug …` and one `filed feature …` INFO line with the issue URL, each followed by one `added <type> message_id=… to the roadmap issue=…` INFO line, and no member text |

2. In the modal, type past 100 characters in the Title. The field stops at 100 characters. Cancel the modal.
3. Run `/bug` in another channel. You get a private refusal ("Reports go in the intake channel: run this command there."), no modal opens, and the log shows `refused bug outside the intake channel …`.
4. Optionally, an answer containing `@someone`, filed with **File**. It files a third issue, and nobody is notified.
5. Run `/bug`, submit the form and leave the preview for 10 minutes without pressing anything. That same preview message changes to "This preview expired, so nothing was filed. Run the command again to report it.", keeps the body and loses its buttons. Nothing is posted in the channel or filed, and the log shows `preview expired bug …`.
6. Run `/bug`, submit, press **Edit**, submit again and leave the new preview for 10 minutes. That same message says it expired, and nothing is filed.

## 3. Failure path

1. Stop the bot, set a wrong `GITHUB_APP_INSTALLATION_ID` in `.env` and restart it. The startup log shows an ERROR `github access check failed for repo_id=…: GitHubError stage=token status=…`, and the bot keeps running.
2. Run one `/bug`. No form opens; you get the private reply "Sorry, reports can't be filed to GitHub right now, so the form didn't open. Try again later." The log shows `filing unavailable for bug interaction_id=…: GitHubError stage=token status=…` with no member text. Nothing is posted in the channel and nothing goes to GitHub.
3. Restore the right ID.

A filing failure after File (the `FILING_ERROR_REPLY` posted in the thread, or as a reply to the summary when no thread opened) can't be triggered this way, since the check now stops the form first; the unit tests cover it.

Restart the bot after every `.env` or route-file change. It reads its configuration only at startup.

## 4. Container run

Stop the local bot first. Two processes on one bot token both receive each command: one opens the modal and the other's reply fails (logged by the command tree's error handler), so a report is filed once. Still, never run two for the smoke test. README [Run several instances](../README.md#run-several-instances) covers deliberate multi-container runs.

The image runs as uid 10001, which can't read your `0600` key. Give the container its own copy rather than changing the original's owner, because a key `chown`ed to 10001 is no longer readable by you for local runs:

```sh
sudo install -o 10001 -m 0400 ~/.config/discord-github-issue-bot/github-app.pem ~/.config/discord-github-issue-bot/github-app.container.pem
```

Build the image first, from the branch you're testing. Rebuild after any code change: the image is a snapshot taken when it is built.

```sh
docker build -t discord-github-issue-bot .
```

Set `GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem` and `ROUTES_PATH=/run/config/routes.toml` in `.env`. Before starting the bot, check the literal values and confirm the container can read the key:

```sh
grep '^GITHUB_APP_PRIVATE_KEY_PATH=' .env      # exactly: GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-key.pem
grep '^ROUTES_PATH=' .env                      # exactly: ROUTES_PATH=/run/config/routes.toml
ls -l ~/.config/discord-github-issue-bot/github-app.container.pem   # a regular file (-r--------) owned by 10001, not a "d" directory
docker run --rm --entrypoint sh \
  -v ~/.config/discord-github-issue-bot/github-app.container.pem:/run/secrets/github-app-key.pem:ro \
  discord-github-issue-bot -c 'test -r /run/secrets/github-app-key.pem && echo readable || echo NOT-readable'
```

Then run:

```sh
docker run --rm --env-file .env \
  -v ~/.config/discord-github-issue-bot/github-app.container.pem:/run/secrets/github-app-key.pem:ro \
  -v ~/.config/discord-github-issue-bot/routes.smoke.toml:/run/config/routes.toml:ro \
  discord-github-issue-bot
```

Submit one `/bug` and press **File** on the preview. It is filed as in section 2. Set the key path and `ROUTES_PATH` back to the host paths afterwards.

For a quick test, add `--user "$(id -u)"` instead and mount the original `github-app.pem`. The container then runs as you.

## 5. Record and tear down

1. In the PR description, record:
   - the scratch repo name
   - each filed issue number and what each check showed: title, author line, type label, `complexity:<band>` label (and whether the band was pressed), `[bot]` author and the 100-character Title cap
   - the teardown date

   Do this before deleting the repo, because the issue links stop working once it's gone.
2. Delete the test Project (or its items).
3. Remove the scratch repo from the installation's selected repositories (org **Settings → GitHub Apps → Configure**), then delete the repo. Keep the App and its installation for the real target.
4. Restore `ROUTES_PATH` to the real route file and the host key path. Delete the container key copy unless you'll keep running the bot in Docker: `sudo rm ~/.config/discord-github-issue-bot/github-app.container.pem`.
5. Delete the smoke-test summary messages and threads, or leave them if the test channel is private to you.
6. The test guild keeps `/bug` and `/feature`, which is harmless (they answer "The application did not respond" while the bot is down), or you can delete the test guild. Restore `.env`, but don't start the bot with the real config until the owner approves the live deploy and has posted the cutover notice (step 7): that start syncs the commands to the live server.
7. Cutover: before the live deploy, the owner posts a notice in the live intake channel that `!bug` and `!feature` no longer work. Agents never post.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Unable to find image 'discord-github-issue-bot:latest' locally` | The image was never built. Run `docker build -t discord-github-issue-bot .` first. |
| `configuration error: GITHUB_APP_PRIVATE_KEY_PATH must name a readable RSA private key` (exit 2), local run | The `.env` path is wrong, often still the container path, or you can't read the file, for example after a `chown 10001`. Run the `test -r` check in section 0. |
| The same error, container run | Run the three checks in section 4. `.env` must say exactly `/run/secrets/github-app-key.pem`. The `-v` source must be a regular file owned by 10001: if it was missing, Docker created an empty directory there, so remove it with `sudo rmdir` and recreate the copy. The key file must start with `-----BEGIN RSA PRIVATE KEY-----`, which `sudo head -c 31 <file>` shows without printing the key. |
| `/bug` and `/feature` are missing | The commands weren't synced to this guild. The bot must be invited with the `applications.commands` scope, `DISCORD_GUILD_ID` must be the test channel's guild, and the startup log must show `synced 2 commands to guild …` (a `could not sync commands …` ERROR names the failure). If the log is right, reload the Discord client, which caches the command list. |
| The command is refused in the right channel | A command run inside a thread, including a summary's thread, is refused: run it in the channel itself. Otherwise the route's `channel_id` doesn't match the channel: copy the channel ID again into the route file and restart the bot. |
| "The application did not respond" in a thread or an unrouted channel | With `UNROUTED_COMMANDS=ignore` the bot stays silent there: run the command in the routed channel itself. |
| `/bug` says reports can't be filed | The bot can't get a GitHub token for the repo. Check the startup log's `github access check failed …` line (its `status`) and the `filing unavailable …` lines, then the App ID, installation ID, the route's `repo_id` in the route file and private key; the token probe in section 1 shows the same failure. On a route with a `project` table, a missing or not-yet-accepted **Projects: Read and write** grant also fails the token mint. Restart the bot after fixing `.env` or the route file. |
| `configuration error: routes.<name>.repo must be in GITHUB_ORG` (exit 2) | The route's `repo` owner isn't `GITHUB_ORG`. Point the route at a repo in that org (for the smoke test, `4IRL/issue-bot-scratch`) or fix `GITHUB_ORG`. |
| `configuration error: ROUTES_PATH must name a readable TOML route file` (exit 2) | A wrong path, or a TOML syntax error. In a container run, also a `-v` route-file mount left off, a `-v` source path that didn't exist (Docker then created an empty directory there: remove it with `sudo rmdir` and create the file), or a route file uid 10001 can't read. To find a syntax error, run from the repo root `.venv/bin/python -c 'import sys, tomllib; sys.excepthook = lambda t, e, tb: print(f"{t.__name__}: {e}"); tomllib.load(open(sys.argv[1], "rb")); print("ok")' <route file>`. It prints only the parser's one-line position message, e.g. `TOMLDecodeError: Invalid value (at line 2, column 14)` (exit 1); a valid file prints `ok`, and a missing file prints a `FileNotFoundError: …` line. A file saved with a UTF-8 BOM fails at line 1, column 1 (`TOMLDecodeError: Invalid statement (at line 1, column 1)`): re-save it as UTF-8 without a BOM. |
| Pressing File gets a private error and no summary | The bot can't post in the channel. Check the startup log for `connected as …` with no channel ERROR or WARNING after it, and that the bot has View Channel, Read Message History, Send Messages, Create Public Threads and Send Messages in Threads there. |
| The issue is filed but no link appears in the thread | The bot couldn't post it. Check the log for `could not send issue link …` (its status and code): the thread post needs Send Messages in Threads; the reply on the summary (when no thread opened) needs Send Messages and Read Message History. |
| The probe prints `JWT generation failed` | The key couldn't be loaded. Check the `<KEY_PATH>` argument and the Python error above that line. |
| The probe returns 401 | The JWT was rejected. The App ID may be wrong, the key may belong to another App, or the system clock may be off by more than a minute. |
| The probe returns 400 | A `<…>` placeholder was left in the command, or the JSON body is malformed. |
| The probe returns 403 | The App is suspended, or the org hasn't approved its permissions. |
| The probe returns 404 | The installation ID is wrong, or the installation belongs to another App. |
| The probe returns 422 | The scratch repo isn't in the installation's selected repositories, or the App lacks Issues: write; or, with the Project-route payload, the App lacks **Projects: Read and write** or the installation hasn't accepted it. |
| An issue is filed without its type label | The type label (`bug` / `enhancement`) doesn't exist in the repo. Create it. |
| An issue is filed without its `complexity:<band>` label and the log shows `could not create complexity label … stage=label` | GitHub refused to create that label. Add it to the filed issue by hand rather than re-running, which files a second issue; the next filing with that band tries again. A 401 is a stale token, which the bot drops, so the next filing gets a fresh one. A 403 or 404 means the token can't create labels in that repo: check that the App has Issues: write there (that this covers labels is proven only by this run). With `stage=token` or `status=None` instead, the token request or the network failed. |
| The issue is filed, the thread says "Couldn't finish adding it to the roadmap; the owner can fix it by hand." and the log shows `could not add … to the roadmap … stage=project…` or `… stage=token …` | The issue is filed, so finish by hand rather than re-running, which files a second issue. After `stage=project`, add the issue to the Project and set its Status and Effort (and its Track, when the log line ends with `track='<option>'`); after `stage=project-item` or `stage=token`, or the stage-less form (`could not add … to the roadmap issue=…: <type>`), check whether the issue is already on the Project, add it if not, then set its Status and Effort (and its Track, when the log line ends with `track='<option>'`); after `stage=project-field` the item is already on the Project, so set its Status and Effort there; after `stage=project-track` the item is on the Project with its Status and Effort, so set its Track there to the option the log line's `track='<option>'` names. With `stage=project status=200` the route's `project` table doesn't match GitHub: its `number` names no Project in `GITHUB_ORG`, or a field or option name doesn't match the Project; with `stage=project-track status=200` the picked Track option is no longer on the Project (deleted or renamed since the bot read it) or GitHub's reply was malformed. After a `stage=project-item`, `stage=project-field` or `stage=project-track` failure the bot looks the Project's ids up again on the next filing, so a field or option deleted and re-created on GitHub is picked up without a restart. |
| `github project check failed for repo_id=… project=…` at startup | The same causes as the row above: with `stage=project status=200`, the route's `project` table doesn't match GitHub. It runs only after that route's `github access check …` passed (a missing or not-yet-accepted **Projects: Read and write** grant shows as `github access check failed …` instead). The bot keeps running, and filings on that route are filed but get the roadmap failure note until the mismatch is fixed: a fix on the Project itself is picked up on the next filing (a failed lookup is not cached), a route-file fix after a restart. |
