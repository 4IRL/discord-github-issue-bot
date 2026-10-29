# Track dropdown in the private preview (F17)

## Summary
On a route whose Project has a Track single-select, the reporter's private preview gets an optional
Track dropdown (row 2, under the band buttons). Its options are the Project's own Track options,
read through GitHub's GraphQL API and cached with F6's Project ids. A route can pre-select a default
per issue type. The pick lives in `Draft`, survives Edit like the band override, shows as a **Track**
embed field, and on File the bot sets the item's Track after F6 adds it (blank with no pick). A failed
Track write follows F6's failed-Project-write policy.

## Research Findings
- `PROJECT_FIELDS_QUERY` (`issue_bot/github.py`) already returns every single-select field
  with its options; `_single_select_options(nodes, name)` (`github.py`) returns
  `(field id, {option name: id})` in Project order. Track needs a parser change only, and it must be
  optional: `_parse_project_fields` (`github.py`) returns None (→ `GitHubError("project", 200)`)
  on any Status/Effort mismatch, which must not happen for a missing Track field.
- `ProjectConfig` (`issue_bot/config.py`) is part of `GitHubClient._projects`' cache key
  (`github.py`, `_project_key` at 343-347), so new fields must stay hashable (tuple of pairs).
  `_route_project` (`config.py`) rejects keys outside `PROJECT_KEYS` (`config.py`).
- The intake path has no GitHub access: only `filing_check` is passed `__main__.py` →
  `IssueBot.__init__` (`bot.py`) → `intake_command` (5th positional at `bot.py`).
  `PreviewView` is built once, synchronously, in `IntakeModal.on_submit` (`intake.py`). The fresh
  submit defers first (`intake.py`); the Edit submit answers with `response.edit_message`
  without deferring, so it must reuse the old preview's options (no fetch).
- `place_on_roadmap` (`issue_bot/issues.py`) discards `add_to_project`'s returned item id
  (`issues.py`); its never-raise policy (WARNING, return False → `ROADMAP_FAILED_NOTE`) covers a
  Track-write failure with no new reply text.
- discord.py 2.7.1: `discord.ui.Select(placeholder=, min_values=, max_values=, options=, row=)` is
  width 5, so it takes row 2 alone; `SelectOption(label=, value=, default=)` pre-selects;
  `select.values` is a `list[str]`; 25 options max; labels and values max 100 characters. No Select
  exists in the codebase yet. Tests build positional `Draft(...)` (5 args), `IntakeModal(t, route,
  hook)`, `intake_command(...)` (4-5 args) and `candidate_from_submission(...)` (7 args), so every new
  parameter is trailing with a default.
- Assumption 3 verified at the cold survey (2026-10-29, read-only `gh api graphql` query of
  `organization(login: "4IRL") { projectV2(number: 2) { fields … } }`): Project #2 "chores4irl
  fold" has a `Track` SINGLE_SELECT with options `A · Bugs`, `B · Form & feedback`,
  `S · Status & sort`, `C · List UX`, `D · Sync & recovery`, `E · Ops` (6, under the 25 cap),
  beside `Status`, `Effort`, `ID`, `Order`, `Lane`, `Start date`, `Target date` and `Days`.

## Decisions
- **DD-1 (assumed: dd-policy, dd-261029-024).** Options come from `project_fields`' per-process
  cache (warmed by the startup Project check), read in the fresh `on_submit` after the defer within
  `FILING_CHECK_TIMEOUT`; any failure or timeout shows no row and files normally. An Edit reuses the
  old preview's options. Stale until restart or a failed Project write drops the cache, like F6's ids.
- **DD-2 (asked, dd-261029-025).** Two optional keys in `[routes.<name>.project]`: `track_field`
  (the Track field's name; absent → no row) and a `[routes.<name>.project.track_default]` table
  mapping `bug` and/or `feature` to an option name, allowed only with `track_field`. Standing
  invariant 3's wording changes at fold-back (META-PLAN is edited in Phase C, not by this plan).
- **DD-3 (asked, dd-261029-026; owner chose over the Recommended warning).** A default that is not
  one of the shown options is a silent blank: nothing pre-selected, no log. A `track_field` the
  Project lacks (or a malformed field) is likewise just no row.
- **DD-4 (asked, dd-261029-027).** More than 25 options: the row shows the first 25 in Project
  order, and the startup Project check logs a WARNING.
- **DD-5 (asked, dd-261029-028).** The preview embed gets a **Track** field (the pick, or `None`)
  whenever the row is shown, like Complexity.
- **Review pass 2:** the lookup callable is `track_lookup: TrackLookup` in the wiring (assumed,
  dd-261029-035); a lost Track pick is recovered by asking the reporter (assumed, dd-261029-034);
  guard tests for a no-project lookup and a Track route without a lookup (assumed, dd-261029-036).
- **Review pass 1** (`reviews/preview-track-review.md`): no live Track smoke check (owner,
  dd-261029-029); a failed Track write uses its own stage `project-track` (dd-261029-030); a failed
  Track lookup logs like the filing check (dd-261029-031); the select passes `required=False`
  (assumed, dd-261029-032); extra tests for band/Edit keeping the Track field, padded defaults, a
  default past the 25th option and the example's Track values (assumed, dd-261029-033).

## Steps

### 1. Route-file Track keys - COMPLETE (2026-10-29)
`ProjectConfig` gains the two optional, hashable Track settings, validated at startup.

**To-do:**
- [x] Red (2026-10-29): in `tests/test_config.py`, next to `test_route_with_project_loads` (line ~491), add tests using
  `with_project()` plus appended lines: (a) `track_field = "Track"` and a
  `[routes.intake.project.track_default]` table with `bug = "A · Bugs"` loads as
  `ProjectConfig(number=2, status_field="Status", status="Todo", effort_field="Effort",
  track_field="Track", track_defaults=((IssueType.BUG, "A · Bugs"),))`; (b) no Track keys loads
  `track_field=None, track_defaults=()` (the existing equality at 491-495 keeps passing via
  defaults); (c) both `bug` and `feature` defaults load in `IssueType` order regardless of file order,
  and a padded `bug = " A · Bugs "` loads as `"A · Bugs"`;
  (d) `hash(project)` works for a config with defaults. Add parametrized error cases to
  `test_project_errors` (502-532) asserting exact messages: `track_field = ""` →
  `routes.intake.project.track_field is required` (via `_route_str`'s blank rule, matching its
  existing wording), `track_field = 3` → `routes.intake.project.track_field must be a string`,
  a well-formed `[routes.intake.project.track_default]` table with `bug = "A · Bugs"` and no
  `track_field` → `routes.intake.project.track_default needs track_field`, and, each appended after
  a `track_field = "Track"` line,
  `track_default = "x"`, `track_default = {chore = "x"}`, `{bug = ""}`, `{bug = "  "}`, `{bug = 3}`
  and `{}` →
  `routes.intake.project.track_default must map bug or feature to Track option names`. Keep
  `PROJECT_KEYS_IN_ORDER`'s "is required" cases to the four required keys only. Extend
  `test_project_error_does_not_quote_value` with a bad `track_default` value. Run
  `.venv/bin/pytest tests/test_config.py` and confirm the new tests fail.
- [x] Green (2026-10-29) in `issue_bot/config.py`: add `track_field: str | None = None` and
  `track_defaults: tuple[tuple[IssueType, str], ...] = ()` (trailing, with a comment: a tuple of
  pairs because `ProjectConfig` is a cache key and must stay hashable) to `ProjectConfig`; extend
  `PROJECT_KEYS` with `"track_field"` and `"track_default"`; in `_route_project`, read
  `track_field` with `_route_str(table, where_p, "track_field")` only when the key is present, and
  parse `track_default` with a new `_route_track_defaults(table, where_p, track_field)` helper that
  first raises `needs track_field` when `track_field` is None, then validates the table, raising
  the messages above, and returns the pairs in `IssueType` iteration order (strip each name,
  as `_route_labels` does). Update the `ProjectConfig` docstring, the module docstring (lines 1-7)
  and `load_routes`' docstring (311-322): the project table's four keys are required, `track_field`
  and `track_default` optional.
- [x] (2026-10-29, test_config 187 passed, full suite 461 passed) Confirm `test_example_routes_shape` (`tests/test_config.py`) still passes (the example gains
  its Track keys in step 6). Run `.venv/bin/pytest tests/test_config.py` green, then the full
  `.venv/bin/pytest`.

### 2. GitHub client: read Track options and set Track - COMPLETE (2026-10-29)
`ProjectFields` carries the optional Track field; `GitHubClient` gains `track_options` and `set_track`.

**To-do:**
- [x] Red (2026-10-29) in `tests/test_github.py`: add a `track_field(options: list[str] | None = None) -> dict`
  helper beside `status_field`/`effort_field` (line ~646), default options `["A · Bugs",
  "B · Form & feedback"]` with ids `O_t0`, `O_t1`, field id `F_track`. Tests: (a) a project route
  whose `ProjectConfig` has `track_field="Track"` and a `project_response()` including `track_field()`
  parses to `ProjectFields(..., track_field_id="F_track", track_option_ids={"A · Bugs": "O_t0",
  "B · Form & feedback": "O_t1"})` with the mapping read-only (TypeError on assignment), and, for
  `track_field(["B · Form & feedback", "A · Bugs"])`, `tuple(fields.track_option_ids) ==
  ("B · Form & feedback", "A · Bugs")` (Project order, not sorted; dict equality ignores order); (b) `track_field="Track"` but no Track node → `track_field_id=None`,
  `track_option_ids={}` and no error (lookup still cached); (c) a malformed Track node (options not a
  list) → same as (b); (d) `track_field=None` with a Track node present → no Track ids;
  (e) `await client.track_options(target)` returns `("A · Bugs", "B · Form & feedback")`, `()` with
  no Track field, the unsorted Project order for the reversed response above, and reuses the cache
  (one lookup across two calls), and `()` for a route with no project without calling
  `project_fields` (review pass 2); (f)
  `await client.set_track(target, "PVTI_1", "B · Form & feedback")` sends payload
  `{"query": SET_TRACK_MUTATION, "variables": {"project": "PVT_1", "item": "PVTI_1", "field":
  "F_track", "option": "O_t1"}}` and returns None on `(200, {"data": {"track": {"projectV2Item":
  {"id": "PVTI_1"}}}})`; (g) `set_track` with a name not in the options, or with no Track field,
  raises `GitHubError("project-track", 200)` after warming the cache with `track_options(target)`,
  sends no further transport call (no `SET_TRACK_MUTATION`), and drops the cached ids (the next
  `track_options` call looks up again); (h) a `set_track` GraphQL error, a bad alias result and a
  transport failure raise `GitHubError("project-track", 200|None)` with no "Secret detail" text,
  and drop the cached ids
  (mirror `test_failed_set_drops_cached_project_ids`, line ~947). Update the `PROJECT_FIELDS` constant
  (line 636) only if equality checks need the new defaulted fields. Import `SET_TRACK_MUTATION` into
  the existing `from issue_bot.github import (...)` list, after `PROJECT_FIELDS_QUERY`. Run the file
  and confirm the new tests fail.
- [x] Green (2026-10-29) in `issue_bot/github.py`: add `track_field_id: str | None = None` and
  `track_option_ids: Mapping[str, str] = field(default_factory=dict)` (option name → id, Project
  order; import `field` alongside `dataclass` from `dataclasses`) to `ProjectFields`, frozen with
  `MappingProxyType` in `__post_init__` like `effort_option_ids`; update its docstring. In
  `_parse_project_fields`, when `project.track_field` is set, call
  `_single_select_options(nodes, project.track_field)`; a None result leaves the Track members empty
  (never a mismatch; comment: missing and malformed are both "no row", DD-3). Add
  `SET_TRACK_MUTATION` beside `SET_FIELDS_MUTATION`: `mutation($project: ID!, $item: ID!, $field:
  ID!, $option: String!) { track: updateProjectV2ItemFieldValue(input: {projectId: $project, itemId:
  $item, fieldId: $field, value: {singleSelectOptionId: $option}}) { projectV2Item { id } } }` (option
  id as `String!`, per the comment above `PROJECT_FIELDS_QUERY`). Add `async def track_options(self,
  target) -> tuple[str, ...]` (returns `()` for a route with no project or no Track field, else
  `tuple(fields.track_option_ids)`; never logs) and `async def set_track(self, target, item_id: str,
  track: str) -> None` (new stage `"project-track"`, review pass 1; a missing field or option raises
  `GitHubError("project-track", 200)` before any request; it sends the mutation through
  `_graphql("project-track", ...)` and raises `GitHubError("project-track", 200)` unless the result's
  `track` is a dict whose `projectV2Item` is a dict, mirroring `add_to_project`'s alias check). Factor `add_to_project`'s cache pop into
  a private `_drop_project(target)` and call it on a `project-item`, `project-field` or
  `project-track` failure. Add `"project-track"` to `GitHubError`'s documented stage list and update
  `add_to_project`'s docstring as needed.
- [x] (2026-10-29, test_github 96 passed, full suite 478 passed) Run `.venv/bin/pytest tests/test_github.py` green, then the full `.venv/bin/pytest`.

### 3. Carry the pick to filing - COMPLETE (2026-10-29)
`IssueCandidate` gains `track`; `place_on_roadmap` sets it on the new item.

**To-do:**
- [x] Red (2026-10-29): in `tests/test_handler.py` assert `candidate_from_submission(..., target)` (7 positional)
  gives `track is None` and an 8th `track="A · Bugs"` argument sets it, and that `track` shows in
  `repr` (Project option names are not member text). In `tests/conftest.py`, give `make_candidate` a
  `track: str | None = None` keyword and both of `fake_github`'s returned namespaces (the exception
  and the success branch) a `set_track=AsyncMock(return_value=None)` attribute. In `tests/test_issues.py` (beside `test_place_on_roadmap_adds_issue_and_logs`): (a) a
  project candidate with `track="A · Bugs"` awaits `add_to_project` then
  `set_track(project_route, "PVTI_1", "A · Bugs")`, returns True, logs only the existing INFO
  `added bug message_id=99 to the roadmap issue=…`; (b) with `track=None`, `set_track` is not
  awaited; (c) `set_track` raising `GitHubError("project-track", 200)` returns False with WARNING
  `could not add bug message_id=99 to the roadmap issue=…: GitHubError stage=project-track
  status=200`, and a `RuntimeError` logs the type only; both pass `assert_no_member_text`. In
  `tests/test_bot.py`, beside `test_filing_hook_roadmap_failure_posts_failed_note`, add a case where
  `set_track` fails (build the candidate with `make_candidate(..., complexity=Complexity.M,
  track="A · Bugs", target=project_route)`, since `project_candidate` sets no track) and the thread
  gets `filed_reply(issue, title, Complexity.M, False)`. Confirm they fail.
- [x] Green (2026-10-29): in `issue_bot/handler.py` add trailing `track: str | None = None` to `IssueCandidate`
  (docstring: the Project Track option to set, not member text, so it stays in repr) and a trailing
  `track: str | None = None` parameter to `candidate_from_submission`. In `issue_bot/issues.py`,
  `place_on_roadmap` keeps the item id (`item_id = await github.add_to_project(...)`) and, when
  `candidate.track is not None`, awaits `github.set_track(candidate.target, item_id,
  candidate.track)` inside the same `try`, so a failure takes the existing False paths; update its
  docstring and the module docstring.
- [x] (2026-10-29, handler/issues/bot 99 passed, full suite 484 passed) Run `.venv/bin/pytest tests/test_handler.py tests/test_issues.py tests/test_bot.py` green, then
  the full `.venv/bin/pytest`.

### 4. Track row in the preview - COMPLETE (2026-10-29)
`PreviewView` shows the Track select, `Draft` carries the pick across Edit, and the embed shows it.

**To-do:**
- [x] Red (2026-10-29) in `tests/test_intake.py` (import `replace` from `dataclasses`, `PROJECT` from
  `tests.conftest`, and the new `TRACK_*` constants and `TrackLookup` from `issue_bot.intake`, in the
  existing import order), with
  a module helper `track_route(project_route)` returning
  `replace(project_route, project=replace(PROJECT, track_field="Track",
  track_defaults=((IssueType.BUG, "A · Bugs"),)))` and a fake lookup
  `AsyncMock(return_value=("A · Bugs", "B · Form & feedback"))` passed as
  `IntakeModal(..., track_lookup=lookup)`. Give `filled_modal` a trailing keyword
  `track_lookup: TrackLookup | None = None` passed through as `IntakeModal(issue_type, route, hook,
  track_lookup=track_lookup)` (so `submitted_preview(..., track_lookup=lookup)` works); existing
  callers are unchanged:
  (a) a fresh submit on that route awaits the lookup once with the route and the view has a
  `discord.ui.Select` on row 2 with `min_values=0`, `max_values=1`, `required=False`, placeholder
  `TRACK_PLACEHOLDER`, option labels in order, values `"0"`, `"1"`, and `"A · Bugs"` `default=True`
  for a bug; the embed's second field is `TRACK_FIELD` = `"A · Bugs"`; band rows 0/1 unchanged
  (`test_preview_buttons_rows_and_suggested_band_highlighted` still passes);
  (b) a feature report (no default) pre-selects nothing and the field reads `TRACK_NONE`;
  (c) a default not among the options pre-selects nothing, logs nothing (DD-3);
  (d) no row and no Track field (embed has 1 field) for: the plain `route` (lookup not awaited), a
  project route without `track_field` (lookup not awaited), a Track route opened with no lookup
  (nothing logged; review pass 2), a lookup returning `()`, a lookup
  raising `GitHubError("project", 200)` or `RuntimeError`, and a lookup slower than
  `FILING_CHECK_TIMEOUT` (patch the timeout down); the preview still sends and File still works; a
  failed lookup logs one WARNING in the filing check's form (review pass 1):
  `could not read track options for bug interaction_id=4242: GitHubError stage=project status=200`,
  `…: timeout`, or `…: RuntimeError`, and passes `assert_no_member_text`;
  (e) 30 options show the first 25 (`TRACK_OPTION_LIMIT`); a bug default that is the 26th option
  pre-selects nothing and leaves `draft.track` None; a 120-character option name is shown cut to 100
  characters while the pick still maps to the full name;
  (f) picking: set `view.track_select._values = ["1"]` (discord.py 2.7.1 reads `.values` from it)
  and await its callback with `make_interaction()`: `view.draft.track == "B · Form & feedback"`, the
  edit carries `{"embed", "view"}` with the moved `default`, the field updated, nothing logged;
  picking nothing (`[]`) sets `track=None`; a closed view ignores the pick; the deadline is kept
  (mirror the existing closed-view and deadline band-press tests);
  (g) the pick survives Edit: pick, then `edit_submit_with(view, make_interaction, ...)`: the new
  view's `draft.track` is the pick, its select shows the same options with the pick as default, the
  `embed` passed to `edit_message` carries the Track field with the pick, and the lookup is not
  awaited again; a cleared pick (`None`) also survives Edit instead of returning to the default;
  (g2) a band press on a Track view keeps the Track field (with the pick) in the edited embed and the
  select's default unchanged;
  (h) File after a pick hands `on_candidate` a candidate with `track` set (extend
  `test_file_files_issue_through_filing_hook`'s pattern with a `fake_github` and assert
  `set_track` awaited with the pick).
  Add `intake_command(..., track_lookup=lookup)` tests that the modal it opens carries the lookup.
  Confirm the new tests fail.
- [x] Green (2026-10-29; the submit's Track logic lives in an `IntakeModal._track_choices` helper) in `issue_bot/intake.py`: add `TrackLookup = Callable[[TargetConfig],
  Awaitable[tuple[str, ...]]]` beside `FilingCheck` (the lookup callable is named for its role, like
  `filing_check`; `track_options` names the tuple of option names and the client method); constants `TRACK_OPTION_LIMIT = 25  # Discord's
  maximum select options.`, `TRACK_LABEL_LIMIT = 100  # Discord's maximum option label.` and, under
  the fixed-text comment, `TRACK_PLACEHOLDER = "Track (optional)"`, `TRACK_FIELD = "Track"`,
  `TRACK_NONE = "None"`. Extend `FILING_CHECK_TIMEOUT`'s comment: it also bounds the Track lookup
  after a fresh submit's defer, so the preview never waits long (DD-1). Add trailing
  `track: str | None = None` to `Draft` (docstring: the Track option to set, not member text).
  `preview_embed(draft, author_name, track_row: bool = False)` adds the `TRACK_FIELD` field
  (`draft.track or TRACK_NONE`) after Complexity only when `track_row`.
  `PreviewView.__init__` gains trailing `track_options: tuple[str, ...] = ()`, stores
  `self.track_options = track_options[:TRACK_OPTION_LIMIT]`, and when non-empty builds
  `self.track_select = discord.ui.Select(placeholder=TRACK_PLACEHOLDER, min_values=0, max_values=1,
  required=False, row=2)` (review pass 1: the payload then matches the optional row) with its
  `callback` set to a `_pick_track(interaction)` coroutine and `add_item`s it (else
  `self.track_select = None`), all before the existing `self._paint()` call at the end of
  `__init__`; `_paint` also rebuilds the select's options when `self.track_select is not None`
  (`SelectOption(label=name[:TRACK_LABEL_LIMIT], value=str(index), default=name ==
  self.draft.track)`). `_pick_track` mirrors `_choose`: `_keep_deadline()`, return if `_closed`, set
  `self.draft = replace(self.draft, track=...)` from `self.track_select.values` (index → name, or
  None) before any await, `_paint()`, then `edit_message(embed=preview_embed(self.draft,
  interaction.user.display_name, track_row=True), view=self)`; logs nothing. `_choose` passes
  `track_row=bool(self.track_options)`. `_post_and_file` passes `draft.track` as
  `candidate_from_submission`'s 8th argument. Update the class docstring.
  `IntakeModal.__init__` gains trailing `track_lookup: TrackLookup | None = None` (stored as
  `self.track_lookup`). In `on_submit`, after the blank-title check: on Edit, `options =
  self.preview.track_options` and `track = self.preview.draft.track`; on a fresh submit, with
  `project = self.target.project`, when `self.track_lookup` is set and `project is not None and
  project.track_field`, `options = await asyncio.wait_for(self.track_lookup(self.target),
  FILING_CHECK_TIMEOUT)`, catching `GitHubError` (WARNING `could not read track options for %s
  interaction_id=%s: %s stage=%s status=%s`), `TimeoutError` (`…: timeout`) and `Exception` (`…: %s`
  with the type only), each then `()`; otherwise `options = ()`; still on the fresh submit, `track =
  dict(project.track_defaults).get(self.issue_type)` if `options` is non-empty and that name is in
  `options[:TRACK_OPTION_LIMIT]`, else None (never touching `project` when `options` is empty); the Edit branch keeps its carried `track` and
  never applies the default.
  Build `Draft(title, answers, suggested, complexity, overridden, track)`, pass
  `track_options=options` to `PreviewView` and `track_row=bool(view.track_options)` to
  `preview_embed`. `intake_command` gains trailing `track_lookup: TrackLookup | None = None` and
  passes it as `IntakeModal(issue_type, target, on_candidate, track_lookup=track_lookup)`. Keep
  `PREVIEW_REPLY` (the select's placeholder explains itself); update the module docstring.
- [x] (2026-10-29, test_intake 96 passed, full suite 505 passed) Run `.venv/bin/pytest tests/test_intake.py` green, then the full `.venv/bin/pytest`.

### 5. Wire it in the bot and the startup check - COMPLETE (2026-10-29)
`IssueBot` passes the lookup to the commands; the startup Project check warns past 25 options.

**To-do:**
- [x] Red (2026-10-29; (a), (b), the 26-option case of (c) failed first; `test_setup_hook_checks_project_after_access`'s check now returns `PLAIN_FIELDS` too, since its call-order mock would record the new length read) in `tests/test_bot.py`: (a) `IssueBot(config, track_lookup=lookup)` registers commands
  whose modal carries the lookup (drive the registered `/bug` callback as the existing command →
  modal → File end-to-end test does, then inspect the sent modal); (b) the `__main__` wiring test
  asserts `init_kwargs["track_lookup"].__func__ is GitHubClient.track_options` and the sentinel
  `SimpleNamespace(check_access=…, project_fields=…)` gains `track_options=AsyncMock()`; (c) a
  startup project check whose `project_check` returns a `ProjectFields` with 26 Track options logs
  WARNING `github project track field has 26 options; only the first 25 can be picked repo_id=222
  project=2` after the `github project ok` INFO, and 25 options logs no warning; (d) update
  `test_setup_hook_project_check_failure_still_checks_second`: its `side_effect=[GitHubError(
  "project", 200), None]` second value becomes a module-level `ProjectFields` constant with no Track
  ids (e.g. `ProjectFields(project_id="PVT_1", status_field_id="F_status", status_option_id="O_s",
  effort_field_id="F_effort", effort_option_ids={})`; import `ProjectFields` from
  `issue_bot.github`), because with the narrowed `ProjectCheck` a `None` result would make the new
  `len(fields.track_option_ids)` check raise AttributeError out of `setup_hook`. Confirm (a), (b) and
  the 26-option case of (c) fail (the 25-option case already passes; it guards the threshold after
  the Green).
- [x] Green (2026-10-29): in `issue_bot/bot.py`, narrow `ProjectCheck` to `Callable[[TargetConfig],
  Awaitable[ProjectFields]]` (import `ProjectFields` from `issue_bot.github`; no cycle, github.py
  imports only config and complexity), add trailing `track_lookup: TrackLookup | None = None` to
  `IssueBot.__init__` (stored, and documented in its docstring) and pass it to
  `intake_command(..., track_lookup=self.track_lookup)` as a keyword; in `_check_project`, keep the
  returned fields and, after the ok line, log the WARNING when `len(fields.track_option_ids) >
  TRACK_OPTION_LIMIT` (import `TRACK_OPTION_LIMIT` and `TrackLookup` from `issue_bot.intake`, added
  to the existing alphabetized intake import list). In `issue_bot/__main__.py` pass
  `track_lookup=github.track_options`.
- [x] (2026-10-29, test_bot 73 passed, full suite 509 passed) Run `.venv/bin/pytest tests/test_bot.py` green, then the full `.venv/bin/pytest`.

### 6. Docs and example - COMPLETE (2026-10-29)
README, `docs/COMPLEXITY.md`, `docs/SMOKE-TEST.md` and `example.routes.toml` show the Track row
and keys.

**To-do:**
- [x] (2026-10-29, test_config 187 passed) `example.routes.toml`: after `effort_field = "Effort"` add a comment and `track_field = "Track"`,
  then a `[routes.c4i.project.track_default]` table with `bug = "A · Bugs"` (comment: optional, per
  issue type, an option name on the Project; a name that is not an option pre-selects nothing).
  Extend `test_example_routes_shape` (`tests/test_config.py`) so for `c4i` it also asserts
  `project.track_field == "Track"` and `project.track_defaults == ((IssueType.BUG, "A · Bugs"),)`.
  Check Standing invariant 1's grep still prints nothing (the example file is not under
  `issue_bot/`).
- [x] (2026-10-29; review added the `could not read track options` log line beside the failed-Project-step line) `README.md`: the Status paragraph's feature list adds F17 (Track dropdown in the preview) and
  its sentence on the roadmap note says the bot also sets the item's Track from the preview; Reporting
  step 3 gets a bullet for the optional **Track** dropdown (only on a route
  whose `project` table has `track_field`; pre-selected default per type; the pick survives Edit and
  shows as a **Track** field); step 4 says the bot also sets Track (blank with no pick) and that a
  failed Track write gives the same roadmap note; the Configuration intro (every key required except
  the optional `project` table) and the route file reference table add `project.track_field`
  (optional string: the Track single-select's name; absent → no dropdown) and
  `project.track_default.<type>` (optional option names; a name that isn't an option pre-selects
  nothing); note the 25-option limit and the startup warning; *Adding a roadmap Project*'s rollback
  note also covers the new keys (older builds reject them, exit 2); add a *Known limits* bullet:
  Track options are read once and cached, so an option added or renamed on the Project shows in the
  dropdown only after a restart (or after a failed roadmap write drops the cache); the line on a
  failed Project step names `stage=project-track` as the Track write and says the bot doesn't
  record the pick, so the owner sets Track by hand only if the reporter says which one they picked
  (review pass 2).
- [x] (2026-10-29; review added what `stage=project-track status=200` means to the same row) `docs/SMOKE-TEST.md` (owner's choice, review pass 1: no live Track check): add one note that the
  smoke run does not exercise the Track dropdown (the test Project has no Track field and the
  scratch route sets no `track_field`), and in the troubleshooting row for `could not add … to the
  roadmap …` add: after `stage=project-track` the item is on the Project with its Status and Effort,
  so set its Track there if the reporter picked one (the bot doesn't record the pick: ask them);
  after each "set its Status and Effort" for `stage=project`, `stage=project-item`/`stage=token` and
  the stage-less form add "(and its Track, on a route with `track_field`, if the reporter picked
  one)"; and change "After a `stage=project-item` or `stage=project-field` failure" to "After a
  `stage=project-item`, `stage=project-field` or `stage=project-track` failure". No other runbook
  change.
- [x] (2026-10-29, full suite 509 passed) `docs/COMPLEXITY.md` (the preview description paragraph): one sentence that on a route with a
  Track row the preview also has a Track dropdown under the band buttons, which doesn't affect the
  band. Run `.venv/bin/pytest tests/test_complexity.py tests/test_config.py` (they pin this doc's
  thresholds and the example's shape), then the full `.venv/bin/pytest`.

### 7. Verify All Tests Pass
Run the full test suite to confirm nothing is broken.

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm every test passes.
- [ ] Run `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py'
  issue_bot` and confirm it prints nothing (Standing invariant 1), and
  `grep -rn 'A · Bugs\|Form & feedback' issue_bot` prints nothing (no hardcoded Track list).
- [ ] Grep the new log lines in `issue_bot/` (`could not read track options`, `track field has`) and
  confirm each logs only the issue type, ids, counts, stage, status and exception type (Standing
  invariant 2).
- [ ] Investigate and fix any failures before marking the plan finished.
- [ ] Copy the Manual checks below verbatim into the final report.

## Manual checks (owner; not executor boxes)
- No live Track smoke check (owner's choice, review pass 1): the dropdown, the Edit carry-over and
  the Track write are covered by the mocked tests only. The first live Track use is the deployed
  `c4i` route.
- To turn Track on for a live route, add `track_field = "Track"` (and any `track_default` names) to
  that route's `[routes.<name>.project]` table in the deployed route file and restart; Project #2's
  options were checked at the cold survey (Research Findings).

## Status
finished: false
