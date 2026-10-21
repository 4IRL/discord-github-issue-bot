# Slash-command intake (F10)

## Summary
Members report through `/bug` and `/feature` slash commands in the intake channel instead of
`!bug`/`!feature` message tags, which are removed outright. Each command opens a modal with a
required **Title** (max 100 characters) and an optional paragraph **Description**. On submit the bot
defers privately, posts a public summary message in the intake channel (type, title, the reporter as
a non-pinging mention), hands that message and an `IssueCandidate` to the existing `on_candidate`
seam (production: `filing_hook`, which opens the thread and files the issue), then confirms
privately. Commands are synced to the configured guild only, once per process; the Message Content
intent is dropped. META-PLAN § F10 is the source contract; this plan resolves its Open risks (a)–(f).

## Research Findings
- **discord.py 2.7.1 API (read from `.venv`, probed offline).** `app_commands.CommandTree(client)`
  attaches to a plain `discord.Client`, once per client (a second raises `ClientException`).
  `app_commands.Command(name=..., description=..., callback=...)` accepts a nested-closure callback
  whose only parameter is `interaction` (annotated or not); `functools.partial` fails (no
  `__globals__`). `tree.add_command(cmd, guild=discord.Object(id))` registers the command for that
  guild only; omitting `guild=` makes it global. `tree.sync(guild=...)` bulk-overwrites that guild's
  commands; `sync()` without `guild=` would overwrite the **global** set, so it is never called
  that way. `setup_hook` runs once, from `login()` (`client.py`), before any event.
  `allowed_contexts` must stay unset on guild commands (`tree.py`).
- **Modals in 2.7.1.** `TextInput(label=...)` is deprecated; each input is wrapped as
  `discord.ui.Label(text=..., component=discord.ui.TextInput(...))` and added with
  `modal.add_item(label)`. Keep a reference to the `TextInput` and read `.value` (`''` for an empty
  optional field). Lengths (title 45, label 45, max_length 4000) are not checked client-side.
  `repr(TextInput)` emits a DeprecationWarning, so never log or repr inputs. On a modal submit,
  `interaction.response.defer(ephemeral=True, thinking=True)` is required: without `thinking=True`
  it becomes a public message-update defer. `interaction.followup.send(..., ephemeral=True)` follows
  up; the token lives 15 minutes. The default `Modal.on_error` (`modal.py`) and
  `CommandTree.on_error` (`tree.py`) log full tracebacks with `exc_info`, and
  `Interaction.__repr__` includes the member. Both must be overridden to log type and ids only
  (CLAUDE.md log rules). Interaction errors never reach `Client.on_error`.
- **Summary and thread.** `channel.send(content, allowed_mentions=discord.AllowedMentions.none())`
  renders `<@id>` as a mention and pings nobody, including any `@everyone` in the title. The
  returned `Message.thread` is `None`, so `threads.open_thread` and `filing_hook` work unchanged on
  it. The submit interaction's `channel` is a full `TextChannel` (or `None`, which is treated as a
  failure). Slash commands and modals need no intents: keep `guilds` (`get_channel` in `on_ready`,
  thread cache) and drop `guild_messages` and `message_content` with `on_message`.
- **Impact.** `IssueType` lives in `issue_bot/tags.py` and is imported by `config.py`,
  `handler.py`, `threads.py` and the tests. It must sit in a leaf module, because `handler`
  imports `config`, so `config → handler` would cycle. It moves to a new `issue_bot/issue_type.py`.
  `IssueCandidate.content` is read by no runtime code (only `tests/test_handler.py`), so it is
  dropped. `IssueCandidate` is built only in `handler.py`. `FILING_ERROR_REPLY`
  (`threads.py`) says "post a new message (edits are ignored)" and is pinned by
  `tests/test_threads.py`.
- **Tests.** `.venv/bin/pytest` from the repo root (META-PLAN Project facts), with
  `asyncio_mode = "auto"`. Discord is faked with `SimpleNamespace` + `AsyncMock` (no MagicMock or
  spec), real `discord.HTTPException` subclasses are built from a `SimpleNamespace` response, and logs
  are checked with `caplog` plus the `bot_records`/`record_texts`/`assert_no_member_text` helpers in
  `tests/test_bot.py`. Obsolete: all of `tests/test_tags.py` and `tests/test_handler.py` (two
  intents ported), 6 malformed/format-hint tests and the `on_message`-specific `on_error` tests in
  `tests/test_bot.py`, and `test_format_hint_names_tag_and_fields`. The filing-hook tests keep their
  assertions but call `filing_hook(github)(message, candidate)` directly.

**Owner decisions (2026-10-20, resolving META-PLAN F10 risks):** (a) the summary names the
reporter as `<@id>` with `AllowedMentions.none()`, and the issue body keeps the display name;
(f) Title `max_length` is 100 (`THREAD_NAME_LIMIT`), so `thread_name()` never truncates it; no
`default_member_permissions`: anyone who can see the channel may run the commands (the server's
Integrations settings can narrow it later); (d) this PR rewrites the repo `CLAUDE.md` intro (one
sentence, folding in the F9 polish item) and `plans/ROADMAP.md` capabilities 1–2 and Phases 1, 1.5
and 2, plus the Principles/Phase 4 restart-catch-up lines (DD-9). Review DDs (2026-10-20): live
Discord behavior is confirmed by the owner at the merge gate (DD-1); Read Message History stays in
the invite (DD-6); the modal timeout is 30 minutes (DD-10); guild commands are removed by removing the app's integration (DD-12). DD-13: a failed filing with no thread still gets the plain "posted" confirmation. That is F5's deferred no-thread-fallback item, left to F7, which touches the same hook. Risk (b) is resolved by `defer(ephemeral=True, thinking=True)` first in `on_submit`; (c) by
syncing in `setup_hook`; (e) the Description field is the slot F3 replaces; the rest of (f): a failed
summary post sends `SUMMARY_FAILED_REPLY` privately and files nothing.

## Steps

### 1. Move `IssueType` to a leaf module
Pure refactor: `IssueType` gets its own dependency-free module so `tags.py` can be deleted later.

**To-do:**
- [x] Create `issue_bot/issue_type.py` with the module docstring `"""The kinds of issue the bot files; each is one slash command and one target label."""`, `from enum import StrEnum`, and `IssueType(StrEnum)` moved verbatim from `issue_bot/tags.py:30-34` (`BUG = "bug"`, `FEATURE = "feature"`, docstring reworded to `"""The kind of issue a report files."""`).
- [x] In `issue_bot/tags.py`, delete the class and add `from issue_bot.issue_type import IssueType` (the parser still uses it until Step 5); drop `from enum import StrEnum` (now unused there).
- [x] Repoint imports to `from issue_bot.issue_type import IssueType`: `issue_bot/config.py:19`, `issue_bot/handler.py:9` (keep `MalformedTag, parse_tag` imported from `issue_bot.tags` on its own line), `issue_bot/threads.py:11`, `tests/test_config.py:8`, `tests/test_threads.py:7`, `tests/test_bot.py:14` and `tests/test_handler.py:8` (each keeps `from issue_bot.tags import MalformedTag` on its own line until Step 5), `tests/test_tags.py:3` (keep its other names from `issue_bot.tags`).
- [x] Verify: `.venv/bin/pytest` passes with the same count as before the step; `grep -rn --include='*.py' "from issue_bot.tags import.*IssueType" issue_bot tests` prints nothing. Throughout this plan, a grep that should print nothing exits 1 on its pass: judge by the output, not the exit status. Done 2026-10-20: 246 passed before and after; grep printed nothing.

### 2. Candidate from a modal submission
`IssueCandidate` loses its raw-message `content` field and gains a builder for slash-command intake.

**To-do:**
- [x] **Red.** In `tests/test_handler.py` (add `from types import SimpleNamespace` to its stdlib imports), add `test_candidate_from_submission_fields`: build `user = SimpleNamespace(id=7, display_name="Alice")` and `message = SimpleNamespace(id=99, jump_url="https://discord.com/channels/111/555/99")`, call `candidate_from_submission(IssueType.BUG, "Fix it", "Steps", user, message, config.target)`, and assert `type is IssueType.BUG`, `title == "Fix it"`, `body == "Steps"`, `author_id == 7`, `author_name == "Alice"`, `message_id == 99`, `message_url == message.jump_url`, `target is config.target`. Add `test_submission_candidate_repr_hides_text`, which asserts `repr(candidate)` contains none of the title, body or `"Alice"` (port of `test_candidate_repr_hides_text`'s intent). Run them and confirm an `ImportError`.
- [x] **Green.** In `issue_bot/handler.py`, remove the `content: str = field(repr=False)` field from `IssueCandidate`, drop `content=message.content` from `candidate_from_message`'s constructor call (`handler.py:65`), and delete the `content` assertion in `test_tagged_message_becomes_candidate` (`tests/test_handler.py:18`). Change the class docstring's first line to `"""A report ready for the thread and filing steps."""`. Add:
  ```python
  def candidate_from_submission(
      issue_type: IssueType,
      title: str,
      description: str,
      reporter: discord.abc.User,
      message: discord.Message,
      target: TargetConfig,
  ) -> IssueCandidate:
      """Return the candidate for a submitted report, tied to the bot's summary ``message``."""
  ```
  It returns `IssueCandidate(type=issue_type, title=title, body=description, author_id=reporter.id, author_name=reporter.display_name, message_id=message.id, message_url=message.jump_url, target=target)`.
- [x] Verify: `.venv/bin/pytest tests/test_handler.py tests/test_issues.py tests/test_bot.py` green, then the full `.venv/bin/pytest`. Done 2026-10-20: Red gave the expected `ImportError`; after Green the three files gave 69 passed and the full suite 248 passed (246 + 2 new).

### 3. The intake module: commands, modal and submit flow
A new `issue_bot/intake.py` builds one guild command per `IssueType`, and the modal that posts the summary and feeds `on_candidate`. Built test-first in `tests/test_intake.py`.

**To-do:**
- [x] Add a `make_interaction` fixture to `tests/conftest.py` (named like `make_message`), returning a factory `(*, channel_id: int | None = 555, user_id: int = 7, display_name: str = "Alice", interaction_id: int = 4242, summary: SimpleNamespace | None = None) -> SimpleNamespace` with: `id`, `channel_id`, `channel=SimpleNamespace(id=channel_id, send=AsyncMock(return_value=summary))` (or `channel=None` when `channel_id is None`), `user=SimpleNamespace(id=user_id, display_name=display_name, mention=f"<@{user_id}>")`, `response=SimpleNamespace(send_modal=AsyncMock(), send_message=AsyncMock(), defer=AsyncMock(), is_done=Mock(return_value=False))`. After building `response`, set `response.defer.side_effect = lambda *args, **kwargs: setattr(response.is_done, "return_value", True)`, so a deferred interaction reports `is_done()` True as in production (DD-2). Also `followup=SimpleNamespace(send=AsyncMock())`. The fixture depends on `make_message`, and the default `summary` is `make_message()`'s result (`id=99`, `jump_url=".../111/555/99"`, `thread=None`, `create_thread` → thread `id=1234`). Add a module-level alias `InteractionFactory = Callable[..., SimpleNamespace]` beside `MessageFactory`. Change conftest's `from unittest.mock import AsyncMock` to `from unittest.mock import AsyncMock, Mock`. In the same to-do, move `fake_github`, `forbidden`, `record_texts`, `assert_no_member_text` and `ISSUE_URL` from `tests/test_bot.py` into `tests/conftest.py` as plain module-level helpers (adding `from issue_bot.github import FiledIssue` to conftest's project imports), imported by both test files with `from tests.conftest import ...`, as `MessageFactory` is today. Run `.venv/bin/pytest tests/test_bot.py` to confirm the move is green.
- [x] **Red → Green, modal shape.** First create `issue_bot/intake.py` with the module docstring, `logger`, `CandidateHook` and the constants listed in the command-callback to-do below. Its imports, in three groups: `import logging`, `from collections.abc import Awaitable, Callable`; `import discord`, `from discord import app_commands`; `from issue_bot.config import TargetConfig`, `from issue_bot.handler import IssueCandidate, candidate_from_submission`, `from issue_bot.issue_type import IssueType`, `from issue_bot.threads import THREAD_NAME_LIMIT`. Test `test_modal_fields`: `IntakeModal(IssueType.FEATURE, config.target, hook)` has `title == "New feature"`, `timeout == MODAL_TIMEOUT`, and exactly two children, both `discord.ui.Label`, with texts `"Title"` and `"Description"`. `modal.title_input` has `style is discord.TextStyle.short`, `required is True`, `max_length == 100`. `modal.description_input` has `style is discord.TextStyle.paragraph`, `required is False`, `max_length == 4000`. Implement `class IntakeModal(discord.ui.Modal)` with `__init__(self, issue_type, target, on_candidate)`: `super().__init__(title=f"New {issue_type}", timeout=MODAL_TIMEOUT)`, store the three arguments, build `self.title_input = discord.ui.TextInput(style=discord.TextStyle.short, required=True, max_length=TITLE_MAX_LENGTH)` and `self.description_input = discord.ui.TextInput(style=discord.TextStyle.paragraph, required=False, max_length=DESCRIPTION_MAX_LENGTH)`, then `self.add_item(discord.ui.Label(text="Title", component=self.title_input))` and the same for `"Description"`. Never pass `label=` to `TextInput` (deprecated since 2.6).
- [x] **Red → Green, command callback.** Tests: `test_command_names_follow_issue_type` (`intake_command(t, config.target, hook).name == str(t)` for each `IssueType`, and the description is under 100 characters); `test_command_opens_modal_in_intake_channel` (await `cmd.callback(interaction)`; `send_modal` is awaited once with an `IntakeModal` whose `issue_type` matches, and `send_message` is not awaited); `test_command_refused_outside_intake_channel`, parametrized over `channel_id` 556 and `None` (`send_message` awaited once with `INTAKE_REFUSAL, ephemeral=True`; `send_modal` and the hook not awaited; an INFO log `refused bug outside the intake channel interaction_id=4242 channel_id=<the parametrized value>`, i.e. `556` or `None`). Then implement in `issue_bot/intake.py`:
  - Module docstring: `"""Slash-command intake: ``/bug`` and ``/feature`` open a modal; a submit posts a public summary and hands it to ``on_candidate``.` + blank line + a paragraph saying modal text and interaction payloads are member text: logs carry the issue type, interaction, message and channel ids and the summary URL only, and Discord errors by type, status and code. Give `intake_command`, `IntakeModal`, `summary_text`, `on_submit` and `_reply` a one-line docstring each, as every function in `threads.py` and `bot.py` has; none quotes member text.
  - `logger = logging.getLogger(__name__)`; `CandidateHook = Callable[[discord.Message, IssueCandidate], Awaitable[None]]` is defined here (Step 4 replaces `bot.py`'s own alias with an import from `intake`, so `intake` never imports `bot`).
  - Constants (fixed text, no member text): `TITLE_MAX_LENGTH = THREAD_NAME_LIMIT  # Owner's choice: a title is never cut in the thread name.`; `DESCRIPTION_MAX_LENGTH = 4000  # Discord's maximum text-input length.`; `MODAL_TIMEOUT = 1800  # Seconds an open modal is kept; a later submit fails in Discord, unfiled (DD-10).`; `NO_MENTIONS = discord.AllowedMentions.none()`; `INTAKE_REFUSAL = "Reports go in the intake channel: run this command there."`; `BLANK_TITLE_REPLY = "No report was posted: the title needs a letter or digit. Run the command again."`; `SUMMARY_FAILED_REPLY = "Sorry, I couldn't post your report in the channel, so nothing was filed. Try again later."`; `SUBMITTED_REPLY = "Thanks! Your report is posted: {url}"`; `INTAKE_ERROR_REPLY = "Sorry, something went wrong with this report. Check the channel before running the command again."`.
  - `def intake_command(issue_type: IssueType, target: TargetConfig, on_candidate: CandidateHook) -> app_commands.Command`. It defines a nested `async def report(interaction: discord.Interaction) -> None`: if `interaction.channel_id != target.channel_id`, log the refusal (`"refused %s outside the intake channel interaction_id=%s channel_id=%s"`) and `await interaction.response.send_message(INTAKE_REFUSAL, ephemeral=True)`; otherwise `await interaction.response.send_modal(IntakeModal(issue_type, target, on_candidate))`. It returns `app_commands.Command(name=str(issue_type), description=f"Report a {issue_type} as a GitHub issue", callback=report)`. A comment says why a closure: `Command` needs a real function, and `functools.partial` has no `__globals__`.
- [x] **Red → Green, submit happy path.** Tests set `modal.title_input._value` / `modal.description_input._value` (a comment notes this is discord.py's own seed, used because a real submit needs the Gateway) and `await modal.on_submit(interaction)` with `hook = AsyncMock()`:
  - `test_submit_defers_privately_first`: `defer` is awaited once with `ephemeral=True, thinking=True`, before `channel.send` (check with a shared `Mock().attach_mock` call-order manager or `mock_calls` ordering).
  - `test_summary_text_escapes_markdown` (DD-14): `summary_text(IssueType.BUG, "**x** [y](https://e.com)", "<@7>") == "**New bug** from <@7>: \\*\\*x\\*\\* \\[y](https://e.com)"`.
  - `test_submit_posts_summary_without_pings`: `channel.send` is awaited once, its content equals `summary_text(IssueType.BUG, "Fix it", "<@7>")`, and its `allowed_mentions is NO_MENTIONS`.
  - `test_submit_hands_summary_and_candidate_to_hook`: the hook is awaited once with `(summary, candidate)`, where the candidate has `title == "Fix it"`, `body == "Steps"`, `author_name == "Alice"`, `author_id == 7`, `message_id == 99`, `message_url == summary.jump_url`, and `target is config.target`.
  - `test_submit_confirms_privately`: `followup.send` is awaited once with `SUBMITTED_REPLY.format(url=summary.jump_url), ephemeral=True`.
  - `test_submit_normalizes_title_and_description`: a title of `"  Fix   it \n"` becomes `"Fix it"`, and a description of `"\n Steps \n"` becomes `"Steps"` (strip only, keeping inner newlines).
  - `test_submit_files_issue_through_filing_hook` (DD-7): hook = `filing_hook(fake_github(FiledIssue(7, ISSUE_URL)))`. `summary.create_thread` is awaited once with `name="Fix it"`, and `create_issue` is awaited once with `config.target`, title `"Fix it"`, labels `["bug"]` and a body starting ``Reported by `Alice` in Discord: https://discord.com/channels/111/555/99``.
  - `test_submit_logs_ids_not_text`: with caplog at INFO, the records contain `interaction_id=4242` and `message_id=99`, and none of the title, description or `"Alice"`.

  Implement `def summary_text(issue_type: IssueType, title: str, reporter_mention: str) -> str` → `f"**New {issue_type}** from {reporter_mention}: {discord.utils.escape_markdown(title)}"`. The member's title is escaped so its markdown (masked links, headings, spoilers) never renders under the bot's name (DD-14); the thread name and issue title keep the raw text. Implement `async def on_submit(self, interaction: discord.Interaction, /) -> None`:
  1. `await interaction.response.defer(ephemeral=True, thinking=True)`. A comment says this must come first: Discord allows 3 s, and without `thinking=True` a modal-submit defer is a public message update.
  2. `title = " ".join(self.title_input.value.split())`, `description = self.description_input.value.strip()`.
  3. If `title` has no alphanumeric character (`not any(c.isalnum() for c in title)`), send `BLANK_TITLE_REPLY` privately (step 6's helper) and return.
  4. If `interaction.channel is None`, log ERROR `"could not post %s summary interaction_id=%s: no channel"` (DD-4), send `SUMMARY_FAILED_REPLY` privately and return without filing. Otherwise `summary = await interaction.channel.send(summary_text(self.issue_type, title, interaction.user.mention), allowed_mentions=NO_MENTIONS)`. On `discord.HTTPException as exc`, log ERROR `"could not post %s summary interaction_id=%s: %s status=%s code=%s"` (type, `interaction.id`, `type(exc).__name__`, `exc.status`, `exc.code`), send `SUMMARY_FAILED_REPLY` privately, and return without filing.
  5. Log INFO `"posted %s summary interaction_id=%s message_id=%s (%s)"` (`self.issue_type`, `interaction.id`, `summary.id`, `summary.jump_url`), then `await self.on_candidate(summary, candidate_from_submission(self.issue_type, title, description, interaction.user, summary, self.target))`.
  6. Send `SUBMITTED_REPLY.format(url=summary.jump_url)` privately through a private helper `async def _reply(interaction, text, issue_type) -> None`, which calls `interaction.followup.send(text, ephemeral=True)` and, on `discord.HTTPException`, logs ERROR `"could not send %s reply interaction_id=%s: %s status=%s code=%s"`.
- [x] **Red → Green, submit failure paths.** Tests:
  - `test_blank_title_files_nothing` (title `"  ...  "`): no `channel.send`, no hook, and `followup.send` with `BLANK_TITLE_REPLY`.
  - `test_summary_failure_files_nothing`: `channel.send.side_effect = forbidden-style discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), {"code": 50013, "message": "Secret error words"})`. No hook, `SUMMARY_FAILED_REPLY` sent privately, and the log has `Forbidden`, `403`, `50013` but not `"Secret error words"`.
  - `test_missing_channel_files_nothing` (`make_interaction(channel_id=None)` passed to `on_submit`): `SUMMARY_FAILED_REPLY` is sent, the hook is not called, and the ERROR log reads `could not post bug summary interaction_id=4242: no channel`.
  - `test_followup_failure_logged_without_text`: `followup.send.side_effect` is an HTTPException carrying secret text; it is logged by type/status/code only and does not raise.
  - `test_github_error_still_posts_filing_error_reply`: hook = `filing_hook(fake_github(GitHubError("issue", 422)))`. The summary's thread `send` is awaited with `FILING_ERROR_REPLY`, and `followup.send` still gets `SUBMITTED_REPLY` (the report is posted; the thread carries the failure).
- [x] **Red → Green, modal error handler.** Tests:
  - `test_modal_on_error_logs_type_only`: `await modal.on_error(interaction, RuntimeError("Secret exception words"))` logs ERROR `unhandled RuntimeError in bug modal interaction_id=4242 status=None code=None`, with no `Secret exception words` in `record_texts` (which includes `exc_text`). A second case passes `forbidden(50013, "Secret error words")` and expects `unhandled Forbidden in bug modal interaction_id=4242 status=403 code=50013` (DD-5).
  - `test_modal_on_error_replies_privately`: with `response.is_done` returning True, `followup.send(INTAKE_ERROR_REPLY, ephemeral=True)` is awaited. With False, `response.send_message(INTAKE_ERROR_REPLY, ephemeral=True)` is awaited.
  - `test_modal_on_error_reply_failure_swallowed`, parametrized over `is_done` True (`followup.send` raises) and False (`response.send_message` raises): the raised `forbidden(50013, "Secret error words")` is logged as ERROR `could not send bug reply interaction_id=4242: Forbidden status=403 code=50013` without the secret, and `on_error` returns normally (DD-11).

  Implement `async def on_error(self, interaction: discord.Interaction, error: Exception, /) -> None` with the log line `"unhandled %s in %s modal interaction_id=%s status=%s code=%s"` (never `exc_info`). Status and code come from a shared helper, `def discord_error_fields(error: BaseException) -> tuple[int | None, int | None]`, which returns `(error.status, error.code)` for a `discord.HTTPException` and `(None, None)` otherwise. The helper is defined in `intake.py`; `bot.py` imports it (DD-5). Then it replies, branching on `interaction.response.is_done()` (`followup.send` when True, `response.send_message` when False, both with `ephemeral=True`). Both branches sit inside one `try`, whose `except discord.HTTPException` logs the same `could not send %s reply …` line as `_reply`, so no Discord error text escapes to discord.py's traceback log (DD-11). The docstring says it replaces discord.py's default, which logs the traceback (it can quote member text).
- [x] Verify: `.venv/bin/pytest tests/test_intake.py tests/test_handler.py` green, then the full suite. Add no new package: `discord.app_commands` and `discord.ui` ship with the pinned `discord.py==2.7.1`. Done 2026-10-20: Red gave the expected collection error (no `issue_bot.intake`); after Green `tests/test_intake.py tests/test_handler.py` gave 37 passed and the full suite 272 passed (248 + 24 new); no new package.

### 4. Register and sync the commands in `IssueBot`
`IssueBot` owns a privacy-safe command tree, registers `/bug` and `/feature` for the configured guild only, and syncs once per process.

**To-do:**
- [x] **Step 3 hardening (owner-approved 2026-10-20, from Step 3's security review).** In `issue_bot/intake.py`, Red → Green:
  (a) `IntakeModal.on_error`'s reply `try` gains a final `except Exception as exc` that logs ERROR `"could not send %s reply interaction_id=%s: %s"` (type only, never `exc_info`) and returns, so a non-HTTP failure (network or timeout) during the error reply never reaches asyncio's traceback log. Test `test_modal_on_error_reply_non_http_failure_swallowed`: the reply raises `RuntimeError("Secret exception words")`; `on_error` returns normally, the log names `RuntimeError`, and the secret is absent from `record_texts`.
  (b) The summary post passes `suppress_embeds=True` to `interaction.channel.send(...)`, so a bare URL in a member's title never unfurls under the bot's name (extends DD-14). Extend `test_submit_posts_summary_without_pings` to assert `suppress_embeds is True` in the `send` kwargs. Check that `Messageable.send` accepts `suppress_embeds` in discord.py 2.7.1 (`abc.py`) before relying on it.
- [x] **Red.** In `tests/test_bot.py`:
  - `test_commands_registered_for_guild_only`: after `IssueBot(config)`, `sorted(c.name for c in bot.tree.get_commands(guild=discord.Object(111)))` is `["bug", "feature"]` and `bot.tree.get_commands()` (global) is `[]`.
  - `test_setup_hook_syncs_guild_once`: monkeypatch `bot.tree.sync` with `AsyncMock(return_value=[...two items...])` and `await bot.setup_hook()`. `sync` is awaited once; its only kwarg `guild` has `.id == 111`; and no call has `guild=None` or no `guild`. An INFO log reads `synced 2 commands to guild 111`.
  - `test_setup_hook_sync_failure_logged_without_text`: `sync.side_effect = forbidden(50001, "Secret error words")`. `setup_hook` returns normally and logs ERROR with `Forbidden`, `403`, `50001`, without the secret.
  - `test_tree_on_error_logs_type_only`, parametrized:
    - an `app_commands.CommandInvokeError` whose `.original` is `RuntimeError("Secret exception words")` (build it with `CommandInvokeError(bot.tree.get_command("bug", guild=discord.Object(111)), RuntimeError(...))`), with `interaction=SimpleNamespace(id=4242, command=<that command>)`;
    - an `app_commands.CheckFailure("Secret exception words")` with `command=None`.
    - a `CommandInvokeError` whose `.original` is `forbidden(50013, "Secret error words")`.

    Add `from discord import app_commands` to `tests/test_bot.py`'s imports for `CommandInvokeError` and `CheckFailure`.

    Assert the log line `unhandled RuntimeError in command bug interaction_id=4242 status=None code=None` (or `unhandled CheckFailure in command tree interaction_id=4242 status=None code=None`, or `unhandled Forbidden in command bug interaction_id=4242 status=403 code=50013`), and that the secret is absent.
  - `test_command_callback_reaches_hook_end_to_end`: build `hook = AsyncMock()` and `bot = IssueBot(config, on_candidate=hook)`. The command captures the hook at construction, so assigning `bot.on_candidate` afterwards would not reach it. Get the `bug` command from `bot.tree`, await its callback with `make_interaction()`, take the modal from `send_modal.await_args`, set its values, and await `on_submit`. `hook` receives `(summary, candidate)`.
- [x] **Green.** In `issue_bot/bot.py`:
  - Add `class IntakeTree(app_commands.CommandTree)` with `async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError, /) -> None`. It logs ERROR `"unhandled %s in %s interaction_id=%s status=%s code=%s"`. Let `cause` be `error.original` for a `CommandInvokeError`, else `error`. The arguments are `type(cause).__name__`, `f"command {interaction.command.name}"` when `interaction.command` is set (else `"command tree"`), `interaction.id`, and `*discord_error_fields(cause)` (DD-5). It never uses `exc_info` and never reprs the interaction. Docstring: it replaces discord.py's default traceback log, which can quote member text.
  - In `IssueBot.__init__`, after `self._startup_checked`: `self.tree = IntakeTree(self)`; `self._guild = discord.Object(id=config.guild_id)`; `for issue_type in IssueType: self.tree.add_command(intake_command(issue_type, config.target, self.on_candidate), guild=self._guild)`. A comment says always pass `guild=`: without it the command would be global.
  - Add `async def setup_hook(self) -> None` (docstring: login() calls it once per process, unlike on_ready). It runs `synced = await self.tree.sync(guild=self._guild)` and logs INFO `"synced %d commands to guild %s"`, `len(synced)`, `self.config.guild_id`. On `discord.HTTPException as exc` it logs ERROR `"could not sync commands to guild %s: %s status=%s code=%s"` and returns, so the bot still runs: commands from an earlier sync keep working, and the log names the failure.
  - Imports: add `from discord import app_commands`, `from issue_bot.intake import CandidateHook, discord_error_fields, intake_command`, `from issue_bot.issue_type import IssueType`; delete the local `CandidateHook` alias, now imported from `intake`.
- [x] Verify: `.venv/bin/pytest tests/test_bot.py tests/test_intake.py`, then the full suite. Done 2026-10-20: `Messageable.send` accepts `suppress_embeds` in 2.7.1 (`abc.py`); hardening Red gave 2 failures (missing `suppress_embeds` kwarg, unswallowed `RuntimeError`), Step 4 Red gave 7 `AttributeError` failures (no `bot.tree`); after Green the two files gave 77 passed and the full suite 280 passed (272 + 1 hardening + 7 Step 4).

### 5. Remove the tag intake
Delete the `!bug`/`!feature` path, the format hint, `on_message` and the privileged intents, and port the surviving tests to direct calls.

**To-do:**
- [x] **Step 4 hardening (owner-approved 2026-10-21, from Step 4's security review).** In `issue_bot/bot.py` `setup_hook`, after the `except discord.HTTPException` branch, add `except Exception as exc` that logs ERROR `"could not sync commands to guild %s: %s"` (`self.config.guild_id`, `type(exc).__name__`; never `exc_info`) and returns, so a non-HTTP sync failure (network, timeout, `MissingApplicationID`) leaves the bot running on the previously synced commands. Red → Green with `test_setup_hook_non_http_sync_failure_logged_type_only` in `tests/test_bot.py`: `sync.side_effect = RuntimeError("Secret exception words")`; `setup_hook` returns normally, the log names `RuntimeError`, and the secret is absent from `record_texts`.
- [x] Delete `issue_bot/tags.py` and `tests/test_tags.py`.
- [x] `issue_bot/handler.py`: delete `candidate_from_message`, `ACCEPTED_MESSAGE_TYPES` and `logger` (no remaining log call), and the dead imports `logging`, `Config` (keep `TargetConfig`), and `from issue_bot.tags import MalformedTag, parse_tag`. Keep `import discord` (it is used by the `candidate_from_submission` annotations). Change the module docstring to `"""The issue candidate a slash-command report becomes."""`.
- [x] `tests/test_handler.py`: delete every `candidate_from_message` test (`test_tagged_message_becomes_candidate`, `test_candidate_repr_hides_text`, `test_other_channel_ignored`, `test_thread_message_ignored`, `test_bot_author_ignored`, `test_webhook_ignored`, `test_system_message_ignored`, `test_reply_type_accepted`, `test_untagged_ignored`, `test_malformed_returned_and_logged_without_text`) and their now-unused imports (`logging`, `discord`, `pytest`, `IssueCandidate`, `MalformedTag`, `candidate_from_message`, `MessageFactory`, each only if no remaining test uses it), keeping the Step 2 tests.
- [x] `issue_bot/threads.py`: delete `format_hint` and `from issue_bot.issue_type import IssueType` (Step 1's import, unused once `format_hint` is gone). Change the module docstring's first line to `"""Open the public thread on a report's summary message, and the helpers that name and fill it.`. Reword `FILING_ERROR_REPLY = "Sorry, I couldn't file this as a GitHub issue. Check the repo before reporting it again; to retry, run the command again."`. In `tests/test_threads.py`, delete `test_format_hint_names_tag_and_fields` and the `IssueType` and `format_hint` imports, and update `test_filing_error_reply_is_fixed_text` to the new text.
- [x] `issue_bot/bot.py`:
  - Delete `MalformedHook`, `reply_format_hint`, the `on_malformed` parameter and attribute, and `on_message`.
  - Delete the dead imports `candidate_from_message`, `MalformedTag`, `format_hint` and `from collections.abc import Awaitable, Callable` (its last users, the two hook aliases, are gone). Keep `IssueCandidate`, which `open_issue_thread` and `filing_hook` still annotate.
  - `build_intents()`: only `intents.guilds = True`, with the docstring `"""Least-privilege intents: guilds only (slash commands and modals need no intent)."""`.
  - `on_error`: drop the `on_message` message-id branch and log `"unhandled %s in %s"` only, removing the docstring sentence about message ids.
  - Change the module docstring to `"""The Discord client: registers the intake commands and hands each report to a hook."""` and the class docstring to describe `/bug`/`/feature` → summary → `on_candidate`, with no `on_malformed`.
  - Keep `open_issue_thread` and `filing_hook` unchanged except wording that says "tagged" (grep `tagged` in `issue_bot/` and reword each to "report").
- [x] `tests/test_bot.py`:
  - Delete `test_on_message_ignores_untagged`, `test_on_message_malformed_skips_candidate_hook`, the five malformed/format-hint tests (`test_malformed_message_gets_format_hint_in_thread`, `test_malformed_with_existing_thread_reuses_it`, `test_malformed_hint_skipped_when_thread_fails`, `test_malformed_hint_send_failure_logged_without_text`, `test_custom_on_malformed_hook`), `test_on_error_adds_message_id_for_on_message`, `test_raising_hook_dispatched_by_discord_logs_type_and_id_only`, `test_on_error_omits_non_message_ids` and `test_edits_not_handled`.
  - Rewrite `test_intents` to assert `guilds` is True, and `message_content` and `guild_messages` are False.
  - Add `test_no_message_listeners` (DD-8): `assert not hasattr(IssueBot, "on_message")` and `assert not hasattr(IssueBot, "on_message_edit")`. `discord.Client` defines neither.
  - Delete `test_on_message_calls_hook_with_message_and_candidate` (covered by Step 4's end-to-end test).
  - Port `test_default_hook_*` and `test_filing_hook_*` / `test_filing_error_send_failure_logged_without_text` to call `open_issue_thread(message, candidate)` / `filing_hook(github)(message, candidate)` directly, with `candidate` from a new conftest `make_candidate` fixture (see below) and `message = make_message()`. Keep every log and reply assertion. Drop `SECRET_CONTENT` and use the candidate's `title="Secret title words"`, `body="Secret body words"`, `author_name="Alice"`, so `assert_no_member_text` keeps its strings.
  - Rewrite `test_filing_hook_unexpected_error_reaches_on_error` as `test_filing_hook_unexpected_error_reaches_modal_on_error`: drive `modal.on_submit` with a hook raising `RuntimeError("Secret exception words")` through discord.py's own dispatch, `await modal._scheduled_task(interaction, [], {})`. Its 2.7.1 signature is `(interaction, components, resolved)`; empty components keep the `_value`s the test set, and an exception in `on_submit` is routed to `on_error`. Assert the `unhandled RuntimeError in bug modal interaction_id=4242 status=None code=None` log (read from records named `issue_bot.intake`; `bot_records` keeps only `issue_bot.bot`), that `Secret exception words` is absent from `record_texts`, and that `assert_no_member_text` passes (DD-16), and that `INTAKE_ERROR_REPLY` went through `followup.send(..., ephemeral=True)`: the fixture's `defer` has flipped `is_done`, as in production (DD-2), and `response.send_message` was not awaited. This records the F5 deferred decision: an unexpected filing error now gets a fixed private reply.
  - Remove the dead imports `MalformedTag` and `format_hint`, plus `MessageFactory` and `IssueCandidate` if no remaining test uses them. Add `open_issue_thread` to the existing `issue_bot.bot` import, import `IntakeModal` and `INTAKE_ERROR_REPLY` from `issue_bot.intake`, and import the conftest helpers (plus `CandidateFactory`) the ported tests now call; `IssueType` stays, because the modal test builds `IntakeModal(IssueType.BUG, ...)`.
- [x] `tests/conftest.py`:
  - Slim `make_message` to `(*, channel_id=555, message_id=99, thread=None, created_thread_id=1234)`, dropping `content`, `author_bot`, `webhook_id`, `message_type` and the `author` namespace. Keep `channel`, `id`, `jump_url`, `thread`, `create_thread` and `fetch_thread`, and update `MessageFactory` callers that passed the removed args (`tests/test_threads.py`'s `test_open_thread_logs_forbidden_without_text` passes content: drop that argument).
  - Add a `make_candidate` fixture: `(*, type=IssueType.BUG, title="Fix it", body="Steps", author_name="Alice", author_id=7, message_id=99, message_url="https://discord.com/channels/111/555/99", target: TargetConfig | None = None) -> IssueCandidate`, using `target or config.target` (DD-3: `test_issue_labels_use_target_mapping` passes `custom_config.target`). Import `IssueCandidate` from `issue_bot.handler`, `IssueType` from `issue_bot.issue_type`, and `TargetConfig` beside `Config`. Add `CandidateFactory = Callable[..., IssueCandidate]` beside `MessageFactory` and `InteractionFactory`.
- [x] `tests/test_issues.py`: replace the local `make_candidate(make_message, config, content, ...)` with the conftest `make_candidate` fixture. Drop `candidate_from_message` from the `issue_bot.handler` import and the `from tests.conftest import MessageFactory` line (import `CandidateFactory` from `tests.conftest` instead; keep `IssueCandidate` only if a remaining annotation uses it), and add `from issue_bot.issue_type import IssueType` for the `type=` arguments and the parametrization. Map each test's tag string to `title`/`body`/`type` arguments (e.g. `"!bug\nTitle: T\nBody: Steps here"` → `title="T", body="Steps here"`); a tag string with no Body line maps to `body=""` (`test_issue_body_without_body_uses_placeholder` needs it, since the fixture's default body is `"Steps"`). Parametrize `test_issue_labels_follow_config` on `IssueType` instead of tag strings. Keep every expected body/title/label assertion byte for byte.
- [x] Verify the removals: `.venv/bin/pytest` green; `grep -rnE '!bug|!feature' --include='*.py' issue_bot` prints nothing; `grep -rnE --include='*.py' 'parse_tag|MalformedTag|on_malformed|reply_format_hint|format_hint|candidate_from_message|issue_bot.tags' issue_bot tests` prints nothing; `grep -rn --include='*.py' 'message_content' issue_bot` prints nothing (the rewritten `test_intents` names it in its False assertion, so `tests` is not searched); `grep -rn --include='*.py' tagged issue_bot` prints nothing; Standing invariant 1 `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot` prints nothing. Done 2026-10-21: hardening Red gave 1 failure (unswallowed `RuntimeError`), green after the catch-all; after the removals the full suite gave 197 passed (280 + 1 hardening + 1 `test_no_message_listeners` − 57 `test_tags.py` − 11 `candidate_from_message` items − 1 format-hint test − 16 removed `test_bot.py` items); every verify grep printed nothing. Review fixes (all minor): restored the `\u200b` escapes in `tests/test_issues.py`, PEP 8 spacing in `bot.py`, `test_on_error_hides_exception_text` now uses `on_ready` with an exact log assertion, and a new `test_raising_event_dispatched_by_discord_logs_type_only` replaces the removed dispatch-path guard; full suite 198 passed.

### 6. Docs: README, smoke test, CLAUDE.md, ROADMAP, example.env
Describe the modal intake everywhere the tag intake is described (owner-approved for CLAUDE.md and ROADMAP).

**To-do:**
- [x] `README.md`:
  - L3 intro: replace "turns tagged messages (`!bug`, `!feature`) … asks clarifying questions in a thread" with the `/bug`/`/feature` modal intake (summary message, thread, filed issue; link-back and question work as planned features).
  - L9 status paragraph: replace the tag description with F10's flow, and say commands are synced to `DISCORD_GUILD_ID` only and refused outside the intake channel.
  - Delete L12-13 (edits/threads/bots ignored; first tag wins) and replace the whole `### Message format` section (L15-29) with `### Reporting`: `/bug` or `/feature` in the intake channel; Title (required, ≤100) and Description (optional); the public summary with a non-pinging mention; the thread and issue; private confirmations; refusal elsewhere.
  - Known limits (L35-37): keep L35. Replace L36 with "A command run while the bot is down fails in Discord ("The application did not respond") and files nothing." Replace L37 with "An open modal expires after 30 minutes, and a bot restart drops every open modal: its submit fails in Discord, and nothing is filed or logged." Add "If GitHub filing fails, the Description typed in the modal is not kept anywhere in Discord; the reporter must type it again (F3's preview step addresses this)." (DD-17) Add "Rolling back to a build without slash commands leaves `/bug` and `/feature` registered in the guild. To remove them, remove the app under Server Settings → Integrations (or kick the bot), then re-invite it." _(unverified: the owner confirms it in the smoke-test teardown, DD-12)_
  - Setup: delete L49 (Message Content intent). Rewrite L50: invite with the `bot` and `applications.commands` scopes, with View Channel, Read Message History (kept for opening and fetching threads on the summary, DD-6), Send Messages, Create Public Threads and Send Messages in Threads on the intake channel.
  - L83-84: "Label for `/bug`" / "Label for `/feature`".
- [x] `docs/SMOKE-TEST.md`:
  - L10-11: two issues in the scratch repo (no long-title issue), and one summary message plus one thread per submission. The failure check writes one summary, one thread and one thread reply, and nothing to GitHub.
  - L9-12 "What it writes": add a **Startup** bullet: the bot registers `/bug` and `/feature` in the guild `DISCORD_GUILD_ID` names, overwrites them on every start, and they stay after teardown (see §5).
  - L44-57 `.env` block: add `DISCORD_GUILD_ID=<the test channel's guild ID>`, with a sentence that the commands sync to this guild, so leaving example.env's value would register `/bug` and `/feature` in the live server.
  - L166 (§5 Record): record the 100-character Title cap instead of the 256-character title. L172 (teardown): delete the smoke-test summary messages and threads, and note that the test guild keeps `/bug` and `/feature` until the app is removed under Server Settings → Integrations (or the bot is kicked). Record whether that removed the commands (DD-12, unverified until this run). Restoring `.env` and restarting the bot syncs the real guild.
  - L42: add Send Messages and the `applications.commands` scope.
  - L101-112: `/bug` then `/feature` through the modal. The table rows: a summary with the mention and title, a thread on it, the issue title = the modal Title, the body's author line linking the summary message, and the labels. Replace the 300-character title check with "the Title field stops at 100 characters".
  - L117-118: run one `/bug`, and quote the new `FILING_ERROR_REPLY` text exactly.
  - L126: two processes on one token both receive each command. One opens the modal and the other's reply fails (logged by the tree's error handler), so a report is filed once, but the owner must still not run two.
  - L158: one `/bug` submission.
  - L181 troubleshooting: replace the Message Content row with "commands missing" (the `applications.commands` scope, `DISCORD_GUILD_ID`, the `synced … commands` log line) and "refused in the right channel" (`DISCORD_CHANNEL_ID`).
  - Add a step: the command in another channel gets the private refusal.
  - Add a cutover note: the owner posts a notice in the channel that `!bug`/`!feature` no longer work. Agents never post.
- [x] `CLAUDE.md`:
  - L3: a one-sentence description, followed by the kept target sentence: "A Discord bot that turns `/bug` and `/feature` reports, made through a modal in a configured intake channel of a Discord server, into fleshed-out GitHub issues in a configured repo of the 4IRL GitHub org and onto that repo's roadmap." (DD-15) Keep the second sentence naming the first target.
  - L22: "per-tag templates" → "per-type templates".
  - L35 log rule: replace `ids (message, thread)` with `ids (guild, channel, message, thread, interaction)`; add that modal text and interaction payloads are member text; and replace the sentence `Exceptions escaping event handlers and hooks are logged by type and event name only.` with one saying that exceptions escaping event handlers and hooks are logged by type and event name only, while the command and modal error handlers log the exception type, the command or modal name, the interaction id and, for a Discord API error, its HTTP status and Discord error code, never `exc_info` or an interaction's repr.
- [x] `plans/ROADMAP.md`:
  - L22 and L26-31 (overview).
  - Capability 1 (L43-48): **Slash-command capture**, with the `/feature` modal acceptance example ("Title: Sharing/Inviting to UTubs").
  - Capability 2 (L49-52): **Per-type questions**, the per-type modal questions with preview, per F3's amended line.
  - L64-65 and L169-176: "a report in a second configured channel".
  - L84-85: the Current-state rows renamed to match, and L80's `*As of …*` date set to the implementation date.
  - L115-118 (Principles, the whole restart-catch-up mention) and L235-238 (Phase 4): drop "messages posted while the bot was down are picked up on restart" and "the restart catch-up covers the gap". Say instead that a command needs the bot online and nothing is queued (DD-9, owner-approved).
  - Phase 1 (L139-159): goal, bullets and exit criteria for `/bug`/`/feature` → summary → thread → issue, and "a command outside the channel is refused".
  - Phase 1.5 (L169): "its own type → label map".
  - Phase 2 (L183-203): per-type modal questions, ephemeral preview with File/Edit, no thread conversation or persisted state.

  Leave Phases 3-4's vision unchanged apart from those lines. The generic "tag" wording in Capability 3, Principles, Phase 3 and Phase 4 stays as is (outside the approved scope); F3/F4 planning rewords it. Afterwards, `grep -nE '!bug|!feature' CLAUDE.md plans/ROADMAP.md` prints nothing, or only lines naming the removed tags as history.
- [x] `example.env`: add the line `# Guild (server) ID: the /bug and /feature commands are synced to this guild only.` directly above `DISCORD_GUILD_ID=`. Read the file before editing (it is the secret-free template; never open `.env`).
- [x] Verify: `grep -n 'applications.commands' README.md` prints the Setup invite line; `grep -niE 'message content' README.md` prints nothing; `grep -n 'DISCORD_GUILD_ID' docs/SMOKE-TEST.md` prints the `.env` block's override line; `grep -nE '!bug|!feature' README.md docs/SMOKE-TEST.md` prints nothing, or only lines naming the removed tags as history (the SMOKE-TEST cutover note); `grep -n 'interaction' CLAUDE.md` prints the log-rule line; `grep -n 'per-tag' CLAUDE.md` prints nothing; `grep -n 'synced to this guild only' example.env` prints the comment line. Done 2026-10-21: every verify grep gave the expected output (the only `!bug`/`!feature` line in README.md and docs/SMOKE-TEST.md is the SMOKE-TEST cutover note; none in CLAUDE.md or ROADMAP.md); the full suite gave 198 passed. Review fixes: SMOKE-TEST requires a separate test guild (never the live server) and holds the real-config restart until the owner's go-ahead and the cutover notice; refusal inside a thread, the confirmation-after-failed-filing limit and the optional third `@someone` issue are documented; README Status links to Reporting instead of repeating it; gates re-run green, 198 passed.

### 7. Verify All Tests Pass

Run the full test suite and the Expected-end-state checks.

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm every test passes. Record the new count.
- [ ] Run the Expected-end-state greps:
  - `grep -rnE '!bug|!feature' --include='*.py' issue_bot` prints nothing;
  - `grep -nE '!bug|!feature' CLAUDE.md plans/ROADMAP.md` prints nothing, or only history lines;
  - `grep -rn --include='*.py' 'message_content' issue_bot` prints nothing;
  - Standing invariant 1's grep prints nothing;
  - `grep -rn --include='*.py' 'tree.sync(' issue_bot` shows only the `guild=` call;
  - `grep -rnE --include='*.py' 'exc_info=|%r|logger\.exception' issue_bot` prints nothing (exit 1 is the pass);
  - `grep -n 'applications.commands' README.md` prints the Setup invite line, and `grep -niE 'message content' README.md` prints nothing;
  - `grep -nE '!bug|!feature' README.md docs/SMOKE-TEST.md` prints nothing, or only history lines.
- [ ] Investigate and fix any failure before marking the plan finished.
- [ ] Copy the **Owner checks** below verbatim into the final report.
- [ ] Add one final-report line for the fold-back: F8's Open risks gain "in multi-container mode every container receives every `/bug`/`/feature`; a container whose route doesn't match must stay silent rather than send F10's refusal, or it races the right container" (DD-18).
- [ ] Add one final-report line for the fold-back: Standing invariant 2 must be updated to match the new CLAUDE.md log rule (ids: guild, channel, message, thread, interaction; `on_error` logs type and event name only; the command and modal error handlers log type, name, interaction id, status and code).

## Owner checks (not executor tasks)
- In a test guild, after the bot is re-invited with the `applications.commands` scope and Send Messages on the intake channel:
  - `/bug` and `/feature` appear only in the configured guild.
  - Each opens a "New bug"/"New feature" modal, and the Title field stops at 100 characters.
  - A submit posts the summary (the mention does not ping), opens a thread on it and files the issue in the scratch repo.
  - The private confirmation links the summary.
  - While the submit is processed, only the reporter sees the bot's "thinking" state; the summary is the only public message.
  - A command in another channel gets the private refusal.
- Run `docs/SMOKE-TEST.md` against the scratch repo (a live run needs your go-ahead each time).
- Before deploying to the live server: re-invite the bot there with the `bot` and `applications.commands` scopes (or confirm the scope is already granted), and grant View Channel and Send Messages on the live intake channel, alongside the existing thread permissions. Post the cutover notice in the intake channel that `!bug`/`!feature` no longer work (agents never post live). After the deploy, confirm the log shows `synced 2 commands to guild <DISCORD_GUILD_ID>` and that `/bug` opens the modal in the live intake channel.

## Status
finished: false
