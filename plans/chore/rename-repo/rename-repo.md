# Rename to discord-github-issue-bot (F9)

## Summary
Rename the project from `c4i-issue-bot` to `discord-github-issue-bot` (the name the owner
settled on at planning, 2026-10-18, in place of META-PLAN's provisional
`discord-github-issue-management-bot`). The repo's own docs (README, CLAUDE.md, ROADMAP,
META-PLAN title and *PR link form*) are updated, and the Docker image tag too. README and
ROADMAP describe the portable function: any channel in the 4irl server → any repo in the
4IRL org, with `#c4i-github-issues` → `4IRL/chores4irl` as the first, example target. The
GitHub rename, folder move and agent-write-denied config are owner steps (Owner checklist).

## Research Findings
Research was done inline: the change is docs-only in a small Python repo, so no subagents.
- Old-name hits in tracked files outside `plans/`: the `README.md` and `CLAUDE.md` titles and
  the `.claude/settings.json` sandbox `allowWrite` entry (tracked, but agent sessions can't
  write it, so the owner edits it; DD-2). No `.py`, test, `Dockerfile` or `pyproject.toml` mentions the name.
  The package is already `issue_bot`.
- The Docker image tag is `issue-bot` (README § *Run with Docker*); the Dockerfile names no
  image.
- `plans/ROADMAP.md` says `c4i-issue-bot` in its title and End state, and
  `discord-github-issue-management-bot` in the End state and the Phase 1.5 rename bullet.
- `.venv/` (gitignored) has the old absolute folder path in `pyvenv.cfg` and its script
  shebangs, so it breaks after the folder move and must be recreated. This plan therefore
  checks the end state with `git grep` (tracked files only), not a plain `grep -r`, which
  would hit `.venv/`.
- `c4i-github-issues` (channel) and `C4I` (category) are config values in `example.env`.
  They stay, per F9 open risk (c).
- F9's Assumed starting state, checked 2026-10-18: `git stash list` is empty, no other
  worktree exists and no PR is open. Open PRs are re-checked right before the GitHub rename
  (Owner checklist).

## Steps

### 1. README and CLAUDE.md describe the portable bot under its new name
Retitle both docs and rewrite their opening paragraph around the portable function.

**To-do:**
- [x] Owner's settings edit is present (DD-2, checked first per DD-4 so a stop happens
  before any edit or commit). `.claude/settings.json` is write-denied to agents, so the owner
  hand-edits it on this branch: `allowWrite` becomes
  `["/home/rmila/Code/c4i-issue-bot", "/home/rmila/Code/discord-github-issue-bot", "/tmp"]`
  (both paths, so this session stays writable and a session in the new folder is too; one
  entry per line is fine). Check:
  `.venv/bin/python -c 'import json,sys;w=json.load(open(".claude/settings.json"))["sandbox"]["filesystem"]["allowWrite"];sys.exit(0 if {"/home/rmila/Code/c4i-issue-bot","/home/rmila/Code/discord-github-issue-bot"}<=set(w) else 1)'`
  exits 0 (it parses the JSON and needs both paths in `allowWrite`; exit 1 or a traceback
  fails), and `git diff --name-only $(git merge-base main HEAD) -- .claude/settings.json`
  prints `.claude/settings.json` (this covers an unstaged, staged or committed edit). Stage it with
  this step's commit: `git add -- .claude/settings.json` (a no-op if it is already
  committed). If the new path is missing or the JSON is invalid, leave this box unticked,
  write directly under it
  `UNRESOLVED — requires user decision/action: owner must add /home/rmila/Code/discord-github-issue-bot to .claude/settings.json allowWrite (keeping the old path)`,
  end your final report with that same line, and stop. On a later run where the gate passes,
  delete that marker line before ticking the box. **Resume:** after the owner's edit, re-run
  `/run-plan rename-repo` (its Branch Guard accepts `chore/rename-repo`; it restarts at this
  box), then continue `/run-feature F9` at Phase A step 7. In a new session, a fresh
  `/run-feature F9`'s PR-mode Branch Guard stops because the branch is `chore/rename-repo`,
  not `main`: answer that it stays on `chore/rename-repo` and resumes at Phase A step 7
  (steps 1–6 are done once `/run-plan` finishes).
- [x] `README.md`: change line 1 to `# discord-github-issue-bot`. Replace the opening
  paragraph (line 3) with prose that says the bot turns tagged messages (`!bug`,
  `!feature`) in a configured intake channel of a Discord server into fleshed-out GitHub
  issues in a configured repo of the 4IRL GitHub org (and its roadmap), asks clarifying
  questions in a thread, and posts the issue link back there. The paragraph must contain the
  exact phrase `4IRL GitHub org` (Step 4 greps for it). Name the first, example target
  explicitly: `#c4i-github-issues` in the 4irl server → `4IRL/chores4irl`. Keep line 5's
  "target-agnostic … `example.env`" paragraph as is.
- [x] `README.md` § *Run with Docker*: change the image tag `issue-bot` to
  `discord-github-issue-bot` in both the build line (after `-t`) and the run line of that
  section's code block.
- [x] `CLAUDE.md`: change line 1 to `# CLAUDE.md — discord-github-issue-bot` and rewrite
  line 3 in the same portable terms as the README opening (configured channel → configured
  repo in the `4IRL GitHub org`, that exact phrase; first target `#c4i-github-issues` →
  `4IRL/chores4irl`). Leave the *Project rules* (including the identifiers rule on line 33)
  unchanged.
- [x] Verify: `git grep -n 'c4i-issue-bot\|c4i_issue_bot' -- README.md CLAUDE.md` prints
  nothing (exit status 1 is the expected, passing result), and
  `git grep -n 'issue-bot' -- README.md` shows only `discord-github-issue-bot`.

### 2. ROADMAP end state, Phase 1.5 and sequencing name the new project
Update the ROADMAP's title, End state and rename bullet, and record why the rename went
first.

**To-do:**
- [x] `plans/ROADMAP.md` title: `# discord-github-issue-bot Roadmap — Current State to End State`.
- [x] *End state* first paragraph: lead with the portable function, using the exact phrase
  `configured intake channels` on one line (Step 4 greps for it). The bot watches
  configured intake channels in the 4irl Discord server and turns members' tagged ideas into
  well-formed issues in configured repos of the 4IRL GitHub org and their roadmaps. Its first
  target is `#c4i-github-issues` in the `C4I` category (guild `1137236302358659185`) →
  `4IRL/chores4irl` (repo id `969373970`). Keep the rest of the paragraph (the example
  message, ignoring untagged chatter, the thread → questions → rating → file → link flow).
- [x] *End state* second paragraph: drop the closing sentence "The project is to be renamed
  `discord-github-issue-management-bot` to match." (the rename is now done in-repo) and keep
  the portability description.
- [x] Phase 1.5: change the bullet "The repo, local folder, docs and image are renamed to
  `discord-github-issue-management-bot`." to name `discord-github-issue-bot`. Leave the
  phase's status (`planned`), goal, other bullets and exit criteria unchanged: F8 is still
  open, so the phase isn't finished.
- [x] *Sequencing rationale*: append one sentence, containing the exact phrase
  `ahead of the rest of Phase 1` kept on one line (Step 4 greps for it; ROADMAP hard-wraps,
  so wrap before or after the phrase, never inside it), saying that the Phase 1.5 rename went
  ahead of the rest of Phase 1 (owner's choice, 2026-10-17), so the stronghold index lists
  the project under its portable name early and later work never has to rename files. Do not
  name F-IDs (the ROADMAP never lists them).
- [x] Don't change capabilities, other phases, Current state or *Maintaining this file*.
- [x] Verify: `git grep -n 'c4i-issue-bot\|issue-management-bot' -- plans/ROADMAP.md`
  prints nothing (exit status 1 is the expected, passing result).

### 3. META-PLAN title, PR link form and owner pointer
Point META-PLAN's title and *PR link form* fact at the new repo, and its *Shortest path* at
this plan's Owner checklist (DD-5).

**To-do:**
- [ ] `plans/META-PLAN.md` line 1: `# META-PLAN — discord-github-issue-bot feature rollout`.
- [ ] *Project facts* `PR link form` row: change it to
  `` `[#N](https://github.com/4IRL/discord-github-issue-bot/pull/N)` ``. (Links in this form
  404 until the owner renames the repo. After the rename, GitHub redirects the old URLs, so
  links already written in the old form keep working. F9's own in-review ledger cell
  (Phase A step 10) may carry either form, since `/run-feature` reads Project facts at the
  start of its invocation; both resolve after the rename, and the row is removed at
  fold-back.)
- [ ] *Where the work stands* → *Shortest path to the focus feature*, item 2: replace its
  pointer "(its *Expected end state*, "Owner checklist")" with
  "(`plans/chore/rename-repo/rename-repo.md` § Owner checklist, which supersedes the copy in
  F9's section: each item has a **Check**, and `allowWrite` keeps both paths)", keeping
  `rename-repo.md` § Owner checklist on one line (the verify gate greps it). In the same
  item, replace "`.claude/settings.json` and `.claude/skill-config.md` (agent sessions can't
  write these)" with "`.claude/skill-config.md` (agent sessions can't write it; the
  `.claude/settings.json` change already rides F9's PR)". Item 3:
  replace "Then fold F9 back from the renamed folder (`/run-feature F9`), which re-checks
  the checklist." with "Then, once every Check in that checklist passes, fold F9 back from
  the renamed folder (`/run-feature F9`); `/run-feature` has no checklist step of its own."
- [ ] Leave every other META-PLAN line alone: F9's own section, ledger row, Backlog row,
  ★FOCUS lines and Feature-list line go at F9's fold-back, the Feature list is written only by
  `/new-feature`, and the stale Baseline is refreshed at the fold-back (owner's choice,
  2026-10-18).
- [ ] Verify: `git diff $(git merge-base main HEAD) -- plans/META-PLAN.md` shows only line 1,
  the PR-link-form row, the two *Shortest path* items above and the F9 Status-ledger change
  `/run-feature` already committed; `git grep -n 'rename-repo.md. § Owner checklist' -- plans/META-PLAN.md`
  shows the new item-2 pointer, and `git grep -n 're-checks the checklist' -- plans/META-PLAN.md`
  prints nothing (exit status 1 is the expected, passing result).

### 4. Verify the end state
Check every Expected-end-state fact that can hold before the merge.

**Pre-merge end state (for `/run-feature` Phase A step 8).** META-PLAN's F9 *Expected end
state* has three facts that cannot hold until after F9's PR merges and the owner renames the
repo and moves the folder (F9 open risk e): `gh repo view 4IRL/<new-name>` succeeds,
`git remote get-url origin` points at it, and the literal
`grep -rn 'c4i-issue-bot\|c4i_issue_bot' --exclude-dir=.git --exclude-dir=plans .` prints
nothing. That grep also hits the gitignored `.venv/` (recreated by the owner after the move),
the old path kept in `.claude/settings.json` (DD-2), and it exits 2 on the sandbox's
placeholder dotfiles. Before the merge, this step's `git grep` gate stands in for that grep,
and the first two facts are Owner-checklist items. They are not gaps for step 8. Never run
a GitHub rename or change the remote from an agent session.

**To-do:**
- [ ] The owner's settings edit is in the branch: Step 1's `allowWrite` JSON check still
  exits 0, and `git status --porcelain -- .claude/settings.json` prints nothing (committed
  by Step 1).
- [ ] `git grep -n 'c4i-issue-bot\|c4i_issue_bot' -- ':!plans'` prints only the
  `.claude/settings.json` line holding the old path's `allowWrite` entry (kept, DD-2). Any
  other hit is a gap to fix.
- [ ] The new name and portable wording landed:
  `git grep -n 'discord-github-issue-bot' -- README.md CLAUDE.md plans/ROADMAP.md plans/META-PLAN.md`
  shows the README title and its Docker build and run lines, the CLAUDE.md title, the ROADMAP
  title and Phase 1.5 rename bullet, and the META-PLAN title and PR-link-form row;
  `git grep -n '4IRL GitHub org' -- README.md CLAUDE.md` shows the README opening and
  CLAUDE.md's opening line; `git grep -n 'configured intake channels' -- plans/ROADMAP.md`
  shows the rewritten *End state* paragraph; `git grep -n 'ahead of the rest of Phase 1' -- plans/ROADMAP.md`
  shows the *Sequencing rationale* sentence.
- [ ] Standing invariant 1: `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot`
  prints nothing (exit status 1 is the expected, passing result).
- [ ] `git diff --name-only $(git merge-base main HEAD)` lists only `README.md`, `CLAUDE.md`,
  `.claude/settings.json`, `plans/ROADMAP.md`, `plans/META-PLAN.md` and files under
  `plans/chore/rename-repo/`. No code or test file is changed.
- [ ] Write the pre-merge reconciliation into this plan's *Verification log*: the `git grep`
  gate above replaced META-PLAN F9's literal `grep -rn`, `gh repo view` / origin are
  deferred to the Owner checklist (see *Pre-merge end state* above), and META-PLAN F9's
  settings item ("names the new absolute path, not /home/rmila/Code/c4i-issue-bot") is met in
  DD-2's form: `allowWrite` lists both paths, and dropping the old one is an optional later PR.
- [ ] Re-read the Owner checklist below and confirm each check uses the name right for its
  place in the order: `c4i-issue-bot` in the pre-rename PR check and the absence checks
  (folder, history, skill-config, stronghold META-PLAN), `discord-github-issue-bot`
  everywhere else. End the final report with the line
  `Owner checklist: plans/chore/rename-repo/rename-repo.md § Owner checklist (run after F9's PR merges)`.

**Orchestrator note (`/run-feature`, not a to-do):** F9's branch is `chore/rename-repo`
(META-PLAN's F9 Session line), not `feature/<slug>`: use it wherever `/run-feature` says
`feature/<slug>`, including the phase-decision `gh pr list --head`, Phase A step 10's PR
lookup and its `gh-git.sh push origin`. At the Phase B hand-off, print the Owner checklist
from this plan in full, and tell the owner to leave **Its PR is merged into `main`**
unconfirmed in this session even once the PR has merged, so the session ends there. F9 is
folded back only by re-running `/run-feature F9` from the renamed folder after every
Owner-checklist Check passes (F9 open risk e); that re-run sees the merged PR and goes
straight to Phase C.

### 5. Verify All Tests Pass

Run the full test suites to confirm nothing is broken:

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm the full suite passes (this project has no separate
  UI suite; this one run covers integration and functional tests)
- [ ] Investigate and fix any failures before marking the plan finished

## Owner checklist (not for executors; the owner runs each check before the fold-back)

Copied from META-PLAN's F9 *Expected end state*, with the new name. Each item is outside an
agent's reach. `/run-feature` has no checklist step, so the owner runs every item's
**Check** and sees it pass before re-running `/run-feature F9` for the fold-back (in the
original session, leave Phase B's "PR merged" box unconfirmed; see Step 4's orchestrator
note). The write-check item is the one exception: the fold-back proves it. F2 and F5 don't
start until every item passes.
Order (F9 open risk e): F9's PR merges first, then the owner works through this list in
order, then F9 is folded back from a session in the renamed folder. When re-running
`/run-feature F9` for the fold-back, F9's PR head is `chore/rename-repo`
(`gh pr list --head chore/rename-repo --state all`), not `feature/<slug>`.

- ☐ No PR mid-review before renaming. **Check:**
  `gh pr list --repo 4IRL/c4i-issue-bot --state open` prints nothing, and `git stash list`
  is empty or each entry is accounted for.
- ☐ GitHub repo renamed `4IRL/c4i-issue-bot` → `4IRL/discord-github-issue-bot` (repo
  admin), then `git remote set-url origin https://github.com/4IRL/discord-github-issue-bot.git`.
  **Check:** `git remote get-url origin` prints that URL, and
  `gh repo view 4IRL/discord-github-issue-bot --json name -q .name` prints
  `discord-github-issue-bot`. Revert: rename it back in the repo settings and `set-url` to
  the old URL (GitHub redirects old URLs either way, until a new repo takes the old name).
- ☐ Local folder moved to `~/Code/discord-github-issue-bot` between sessions (close the old
  session first). **Check:** `test -d ~/Code/discord-github-issue-bot/.git && ! test -e ~/Code/c4i-issue-bot && echo ok`
  prints `ok`.
- ☐ Claude project history and memory moved from
  `~/.claude/projects/-home-rmila-Code-c4i-issue-bot/` to
  `~/.claude/projects/-home-rmila-Code-discord-github-issue-bot/`. Do this before opening
  any Claude session in the new folder: a session creates the target directory, and `mv`
  would then nest the old one inside it. **Check:**
  `test -d ~/.claude/projects/-home-rmila-Code-discord-github-issue-bot && ! test -e ~/.claude/projects/-home-rmila-Code-c4i-issue-bot && echo ok`
  prints `ok`.
- ☐ `.venv` recreated in the new folder (`rm -rf .venv && python3 -m venv .venv &&
  .venv/bin/pip install -r requirements-dev.txt`): the old one has the old absolute path in
  `pyvenv.cfg` and its script shebangs. **Check:** `.venv/bin/pytest -q` passes.
- ☐ `.claude/settings.json` already lists both paths in `allowWrite` (landed in F9's PR,
  staged by Step 1). If `.claude/settings.local.json` exists and names the old path, update it too.
  **Check:** `grep -c /home/rmila/Code/discord-github-issue-bot .claude/settings.json` prints
  `1`. Dropping the old path later is optional, in its own small PR.
- ☐ `.claude/skill-config.md`: title `# Skill Config — discord-github-issue-bot`,
  `project_name: discord-github-issue-bot` and `repo: 4IRL/discord-github-issue-bot`
  (gitignored, local only). **Check:** `grep -c c4i-issue-bot .claude/skill-config.md || true`
  prints `0`.
- ☐ A fresh session in the new folder can edit a file and commit (sandbox write check; the
  fold-back session's own commit counts). Expect Claude Code's trust prompt again: its
  per-project state in `~/.claude.json` is keyed by the old path. **Check (during the
  fold-back):** Phase C's commit on `chore/meta-plan-update-f9` succeeds from
  `~/Code/discord-github-issue-bot` with no sandbox write error.
- ☐ `/stronghold-sweep` run from `~/Code`. **Check:**
  `grep -n discord-github-issue-bot ~/Code/_STRONGHOLD/docs/PROJECTS.md` prints the entry,
  and the project summary describes the portable function.
- ☐ From that same `~/Code` session, update the stronghold's own
  `_STRONGHOLD/plans/META-PLAN.md` mentions of `c4i-issue-bot` (the sweep doesn't write that
  file), and commit them on `main` path-scoped:
  `git -C ~/Code add _STRONGHOLD/plans/META-PLAN.md && git -C ~/Code commit` (if that file
  has other uncommitted edits, stage only these hunks; never `/git-commit`). **Check:** `grep -c c4i-issue-bot ~/Code/_STRONGHOLD/plans/META-PLAN.md || true`
  prints `0`.

## Verification log

## Status
finished: false
