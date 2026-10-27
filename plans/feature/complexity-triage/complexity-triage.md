# Complexity triage (S/M/L/XL)

## Summary
F4: documented rules rate every `/bug` and `/feature` report S, M, L or XL from its issue type and
the length of its modal answers. The private preview shows the rating, and four buttons let the
reporter override it before **File**. The filed issue carries exactly one `complexity:<band>` label,
which the bot creates on the route's repo first if it is missing. If that label can't be created,
the issue is still filed with only its type label and a WARNING is logged. The thread's link
message shows the band. The rules live in one pure module,
`issue_bot/complexity.py`, and members read them in `docs/COMPLEXITY.md`, linked from the README.

## Decisions (owner-answered at planning, 2026-10-27)
- **DD-1 Rules** (dd-261027-040): the type sets a starting band (bug → S, feature → M). Total answer
  text (the sum of `len(answer.strip())` over the answers, computed inside `rate` so blanks and
  whitespace-only answers count 0; review DD-5, dd-261027-045) of at least 800
  characters raises it one band, and at least 2000 raises it two. Capped at XL. No route-file change.
- **DD-2 Label creation** (dd-261027-041): an explicit ensure step. `GitHubClient.ensure_label` POSTs
  `repos/<repo>/labels`; 201 or 422 (already exists) counts as success, cached per (repo id, label)
  for the process. Any other result raises `GitHubError("label", status)`. `file_candidate` catches
  it, logs a WARNING (type, message id, error type, stage and status only), and files the issue
  with only the type label, so a label problem never stops filing (owner override at review,
  review DD-1, dd-261027-048). The 401 path still drops the cached token.
- **DD-3 Override UI** (dd-261027-042): four buttons, S / M / L / XL, on row 0 above File and Edit
  (row 1). The current band's button is `primary`, the others `secondary`.
- **DD-4 After Edit** (dd-261027-043): an override sticks across Edit. Any band press sets an
  explicit `Draft.overridden` flag (review DD-2, dd-261027-049), which Edit carries over with the
  chosen band; a draft with `overridden` False is re-rated from the new answers.
- **DD-5 Link message** (review DD-9, dd-261027-052): the thread's link message shows the band:
  `Filed as GitHub issue #<number> (complexity <band>): <title>`.
- **DD-6 Preview field text** (Pass 2 review DD-2, dd-261027-054): the preview's Complexity field
  follows `draft.overridden`, the same flag DD-4 uses. It shows the "your choice" text whenever
  the reporter has pressed a band, even the suggested one, and the "suggested by the rules" text
  otherwise. `preview_embed` takes the `Draft`, so the field and the filed band come from one
  object.

## Research Findings
- The data flows modal → `Draft(title, answers)` → `PreviewView.draft` → `_post_and_file` →
  `candidate_from_submission` (handler.py) → `IssueCandidate` → `file_candidate` → `issue_labels`
  (issues.py) → `GitHubClient.create_issue`. `PreviewView` is built in one place only,
  `IntakeModal.on_submit`. The Edit path builds a fresh `Draft` from the modal inputs, so the
  override must be read from `self.preview.draft` there.
- The modal is full (Title plus 4 questions is Discord's 5-field cap), so the override lives in the
  preview (F3's kept contract). `PreviewView` callbacks must call `_keep_deadline()` first and update
  state before their first `await` (the `_closed` guard pattern of `file_button`).
- The preview embed today is title and description only. Tests pin `embed.description ==
  render_body(...)` (`test_submit_sends_private_preview_only`, `test_preview_embed_boundary`,
  `test_edit_submit_updates_preview_in_place`), so the rating goes in an embed **field**, which
  leaves `render_body`, the filed body and the 4096-character description budget untouched.
- `_request` hard-codes POST, and `POST /repos/{o}/{r}/labels` is a POST, so `ensure_label` needs no
  transport change. The token's `{"issues": "write"}` covers creating labels _(unverified: proven
  only by the owner's live run, Manual checks)_. `GitHubError.stage` is documented as
  `token`/`issue`, so `label` must be added to its docstring. `filing_hook` already logs any
  `GitHubError` by type, stage and status; a label error never reaches it, because
  `file_candidate` catches it (Decisions DD-2).
- These tests pin the exact label list and change when the complexity label is added:
  test_bot.py `test_filing_hook_files_issue_posts_link_and_logs_url`, test_intake.py
  `test_second_route_file_files_to_its_repo_with_its_labels` and
  `test_file_files_issue_through_filing_hook`, and test_issues.py
  `test_issue_labels_follow_config`, `test_issue_labels_use_target_mapping` and
  `test_file_candidate_passes_title_body_labels`. `conftest.fake_github` exposes only
  `create_issue`, so it gains `ensure_label`. `make_candidate` builds `IssueCandidate` by keyword.
  test_handler.py calls `candidate_from_submission` positionally, and test_intake.py's
  `test_modal_prefills_from_draft` and `test_draft_repr_hides_text` build `Draft` positionally.
- Showing the band in the link message changes F7's kept contract `threads.filed_reply(issue,
  title)` (built from `FILED_REPLY`) to `filed_reply(issue, title, complexity)`; record this in
  META-PLAN at fold-back (its Baseline and its F7 section quote the old form). At the same
  fold-back, also update F5's kept contract (an `ensure_label` call precedes `create_issue` inside
  `file_candidate`; its `GitHubError` is caught there and logged as a WARNING, and the issue is
  filed with the type label only) and F3's (`Draft` also carries `suggested`, `complexity` and
  `overridden`), and record in Baseline that a label that can't be created is skipped (review
  DD-1). Every call of `filed_reply`: bot.py `filing_hook`; tests test_threads.py
  `test_filed_reply_has_number_title_and_url`, test_bot.py
  `test_filing_hook_files_issue_posts_link_and_logs_url` and
  `test_filing_hook_without_thread_replies_link_on_summary`, and test_intake.py
  `test_file_files_issue_through_filing_hook`. README.md's Status paragraph and
  docs/SMOKE-TEST.md's check table (`Discord thread` row) quote the old message text. `threads`
  imports only `github` from the project, so importing `Complexity` there adds no cycle.
- F6 coupling: `issue_bot.complexity.Complexity` is the one home of the band names, and F6 reads
  the filed band from `IssueCandidate.complexity` for its Project field (META-PLAN's F6 section).
- issues.py has no logger today; bot.py, intake.py and threads.py each create one with
  `logger = logging.getLogger(__name__)`, so the new WARNING's record name is `issue_bot.issues`
  (test_bot.py's `bot_records` filters on `issue_bot.bot` only).
- Import graph: `issue_type` ← `config` ← `github` ← `handler` ← `issues` ← `intake` ← `bot`. The new
  `complexity.py` imports only `issue_type`, so `handler`, `issues` and `intake` can all import it
  without a cycle. Each module's new `from issue_bot.complexity import …` line goes in alphabetical order in its
  project import group, just before `issue_bot.config` (or first, where there is none). `complexity.py` imports `Mapping` and `Sequence` from
  `collections.abc`, `StrEnum` from `enum`, `MappingProxyType` from `types`, then `IssueType`
  from `issue_bot.issue_type`. Run tests with `.venv/bin/pytest` from the repo root (CLAUDE.md,
  META-PLAN *Verification*); `asyncio_mode = "auto"`.

## Steps

### 1. Rating rules module - COMPLETE (2026-10-27)
Add the pure, log-free `issue_bot/complexity.py` and its unit tests (Red → Green).

**To-do:**
- [x] Red: create `tests/test_complexity.py` with tests that fail on import:
  - `rate(IssueType.BUG, ())` is `Complexity.S`, and `rate(IssueType.FEATURE, ())` is `Complexity.M`.
  - Parametrized boundaries over answers built as `(("Q", "x" * n),)`: bug n=799 → S, 800 → M,
    1999 → M, 2000 → L. Feature n=799 → M, 800 → L, 2000 → XL. A feature at 5000 is still XL (the cap).
  - The length is summed across answers: two answers of 400 chars each make a bug M. Blank answers
    (`("Device", "")`) add 0, and so does a whitespace-only answer: a bug with
    `(("Q", " " * 900),)` is S, and `(("Q", "x" * 798 + " " * 4),)` is S (798 after strip, 802
    before).
  - `complexity_label(Complexity.XL) == "complexity:XL"`, and
    `[str(b) for b in Complexity] == ["S", "M", "L", "XL"]` (the order the buttons use).
  Run `.venv/bin/pytest tests/test_complexity.py` and confirm it fails with `ModuleNotFoundError`.
- [x] Green: write `issue_bot/complexity.py`. Its module docstring says it holds the documented S/M/L/XL
  rules (see `docs/COMPLEXITY.md`), is pure, and never logs:
  - `class Complexity(StrEnum)`: `S = "S"`, `M = "M"`, `L = "L"`, `XL = "XL"`, declared in this order.
  - `STARTING_BAND: Mapping[IssueType, Complexity] = MappingProxyType({IssueType.BUG: Complexity.S,
    IssueType.FEATURE: Complexity.M})`.
  - `RAISE_ONE_AT = 800` and `RAISE_TWO_AT = 2000`, with a trailing comment saying they are total
    answer characters.
  - `def rate(issue_type: IssueType, answers: Sequence[tuple[str, str]]) -> Complexity`: compute
    `length = sum(len(answer.strip()) for _, answer in answers)` (it strips itself, so it matches
    the documented rule whatever its caller passes) and
    `steps = (length >= RAISE_ONE_AT) + (length >= RAISE_TWO_AT)`, then index into `list(Complexity)`
    from the starting band's position plus `steps`, capped at the last member.
  - `def complexity_label(band: Complexity) -> str`: return `f"complexity:{band}"`.
  Run `.venv/bin/pytest tests/test_complexity.py` and confirm it is green.
- [x] Refactor if needed, then run `.venv/bin/pytest` and confirm the full suite is green.

### 2. `GitHubClient.ensure_label` - COMPLETE (2026-10-27)
Create a missing label explicitly before filing (DD-2).

**To-do:**
- [x] Red: in `tests/test_github.py`, reuse the existing `token_response()` / fake-transport pattern
  (`AsyncMock(side_effect=[...])`, calls unpacked as `(method, url, headers, payload)`) and add:
  - `ensure_label(route, "complexity:M")` with responses `[token_response(), (201, {...})]` sends
    `POST {API_URL}/repos/example-org/example-repo/labels` with payload
    `{"name": "complexity:M", "color": LABEL_COLOR}` and the installation token's Bearer header.
  - A 422 response is success (no raise).
  - A second `ensure_label` for the same repo and name makes no further transport call (the cache).
    A different name does make one.
  - The cache is keyed per repo: with the `two_route_config` fixture (`first, second =
    two_route_config.routes.values()`, repo ids 222 and 223, as in
    `test_two_routes_mint_separate_tokens`), `ensure_label(first, "complexity:S")` then
    `ensure_label(second, "complexity:S")` with responses `[token_response(), (201, {}),
    token_response(), (201, {})]` makes four transport calls, the fourth a POST to
    `{API_URL}/repos/example-org/other-repo/labels` (Pass 2 review DD-5, dd-261027-057).
  - A 401 raises `GitHubError` with `stage == "label"`, `status == 401`, and drops the cached token
    (the next call mints again, as in the existing `create_issue` 401 test).
  - A 500 raises `GitHubError("label", 500)`, and an `aiohttp.ClientConnectionError()` on the label
    request (`side_effect=[token_response(), error]`) raises `GitHubError("label", None)` with
    `__context__ is None`. A failed name is not cached.
  Run them and confirm they fail (an `ImportError` on `LABEL_COLOR` when test_github.py is collected).
- [x] Green: in `issue_bot/github.py`, add `LABEL_COLOR = "c5def5"` (comment: the colour new
  labels get; any later colour change happens on GitHub). Add `self._labels: set[tuple[int, str]] =
  set()` in `__init__`, and add
  `async def ensure_label(self, target: TargetConfig, name: str) -> None` (docstring: create the
  label in the target repo unless it exists; raise GitHubError otherwise). It returns at once when
  `(target.github_repo_id, name)` is in `self._labels`. Otherwise it gets a token with
  `_installation_token(target.github_repo_id)` and calls `_request("label",
  f"{API_URL}/repos/{target.github_repo}/labels", self._headers(token), {"name": name, "color":
  LABEL_COLOR})`. On 401 it pops the cached token as `create_issue` does and raises
  `GitHubError("label", 401) from None`. Any status other than 201 or 422 raises
  `GitHubError("label", status) from None`. On success it adds the pair to `self._labels`.
  A code comment at the 201/422 check says: every 422 is taken as "already exists" (GitHub also
  uses 422 for other validation errors, unlikely with a fixed name and colour), and labels stay
  cached for the process, so one deleted on GitHub is re-created only after a restart (review
  DD-3, dd-261027-050).
- [x] Update the `GitHubError` docstring: ``stage`` is ``"token"``, ``"label"`` or ``"issue"``.
  Update the `GitHubClient` docstring: it creates issues, and the labels they need, as a GitHub App
  installation, caching a repo-scoped token per repo.
- [x] Run `.venv/bin/pytest tests/test_github.py`, then `.venv/bin/pytest`, and confirm both are green.

### 3. Carry the band from submit to the filed label - COMPLETE (2026-10-27)
Rate each submission, carry the band (and the override flag) on `Draft` and the band on
`IssueCandidate`, file it as a label (skipped with a WARNING if the label can't be created), and
show it in the thread's link message (Decisions DD-5).

**To-do:**
- [x] Red: update and add tests first:
  - In `tests/test_issues.py`, change
    `test_issue_labels_follow_config` to expect `["bug", "complexity:S"]` /
    `["enhancement", "complexity:S"]` (make_candidate's default band, below), change
    `test_issue_labels_use_target_mapping` to `["idea", "complexity:S"]`, and add a test that
    `make_candidate(complexity=Complexity.XL)` gives a label list ending `"complexity:XL"`.
  - Change `test_file_candidate_passes_title_body_labels` to give the fake github
    `ensure_label=AsyncMock()`. Assert `ensure_label.assert_awaited_once_with(candidate.target,
    "complexity:S")`, assert that it was awaited before `create_issue` (attach both to one parent
    `Mock` and compare `mock_calls` order, the pattern test_intake already uses), and assert
    `create_issue` got `[..., "complexity:S"]`. Add a test that a `GitHubError("label", 500)` from
    `ensure_label` does not stop filing: build the candidate with `title="Secret title words"`,
    `answers=(("What happened?", "Secret body words"),)` and `author_name="Alice"`, run under
    `caplog.at_level(logging.INFO)`, and assert `file_candidate` returns the filed issue,
    `create_issue` is awaited once with labels exactly `["bug"]`, exactly one WARNING record named
    `issue_bot.issues` contains `could not create complexity label for bug`, `message_id=99`,
    `GitHubError`, `stage=label` and `status=500`, and `assert_no_member_text(caplog)` passes.
    test_issues.py adds `import logging`, `GitHubError` to its `issue_bot.github` import, and
    `assert_no_member_text` to its `tests.conftest` import.
  - In `tests/test_handler.py`, pass the band positionally after `answers`
    (`candidate_from_submission(IssueType.BUG, "Fix it", (("Q", "A"),), Complexity.M, user,
    message, route)`) and assert `candidate.complexity is Complexity.M`. Also insert `Complexity.M`
    after the answers tuple in `test_submission_candidate_repr_hides_text`'s positional call; its
    assertions stay unchanged (the band is not member text, so it stays in `repr`).
  - In `tests/test_intake.py`, add `Complexity.S, Complexity.S, False` (suggested, complexity,
    overridden) to the positional `Draft(...)` builds in `test_modal_prefills_from_draft` and
    `test_draft_repr_hides_text`. Change the label assert in
    `test_second_route_file_files_to_its_repo_with_its_labels` to `["defect", "complexity:S"]` and
    the one in `test_file_files_issue_through_filing_hook` to `["bug", "complexity:S"]`, and that
    test's `filed_reply(FiledIssue(7, ISSUE_URL), "Fix it")` expectation to pass
    `Complexity.S` as a third argument. Add a test that a fresh submit's view has
    `view.draft.suggested == view.draft.complexity == rate(issue_type, answers)` and
    `view.draft.overridden is False`, and one that a bug submitted with 900 characters of answers
    is filed with `"complexity:M"`.
  - In `tests/test_threads.py`, change `test_filed_reply_has_number_title_and_url` to
    `filed_reply(FiledIssue(7, ISSUE_URL), "Fix *it*", Complexity.L) ==
    f"Filed as GitHub issue #7 (complexity L): Fix \\*it\\*\n{ISSUE_URL}"`.
  - In `tests/test_bot.py`, change the label assert in
    `test_filing_hook_files_issue_posts_link_and_logs_url` to `["bug", "complexity:S"]`, and the
    `filed_reply(FiledIssue(7, ISSUE_URL), "Secret title words")` expectations in that test and in
    `test_filing_hook_without_thread_replies_link_on_summary`
    to pass `Complexity.S` as a third argument (make_candidate's default band). Add
    `test_filing_hook_files_without_complexity_label_when_label_fails`: `github =
    fake_github(FiledIssue(7, ISSUE_URL))`, then `github.ensure_label.side_effect =
    GitHubError("label", 403)`; run `filing_hook(github)(message, secret_candidate(make_candidate))`
    under `caplog.at_level(logging.INFO)`. Assert `create_issue` is awaited once with labels
    exactly `["bug"]`; the thread send is awaited once with
    `filed_reply(FiledIssue(7, ISSUE_URL), "Secret title words", Complexity.S)`,
    `allowed_mentions=NO_MENTIONS, suppress_embeds=True` (never `FILING_ERROR_REPLY`); exactly one
    WARNING record named `issue_bot.issues` contains `stage=label` and `status=403`; no
    `issue_bot.bot` record is an ERROR; and `assert_no_member_text(caplog)` passes.
  - Each edited test module (test_issues, test_handler, test_intake, test_threads, test_bot)
    imports `Complexity` (test_intake also `rate`) from `issue_bot.complexity`, and so does
    conftest.py.
  Run `.venv/bin/pytest` and confirm these fail.
- [x] `tests/conftest.py`: in `fake_github(result)`, both branches (the exception `side_effect` one
  and the `return_value` one) also set `ensure_label=AsyncMock(return_value=None)`. `make_candidate` gains the keyword
  `complexity: Complexity = Complexity.S` and passes it through (update the `CandidateFactory` alias
  if it spells out the parameters).
- [x] `issue_bot/handler.py`: add the field `complexity: Complexity` to `IssueCandidate` after
  `answers`, with no default (it is not member text, so no `repr=False`). `candidate_from_submission`
  gains the parameter `complexity: Complexity` after `answers` and passes it through. Update the
  `IssueCandidate` docstring to say `complexity` is the band the reporter filed with (not member
  text, so it stays in `repr`). Import `Complexity` from `issue_bot.complexity`.
- [x] `issue_bot/intake.py`:
  - `Draft` gains `suggested: Complexity`, `complexity: Complexity` and `overridden: bool`, in that
    order after `answers`, no defaults and in `repr` (the docstring says `suggested` is the rules'
    band, `complexity` the band to file, and `overridden` whether the reporter pressed a band
    button).
  - In `IntakeModal.on_submit`, after computing `answers`, set `suggested = rate(self.issue_type,
    answers)`. When `self.preview is not None and self.preview.draft.overridden` (DD-4: keep an
    override), set `complexity = self.preview.draft.complexity` and `overridden = True`; else
    `complexity = suggested` and `overridden = False`. Build
    `Draft(title, answers, suggested, complexity, overridden)`.
  - In `_post_and_file`, pass `draft.complexity` to `candidate_from_submission` after `draft.answers`.
  - Import `Complexity` and `rate` from `issue_bot.complexity`.
- [x] `issue_bot/issues.py`: add `import logging`, `GitHubError` to the `issue_bot.github` import,
  and a module logger `logger = logging.getLogger(__name__)` (the form bot.py, intake.py and
  threads.py use). `issue_labels` returns `[candidate.target.labels[candidate.type],
  complexity_label(candidate.complexity)]` (type label first). `file_candidate` sets
  `labels = issue_labels(candidate)`, then `try: await github.ensure_label(candidate.target,
  labels[1])` `except GitHubError as exc:` logs
  `logger.warning("could not create complexity label for %s message_id=%s: %s stage=%s status=%s",
  candidate.type, candidate.message_id, type(exc).__name__, exc.stage, exc.status)` and sets
  `labels = labels[:1]` (the type label only). It then returns `await
  github.create_issue(candidate.target, issue_title(candidate), issue_body(candidate), labels)`.
  The log carries no member text and no response text; a 401 has already dropped the cached
  token inside `ensure_label`, so the following `create_issue` mints a fresh one. A token failure
  inside `ensure_label` (`stage=token`) is caught the same way; `create_issue` then tries to mint
  again and, if that fails too, raises as today. Other
  `GitHubError`s (from `create_issue`) still propagate to `filing_hook` unchanged. Import
  `complexity_label` from `issue_bot.complexity`. Update the module docstring ("…title, body and
  labels…"), adding a sentence that its one log line, a skipped complexity label, carries the
  issue type, the message id and the `GitHubError`'s type, stage and status only, never member
  text or response text; and update the `issue_labels` / `file_candidate` docstrings: the type label plus one
  `complexity:<band>` label, and a label that can't be created is skipped with a WARNING.
- [x] `issue_bot/threads.py`: `FILED_REPLY = "Filed as GitHub issue #{number} (complexity {band}):
  {title}\n{url}"` and `def filed_reply(issue: FiledIssue, title: str, complexity: Complexity) ->
  str`, passing `band=complexity` to `format` (the band is fixed text, not escaped). Import
  `Complexity` from `issue_bot.complexity` (no cycle: complexity imports only `issue_type`).
- [x] `issue_bot/bot.py` `filing_hook`: pass `candidate.complexity` as the third argument of
  `filed_reply(issue, candidate.title, candidate.complexity)`.
- [x] Run `.venv/bin/pytest` and confirm it is green. Then run the invariant-1 grep from META-PLAN
  (`grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py'
  issue_bot`) and confirm it prints nothing.

### 4. Show the rating and the override buttons in the preview - COMPLETE (2026-10-27)
The preview shows the band in an embed field, and the S/M/L/XL buttons change it in place (DD-3, DD-4).

**To-do:**
- [x] Red: in `tests/test_intake.py` add:
  - `preview_embed(Draft("T", answers, Complexity.M, Complexity.M, False), "Alice")` has one field
    with `name == COMPLEXITY_FIELD` and `value == COMPLEXITY_SUGGESTED.format(band="M")`, and its
    description is still exactly `render_body("Alice", PREVIEW_LINK, answers)`. With
    `Draft("T", answers, Complexity.M, Complexity.L, True)` the value is
    `COMPLEXITY_CHOSEN.format(band="L", suggested="M")`, and with
    `Draft("T", answers, Complexity.M, Complexity.M, True)` it is
    `COMPLEXITY_CHOSEN.format(band="M", suggested="M")` (Decisions DD-6). Update the existing direct
    `preview_embed(...)` calls in `test_preview_embed_boundary` and
    `test_edit_submit_updates_preview_in_place` to pass a `Draft` (with `Complexity.S,
    Complexity.S, False`) and the author name.
  - A fresh preview's view has the buttons `s_button`, `m_button`, `l_button` and `xl_button` on
    row 0 and `file_button` and `edit_button` on row 1. Only the suggested band's button is
    `discord.ButtonStyle.primary`.
  - Pressing `await view.l_button.callback(click)` (a fresh `make_interaction()`) sets
    `view.draft.complexity is Complexity.L` and `view.draft.overridden is True`, and keeps
    `view.draft.suggested`. It awaits
    `click.response.edit_message` once with kwargs exactly `{"embed", "view"}`, where `view is view`
    and the embed's only field has `value == COMPLEXITY_CHOSEN.format(band="L", suggested="S")`
    (the view comes from `submitted_preview`, a short bug, so the rules suggested S).
    `l_button` is then the only primary button.
  - A band press logs no member text (Pass 2 review DD-1, dd-261027-053): build the view with
    `submitted_preview(route, AsyncMock(), make_interaction(), title="Secret title words",
    answers=("Secret body words",))`, press `l_button` inside `caplog.at_level(logging.INFO)`,
    and call `assert_no_member_text(caplog)` (it checks `Secret title words`, `Secret body words`
    and `Alice`, the `make_interaction` user's display name).
  - After an L press, File files with labels ending `"complexity:L"`.
  - These Edit-submits need chosen answer lengths, so they can't use `edited_submit` (its fixed
    `"Steps v2"` stays below every threshold). Each gets the modal with
    `modal = await reopened_modal(view, make_interaction)`, sets `modal.answer_inputs[0]._value`
    to the needed text (e.g. `"x" * 900`, `"x" * 2000`) as `test_preview_flow_logs_ids_not_text`
    does, runs `await modal.on_submit(edit_interaction)` (a fresh `make_interaction()`), and takes
    the new view from `edit_interaction.response.edit_message.await_args.kwargs["view"]`.
  - Override then Edit-submit with new answers keeps L (`new_view.draft.complexity is L`,
    `new_view.draft.overridden is True`, and the suggested band is re-rated). The new view's
    `l_button.style is discord.ButtonStyle.primary` and it is the only primary band button, and
    the embed passed to `edit_message` has the field value
    `COMPLEXITY_CHOSEN.format(band="L", suggested=<the re-rated band>)`. With no override, an
    Edit-submit whose answers now exceed 800 characters re-rates to the new suggestion.
  - Double Edit: on a short bug (suggested S), press L; an Edit-submit with 2000+ characters
    re-rates `suggested` to L; a second Edit-submit with short answers re-rates `suggested` to S,
    and `draft.complexity` is still L (`overridden` carries it; equality inference would drop it).
  - Pressing the suggested band counts as an override: on a short bug (suggested S), press S, then
    Edit-submit with 900 characters (suggested M); `draft.complexity` stays S and
    `draft.overridden is True`. Right after the S press, the embed passed to `edit_message` has the
    field value `COMPLEXITY_CHOSEN.format(band="S", suggested="S")` (Decisions DD-6).
  - A band press after File (`view._closed` set) does nothing: `edit_message` is not awaited, and
    `view.draft` is the same object as before the press (`is`), so a guard placed after the
    `replace` line fails it (Pass 2 review DD-4, dd-261027-056).
  - A band press keeps the deadline, mirroring `test_edit_keeps_the_deadline`: set
    `view._deadline -= 120`, press `l_button`, and assert
    `PREVIEW_TIMEOUT - 121 < view.timeout <= PREVIEW_TIMEOUT - 120`. This fails if `_choose` skips
    `_keep_deadline()`, because a direct `.callback` call leaves `view.timeout` at `PREVIEW_TIMEOUT`.
  - tests/test_intake.py adds `COMPLEXITY_CHOSEN`, `COMPLEXITY_FIELD` and `COMPLEXITY_SUGGESTED` to
    its `issue_bot.intake` import.
  Run them and confirm they fail.
- [x] `issue_bot/intake.py` constants, next to the other fixed text (none carries member text):
  `COMPLEXITY_FIELD = "Complexity"`, `COMPLEXITY_SUGGESTED = "{band}, suggested by the rules"` and
  `COMPLEXITY_CHOSEN = "{band}, your choice (the rules suggested {suggested})"`. Change
  `PREVIEW_REPLY` to `"Here's your report as it will be filed. Pick a complexity if the suggested one
  is off; **File** posts it; **Edit** changes it. This preview expires in 10 minutes."`.
- [x] `preview_embed(draft: Draft, author_name: str)` (it replaces the `title, answers` parameters):
  build the embed as today from `draft.title` and `draft.answers`, then
  `embed.add_field(name=COMPLEXITY_FIELD, value=...)` with
  `COMPLEXITY_CHOSEN.format(band=draft.complexity, suggested=draft.suggested)` when
  `draft.overridden` is set, else `COMPLEXITY_SUGGESTED.format(band=draft.complexity)` (Decisions
  DD-6). Update its docstring. In `on_submit`, bind `draft = Draft(title, answers, suggested,
  complexity, overridden)` once, pass it to `PreviewView`, and call
  `preview_embed(draft, interaction.user.display_name)`.
- [x] Update intake.py's module docstring to mention the S/M/L/XL buttons and the Complexity field
  (they carry no member text and log nothing), and `PreviewView`'s docstring: the band buttons
  override the rated band, **File** files the draft once, **Edit** reopens the modal.
- [x] `PreviewView`:
  - Add four decorated buttons, `@discord.ui.button(label="S", style=discord.ButtonStyle.secondary,
    row=0)` and likewise for M, L and XL (`s_button`, `m_button`, `l_button`, `xl_button`). Each body
    is `await self._choose(interaction, Complexity.<band>)`.
  - Add `row=1` to the `File` and `Edit` decorators.
  - Add `_paint(self) -> None`, which sets each band button's style to `primary` when its band is
    `self.draft.complexity` and to `secondary` otherwise (a `{Complexity: button}` mapping built in
    `__init__` from the four bound buttons). Call it at the end of `__init__`.
  - Add `async def _choose(self, interaction, band: Complexity) -> None`. It calls
    `self._keep_deadline()`, returns if `self._closed`, then (before any `await`) sets
    `self.draft = replace(self.draft, complexity=band, overridden=True)` and `self._paint()`, with
    a code comment: the band is set before the edit so a concurrent File sees it; if the edit
    fails, the view keeps the new band (accepted, review DD-4, dd-261027-051). The edit re-stores
    the view and restarts its timeout, so the expiry drifts later by the edit's sub-second round
    trip; this is accepted (review DD-7), as on the Edit-submit path. A press racing File can
    re-show dead buttons on the filed preview; this is harmless, and the issue files once (Pass 2
    review DD-3, dd-261027-055). A band press on the old preview while its Edit modal is being
    submitted is not carried into the new draft, and if that press's edit lands last the message
    briefly shows the old, dead buttons; this is accepted, as it is sub-second and the modal covers
    the preview (assumed: dd-policy, dd-261027-058). (Extend intake.py's
    `from dataclasses import dataclass, field` to `from dataclasses import dataclass, field,
    replace`). Then it awaits
    `interaction.response.edit_message(embed=preview_embed(self.draft,
    interaction.user.display_name), view=self)`. Errors
    reach the existing `PreviewView.on_error`. It logs nothing: neither band nor answers is needed in
    the logs.
- [x] Run `.venv/bin/pytest` and confirm it is green. The band-press log test proves `_choose`
  logs no member text, and `test_preview_flow_logs_ids_not_text` still passes unchanged (it never
  presses a band button).

### 5. Member-readable rules and docs
Document the rules where members can read them, and bring the README, runbook and CLAUDE.md up to date.

**To-do:**
- [ ] Create `docs/COMPLEXITY.md`. It covers what the four bands mean (S=1, M=2, L=3, XL=5 points);
  the rules (the starting band per type, the 800 and 2000 total-character thresholds, the XL cap)
  with two worked examples; that the reporter can override in the preview and that an override
  survives Edit; the filed `complexity:<band>` label, which the bot creates if missing (on each
  route's repo, the first time a band is filed there; to remove the labels, delete them on the
  repo's Labels page; an older build stops applying them and needs no config change; a label the
  bot can't create is skipped for that issue, which is still filed with its type label); that the
  bot remembers a label it created or found until it restarts, so a `complexity:<band>` label
  deleted on GitHub comes back only after a restart; that the thread's link message names the
  band (without quoting the message text, whose home is README's Status paragraph); and that
  other members change the label on GitHub after filing (the preview is private, open risk c).
  It also says the rules live in `issue_bot/complexity.py`.
- [ ] Drift test in `tests/test_complexity.py`: read
  `Path(__file__).resolve().parent.parent / "docs" / "COMPLEXITY.md"` (the `REPO_ROOT` pattern of
  tests/test_config.py) and assert it contains
  `str(RAISE_ONE_AT)`, `str(RAISE_TWO_AT)` and, for each `IssueType`, the line
  `` `<type>` starts at <band> `` built from `STARTING_BAND` (write the doc's rule lines in exactly
  that form). tests/test_complexity.py adds `from pathlib import Path` and imports `STARTING_BAND`,
  `RAISE_ONE_AT` and `RAISE_TWO_AT` from `issue_bot.complexity`.
- [ ] `README.md`:
  - Replace the quoted `PREVIEW_REPLY` text in the usage step with the new one, and add one sentence
    on the S/M/L/XL buttons with a link to `docs/COMPLEXITY.md`.
  - Change the labels note (in Configuration, "must already exist … may be dropped or auto-created …
    _(unverified)_") to say each route's type labels must exist, while the bot creates
    `complexity:<band>` labels itself.
  - In the Reporting section's step 4, change "posts the issue's number, title and link in the
    thread" to "posts the issue's number, complexity band, title and link in the thread".
  - Add F4 to the Status paragraph. In the same paragraph, change the quoted link
    message `Filed as GitHub issue #<number>: <title>` to
    `Filed as GitHub issue #<number> (complexity <band>): <title>`, and "the issue gets its type's
    label" to say it also gets one `complexity:<band>` label.
- [ ] `docs/SMOKE-TEST.md`: add a step to the filing run: check that the preview shows the
  Complexity field, that pressing a band button highlights it, and that the filed issue carries that
  `complexity:<band>` label (created on the test repo on first use). Change the "filed without its
  label" troubleshooting row to cover only type labels. Also:
  - Replace the quoted preview text in the filing run ("A private preview appears, reading …") with
    the new `PREVIEW_REPLY`, and say the preview shows a **Complexity** field.
  - Change the check table's `Issue label` row to: the type label (`bug` / `enhancement`) plus
    exactly one `complexity:<band>` label, matching the band the preview showed.
  - In `## What it writes`, add to the Success checks that the first filing with each band creates
    that `complexity:<band>` label in the scratch repo.
  - Change the `Re-runs` line in `## What it writes` to: every re-run repeats its writes, except
    that a `complexity:<band>` label already in the repo is not created again.
  - Change the check table's `Discord thread` row to quote
    `Filed as GitHub issue #<n> (complexity <band>): <title>`, with the band the preview showed.
  - Add a troubleshooting row: "An issue is filed without its `complexity:<band>` label and the
    log shows `could not create complexity label … stage=label`" → the bot could not create that
    label. A 401 is a stale token (run the command again). A 403 or 404 means the App lacks
    Issues: write on that repo, or the repo isn't in the installation.
- [ ] `CLAUDE.md` Stack line: change "complexity ratings are planned as rule-based, with no LLM" to
  "complexity ratings are rule-based (`issue_bot/complexity.py`, documented in
  `docs/COMPLEXITY.md`), with no LLM".
- [ ] Run `.venv/bin/pytest` and confirm it is green.

### 6. Verify All Tests Pass
Run the full suite and the Expected-end-state checks.

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm every test passes.
- [ ] Confirm the Expected end state. `docs/COMPLEXITY.md` exists and `grep -n 'COMPLEXITY.md'
  README.md` prints a link. `issue_labels` returns exactly one `complexity:` label, with
  `ensure_label` before `create_issue`, and a failed `ensure_label` files with the type label only
  and logs a WARNING (steps 2-3 tests). `filed_reply` shows the band (step 3 tests). The
  invariant-1 grep prints nothing.
- [ ] Investigate and fix any failures before marking the plan finished.
- [ ] Copy the Manual checks below verbatim into the final report.

## Manual checks (owner, live; never run by an agent)
- On the separate test server (`docs/SMOKE-TEST.md`), run `/bug` with short answers. The preview
  shows a **Complexity** field whose value reads `S, suggested by the rules`, with the S button
  highlighted.
- Press S. The field now reads `S, your choice (the rules suggested S)` (Decisions DD-6).
- Press L. The field reads `L, your choice (the rules suggested S)` and L is highlighted. Press
  Edit, change an answer, and submit: L is still selected.
- Press File. The test repo's issue carries the type label and `complexity:L`, and the
  `complexity:L` label now exists in the repo's Labels page. This run is also the only proof that
  the installation token can create labels; if it can't, the issue is filed with only the type
  label and the log shows `could not create complexity label … stage=label`.
- The thread's link message reads `Filed as GitHub issue #<n> (complexity L): <title>`, with the
  issue link on the next line.
- Each re-run of these checks files another issue on the test repo; the
  `complexity:L` label is not created again.

## Status
finished: false
