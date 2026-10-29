# Roadmap Project placement (F6)

## Summary
After the bot files an issue for a route that has a GitHub Project configured, it adds the issue
to that org Project (Projects v2, GraphQL) and sets the item's Status to the configured option
(`Todo`) and its `Effort` single-select to the option named `str(candidate.complexity)`. The
Project is an optional `[routes.<name>.project]` table of names; the bot looks the node, field
and option ids up through GraphQL and caches them per process. A failed Project step never
undoes or blocks filing: it is logged as a WARNING and the thread's link message says adding
it to the roadmap could not be finished (`ROADMAP_FAILED_NOTE`). On success the link message
says it was added.

## Decisions (asked at planning, 2026-10-29)
- **Open risk (a), token scope** (dd-261029-001): only a route with a `project` table gets
  `organization_projects: write` on its repo-scoped installation token, alongside
  `issues: write`; routes without one keep `issues: write` only. Tokens are cached per
  `(repo id, has project)`. A missing App grant therefore shows as a failed token mint for
  that route (the startup `github access check failed …` line and the per-command
  "filing unavailable" reply), never for routes without a Project.
- **Open risk (b), config shape** (dd-261029-002): names, not ids. `number`, `status_field`,
  `status`, `effort_field`; the Project's owner is the route repo's owner (already enforced
  equal to `GITHUB_ORG`). Ids are looked up with one GraphQL query, checked at startup and
  cached per process. The Effort option is found by `str(band)`; there is no second band list
  (F4's kept contract).
- **Open risk (c), failure policy** (dd-261029-003): the issue stays filed; a WARNING is logged
  by type, stage and status for a `GitHubError`, and by exception type only for any other
  exception (dd-261029-004); the link message gets a third line `ROADMAP_FAILED_NOTE`.
  Success adds `ROADMAP_ADDED_NOTE`. A route with no Project gets no roadmap line.
- **Review decisions** (2026-10-29): one failure note true at every stage (dd-261029-005);
  `TargetConfig.project` has no default (dd-261029-006); a failed add or field set drops that
  route's cached Project ids so the next filing looks them up again (dd-261029-007); the owner's
  smoke test against a test Project is the live gate for the mutations (dd-261029-008); a
  concurrent first lookup runs twice, harmlessly (dd-261029-009).

## Research Findings
- `GitHubClient` (`issue_bot/github.py`) never logs; every request goes through
  `_request(stage, url, headers, payload)` (always POST, transport failure →
  `GitHubError(stage, None) from None`); public methods validate the response strictly, pop the
  cached token on 401 and raise `GitHubError(stage, status) from None`. A bad success shape is
  raised with the real status (e.g. `GitHubError("issue", 201)`), so a GraphQL `errors` payload
  maps to `GitHubError(<stage>, 200)`. `_installation_token(repo_id)` caches
  `self._tokens: dict[int, tuple[str, float]]` per repo id and sends
  `{"repository_ids": [repo_id], "permissions": {"issues": "write"}}`.
- `FiledIssue(number, html_url)` has no `node_id`; `create_issue`
  reads only `number` and `html_url`. `addProjectV2ItemById` needs the
  issue's node id as `contentId`. `FiledIssue` is constructed positionally in tests/test_bot.py,
  test_github.py, test_threads.py, test_intake.py and test_issues.py.
- Route config (`issue_bot/config.py`): `ROUTE_KEYS` drives unknown-key rejection
  in `_route`; every key goes through `_route_value` (presence → `<where>.<key> is required`);
  `_question` is the model for a fixed-schema sub-table (table check, unknown-key rejection,
  every inner key required via `_route_str`/`_route_int`). `TargetConfig` is frozen with no
  defaults (the new `project` field keeps that: no default, dd-261029-006); tests construct it
  directly by keyword only in `tests/test_config.py`: `test_full_env_loads`, the `make_target`
  helper and `test_one_route_loads` (`grep -rn 'TargetConfig(' tests`; every other test gets
  its route from `conftest`'s `config`/`route` fixtures, built by `load_routes`).
  `dataclasses.replace(config, routes={...})` works on `Config` (its `__post_init__` re-wraps
  the routes read-only; checked with a throwaway test in `tests/`, since deleted).
  `test_example_routes_shape` asserts `set(route) == set(ROUTE_KEYS)` for every example route;
  `ROUTE_FILE_KEYS` in tests lists the required keys (questions excluded).
- Filing chain: `PreviewView.file_button` → `_post_and_file` → `filing_hook`'s
  `file_and_report`: `open_thread` → `file_candidate` (a
  best-effort `ensure_label` WARNING then `create_issue`) → `filed …` INFO → `_post_outcome(…,
  filed_reply(issue, title, complexity), "issue link")`. Only `GitHubError` is caught there; any
  other exception reaches `PreviewView.on_error`, so every GraphQL parse failure must surface
  as `GitHubError`, and `place_on_roadmap` also catches any other exception (dd-261029-004) so
  the link message is always posted. `conftest.fake_github` is a `SimpleNamespace` of
  `create_issue`/`ensure_label` AsyncMocks; tests fake HTTP with an injected
  `transport=AsyncMock(side_effect=[(status, json), …])`, and the autouse `no_live_github`
  guard covers any call through `aiohttp_transport`.
- Project #2 (cold survey, read-only `gh api graphql`, 2026-10-28): linked to
  `4IRL/chores4irl`; `Status` options `Todo`, `In Progress`, `Done`; `Effort` options `S`, `M`,
  `L`, `XL` (exact `str(Complexity)` names). The `4irl-issue-bot`
  installation has only `issues: write` and `metadata: read` today, so the owner must add the
  Organization permission **Projects: Read and write** and accept it on the installation before a
  live run (owner checks below). chores4irl is public.
- GraphQL schema probes (read-only `gh api graphql` introspection, run in review 2026-10-29
  and re-run from this repo the same day): `UpdateProjectV2ItemFieldValueInput.projectId`,
  `.itemId` and `.fieldId` are `ID!`; `ProjectV2FieldValue.singleSelectOptionId` is a nullable
  `String`; `AddProjectV2ItemByIdInput.projectId` and `.contentId` are `ID!`;
  `organization(login: String!)` and `projectV2(number: Int!)`. The plan's
  `PROJECT_FIELDS_QUERY` run with `-f org=4IRL -F number=2` returned Project #2's fields with
  `Status` (`Todo`, `In Progress`, `Done`) and `Effort` (`S`, `M`, `L`, `XL`). A `String!`
  variable is accepted for a nullable `String` argument, while declaring it `ID!` fails with
  `variableMismatch` (shown on the read-only `organization(login: "4IRL") { projectsV2(first:
  1, query: $q) { totalCount } }`, whose `query` argument is a nullable `String`). The two
  mutations and the `organization_projects` token were not run
  (writes): the owner's smoke test against a test Project is their live acceptance gate (Owner
  checks).

## Steps

### 1. Optional per-route Project config
Add a frozen `ProjectConfig` and an optional `[routes.<name>.project]` table to the route file.

**To-do:**
- [x] Red: in `tests/test_config.py` add tests (using `ONE_ROUTE_TOML` + an appended
  `[routes.intake.project]` table: `number = 2`, `status_field = "Status"`, `status = "Todo"`,
  `effort_field = "Effort"`):
  - a route with the table loads with `route.project == ProjectConfig(number=2,
    status_field="Status", status="Todo", effort_field="Effort")`;
  - a route without it loads with `route.project is None` (the existing `ONE_ROUTE_TOML` case);
  - parametrized errors (text, expected message), all naming the key, never the value:
    `ONE_ROUTE_TOML.replace("[routes.intake]\n", "[routes.intake]\nproject = 3\n")` (inserted
    into the route table, as `test_unknown_route_key_raises` does: appended after the last
    `[[routes.intake.questions.feature]]` entry, `project = 3` would land in that question) →
    `routes.intake.project must be a table`; an extra key `owner = "x"` →
    `routes.intake.project has unknown key 'owner'`; each of the four keys missing →
    `routes.intake.project.<key> is required`; `number = 0` / `number = "2"` / `number = true` →
    `routes.intake.project.number must be a positive integer`; a blank or non-string name →
    `routes.intake.project.<key> is required` / `… must be a string`;
  - a no-value-leak test (dd-261029-017): with `status = ["Secret words"]` in the table, assert
    both `str(exc) == "routes.intake.project.status must be a string"` and `"Secret words" not
    in str(exc)` (before Green the loader raises `routes.intake has unknown key 'project'`, so
    the equality fails in Red);
  - direct construction: `TargetConfig(..., project="x")` raises
    `ConfigError("project must be a ProjectConfig or None")`;
  - `project` has no default (dd-261029-006), so add `project=None` to each existing direct
    `TargetConfig(...)` construction: `test_full_env_loads`, the `make_target` helper and
    `test_one_route_loads` (`grep -rn 'TargetConfig(' tests` lists them; `conftest` builds
    its routes through `load_routes`);
  - `test_example_routes_shape` also calls `_route_project(route, f"routes.{name}")` for each
    example route (import `_route_project` beside `_route_questions` in the `issue_bot.config`
    import) and asserts the result is not `None` for `c4i`;
  - import `ProjectConfig` in the same `issue_bot.config` import.
  Run `.venv/bin/pytest tests/test_config.py` and confirm the new tests fail.
- [x] Green, `issue_bot/config.py`:
  - add `PROJECT_KEYS = frozenset({"number", "status_field", "status", "effort_field"})` next to
    `QUESTION_KEYS`;
  - add `@dataclass(frozen=True) class ProjectConfig` with fields `number: int`,
    `status_field: str`, `status: str`, `effort_field: str` and docstring `"""A route's GitHub
    Project: its number in the route repo's org, and the field and option names the bot sets."""`;
  - append `"project"` to `ROUTE_KEYS` (last, so read order still reports the first bad key);
  - add `_route_project(route: Mapping[str, object], where: str) -> ProjectConfig | None`:
    `if "project" not in route: return None` (comment: the one optional route key: a route may
    have no Project), then `where_p = f"{where}.project"`, non-dict →
    `ConfigError(f"{where_p} must be a table")`, unknown keys against `PROJECT_KEYS` with the
    same message form as `_question` (`f"{where_p} has unknown key {unknown_keys[0]!r}"`), then
    `ProjectConfig(number=_route_int(table, where_p, "number"), status_field=_route_str(table,
    where_p, "status_field"), status=_route_str(table, where_p, "status"),
    effort_field=_route_str(table, where_p, "effort_field"))`;
  - add `project: ProjectConfig | None` (no default, like every other field) as
    `TargetConfig`'s last field (extend its docstring: "and, optionally, the Project its issues
    are added to"), and in `__post_init__` raise `ConfigError("project must be a ProjectConfig or None")` unless
    `self.project is None or isinstance(self.project, ProjectConfig)`;
  - in `_route`, pass `project=_route_project(route, where)` last;
  - update the module docstring and `load_routes` docstring: every key is required except the
    optional `project` table, whose keys are then all required.
- [x] In `example.routes.toml`, append after the last `[[routes.c4i.questions.feature]]` entry a
  `[routes.c4i.project]` table: `number = 2`, `status_field = "Status"`, `status = "Todo"`,
  `effort_field = "Effort"`. Comment above the table: it is optional (delete it for a route with
  no roadmap); the names must match the Project's own field and option names, and `Effort` needs
  one option per complexity band (S, M, L, XL). Comment above `number`: the number at the end of
  the Project's URL, `github.com/orgs/<org>/projects/<number>`. It lands in this step because
  `test_example_routes_shape` asserts `set(route) == set(ROUTE_KEYS)`. Keep `ROUTE_FILE_KEYS` in
  `tests/test_config.py` without `project` (it lists required keys).
- [x] Run `.venv/bin/pytest` and confirm all tests pass. — 390 passed (2026-10-29)

### 2. Issue node id and Project-scoped tokens
Capture the issue's node id, and give a Project route's token the Projects permission.

**To-do:**
- [ ] Red, `tests/conftest.py` (shared Project-route fixtures, used by Steps 2-5): add
  `import dataclasses`, `ProjectConfig` to the `issue_bot.config` import, a module constant
  `PROJECT = ProjectConfig(number=2, status_field="Status", status="Todo",
  effort_field="Effort")`, a `project_route(route: TargetConfig) -> TargetConfig` fixture
  returning `dataclasses.replace(route, project=PROJECT)` (docstring: the test route with a
  Project), and a `project_config(config: Config, project_route: TargetConfig) -> Config`
  fixture returning `dataclasses.replace(config, routes={project_route.channel_id:
  project_route})` (`Config.__post_init__` re-wraps the new routes dict read-only).
- [ ] Red, `tests/test_github.py`: `issue_response()` gains `"node_id": "I_node7"`; `create_issue`
  returns `FiledIssue(7, HTML_URL, "I_node7")`; add `(201, {"number": 7, "html_url": HTML_URL})`
  (no `node_id`) and `(201, {"number": 7, "html_url": HTML_URL, "node_id": 5})` to
  `test_bad_success_shape_raises`'s `response` parameters (it already asserts stage `issue`,
  status 201); with the `project_route` fixture, both `check_access(project_route)` and
  `create_issue(project_route, …)` mint with payload `{"repository_ids": [222], "permissions":
  {"issues": "write", "organization_projects": "write"}}`, while the plain route keeps
  `{"issues": "write"}` (the existing asserts in `test_create_issue_success` and `test_check_access_mints_a_token` stay); a plain and a
  Project route on the same repo id mint two tokens; a 401 on `create_issue` for a Project route
  drops only that route's cached token: `check_access(route)`, `check_access(project_route)`,
  `create(client, project_route)` raising `GitHubError("issue", 401)`, then `create(client,
  route)` and `create(client, project_route)`, with transport side_effect `[token_response(),
  token_response(), (401, None), issue_response(), token_response(), issue_response()]` and call
  URLs (`call.args[1]`) `[TOKEN_URL, TOKEN_URL, ISSUE_URL, ISSUE_URL, TOKEN_URL, ISSUE_URL]`. Run `.venv/bin/pytest tests/test_github.py`; confirm the
  new tests fail.
- [ ] Green, `issue_bot/github.py`:
  - `FiledIssue` gains `node_id: str` (third field, docstring: the GraphQL id a Project item is
    added by);
  - `create_issue` also requires `isinstance(data.get("node_id"), str)` and returns
    `FiledIssue(data["number"], data["html_url"], data["node_id"])`;
  - change `_installation_token(self, repo_id: int)` to `_installation_token(self, target:
    TargetConfig)`, with a private `_token_key(target) -> tuple[int, bool]` returning
    `(target.github_repo_id, target.project is not None)`; `self._tokens` becomes
    `dict[tuple[int, bool], tuple[str, float]]`; permissions are `{"issues": "write"}` plus
    `"organization_projects": "write"` when `target.project` is set (comment: least privilege,
    only a route with a Project asks for it);
  - update the callers (`check_access`, `ensure_label`, `create_issue`) to pass `target`,
    and both 401 pops to `self._tokens.pop(self._token_key(target), None)`;
  - update the class docstring's caching line ("Caches a repo-scoped token per repo and Project
    need").
- [ ] Update every positional `FiledIssue(7, …)` construction in the tests to pass a node id
  (`tests/test_bot.py`, `tests/test_threads.py`, `tests/test_intake.py`, `tests/test_issues.py`,
  `tests/test_github.py`; find them with `grep -rn 'FiledIssue(' tests`), using `"I_node7"`.
- [ ] Run `.venv/bin/pytest` and confirm all tests pass.

### 3. GraphQL: look up the Project and add the item
Add the Project lookup and the add-and-set calls to `GitHubClient`, all through `_request`.

**To-do:**
- [ ] Red, `tests/test_github.py` (fake transport; first response is the token mint):
  - import `Complexity` from `issue_bot.complexity` and `PROJECT_FIELDS_QUERY` and
    `ProjectFields` in the `issue_bot.github` import; add `GRAPHQL_URL =
    "https://api.github.com/graphql"` beside `TOKEN_URL`/`ISSUE_URL`/`LABEL_URL`;
  - `project_fields(project_route)` POSTs to `GRAPHQL_URL` with variables
    `{"org": "example-org", "number": 2}` and returns `ProjectFields(project_id="PVT_1",
    status_field_id="F_status", status_option_id="O_todo", effort_field_id="F_effort",
    effort_option_ids={"S": "O_s", "M": "O_m", "L": "O_l", "XL": "O_xl"})` from a response
    whose `fields.nodes` also holds a `None` entry, non-single-select `{}` nodes and other
    fields; a second call makes no request (cached);
  - `project_fields(route)` on the plain `route` fixture (no project) raises `ValueError` and
    makes no transport call (`transport.await_count == 0`);
  - `project_fields` raises `GitHubError("project", 200)` for: an `errors` key, a null
    `projectV2`, a missing status field, a status field without the `Todo` option, a missing
    effort field, an effort field missing any `Complexity` band; `GitHubError("project", 502)`
    for a non-200; `GitHubError("project", 401)` drops the token; a failed lookup is not cached
    (the next call requests again);
  - `add_to_project(project_route, issue, Complexity.M)` sends, after the lookup, an
    `addProjectV2ItemById` mutation with variables `{"project": "PVT_1", "content": "I_node7"}`,
    then one mutation with two aliased `updateProjectV2ItemFieldValue` fields with variables
    `{"project": "PVT_1", "item": "PVTI_1", "statusField": "F_status", "status": "O_todo",
    "effortField": "F_effort", "effort": "O_m"}`; the first (token) call's payload is
    `{"repository_ids": [222], "permissions": {"issues": "write", "organization_projects":
    "write"}}` and every GraphQL call's Authorization is `Bearer ghs_secret_token`;
  - `add_to_project` raises `GitHubError("project-item", 200)` when the add returns `errors` or
    no item id, `GitHubError("project-field", 200)` when the update returns `errors` or a null
    alias, and the transport-failure form `GitHubError(<stage>, None)` for each stage;
  - a failed add or field set drops the cached Project ids (dd-261029-007): with responses
    token, lookup, add, then a set returning `errors` (`GitHubError("project-field", 200)`),
    the next `add_to_project(project_route, issue, Complexity.M)` sends the lookup again (the
    fifth transport call's payload `query` is `PROJECT_FIELDS_QUERY`; the token stays cached,
    so it is followed by the add and the set); after an add returning `errors`
    (`GitHubError("project-item", 200)`) the next call's lookup is the fourth transport call;
  - no `GitHubError` message or attribute contains a GraphQL error message from the fake response
    (pass `"errors": [{"message": "Secret detail"}]` and assert `"Secret detail"` is absent from
    `str(exc)` and `repr(exc)`).
  Run `.venv/bin/pytest tests/test_github.py`; confirm they fail.
- [ ] Green, `issue_bot/github.py`:
  - add `GRAPHQL_URL = f"{API_URL}/graphql"` beside `API_URL`, and module-level query strings
    `PROJECT_FIELDS_QUERY` (`query($org: String!, $number: Int!) { organization(login: $org) {
    projectV2(number: $number) { id fields(first: 100) { nodes { ... on
    ProjectV2SingleSelectField { id name options { id name } } } } } } }`),
    `ADD_ITEM_MUTATION` (`mutation($project: ID!, $content: ID!) { addProjectV2ItemById(input:
    {projectId: $project, contentId: $content}) { item { id } } }`) and `SET_FIELDS_MUTATION`
    (`mutation($project: ID!, $item: ID!, $statusField: ID!, $status: String!, $effortField:
    ID!, $effort: String!) { status: updateProjectV2ItemFieldValue(input: {projectId: $project,
    itemId: $item, fieldId: $statusField, value: {singleSelectOptionId: $status}}) {
    projectV2Item { id } } effort: updateProjectV2ItemFieldValue(input: {projectId: $project,
    itemId: $item, fieldId: $effortField, value: {singleSelectOptionId: $effort}}) {
    projectV2Item { id } } }`); option ids are GraphQL `String`, not `ID` (a `String!` variable
    is accepted for the nullable `singleSelectOptionId`), and a mismatched declaration fails
    with `variableMismatch`;
  - `from types import MappingProxyType` in the stdlib group (after `from datetime import
    datetime`, before `from typing import Any`);
  - `from issue_bot.complexity import Complexity` (acyclic: complexity imports only
    issue_type) and `ProjectConfig` from config;
  - frozen `ProjectFields(project_id: str, status_field_id: str, status_option_id: str,
    effort_field_id: str, effort_option_ids: Mapping[str, str])`, freezing the mapping with
    `MappingProxyType(dict(...))` in `__post_init__` as `TargetConfig` does;
  - private `async def _graphql(self, stage: str, target: TargetConfig, query: str, variables:
    dict[str, object]) -> dict[str, Any]`: token via `_installation_token(target)`, `_request(stage,
    GRAPHQL_URL, self._headers(token), {"query": query, "variables": variables})`; a 401 pops the
    token and raises; any status other than 200, a non-dict body, an `errors` key or a non-dict
    `data` raises `GitHubError(stage, status) from None`; returns `data["data"]`;
  - `async def project_fields(self, target: TargetConfig) -> ProjectFields`: requires
    `target.project` (a `None` project is a caller bug: `raise ValueError("route has no
    project")`, before any request); cache `self._projects: dict[tuple[str, ProjectConfig],
    ProjectFields]` (initialised in `__init__` beside `self._labels`, with the comment: a
    concurrent first miss looks up twice, harmlessly, like the token and label caches) keyed by
    a private `_project_key(target) -> tuple[str, ProjectConfig]` returning
    `(owner.casefold(), target.project)` where `owner = target.github_repo.split("/")[0]`;
    the lookup is `self._graphql("project", target, PROJECT_FIELDS_QUERY, {"org": owner,
    "number": target.project.number})` (owner as written, not casefolded; `number` an int for
    `$number: Int!`); validate each step of the path with `isinstance` checks, skip `fields.nodes` entries that
    are not dicts (the schema allows `null` nodes), select single-select nodes by `name`, and
    raise `GitHubError("project", 200)` for every mismatch listed in the Red to-do; the effort
    check is `all(str(band) in options for band in Complexity)`, where `options` maps the
    Effort field's option names to ids, and `effort_option_ids` holds the band options only,
    `{str(band): options[str(band)] for band in Complexity}`; a failed lookup is never cached;
  - `async def add_to_project(self, target: TargetConfig, issue: FiledIssue, band: Complexity)
    -> None`: `fields = await self.project_fields(target)`, add mutation (stage
    `project-item`, item id must be a `str` at `addProjectV2ItemById.item.id`), then the set
    mutation (stage `project-field`, both aliases must be dicts with a `projectV2Item`); wrap
    the two mutations in `try:` / `except GitHubError as exc:` that, when `exc.stage` is
    `"project-item"` or `"project-field"`, drops the route's cached ids
    (`self._projects.pop(self._project_key(target), None)`, never a keyed `del`; comment: ids
    changed on GitHub, e.g. a deleted and re-created option, are looked up again on the next filing) and
    then re-raises with a bare `raise`;
  - update the `GitHubError` docstring's stage list (`token`, `label`, `issue`, `project`,
    `project-item`, `project-field`), the module docstring (REST and GraphQL APIs) and the
    first line of `GitHubClient`'s docstring (it also adds issues to a route's Project).
- [ ] Run `.venv/bin/pytest` and confirm all tests pass.

### 4. Place the filed issue on the roadmap and report it
Call the Project step from `filing_hook` after filing, and add the roadmap line to the link
message.

**To-do:**
- [ ] Red:
  - `tests/test_threads.py`: `filed_reply(issue, title, band, None)` is unchanged from today;
    `True` appends `"\n" + ROADMAP_ADDED_NOTE`; `False` appends `"\n" + ROADMAP_FAILED_NOTE`;
    `test_roadmap_notes_are_fixed_text` (dd-261029-018, as `test_filing_error_reply_is_fixed_text`
    does) asserts `ROADMAP_ADDED_NOTE == "Added to the roadmap."` and `ROADMAP_FAILED_NOTE ==
    "Couldn't finish adding it to the roadmap; the owner can fix it by hand."`; import
    `ROADMAP_ADDED_NOTE` and `ROADMAP_FAILED_NOTE` in the `issue_bot.threads` import;
  - `tests/test_issues.py`: `place_on_roadmap(github, candidate, issue)` returns `None` without
    calling GitHub for a route with no project (`make_candidate()`); for a Project route
    (`make_candidate(target=project_route)`, the Step 2 `conftest` fixture) it awaits
    `github.add_to_project(candidate.target, issue, candidate.complexity)` and returns `True`
    (INFO `added bug message_id=99 to the roadmap issue=<url>`); on `GitHubError("project-item",
    200)` it returns `False` and logs a WARNING `could not add bug message_id=99 to the roadmap
    issue=<url>: GitHubError stage=project-item status=200`, with `assert_no_member_text`; on
    any other exception (`RuntimeError("Secret exception words")`) it returns `False` and logs
    exactly the WARNING `could not add bug message_id=99 to the roadmap issue=<url>:
    RuntimeError`, with no record's text (`record_texts(caplog)`; add `record_texts` to the
    `tests.conftest` import) containing `"Secret exception words"`; import `place_on_roadmap` in
    the `issue_bot.issues` import;
  - `tests/test_bot.py`: `filing_hook` on a Project route (`make_candidate(target=project_route)`)
    posts `filed_reply(issue, title, band, True)`, and with `add_to_project` raising
    `GitHubError` posts the `False` form, still logs `filed …` and never posts
    `FILING_ERROR_REPLY`; with `add_to_project` raising `RuntimeError("Secret exception words")`
    it also posts the `False` form and `"Secret exception words"` is in no record's text; a
    plain route posts the `None` form and never calls `add_to_project`; the roadmap step runs
    after the `filed …` log line (record order in `caplog`).
  Run `.venv/bin/pytest`; confirm the new tests fail.
- [ ] Green:
  - `issue_bot/threads.py`: add `ROADMAP_ADDED_NOTE = "Added to the roadmap."` and (one note,
    true whether the add or the field set failed)
    `ROADMAP_FAILED_NOTE = "Couldn't finish adding it to the roadmap; the owner can fix it by hand."`;
    `filed_reply(issue: FiledIssue, title: str, complexity: Complexity, roadmap: bool | None)`
    appends `"\n" + note` when `roadmap` is not `None`; update its docstring;
  - `issue_bot/issues.py`: `async def place_on_roadmap(github: GitHubClient, candidate:
    IssueCandidate, issue: FiledIssue) -> bool | None` as tested: `except GitHubError` logs the
    WARNING with type, stage and status and returns `False`; then `except Exception` (comment:
    the issue is already filed, so a parsing bug must not drop the link message) logs the
    WARNING `could not add %s message_id=%s to the roadmap issue=%s: %s` with the exception
    type only, never `exc_info` or its text (as `bot.py`'s `_check_github_access` generic
    branch does) and returns `False`; logs carry the type, message id, issue URL, exception
    type, stage and status only; update the module docstring (its log lines, plural);
  - `issue_bot/bot.py` `file_and_report`: after the `filed …` INFO line, `roadmap = await
    place_on_roadmap(github, candidate, issue)`, then `filed_reply(issue, candidate.title,
    candidate.complexity, roadmap)`; import `place_on_roadmap`; update `filing_hook`'s docstring
    (a Project route also gets the roadmap step; its failure is a WARNING and a note, never a
    filing error);
  - `tests/conftest.py` `fake_github`: add `add_to_project=AsyncMock(return_value=None)` to both
    returned `SimpleNamespace`s (the exception and the success branch);
  - update every other `filed_reply(...)` call in the tests to pass `None` (find them with
    `grep -rn 'filed_reply(' tests`).
- [ ] Run `.venv/bin/pytest` and confirm all tests pass.

### 5. Check each Project at startup
Look each Project route's fields up once at startup and log the result, as the access check does.

**To-do:**
- [ ] Red, `tests/test_bot.py`. `_check_github_access` returns at once when `filing_check` is
  None, so every case passes both checks: `access = AsyncMock()`, `check = AsyncMock()`, and
  `IssueBot(project_config, filing_check=access, project_check=check)` with the Step 2
  `conftest` fixtures `project_config` and `project_route`. Drive it as the existing
  `test_setup_hook_*` access tests do: `monkeypatch.setattr(bot.tree, "sync",
  AsyncMock(return_value=[]))`, then `await bot.setup_hook()` under `caplog.at_level(logging.INFO)`.
  Cases: `check` is awaited once with `project_route` and logs INFO `github project ok for
  repo_id=222 project=2`, after that route's access check (a parent `order = Mock()` that
  `attach_mock`s `access` as `"access"` and `check` as `"check"`; assert `"access"` precedes
  `"check"` in `[name for name, _args, _kwargs in order.mock_calls]`, as `tests/test_issues.py`'s
  `test_file_candidate_passes_title_body_labels` does); `check` raising `GitHubError("project",
  200)` logs ERROR `github project check failed for repo_id=222 project=2: GitHubError
  stage=project status=200` and, on a two-route Config built from `two_route_config` with both
  routes given `PROJECT` (`dataclasses.replace(two_route_config, routes={channel_id:
  dataclasses.replace(r, project=PROJECT) for channel_id, r in
  two_route_config.routes.items()})`), `check(side_effect=[GitHubError("project", 200), None])`
  is still awaited for the second route (channel 556) and logs `github project ok for
  repo_id=223 project=2`; any other exception (`RuntimeError("Secret exception words")`) logs
  exactly `github project check failed for repo_id=222 project=2: RuntimeError`, and no record
  text contains the exception message; with the unchanged `config` (no project) `check` is
  never awaited; with `project_check=None` on `project_config` nothing beyond the access check
  runs (a regression guard: it passes before Green too); with `filing_check=None` and `project_check=check` on `project_config`, `check` is never
  awaited; with `access(side_effect=GitHubError("token", 401))`, `check` is never awaited. Add
  `import dataclasses`, `Mock` to the `unittest.mock` import and `PROJECT` to the
  `tests.conftest` import. In `test_main_runs_bot_with_token`, also assert
  `init_kwargs["project_check"].__func__ is GitHubClient.project_fields` (and its `__self__` is
  a `GitHubClient`). Run them; confirm every other new case fails.
- [ ] Green: in `issue_bot/bot.py`, add `from collections.abc import Awaitable, Callable` to the
  stdlib import group (after `import sys`, before `from typing import Any`, as the repo puts
  plain imports first), and at module level, after
  `logger`, `ProjectCheck = Callable[[TargetConfig], Awaitable[object]]` (mirroring
  `issue_bot/intake.py`'s `FilingCheck`); `IssueBot.__init__` gains `project_check: ProjectCheck
  | None = None` (stored as `self.project_check`); `_check_github_access` runs it for each route
  with `route.project` after that route's successful access check (`project_check` set), logging
  INFO `github project ok for repo_id=%s project=%s`, ERROR `github project check failed for
  repo_id=%s project=%s: %s stage=%s status=%s` for a `GitHubError` and `github project check
  failed for repo_id=%s project=%s: %s` (type only, no `exc_info`) for any other exception, with
  `route.github_repo_id` and `route.project.number` (ids only, like the access lines); update
  `IssueBot`'s class docstring (`project_check`, when set, runs once at startup for each route
  with a `project`, after that route's access check; production wires
  `GitHubClient.project_fields` as `project_check` in `__main__`) and `setup_hook`'s first line
  (then check GitHub access and each route's Project); `issue_bot/__main__.py` passes
  `project_check=github.project_fields`. In `test_main_builds_github_client`, the GitHubClient
  sentinel becomes `SimpleNamespace(check_access=AsyncMock(), project_fields=AsyncMock())`, since
  `main()` now reads `github.project_fields`.
- [ ] Run `.venv/bin/pytest` and confirm all tests pass.

### 6. Docs
Document the Project table, the App permission and the smoke check.

**To-do:**
- [ ] `README.md` § GitHub App setup step 1: add that a route with a `project` table also needs
  the Organization permission **Projects: Read and write** (accept the new permission on the
  installation after adding it); the bot asks for it only on those routes' tokens. Also say its
  reach: the permission covers every Project in the org, not only the route's, so a Project
  route's token can write any 4IRL Project (keeping the bot off other Projects is procedure,
  not a GitHub limit). To revert: remove every route's `project` table, then remove the
  Projects permission from the App and accept the change on the installation.
- [ ] `README.md` § Status: add F6 (roadmap placement) to the shipped-features list, in that
  paragraph's own `F<n> (<what>)` style, and replace the intro's "Roadmap placement is
  planned." sentence with one saying a route with a `project` table also places each filed
  issue on its roadmap Project; in that paragraph's description of the success post ("with the
  link on the next line"), add that on a route with a `project` table a third line carries the
  roadmap note (`ROADMAP_ADDED_NOTE` or `ROADMAP_FAILED_NOTE`). In § Reporting step 4 (the step that says the bot "posts the
  issue's number, complexity band, title and link in the thread"), add: on a route with a
  `project` table the bot then adds the issue to the route's Project with its Status and
  Effort, and the link message gets a third line, `ROADMAP_ADDED_NOTE` on success or
  `ROADMAP_FAILED_NOTE` on failure (write each note's text as it stands in
  `issue_bot/threads.py` when this step runs).
- [ ] `README.md` § Configuration: change "Every key is required: there are no defaults in code"
  to say the one optional route key is the `project` table; add rows for `project.number`
  (positive integer: the Project's number in `GITHUB_ORG`, from its URL), `project.status_field`
  / `project.status` (the Status single-select's name and the option new items get) and
  `project.effort_field` (the single-select set to the complexity band; it needs options named
  `S`, `M`, `L` and `XL`); say the bot checks them at startup (`github project ok for repo_id=… project=…`)
  and that a failed Project step leaves the issue filed with a note in the thread.
- [ ] `README.md`: add `#### Adding a roadmap Project` after the Upgrading sections: existing
  route files load unchanged; to turn it on, first add the Organization permission **Projects:
  Read and write** and accept it on the installation, then add the route's `project` table and
  restart, and confirm the startup line `github project ok for repo_id=… project=…`. A
  `project` table added before the grant is accepted fails that route's token mint, so its
  `/bug` and `/feature` reply that reports can't be filed until the grant is accepted or the
  table removed. A route file copied from `example.routes.toml` already has a `project` table
  on its `c4i` route: delete it if the route has no roadmap. Rolling back to an older build needs the `project` tables removed
  (older builds reject the unknown key and exit with code 2). To stop using Projects entirely:
  remove every route's `project` table, then remove the Projects permission from the App and
  accept the change on the installation.
- [ ] `docs/SMOKE-TEST.md`:
  - § What it writes: in **Probe**, add that with a Project route the token also carries
    `organization_projects: write`; add that each report filed on a Project route writes one
    item in the test Project with Status `Todo` and Effort set to the filed band; in
    **Re-runs**, add that each re-run adds a new item for each new issue.
  - § Scratch repo and test channel: add a step creating a test Project in the 4IRL org (its
    default `Status` field already has `Todo`; add an `Effort` single-select with options `S`,
    `M`, `L` and `XL`), linking it to `4IRL/issue-bot-scratch`, and reading its number from its
    URL. In § `.env` for a local run, add to the `routes.smoke.toml` example a
    `[routes.smoke.project]` block (`number = <test Project number>`, `status_field =
    "Status"`, `status = "Todo"`, `effort_field = "Effort"`).
  - § 1. Token probe: give the Project-route payload (`"permissions": {"issues": "write",
    "organization_projects": "write"}`) and accept `organization_projects: write` in the pass
    list for a Project route.
  - § 2. Local run: in step 1's check table, the "Discord thread" row's bot message ends with a
    third line, the `ROADMAP_ADDED_NOTE` text in `issue_bot/threads.py`; the "Log" row also
    lists the startup `github project ok for repo_id=… project=…` line and one `added <type>
    message_id=… to the roadmap issue=…` INFO line per filing; a new "Test Project" row says
    each filed issue appears as an item with Status `Todo` and Effort set to the band the
    preview showed (the scratch route points at the test Project, never Project #2 or the live
    channel).
  - § 5. Record and tear down: add deleting the test Project (or its items) to the teardown.
  - § Troubleshooting: add a row for `could not add … to the roadmap … stage=project…`: the
    issue is filed, so finish by hand rather than re-running, which files a second issue: after
    `stage=project`, `stage=project-item` or `stage=token`, add the issue to the Project and set
    its Status and Effort; after `stage=project-field` the item is already on the Project, so
    set its Status and Effort there; with `stage=project status=200` the route's `project`
    table doesn't match GitHub: its `number` names no Project in `GITHUB_ORG`, or a field or
    option name doesn't match the Project; after a `stage=project-item` or `stage=project-field` failure the bot
    looks the Project's ids up again on the next filing, so a field or option deleted and
    re-created on GitHub is picked up without a restart. Add a row for `github project check failed …` at startup: the
    same causes. In the existing `/bug` says reports can't be filed row, add that on a route with a
    `project` table a missing or not-yet-accepted **Projects: Read and write** grant also fails
    the token mint. In the existing `The probe returns 422` row, add: or, with the Project-route
    payload, the App lacks **Projects: Read and write** or the installation hasn't accepted it.
- [ ] `plans/META-PLAN.md` (re-read it first; dd-261029-010): in the `## F6 — Add the issue to
  the chores4irl roadmap Project` section's **Expected end state**, replace the first bullet
  ```
  - The Project number and field IDs are config, never hardcoded.
  ```
  with
  ```
  - The Project number and field/option names are per-route config; their ids are looked up through GraphQL and cached, never hardcoded (dd-261029-002).
  ```
  and, in the same section's **Dependencies.** paragraph, replace the phrase `the Project number
  and field IDs are per-route config under` (on one line there) with `the Project number and
  field/option names are per-route config under`,
  and in `### Standing invariants (must not regress)` replace invariant 3, now (over two lines)
  ```
  3. Every config key, in the environment and the route file, is required and validated at
     startup; a bad config exits with code 2 before connecting (F1; route file F8, PR #17).
  ```
  with (each replacement on one line, as written)
  ```
  3. Every config key, in the environment and the route file, is required and validated at startup, except the optional `[routes.<name>.project]` table, whose keys are then all required (F6); a bad config exits with code 2 before connecting (F1; route file F8, PR #17).
  ```
  Confirm: `grep -c 'looked up through GraphQL and cached' plans/META-PLAN.md` and
  `grep -c 'except the optional' plans/META-PLAN.md` each print `1`, and
  `grep -c 'field IDs are config, never hardcoded' plans/META-PLAN.md || true` and `grep -c
  'field IDs are per-route config' plans/META-PLAN.md || true` each print `0`.
- [ ] Confirm Standing invariant 1: `grep -rnE
  '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot`
  prints nothing, and `grep -rn 'PVT_\|number = 2' issue_bot` prints nothing (each exits 1
  when it finds nothing; that is the pass). The Project number lives only in
  `example.routes.toml`; its ids are looked up at runtime and never stored.

### 7. Verify All Tests Pass

Run the full test suites to confirm nothing is broken:

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm all tests pass
- [ ] Investigate and fix any failures before marking the plan finished. If every check above
  passed, tick this box with `— N/A: no failures`.
- [ ] Copy the Owner checks below verbatim into the final report (for the orchestrator's
  record; the durable carriers are the Owner checks section below and Step 6's README and
  docs/SMOKE-TEST.md text, which merge with the PR).

## Owner checks (manual, not for the executor)
- On github.com, add the Organization permission **Projects: Read and write** to the
  `4irl-issue-bot` App and accept the updated permissions on its 4IRL installation. The
  permission covers every Project in the org, not only the route's, so a Project route's token
  can write any 4IRL Project (the smoke test's "never Project #2" is procedure, not a GitHub
  limit). To revert: remove every route's `project` table, then remove the Projects permission
  from the App and accept the change on the installation.
- Before the PR is merged, run `docs/SMOKE-TEST.md` against a scratch repo and a test Project
  (never Project #2 or the live channel): the item lands with Status `Todo` and the right
  Effort, and the thread says "Added to the roadmap." This is the live acceptance gate for the
  `addProjectV2ItemById` and `updateProjectV2ItemFieldValue` mutations and the
  `organization_projects: write` token, which no test or review probe has run against GitHub
  (Research Findings: GraphQL schema probes).

## Status
finished: false
