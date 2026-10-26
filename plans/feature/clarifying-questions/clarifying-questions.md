# Per-tag modal questions with preview and confirm (F3)

## Summary
Each issue type's questions, defined per route in the route file, become the fields of the
`/bug` and `/feature` modal: Title plus one to four questions (Discord's five-field cap). On
submit the reporter gets a private preview of the issue body, built by the same formatter that
files it, with **File** and **Edit** buttons. File posts the public summary and files the issue
through the existing path. Edit reopens the modal prefilled. An expired preview files nothing
and says so. The filed body has one section per answered question.

## Research Findings
- **Where the questions live.** F8's kept contract (META-PLAN, "F8 — Multi-target routes") says
  F3 adds its keys under `[routes.<name>]` "by extending `ROUTE_KEYS` and `load_routes`, never a
  second config file or per-route env keys". Standing invariant 3 makes every key required. So
  `questions` becomes a required route key, checked like `labels` (`issue_bot/config.py` `_route_labels`:
  one entry per `IssueType`). Questions reach `IntakeModal` through the
  `target` it already receives (`intake_command`'s `report` callback), so `intake_command`/`IssueBot` signatures don't
  change. Stdlib `tomllib` only (PyYAML is not installed).
- **Kept contracts F7 and F10.** F7 says F3's preview reuses `bot._post_outcome`, but the preview
  is an ephemeral interaction response that exists before any summary or thread, so it uses the
  interaction's own responses (`followup.send`, `edit_message`, `edit_original_response`).
  Filing outcomes still go through `_post_outcome` unchanged. F10's "submit always posts the
  summary before calling on_candidate" becomes File doing so (`_post_and_file`). The fold-back
  amends both contracts. It also amends F1's kept contract ("F10's modal submit feeds it" becomes
  "F3's File button feeds it"). The fold-back also amends Standing invariant 2 to name the preview-view
  error handler (matching Step 5's CLAUDE.md change), and the F3 Expected end state: the question
  sets live in the route file, not a separate data file, and the preview shows `issue_body`'s
  format with `PREVIEW_LINK` in place of the summary link, shortened past 4096 characters
  (DD-2, DD-3).
- **discord.py 2.7.1** (requirements.txt): `TextInput(default=...)` prefills (`TextInput.__init__`),
  which settles risk (b). `Modal.add_item` raises past 5 children (`Modal.add_item`). Label text
  max 45 (`Label` class docstring, ui/label.py) is documented but not enforced in Python, so it's checked at load.
  A button callback may `response.send_modal`. A modal opened from a button can
  `response.edit_message` the preview (`InteractionResponse.edit_message`). `followup.send(ephemeral=True,
  view=...)` stores the view (`Webhook.send`, webhook/async_.py). View dispatch runs one task per click
  (`BaseView._dispatch_item`, ui/view.py), so File needs a synchronous guard. The default `View.on_error` logs
  `exc_info` (`BaseView.on_error`, ui/view.py), so the preview view needs a privacy-safe override, as
  `IntakeModal.on_error` has (`IntakeModal.on_error`). `View._scheduled_task(item, interaction)` reads
  `interaction.data` first, then resets the expiry to now + `timeout` before every callback; the
  `timeout` setter, once the timeout task runs, sets the expiry to now + the new value (view.py,
  `_scheduled_task` and `@timeout.setter`).
- **Body formatting.** `issue_body` (issue_bot/issues.py) is "the only place an issue body is
  formatted" and needs `candidate.message_url`, which exists only after the summary is posted.
  `IssueCandidate.body` (issue_bot/handler.py) is read in production only by `issue_body`, and its only
  producer is `candidate_from_submission` (issue_bot/handler.py), called once from
  `IntakeModal.on_submit`.
- **Tests.** 270 tests run with `.venv/bin/pytest` from the repo root (CLAUDE.md; META-PLAN
  Verification). Modals are driven by seeding `TextInput._value` and awaiting `on_submit`
  (tests/test_intake.py `filled_modal`). `make_interaction` (tests/conftest.py) has no
  `response.edit_message`, `edit_original_response` or `data`. About 13 submit-flow tests
  (test_intake.py, from `test_second_route_submit_files_to_its_repo_with_its_labels` through
  `test_github_error_still_posts_filing_error_reply`; test_bot.py
  `test_filing_hook_unexpected_error_reaches_modal_on_error` and
  `test_command_callback_reaches_hook_end_to_end`) assume filing on submit and move behind
  File. The drift test `test_example_routes_shape` (tests/test_config.py) pins
  `example.routes.toml` to `ROUTE_KEYS`.

## Design decisions
- **DD-1 (asked):** the per-type questions replace the Description field. A route that wants a
  catch-all adds an optional question such as "Anything else?". **Chosen:** questions replace
  Description (dd-261026-001).
- **DD-2 (asked):** `issues.py` gets one formatter, `render_body(author_name, link, answers)`.
  `issue_body(candidate)` calls it with the summary URL; the preview calls it with
  `PREVIEW_LINK = "(link added when filed)"`. Nothing goes public before File. **Chosen:**
  shared formatter with a placeholder (dd-261026-002).
- **DD-3 (asked):** the preview is an embed whose description is the rendered body, cut to fit
  4096 characters with a fixed shortened-preview note. Answers keep Discord's 4000-character
  maximum; the filed issue is never cut. **Chosen:** embed, shortened with a note (dd-261026-003).
- **DD-4 (asked):** adding or changing the questions for `/bug` and `/feature` is route-file data
  only. A new issue type still needs an `IssueType` member (it defines a slash command and a
  required label). The fold-back records this against the Expected end state's "adding a tag ...
  needs no code change". **Chosen:** questions data-only (dd-261026-004).
- **DD-5 (assumed: dd-policy, dd-261026-005):** `PREVIEW_TIMEOUT = 600` s, under the 15-minute
  interaction token, as a fixed deadline from the submit that showed the preview. Each button
  press first trims the view's timeout back to that deadline, because discord.py 2.7.1 resets
  the expiry to now + timeout before every callback; so a press never extends the preview.
  `on_timeout` edits the preview to `PREVIEW_EXPIRED_REPLY`, removes the
  buttons and keeps the embed, so the reporter can copy their text. There is no persisted state
  and the old `data/` store is not used (risk a). Buttons left dead by a bot restart are accepted:
  Discord shows its own "interaction failed".
- **DD-6 (decided at plan review):** an Edit submit always shows a fresh preview with its own
  deadline, even when the old preview already expired or closed while the modal was open.
- **DD-7 (decided at plan review):** the live-Discord message targeting (the expiry edit lands on
  the preview message; an Edit submit updates the preview in place) is proven by the owner's
  smoke test at merge (§ Manual checks), not by a probe. Its code-level wiring (the new view
  edits the Edit submit's own original response) is unit-tested in Step 4's Edit-submit test.
- **DD-8 (decided at plan review):** a question table missing `style` or `required` raises
  `<where_q>.style is required` / `<where_q>.required is required` (§ Route-file shape), as
  `_route_value` words a missing key.
- **DD-9 (decided at plan review):** an Edit submit that replaces the preview logs the first
  preview's line, `previewed %s interaction_id=%s`, with the edit interaction's id.
- **DD-10 (decided at plan review):** the new helpers take the route first, like
  `_route_labels(route, where)`: `_route_questions(route, where)` and `_question(table, where_q)`.
- **DD-11 (decided at plan review):** `Draft`'s repr hiding is pinned by its own test (Step 3).
- **DD-12 (decided at plan review):** the Edit-submit tests pin the edited content: the reopened
  modal is seeded with a changed title and answer, and both the new preview's embed and what
  File then files carry the changed text, never the first draft's.
- **DD-13 (decided at plan review):** an Edit submit closes and stops the old preview only after
  its `edit_message` succeeds. A failed edit leaves the old preview usable, so it still expires
  normally.
- **DD-14 (decided at plan review):** the File-once test's first ack yields
  (`await asyncio.sleep(0)`), so the test fails when File's guard comes after an `await`, not
  only when it is missing.
- Risk (d) needs no code: only the reporter sees the ephemeral preview, and members comment in
  the thread after filing.

## Route-file shape (the contract this plan builds)

```toml
[[routes.c4i.questions.bug]]
label = "Steps to reproduce"   # 1-45 characters, unique within the type
style = "paragraph"            # "short" or "paragraph"
required = true                # TOML boolean

[[routes.c4i.questions.feature]]
label = "Who is it for?"
style = "short"
required = false
```

- `questions` is a required route key, a table with exactly one array per `IssueType` value.
  Each array has 1–4 question tables. Each question table has exactly the keys `label`, `style`
  and `required`.
- A missing `questions` key raises the existing `routes.<name>.questions is required` (from
  `_route_value`).
- Error messages name the key path only, never the value, and the question index is 1-based:
  `routes.<name>.questions must map bug and feature to question lists` (also raised when
  `questions` is not a table, or a type's value is not an array),
  `routes.<name>.questions.<type> must have 1 to 4 questions`,
  `routes.<name>.questions.<type>[<n>] must be a table`,
  `routes.<name>.questions.<type>[<n>] has unknown key '<key>'`,
  `routes.<name>.questions.<type>[<n>].label is required` (missing or blank),
  `routes.<name>.questions.<type>[<n>].label must be a string`,
  `routes.<name>.questions.<type>[<n>].label must be at most 45 characters`,
  `routes.<name>.questions.<type>[<n>].style is required` (missing),
  `routes.<name>.questions.<type>[<n>].style must be short or paragraph`,
  `routes.<name>.questions.<type>[<n>].required is required` (missing),
  `routes.<name>.questions.<type>[<n>].required must be true or false`,
  `routes.<name>.questions.<type> labels must be unique`.

## Steps

### 1. Question sets in the route file
Load and validate per-route, per-type question sets at startup as a required route key.

**To-do:**
- [ ] **Red.** In `tests/conftest.py`, add a `[[routes.intake.questions.bug]]` set and a
  `[[routes.intake.questions.feature]]` set to `ONE_ROUTE_TOML`. Bug gets two questions:
  `label = "What happened?"`, `style = "paragraph"`, `required = true`, then
  `label = "Device"`, `style = "short"`, `required = false`. Feature gets one:
  `label = "The idea"`, `style = "paragraph"`, `required = true`. Give the `[routes.other]` part
  of `TWO_ROUTE_TOML` its own sets: bug `label = "Steps"` (paragraph, required) and feature
  `label = "Why?"` (short, not required). Place each route's question arrays after its
  `.labels` table.
- [ ] **Red.** In `tests/test_config.py`, keep the labels tests meaning the same now that question
  arrays follow `[routes.intake.labels]`:
  - in `test_bad_route_labels_raise`, change the `extra-docs` case from
    `ONE_ROUTE_TOML + 'docs = "documentation"\n'` to
    `ONE_ROUTE_TOML.replace('feature = "enhancement"', 'feature = "enhancement"\ndocs = "documentation"')`,
    so `docs` stays inside the labels table;
  - add a helper `without_questions(text: str) -> str` that returns `text` cut at the first
    `[[routes.intake.questions.` header;
  - leave `"questions"` out of `ROUTE_FILE_KEYS`. Update its comment to: `# File-key order of the
    route's scalar keys and labels; cutting at the [routes.intake.labels] header also drops the
    question arrays after it. "questions" is left out: its arrays have no single line to drop,
    so without_questions covers it.` Update the `without_route_keys` docstring to say that
    dropping `labels` cuts at its header, which also drops the question arrays that follow it.
- [ ] **Red.** In `tests/test_config.py`, add `MAX_QUESTIONS`, `Question`, `QuestionStyle` and
  `_route_questions` to the `from issue_bot.config import (...)` list, then add tests:
  - `route.questions[IssueType.BUG]` equals `(Question("What happened?", QuestionStyle.PARAGRAPH, True), Question("Device", QuestionStyle.SHORT, False))`,
    and `route.questions[IssueType.BUG][1].style is QuestionStyle.SHORT` (equality alone passes
    on a raw `"short"`, since `QuestionStyle` is a `StrEnum`);
  - the second route's own questions: `load_text(tmp_path, TWO_ROUTE_TOML)[556].questions[IssueType.BUG] == (Question("Steps", QuestionStyle.PARAGRAPH, True),)`;
  - the mapping is read-only (`TypeError` on assignment), as `test_direct_construction_makes_labels_read_only` does for labels;
  - one exact-message test per error in § Route-file shape: a missing `questions` key
    (`without_questions(ONE_ROUTE_TOML)`, expecting `routes.intake.questions is required`); a
    missing type; an extra type `docs`; `questions` not a table and a type that isn't an array
    (both `routes.intake.questions must map bug and feature to question lists`); zero
    questions; five questions; a question that isn't a table; an unknown key `hint`; a missing
    label; a blank label; a non-string label; a 46-character label (45 is accepted); a missing
    style (`ONE_ROUTE_TOML.replace('style = "short"\n', "")`, expecting
    `routes.intake.questions.bug[2].style is required`); style `"long"`; a missing required
    (`ONE_ROUTE_TOML.replace("required = false\n", "")`, expecting
    `routes.intake.questions.bug[2].required is required`); `required = 1`; `required = "yes"`;
    a duplicate label within a type (the same label in bug and feature is accepted);
  - no message quotes a label value, mirroring `test_malformed_toml_raises_without_quoting_file`.

  Build the bad files with the existing `load_text`/`route_error` helpers. Put a route-level
  `questions` line inside `[routes.intake]`, never appended after the labels table (it would
  land in `[routes.intake.labels]` and raise the labels error): the not-a-table file is
  `without_questions(ONE_ROUTE_TOML).replace("[routes.intake]\n", "[routes.intake]\nquestions = 1\n")`,
  as `test_unknown_route_key_raises` inserts, and the not-an-array file is
  `without_questions(ONE_ROUTE_TOML).replace("[routes.intake]\n", '[routes.intake]\nquestions = { bug = "x", feature = "y" }\n')`.
  Every file that puts an inline `questions = …` inside `[routes.intake]` starts from
  `without_questions(...)`, since TOML rejects an inline table that the later
  `[[routes.intake.questions.*]]` headers extend. The zero-questions and question-not-a-table
  files are built the same way (cut with `without_questions`, then insert in `[routes.intake]`):
  `questions = { bug = [], feature = [{ label = "The idea", style = "paragraph", required = true }] }`
  (expecting `routes.intake.questions.bug must have 1 to 4 questions`) and
  `questions = { bug = ["x"], feature = [{ label = "The idea", style = "paragraph", required = true }] }`
  (expecting `routes.intake.questions.bug[1] must be a table`). The five-questions file appends
  three more `[[routes.intake.questions.bug]]` tables with distinct labels to `ONE_ROUTE_TOML`;
  tomllib adds them to `bug`. The unknown-key `hint` line appended
  to `ONE_ROUTE_TOML` lands in the last feature question, so it expects
  `routes.intake.questions.feature[1] has unknown key 'hint'`. Run
  `.venv/bin/pytest tests/test_config.py` and confirm the new tests fail.
- [ ] **Green.** In `issue_bot/config.py`:
  - add `class QuestionStyle(StrEnum)` (`SHORT = "short"`, `PARAGRAPH = "paragraph"`) next to
    `UnroutedCommands`;
  - add `@dataclass(frozen=True) class Question` with `label: str`, `style: QuestionStyle`,
    `required: bool` and a one-line docstring saying labels are operator config, not member text;
  - add constants `MAX_QUESTIONS = 4  # Title plus four questions fills Discord's five-field modal.`
    and `QUESTION_LABEL_LIMIT = 45  # Discord's maximum label length.`;
  - append `"questions"` to `ROUTE_KEYS`;
  - add `questions: Mapping[IssueType, tuple[Question, ...]]` as the last `TargetConfig` field.
    In `__post_init__`, after the labels check, raise
    `ConfigError("questions must have one entry per IssueType")` unless
    `isinstance(self.questions, Mapping)` and `set(self.questions) == set(IssueType)` (mirroring
    the labels check) and every value is a `tuple` of 1–`MAX_QUESTIONS`
    `Question`s. Then wrap a copy:
    `object.__setattr__(self, "questions", MappingProxyType(dict(self.questions)))`;
  - add `_route_questions(route, where) -> dict[IssueType, tuple[Question, ...]]` and
    `_question(table, where_q) -> Question`, route first like `_route_labels(route, where)`.
    `_route_questions` reads the key with `_route_value(route, where, "questions")`. They raise
    the § Route-file shape messages in this order: type set and each value a list (`questions` a
    dict whose keys are the `IssueType` values, each value a `list`), then list length, then each
    question in order (table, unknown keys, label, style, required), then label uniqueness.
    `_question` reads `label` with `_route_str(table, where_q, "label")` (missing or blank:
    `is required`; non-string: `must be a string`; returns it stripped) and `style` and
    `required` with `_route_value(table, where_q, key)` (`where_q` is
    `f"{where}.questions.{type}[{n}]"`), never `table[key]`, so an absent key raises
    `<where_q>.<key> is required` and never a `KeyError`. `required` must satisfy
    `isinstance(value, bool)`. The length check runs on the stripped label `_route_str` returns.
    `_question` returns `Question(label, QuestionStyle(style), required)`, converting the
    style as `_route_labels` converts with `IssueType(type_name)`;
  - call `_route_questions` last in `_route`, after `_route_labels`, and pass `questions=` to the
    `TargetConfig(...)` call at the end of `_route`;
  - add the `questions` arrays (`bug`/`feature`, each 1–4 `label`/`style`/`required` tables) to
    the `load_routes` docstring.
- [ ] Update every direct `TargetConfig(...)` construction in the tests to pass a valid
  `questions=` mapping (test_config.py `make_target` and the literals in `test_full_env_loads` and
  `test_one_route_loads`; grep `TargetConfig(` across `tests/` and fix every hit). The two literals are
  compared with a route loaded from `ONE_ROUTE_TOML`, so they pass its exact questions:
  `{IssueType.BUG: (Question("What happened?", QuestionStyle.PARAGRAPH, True), Question("Device", QuestionStyle.SHORT, False)), IssueType.FEATURE: (Question("The idea", QuestionStyle.PARAGRAPH, True),)}`
  (one module constant, e.g. `ONE_ROUTE_QUESTIONS`, shared by both); `make_target` takes any
  valid mapping. Add a test that
  `TargetConfig(...)` with `questions` missing a type raises
  `ConfigError("questions must have one entry per IssueType")`.
- [ ] In `example.routes.toml`, add after `[routes.c4i.labels]` a comment block explaining
  1–4 questions per type, the `label`/`style`/`required` keys, the 45-character label cap and
  that the questions replace a free-form description. Then add the ROADMAP's example sets:
  - bug: `Steps to reproduce` (paragraph, required), `Expected` (paragraph, required), `Actual`
    (paragraph, required), `Device / browser` (short, optional);
  - feature: `Who is it for?` (short, required), `What problem does it solve?` (paragraph,
    required), `What does "done" look like?` (paragraph, optional), written as a TOML literal
    string: `label = 'What does "done" look like?'`.
- [ ] Extend `test_example_routes_shape` (tests/test_config.py) to also assert
  `set(route["questions"]) == {t.value for t in IssueType}` and that each list has
  1–`MAX_QUESTIONS` entries, and to run the real validator on each raw example route:
  iterate `routes.items()` and call `_route_questions(route, f"routes.{name}")`, so every
  example question's keys, style and label length are checked. The existing
  `set(route) == set(ROUTE_KEYS)` check now covers `questions` through `ROUTE_KEYS`.
- [ ] **Verify:** `.venv/bin/pytest` passes in full. Invariant 1's grep
  (`grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot`)
  prints nothing.

### 2. Answers on the candidate and one section per answer
Carry `(label, answer)` pairs on `IssueCandidate` and render them through one shared body formatter.

**To-do:**
- [ ] **Red.** In `tests/test_issues.py`, replace the body-based tests with answer-based ones:
  - exact string: `issue_body(make_candidate(answers=(("What happened?", "It broke"), ("Device", "Pixel"))))` ==
    ``"Reported by `Alice` in Discord: https://discord.com/channels/111/555/99\n\n---\n\n### What happened?\n\nIt broke\n\n### Device\n\nPixel"``;
  - a blank (`""`) or whitespace-only answer leaves its section out;
  - every answer blank ends with `"\n\n---\n\n_No description given._"`;
  - `@` is defanged in both answers and labels;
  - the author line still comes before member text: keep the `<!--` test, now in an answer;
  - `render_body("Alice", PREVIEW_LINK, answers)` equals `issue_body` of the same answers with
    `PREVIEW_LINK` in place of the URL;
  - add `PREVIEW_LINK` and `render_body` to test_issues.py's `from issue_bot.issues import (...)`
    list, keeping it sorted.

  In `tests/test_handler.py`, rewrite `test_candidate_from_submission_fields` and
  `test_submission_candidate_repr_hides_text` (keeping their other assertions) so that
  `candidate_from_submission(IssueType.BUG, "Fix it", (("Q", "A"),), user, message, route)`
  sets `candidate.answers == (("Q", "A"),)` in place of `candidate.body == "Steps"`, and
  `repr(candidate)` hides "Secret body words" when it is passed as
  `(("Q", "Secret body words"),)`. Run them and confirm they fail.
- [ ] **Green.** In `issue_bot/handler.py`, replace `body: str = field(repr=False)` with
  `answers: tuple[tuple[str, str], ...] = field(repr=False)` (in the same position, with the
  docstring updated). Change the signature to
  `candidate_from_submission(issue_type: IssueType, title: str, answers: Sequence[tuple[str, str]], reporter: discord.abc.User, message: discord.Message, target: TargetConfig) -> IssueCandidate`
  and set `answers=tuple(answers)`. Add `from collections.abc import Sequence` (stdlib group).
- [ ] **Green.** In `issue_bot/issues.py`:
  - add `from collections.abc import Sequence` as a stdlib import above the project imports
    (the module has no `from __future__ import annotations`, so the annotation is evaluated at
    import);
  - add `PREVIEW_LINK = "(link added when filed)"`;
  - add `render_body(author_name: str, link: str, answers: Sequence[tuple[str, str]]) -> str`.
    It builds the author line exactly as today, then `---`, then
    `"\n\n".join(f"### {_defang_mentions(label)}\n\n{_defang_mentions(answer.strip())}" for label, answer in answers if answer.strip())`,
    or `_No description given._` when that is empty;
  - make `issue_body(candidate)` return
    `render_body(candidate.author_name, candidate.message_url, candidate.answers)`, and change its
    docstring's "then the member's body (or a placeholder)" to "then one section per answered
    question (or a placeholder)";
  - keep the module docstring's "only place an issue body is formatted" claim true.
- [ ] Update the callers so the suite stays green:
  - `tests/conftest.py` `make_candidate`: replace the `body: str = "Steps"` parameter and
    `body=body` with `answers: tuple[tuple[str, str], ...] = (("What happened?", "Steps"),)` and
    `answers=answers`;
  - `tests/test_bot.py` `secret_candidate`: `answers=(("What happened?", "Secret body words"),)`;
  - every `make_candidate(..., body=...)` in tests/test_issues.py and tests/test_bot.py;
  - `IntakeModal.on_submit`'s `candidate_from_submission` call, as a stopgap until Step 3: pass
    `(("Description", description),)` where it passed `description`;
  - `test_submit_hands_summary_and_candidate_to_hook` and
    `test_submit_normalizes_title_and_description` in test_intake.py, which assert `candidate.body`: assert
    `candidate.answers == (("Description", "Steps"),)` and the normalized pair.
- [ ] **Verify:** `.venv/bin/pytest` passes in full. `grep -rn "\.body\b\|body=" issue_bot tests`
  shows no reference to the removed field.

### 3. The modal asks the route's questions, with optional prefill
Build Title plus one input per question from `target.questions[issue_type]`, with optional prefill for Edit.

**To-do:**
- [ ] **Red.** In `tests/test_intake.py`:
  - rewrite `test_modal_fields` as two tests. Bug: `len(modal.children) == 3`; labels
    `["Title", "What happened?", "Device"]`; `modal.answer_inputs[0]` is paragraph, required,
    `max_length == ANSWER_MAX_LENGTH`; `modal.answer_inputs[1]` is short and not required.
    Feature: 2 children `["Title", "The idea"]`. Both keep the title-input and `MODAL_TIMEOUT`
    assertions;
  - a prefill test: `IntakeModal(IssueType.BUG, route, hook, draft=Draft("Fix it", (("What happened?", "Steps"), ("Device", ""))))`
    has `title_input.default == "Fix it"` and `answer_inputs[0].default == "Steps"`;
  - add `from collections.abc import Sequence` (the module has no
    `from __future__ import annotations`), change `filled_modal` to take
    `answers: Sequence[str] = ("Steps",)`, seed `modal.answer_inputs[i]._value`, and drop
    `description`. Update its keyword callers: `test_submit_normalizes_title_and_description`
    passes `answers=("\n Steps \n more \n",)` (and asserts
    `(("What happened?", "Steps \n more"), ("Device", ""))`), and `test_submit_logs_ids_not_text`
    passes `answers=("Secret body words",)`;
  - the submit tests that asserted `("Description", ...)` pairs now assert
    `(("What happened?", "Steps"), ("Device", ""))`. Answer whitespace is stripped; the title
    keeps its existing normalization;
  - a repr test mirroring `test_submission_candidate_repr_hides_text`:
    `repr(Draft("Secret title words", (("Q", "Secret body words"),)))` contains neither
    `"Secret title words"` nor `"Secret body words"`;
  - add `ANSWER_MAX_LENGTH` and `Draft` to test_intake.py's `from issue_bot.intake import (...)`
    list, keeping it sorted.
- [ ] **Green.** In `issue_bot/intake.py`:
  - rename `DESCRIPTION_MAX_LENGTH` to `ANSWER_MAX_LENGTH`, keeping its comment;
  - add `@dataclass(frozen=True) class Draft` (above `IntakeModal`) with
    `title: str = field(repr=False)` and
    `answers: tuple[tuple[str, str], ...] = field(repr=False)`, and a docstring saying it is
    member text, hidden from repr;
  - change `IntakeModal.__init__(self, issue_type, target, on_candidate, draft: Draft | None = None)`.
    It sets `self.questions = target.questions[issue_type]` and builds `title_input` with
    `default=draft.title if draft else None`. Then, for each question `q` at index `i`, it builds
    `discord.ui.TextInput(style=discord.TextStyle.short if q.style is QuestionStyle.SHORT else discord.TextStyle.paragraph, required=q.required, max_length=ANSWER_MAX_LENGTH, default=draft.answers[i][1] if draft else None)`,
    appends it to `self.answer_inputs: list[discord.ui.TextInput]` and adds
    `discord.ui.Label(text=q.label, component=...)`;
  - delete `description_input`;
  - update the `IntakeModal` docstring to "The report form: a required Title plus the route's
    questions for the issue type.";
  - in `on_submit`, replace the Step 2 stopgap with
    `answers = tuple((q.label, answer_input.value.strip()) for q, answer_input in zip(self.questions, self.answer_inputs))`
    (not `field`, which would shadow `dataclasses.field`);
  - import `QuestionStyle` from `issue_bot.config`, and `dataclass`/`field` if they aren't
    imported yet.
- [ ] Update `tests/test_bot.py`'s `test_filing_hook_unexpected_error_reaches_modal_on_error` and
  `test_command_callback_reaches_hook_end_to_end` to seed `answer_inputs[0]._value`
  instead of `description_input._value`.
- [ ] **Verify:** `.venv/bin/pytest` passes in full.

### 4. Private preview with File and Edit
Show an ephemeral preview on submit; File runs the existing summary and filing path; Edit reopens the modal prefilled; timeout files nothing. The bot-level tests go submit → preview → File, so the step ends green.

**To-do:**
- [ ] **Red.** In `tests/conftest.py` `make_interaction`, add:
  - `response.edit_message = AsyncMock()`, with a side effect that flips `is_done` like `defer`;
  - `edit_original_response = AsyncMock()` on the returned namespace (an `Interaction` method,
    beside `followup`, not on `response`);
  - `data={}` on the returned namespace (discord.py 2.7.1's `View._scheduled_task` reads
    `interaction.data` before the button callback);
  - update its docstring to say it also stands in for a button interaction.
- [ ] **Red.** In `tests/test_intake.py`, add the new intake names the tests use (`PreviewView`,
  `preview_embed`, the `PREVIEW_*` constants, `FILING_REPLY`, `BLANK_TITLE_EDIT_REPLY`) to the
  `from issue_bot.intake import (...)` list and add
  `from issue_bot.issues import PREVIEW_LINK, render_body`, keeping each list sorted. Then add
  preview tests. Each drives `filled_modal(...).on_submit(interaction)`
  and takes the view from `interaction.followup.send.await_args.kwargs["view"]`:
  - submit sends **one** private follow-up:
    `followup.send(PREVIEW_REPLY, embed=<Embed>, view=<PreviewView>, ephemeral=True, allowed_mentions=NO_MENTIONS)`;
  - `embed.description == render_body("Alice", PREVIEW_LINK, answers)`;
  - `embed.title` is the normalized title;
  - `interaction.channel.send` and the hook are **not** awaited;
  - the view's timeout is `PREVIEW_TIMEOUT`;
  - a body over 4096 characters (the bug route's two questions answered with 4000 characters
    each) gives a description of at most 4096 characters ending with `PREVIEW_SHORTENED_NOTE`;
  - **Embed boundary:** `preview_embed("T", (("What happened?", "x" * n),), "Alice")`, with `n`
    chosen so `render_body("Alice", PREVIEW_LINK, ...)` is exactly `PREVIEW_EMBED_LIMIT`
    characters long, has that body as its description, uncut and without
    `PREVIEW_SHORTENED_NOTE`;
  - **File:** `await view.file_button.callback(button_interaction)`, where `button_interaction`
    is a second `make_interaction(summary=make_message())`. It acks with
    `response.edit_message(content=FILING_REPLY, view=None)`, then posts the summary (same
    arguments as today), hands `(summary, candidate)` to the hook with the draft's answers, and
    sends `SUBMITTED_REPLY` privately. The existing summary-failure, missing-channel and
    `test_submit_files_issue_through_filing_hook`/GitHub-error tests move here, with the same
    assertions on the button interaction;
  - **File acks first:** mirroring `test_submit_defers_privately_first`, attach
    `button_interaction.response.edit_message` as `"edit_message"`,
    `button_interaction.channel.send` as `"send"` and the hook as `"hook"` to one `Mock()`; after
    the File callback, `"edit_message"` comes before `"send"` and `"hook"` in `order.mock_calls`;
  - **File once (DD-14):** give `i1.response.edit_message` an async side effect that yields,
    `async def ack(*args, **kwargs): await asyncio.sleep(0); i1.response.is_done.return_value = True`,
    so the second click runs while the first is suspended at its ack. Then
    `asyncio.gather(view.file_button.callback(i1), view.file_button.callback(i2))`
    awaits the hook exactly once, and `view.is_finished()` is true. A guard placed after an
    `await` lets both clicks through and fails the hook-once assertion;
  - **Edit:** `await view.edit_button.callback(button_interaction)` calls
    `response.send_modal` with an `IntakeModal` whose `title_input.default` and
    `answer_inputs[*].default` are the previous values, and files nothing;
  - **Edit keeps the deadline:** move `view._deadline` back 120 s to simulate time passing
    (patching `time.monotonic` globally would also move the event loop's clock), then await
    `view.edit_button.callback(button_interaction)`: `PREVIEW_TIMEOUT - 121 < view.timeout <= PREVIEW_TIMEOUT - 120`.
    With `_deadline` already past, `view.timeout == 1.0`;
  - **Edit after close:** with `view._closed = True`, `edit_button.callback` does not call
    `response.send_modal` and the hook is not awaited;
  - **Edit submit:** seed that modal with a changed title and first answer
    (`title_input._value = "Fix it now"`, `answer_inputs[0]._value = "Steps v2"`; the Device
    input keeps its `""` default) and, under `caplog.at_level(logging.INFO)`, await its
    `on_submit(edit_interaction)` with `edit_interaction = make_interaction(interaction_id=4343)`.
    It answers with
    `response.edit_message(content=PREVIEW_REPLY, embed=<new embed>, view=<new PreviewView>)`,
    with no `defer` or `followup.send`, the old view `is_finished()`, and the intake log has
    `previewed bug interaction_id=4343`. The new embed's `title` and `description` equal those of
    `preview_embed("Fix it now", (("What happened?", "Steps v2"), ("Device", "")), "Alice")`
    (`make_interaction`'s default `display_name` is `"Alice"`). Then take the new view from
    `edit_interaction.response.edit_message.await_args.kwargs["view"]` and await its
    `on_timeout()`: `edit_interaction.edit_original_response` is awaited with
    `content=PREVIEW_EXPIRED_REPLY, view=None`, and the original submit interaction's
    `edit_original_response` is not awaited. A blank title there gets
    `response.send_message(BLANK_TITLE_EDIT_REPLY, ephemeral=True)`, and the old view stays live.
    When `edit_interaction.response.edit_message.side_effect = forbidden(50027, "Secret error words")`,
    `on_submit` raises `discord.Forbidden` and the old view is not `is_finished()`, so it still
    expires normally (DD-13);
  - **Edit submit files the edited text (DD-12):** the same seeded Edit submit, then take the new
    view from `edit_interaction.response.edit_message.await_args.kwargs["view"]` and await
    `new_view.file_button.callback(make_interaction(summary=make_message()))`: the hook's
    candidate has `title == "Fix it now"` and
    `answers == (("What happened?", "Steps v2"), ("Device", ""))` (a separate test, since
    `on_timeout` closes the view File needs);
  - **Edit submit after expiry:** set the old view's `_closed = True` (as `on_timeout` leaves it)
    before the edit submit; it still answers with
    `response.edit_message(content=PREVIEW_REPLY, embed=<new embed>, view=<new PreviewView>)`;
  - **Timeout:** `await view.on_timeout()` calls
    `interaction.edit_original_response(content=PREVIEW_EXPIRED_REPLY, view=None)` on the
    submitting interaction and files nothing. With
    `interaction.edit_original_response.side_effect = forbidden(50027, "Secret error words")`,
    the intake error lines are exactly
    `["could not expire bug preview interaction_id=4242: Forbidden status=403 code=50027"]`, the
    error is swallowed, and no record contains `"Secret error words"`. After File, `on_timeout`
    does nothing;
  - **View errors:** `await view.on_error(button_interaction, RuntimeError("Secret exception words"), view.file_button)`
    logs exactly `unhandled RuntimeError in bug preview interaction_id=4242 status=None code=None`,
    and replies `INTAKE_ERROR_REPLY` privately (`followup` if `is_done()`, else `send_message`);
  - **Privacy:** over two previews, each from
    `filled_modal(route, hook, title="Secret title words", answers=("Secret body words",))`, all
    under `caplog.at_level(logging.INFO)` (File closes a view, so one view can't reach both
    File and the expiry): preview A gets submit, then Edit (`edit_button.callback`), then the
    Edit submit of the reopened modal seeded with the same sentinels, then `await` the new
    view's `on_timeout()`; preview B gets submit, then File (`file_button.callback`).
    `assert_no_member_text(caplog)` passes. The intake INFO lines include
    `previewed bug interaction_id=4242` (once per submit, the Edit submit included), the existing
    `posted bug summary …` line, and `preview expired bug interaction_id=4242`.

  Run them and confirm they fail.
- [ ] **Green.** In `issue_bot/intake.py`, add constants under the `# Fixed text` comment:
  - `PREVIEW_TIMEOUT = 600  # Seconds; under Discord's 15-minute interaction token (DD-5).`;
  - `PREVIEW_EMBED_LIMIT = 4096  # Discord's maximum embed description.`;
  - `PREVIEW_REPLY = "Here's your report as it will be filed. **File** posts it; **Edit** changes it. This preview expires in 10 minutes."`;
  - `PREVIEW_SHORTENED_NOTE = "\n\n_…preview shortened; the full text will be filed._"`;
  - `FILING_REPLY = "Filing your report…"`;
  - `PREVIEW_EXPIRED_REPLY = "This preview expired, so nothing was filed. Run the command again to report it."`;
  - `BLANK_TITLE_EDIT_REPLY = "The title needs a letter or digit. Press Edit to fix it."`.
- [ ] **Green.** Add `preview_embed(title: str, answers: Sequence[tuple[str, str]], author_name: str) -> discord.Embed`
  (add `Sequence` to intake.py's existing `collections.abc` import). It
  builds `discord.Embed(title=title, description=text)`, where
  `text = render_body(author_name, PREVIEW_LINK, answers)`. When that exceeds
  `PREVIEW_EMBED_LIMIT`, it is cut to `PREVIEW_EMBED_LIMIT - len(PREVIEW_SHORTENED_NOTE)` and the
  note appended. Import `render_body` and `PREVIEW_LINK` from `issue_bot.issues` (no cycle:
  issues imports github and handler only).
- [ ] **Green.** Move the post-and-file block of `on_submit` (from its channel check to the end:
  channel check, summary send, its error handling and log, `on_candidate`, `SUBMITTED_REPLY`) unchanged into
  `async def _post_and_file(interaction: discord.Interaction, issue_type: IssueType, target: TargetConfig, on_candidate: CandidateHook, draft: Draft) -> None`.
  It uses `draft.title`/`draft.answers` and the button interaction's `channel` and `user`.
- [ ] **Green.** Add `import time` to intake.py. Add `class PreviewView(discord.ui.View)`.
  `__init__(self, issue_type: IssueType, target: TargetConfig, on_candidate: CandidateHook, draft: Draft, interaction: discord.Interaction) -> None`
  calls `super().__init__(timeout=PREVIEW_TIMEOUT)`. It stores the arguments, keeping
  `interaction` as the one whose original response is the preview, sets `self._closed = False`
  and `self._deadline = time.monotonic() + PREVIEW_TIMEOUT`.
  - Each button callback first runs `self.timeout = max(self._deadline - time.monotonic(), 1.0)`:
    discord.py 2.7.1's `View._scheduled_task` resets the expiry to now + `timeout` before every
    callback, and the `timeout` setter sets it to now + the new value, so this puts it back on
    the deadline (DD-5).
  - `file_button` (`@discord.ui.button(label="File", style=discord.ButtonStyle.success)`):
    after the timeout line, `if self._closed: return`, then `self._closed = True; self.stop()`
    with no `await` before them. Then
    `await interaction.response.edit_message(content=FILING_REPLY, view=None)` and
    `await _post_and_file(...)`.
  - `edit_button` (`label="Edit"`, `ButtonStyle.secondary`): after the timeout line,
    `if self._closed: return`, then
    `await interaction.response.send_modal(IntakeModal(self.issue_type, self.target, self.on_candidate, draft=self.draft, preview=self))`.
    It does not close the view, so a cancelled Edit leaves the preview usable.
  - `on_timeout`: if not `_closed`, set it, log `preview expired %s interaction_id=%s`, and
    `await self.interaction.edit_original_response(content=PREVIEW_EXPIRED_REPLY, view=None)`
    (the embed is kept). Catch `discord.HTTPException`, logging
    `could not expire %s preview interaction_id=%s: %s status=%s code=%s` (issue type,
    `self.interaction.id`, exception type, status, code), and `Exception`, logging
    `could not expire %s preview interaction_id=%s: %s` (type only).
  - `on_error(interaction, error, item)`: the same logging and reply as `IntakeModal.on_error`.
    Factor both into one module coroutine
    `async def _report_error(interaction: discord.Interaction, error: Exception, issue_type: IssueType, what: str) -> None`
    and have `IntakeModal.on_error` and `PreviewView.on_error` `await` it (C7). It logs
    `"unhandled %s in %s %s interaction_id=%s status=%s code=%s"` with
    `type(error).__name__, issue_type, what, interaction.id, status, code`; `IntakeModal` passes
    `what="modal"` (the existing line is unchanged) and `PreviewView` passes `what="preview"`,
    so the view line is `unhandled RuntimeError in bug preview interaction_id=4242 status=None code=None`.
- [ ] **Green.** Change `IntakeModal`:
  - `__init__` gains `preview: "PreviewView | None" = None` and stores it.
  - `on_submit`, fresh (`self.preview is None`): `defer(ephemeral=True, thinking=True)` as
    today, the blank-title check and `BLANK_TITLE_REPLY` as today, then
    `draft = Draft(title, answers)`, `view = PreviewView(..., draft, interaction)`, log
    `previewed %s interaction_id=%s`, and
    `followup.send(PREVIEW_REPLY, embed=preview_embed(title, answers, interaction.user.display_name), view=view, ephemeral=True, allowed_mentions=NO_MENTIONS)`.
    Wrap the send like `_reply`, logging an `HTTPException` with `_reply`'s format
    `could not send %s reply interaction_id=%s: %s status=%s code=%s`, so
    `test_followup_failure_logged_without_text` keeps its exact assertion.
  - `on_submit`, edit (`self.preview` set): no defer. A blank title gets
    `response.send_message(BLANK_TITLE_EDIT_REPLY, ephemeral=True)`. Otherwise, always, even
    when the old preview already expired or closed (DD-6): `draft = Draft(title, answers)` from
    this modal's inputs, a new `PreviewView(..., draft, interaction)` (the edit interaction, whose
    original response is now the preview), log the same line as the first preview,
    `previewed %s interaction_id=%s` with the edit interaction's id,
    `await interaction.response.edit_message(content=PREVIEW_REPLY, embed=preview_embed(title, answers, interaction.user.display_name), view=new_view)`,
    and only after it returns `self.preview._closed = True; self.preview.stop()`. A failed edit
    raises before the old view is closed, so the old preview stays usable and still expires
    normally (DD-13).
  - The author shown is `interaction.user.display_name`, as `candidate_from_submission` uses
    (verify against handler.py and match it).
  - Update the intake.py module docstring to say a submit shows a private preview and File posts
    the summary and hands it to `on_candidate`, and update `on_submit`'s docstring to match.
- [ ] Update the `IssueBot` docstring in `issue_bot/bot.py` ("Each submitted report is posted as
  a public summary message ...") to say a report is posted as the public summary once its
  reporter presses File on the private preview.
- [ ] Rewrite the old submit-flow tests (test_intake.py, as listed in Research Findings)
  so the summary, hook and `SUBMITTED_REPLY` assertions run on File. In
  `test_submit_defers_privately_first`, attach `interaction.followup.send` (the preview send) as
  `"send"` instead of `interaction.channel.send`, keeping the defer-first assertion. Remove only
  tests whose behaviour no longer exists, never weaken an assertion. In
  `test_second_route_submit_files_to_its_repo_with_its_labels`, the File interaction is
  `make_interaction(channel_id=556, summary=make_message(channel_id=556))`, as its submit
  interaction is today.
- [ ] `tests/test_bot.py` `test_filing_hook_unexpected_error_reaches_modal_on_error`:
  the unexpected filing error now surfaces in the File callback. After `on_submit`, take the
  view from the follow-up and drive File through the view's dispatch,
  `await view._scheduled_task(view.file_button, button_interaction)` (2.7.1:
  `_scheduled_task(item, interaction)`; it reads `interaction.data`, which `make_interaction`
  sets to `{}`). Assert it reaches `PreviewView.on_error`: the intake error lines are exactly
  `["unhandled RuntimeError in bug preview interaction_id=4242 status=None code=None"]`, with the
  same privacy assertions, and `button_interaction.followup.send` is awaited once with
  `INTAKE_ERROR_REPLY, ephemeral=True`. Read `summary` from
  `button_interaction.channel.send.return_value` (the File interaction posts it), and assert
  `summary.create_thread.return_value.send`, `summary.reply` and
  `button_interaction.response.send_message` are not awaited. Rename the test to
  `test_filing_hook_unexpected_error_reaches_preview_on_error`.
- [ ] `tests/test_bot.py` `test_command_callback_reaches_hook_end_to_end`: after
  `on_submit`, take the view from the follow-up and await
  `view.file_button.callback(button_interaction)` with `button_interaction = make_interaction()`.
  Then assert the hook as today, with `summary is button_interaction.channel.send.return_value`.
- [ ] **Verify:** `.venv/bin/pytest` passes in full.

### 5. Docs
Describe the new modal, preview and route-file keys wherever the old flow is described.

**To-do:**
- [ ] `README.md`:
  - line 3: replace "Clarifying questions and roadmap placement are planned features" with
    per-type questions and a private preview, and "roadmap placement is planned";
  - the Status paragraph (line 9): add F3 to the features that exist;
  - line 17's usage steps: Title plus the route's questions, then the private preview with
    File/Edit and its 10-minute expiry; Reporting steps 3-4: the summary, thread and issue
    follow File;
  - Known limits: replace line 34 (the reporter's answers stay visible in the private preview
    until File, and after an expiry or a failed filing; a preview over 4096 characters shows only
    the start of the text, and the preview is an ephemeral message), and add "a bot restart leaves an open preview's buttons dead;
    run the command again";
  - line 57's mentions note: labels are defanged too;
  - the route-file field table: add `questions.bug` / `questions.feature` (array of tables
    `label`, `style`, `required`; 1–4 per type; label ≤45);
  - add an "Upgrading to per-type questions" subsection next to "Upgrading from single-target
    config": existing route files must add `questions` tables, or the bot exits with code 2;
    rolling back to an older build needs the `questions` tables removed again, since older
    builds reject unknown route keys (exit 2).
- [ ] `docs/SMOKE-TEST.md` § 0 (One-time setup), the `routes.smoke.toml` block: after
  `[routes.smoke.labels]`, add `[[routes.smoke.questions.bug]]` and
  `[[routes.smoke.questions.feature]]` tables copied from `example.routes.toml`'s sets (bug:
  Steps to reproduce, Expected, Actual, Device / browser; feature: Who is it for?, What problem
  does it solve?, What does "done" look like?), so the smoke route file loads.
- [ ] `docs/SMOKE-TEST.md` § 2 (Local run), step 1 and its table: submit with answers, see the preview, press Edit (the modal
  reopens prefilled), change an answer and submit: the same preview message updates in place,
  with no second message. Press File. The Issue body row becomes the author line,
  `---`, then one `###` section per answered question, with blank optional ones left out. Add
  the steps "let a preview sit 10 minutes: that same preview message says it expired and nothing
  is filed" and "after an Edit submit, let the new preview sit 10 minutes: that same message says
  it expired". Keep the `@someone` step, now in an answer.
- [ ] `docs/SMOKE-TEST.md`, the other passages that describe filing on submit:
  - § 3 closing note (line 141): "A filing failure after a submit" becomes "A filing failure
    after File";
  - § 4 Container run (line 181): "Submit one `/bug`. It is filed as in section 2." becomes
    "Submit one `/bug` and press **File** on the preview. It is filed as in section 2.";
  - the Troubleshooting row "A submit gets a private error and no summary" becomes "Pressing
    File gets a private error and no summary";
  - § What it writes, Success checks: "per submission" becomes "per report filed with **File**;
    an expired or edited preview writes nothing".
- [ ] `CLAUDE.md` Stack line: "Clarifying questions ... rule-based (per-type templates)". Change
  it to "Clarifying questions are per-route, per-type question sets in the route file", and
  leave complexity ratings as planned.
- [ ] `CLAUDE.md` logging rule: change "while the command and modal error handlers log the
  exception type, the command or modal name" to "while the command, modal and preview-view error
  handlers log the exception type, the command, modal or view name".
- [ ] **Verify:** `grep -rn "Description" README.md docs/SMOKE-TEST.md` shows no stale reference
  to the removed field.

### 6. Verify All Tests Pass

Run the full test suites to confirm nothing is broken:

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm all tests pass
- [ ] No UI test runner is configured for this project (`ui_runner_cmd` is empty), so there is no UI suite to run; the owner's live check is `docs/SMOKE-TEST.md`
- [ ] Re-run Standing invariant 1's grep (`grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot` prints nothing)
- [ ] Confirm no new log call passes member text: `grep -n "logger\." issue_bot/intake.py` and check each new line logs only type and ids
- [ ] Investigate and fix any failures before marking the plan finished
- [ ] Quote the § Manual checks (owner) bullets verbatim in your final report under a heading `Manual checks (owner)`; the /run-feature orchestrator relays them in its merge-gate verification brief.

## Manual checks (owner)
- Before restarting a live instance on this build, add `questions` tables to its route file
  (README "Upgrading to per-type questions"), or it exits with code 2.
- In the test server per `docs/SMOKE-TEST.md`, check the following for `/bug` and `/feature`:
  - the modal shows the route's questions;
  - the private preview shows the body;
  - Edit reopens the modal prefilled;
  - File files once, with one section per answered question;
  - a preview left 10 minutes says it expired.
- After a submit, the expired notice replaces that same preview message after 10 minutes.
- Edit → change → submit updates the preview in place, with no second message.
- After an Edit submit, the new preview's expiry also edits that same message.

## Status
finished: false
