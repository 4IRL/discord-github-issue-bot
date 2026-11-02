# Never file a report twice (F12)

## Summary
Each report is filed at most once, even after a File press in a second Discord client, a
concurrent Edit or a create that timed out and is retried. Two guards do it: an in-process
`Report` object shared by every preview of one intake session refuses a second **File**, and
`file_candidate` first looks the repo's newest issues up for one whose author line already links
this summary message, reusing it (and its roadmap item) instead of creating another. Source:
`plans/META-PLAN.md` § *F12 — Never file a report twice*; branch `feature/idempotent-filing`.

## Design decisions
- **DD-1 Dedup mechanism** (asked, dd-261101-003): an in-process guard carried across Edit plus a
  GitHub REST list lookup (`GET /repos/{repo}/issues?state=all&sort=created&direction=desc&per_page=100`,
  consistent, unlike search) matching the summary URL on the body's first line. No persisted state.
- **DD-2 Scope of "a report"** (asked, dd-261101-004): one intake session, i.e. one fresh modal
  submit plus all its Edits and previews; at most one **File** succeeds. The GitHub lookup keys on
  the summary message URL (one per File press). A manual rerun of the command is a new report.
- **DD-3 Lookup failure** (asked, dd-261101-005; user chose against the Recommended fail-closed):
  a `GitHubError` from the lookup is a WARNING (`stage=lookup`) and filing proceeds to create.
- Reusing an issue re-runs `place_on_roadmap` on it. `addProjectV2ItemById` returns the existing
  item for content already on the Project, so Track is still set on one item only (F17 contract);
  Status/Effort/Track are written again with the report's values, so a hand change made on the
  Project between the first filing and the retry is overwritten (accepted). The link message stays `filed_reply`
  (the issue *is* filed), so no new reply text on the GitHub path.
- **Review pass 1** (`reviews/idempotent-filing-review.md`): `reports_link` strips a trailing `\r` so a
  body GitHub returns with CRLF (after a web-UI edit) still matches (pass1-DD-2, asked). A File
  press consumes the session's one File even if its summary post then fails; a sibling preview or
  open Edit then gets `ALREADY_FILED_REPLY` and the reporter reruns the command, as
  `SUMMARY_FAILED_REPLY` already says (pass1-DD-3, asked, accepted). After filing, a stale sibling
  preview's Edit, S/M/L/XL and Track presses still run (Edit is refused at submit, a band/Track
  press may redraw its buttons); File and the Edit submit refuse, so the report still files once
  (pass1-DD-4, asked, accepted). The list call's live evidence is the smoke run's log showing no
  lookup WARNING (pass1-DD-1, assumed).
- **Review pass 2:** the GitHub lookup is check-then-create, not atomic: it dedups a retry that
  starts after the earlier attempt finished, not two overlapping filings of one candidate. F12 has
  no overlapping path (one File per session); F13 must keep retries of one report sequential. The
  lookup trusts the author line alone, so a hand-made issue whose first line carries the summary
  URL would be reused (needs repo access and a race; fixed by hand; revisit in F13) (pass2-DD-1,
  asked, accepted). Two concurrent Edits leave the older replacement preview running on the same
  message; if nothing is filed it expires early and blanks its sibling. Pre-existing, unrelated
  to filing once, out of scope (pass2-DD-2, asked, accepted).

## Research Findings
- The public summary message is posted at **File** time (`issue_bot/intake.py` `_post_and_file`,
  `interaction.channel.send` ~l.194), one per File press; its `jump_url` becomes
  `IssueCandidate.message_url` (`issue_bot/handler.py` `candidate_from_submission`) and line 1 of
  the body: `Reported by \`<author>\` in Discord: <url>` (`issue_bot/issues.py` `render_body`).
  So a summary-URL key alone cannot catch the F3 race; it catches only a re-filing of the same
  candidate (a timed-out create retried, F13).
- F3 race: `PreviewView.edit_button` leaves the view open; `file_button` closes V1 (no await
  before `_closed = True`); the pending Edit's `IntakeModal.on_submit` (preview branch) ignores
  `self.preview._closed` on purpose (DD-6, pinned by `test_edit_submit_after_expiry_still_previews`)
  and builds a fresh `PreviewView` V2 whose File posts a new summary and files again. Two
  concurrent Edits from V1 build V2 and V3; V2 is never stopped.
- `GitHubClient._request(stage, url, headers, payload)` hardcodes `"POST"` (`issue_bot/github.py`
  ~l.252); `Transport` already takes the method first. `aiohttp_transport` sends `json=payload`,
  so `None` sends no body. Errors are `GitHubError(stage, status)` raised `from None`; a 401 pops
  the cached token with `self._tokens.pop(self._token_key(target), None)`. `issues: write`
  installation tokens can read issues. `github.py` must not import `issues.py` (cycle), so body
  matching lives in `issues.py` and is passed to the client as a predicate.
- Tests: `.venv/bin/pytest` from the repo root (CLAUDE.md, META-PLAN *Verification*;
  `asyncio_mode=auto`). GitHub HTTP is faked with a `transport` AsyncMock of
  ordered `(status, json)` tuples (`tests/test_github.py` `make_client`, `token_response`);
  higher layers use `tests/conftest.py` `fake_github(result)` (4 AsyncMocks) and ad-hoc
  `SimpleNamespace` fakes in `tests/test_issues.py` (l.142, l.169). Discord is faked with
  `make_interaction` / `make_message`; tests call `view.file_button.callback(interaction)`.
- Logging rule (Standing invariant 2): new log lines carry type, ids, URLs, error type, stage and
  status only.

## Steps

### 1. GET support and `GitHubClient.find_issue`
Add a read path to the client: find the newest issue whose body satisfies a predicate.

**To-do:**
- [x] Red, in `tests/test_github.py`: add `LOOKUP_URL = f"{ISSUE_URL}?state=all&sort=created&direction=desc&per_page=100"` beside the other URL constants and tests, each with `transport = AsyncMock(side_effect=[token_response(), <second>])`, where `<second>` is `(200, [...])` for the list cases and the named status, body or exception for the error cases (the 401 test appends `token_response()` and a further response, as `test_issue_request_401_drops_cached_token` does):
  - `test_find_issue_returns_first_match`: list `[{"number": 9, "html_url": "…/9", "node_id": "I_9", "body": "no"}, {"number": 7, "html_url": HTML_URL, "node_id": "I_node7", "body": "yes"}]`, predicate `lambda body: body == "yes"` → `FiledIssue(7, HTML_URL, "I_node7")`; second transport call is `("GET", LOOKUP_URL, <headers with Bearer ghs_secret_token>, None)`.
  - `test_find_issue_returns_none_without_match` (empty list and non-matching bodies).
  - `test_find_issue_skips_pull_requests_and_null_bodies`: an item with a `"pull_request": {}` key and a matching body is skipped; an item with `"body": None` is skipped without calling the predicate.
  - `test_find_issue_non_200_raises_lookup_error` (e.g. 500 → `GitHubError` with `stage == "lookup"`, `status == 500`), `test_find_issue_401_drops_token` (a following call requests a new token, as the existing create_issue 401 test does), `test_find_issue_non_list_raises` (200 with a dict), `test_find_issue_malformed_match_raises` (matching item missing `node_id` → `GitHubError("lookup", 200)`), `test_find_issue_transport_error_raises_lookup` (`aiohttp.ClientError()` side effect → `stage == "lookup"`, `status is None`, `__context__ is None`).
  - Run `.venv/bin/pytest tests/test_github.py -q`; confirm the new tests fail (AttributeError).
- [x] Green, in `issue_bot/github.py`:
  - Add `LOOKUP_PAGE_SIZE = 100  # newest issues and pull requests searched for an earlier filing of the same summary` beside the other constants.
  - Change `_request` to `async def _request(self, stage: str, url: str, headers: Mapping[str, str], payload: object, method: str = "POST") -> tuple[int, Any]` and pass `method` to `self._transport(method, url, headers, payload)`. Existing callers stay unchanged.
  - Add `async def find_issue(self, target: TargetConfig, matches: Callable[[str], bool]) -> FiledIssue | None` after `create_issue`, docstring "Return the newest issue among the target repo's latest ``LOOKUP_PAGE_SIZE`` issues and pull requests whose body ``matches``, else None; raise GitHubError (stage ``lookup``, or ``token`` when no installation token can be had) on any failure.". Body: `token = await self._installation_token(target)`; `status, data = await self._request("lookup", f"{API_URL}/repos/{target.github_repo}/issues?state=all&sort=created&direction=desc&per_page={LOOKUP_PAGE_SIZE}", self._headers(token), None, method="GET")`; on 401 pop the token (same comment as `create_issue`) and raise `GitHubError("lookup", status) from None`; if `status != 200 or not isinstance(data, list)` raise `GitHubError("lookup", status) from None`; loop items: skip non-dicts, items with `"pull_request"` in them, and non-`str` bodies; on `matches(body)` validate `number` (`type(...) is int`), `html_url` (str) and `node_id` (str) like `create_issue`, raising `GitHubError("lookup", status) from None` if invalid, else return `FiledIssue(...)`; after the loop `return None`.
  - Update the `GitHubClient` class docstring to mention it also finds an earlier issue for a report.
  - Add ``"lookup"`` to the stage list in the `GitHubError` docstring (after ``"issue"``).
  - Run `.venv/bin/pytest tests/test_github.py -q`; all pass.
- [x] Refactor if needed; `.venv/bin/pytest -q` stays green. COMPLETE (2026-11-01): 11 new find_issue tests red (AttributeError) then green; full suite 521 passed, review fixes included (non-dict items added to the skip test, a later second match added to the first-match test).

### 2. Reuse an existing issue in `file_candidate`
Before creating, look for an issue that already links this summary message; reuse it.

**To-do:**
- [x] Red, in `tests/test_issues.py`:
  - `test_reports_link_matches_only_the_author_line`: `reports_link(render_body("Al", URL, ()), URL)` is True, and so is the same body with `\n` replaced by `\r\n` (GitHub returns CRLF after a web edit); False for a different URL, for a body whose *second* line carries `in Discord: URL` (member text), and for a URL that is a prefix of another (`URL + "1"`).
  - `test_file_candidate_reuses_existing_issue`: fake `github = SimpleNamespace(find_issue=AsyncMock(return_value=FiledIssue(5, "https://github.com/o/r/issues/5", "I_5")), ensure_label=AsyncMock(), create_issue=AsyncMock())` → returns that issue; `create_issue` and `ensure_label` not awaited; the predicate passed to `find_issue` returns True for `issue_body(candidate)` and False for another candidate's body; an INFO log `found existing issue for <type> message_id=<id> issue=<url>` and `assert_no_member_text(caplog)`.
  - `test_file_candidate_lookup_failure_still_files`: `github = SimpleNamespace(find_issue=AsyncMock(side_effect=GitHubError("lookup", 502)), ensure_label=AsyncMock(), create_issue=AsyncMock(return_value=FiledIssue(5, "https://github.com/o/r/issues/5", "I_5")))` → `create_issue` awaited once; WARNING `could not look up an existing issue for <type> message_id=<id>: GitHubError stage=lookup status=502`.
  - Add `find_issue=AsyncMock(return_value=None)` to the existing `SimpleNamespace` fakes at l.142 and l.169, and in `test_file_candidate_passes_title_body_labels` add `order.attach_mock(github.find_issue, "find_issue")`, assert `github.find_issue.assert_awaited_once_with(candidate.target, ANY)` (add `ANY` to the `unittest.mock` import) and `call_names.index("find_issue") < call_names.index("ensure_label")`.
  - Run `.venv/bin/pytest tests/test_issues.py -q`; confirm it fails (an ImportError of `reports_link` at collection is the expected red).
- [x] Green, in `issue_bot/issues.py`:
  - Add `def reports_link(body: str, link: str) -> bool` right after `render_body`, docstring "Whether ``body``'s first line is ``render_body``'s author line for ``link``.": `return body.split("\n", 1)[0].rstrip("\r").endswith(f"{AUTHOR_LINK_SEPARATOR}{link}")`. Make `render_body` build its author line with the same `" in Discord: "` text (a module constant `AUTHOR_LINK_SEPARATOR = " in Discord: "` used by both) so the two cannot drift.
  - In `file_candidate`, before the label step:
    ```python
    try:
        existing = await github.find_issue(
            candidate.target, lambda body: reports_link(body, candidate.message_url)
        )
    except GitHubError as exc:
        logger.warning("could not look up an existing issue for %s message_id=%s: %s stage=%s status=%s",
                       candidate.type, candidate.message_id, type(exc).__name__, exc.stage, exc.status)
        existing = None
    if existing is not None:
        logger.info("found existing issue for %s message_id=%s issue=%s",
                    candidate.type, candidate.message_id, existing.html_url)
        return existing
    ```
    and extend its docstring: an issue already linking this summary message is returned instead of filing again; a failed lookup is a WARNING and the issue is filed (DD-3).
  - Update the module docstring's list of log lines (a found issue, a failed lookup).
  - In `tests/conftest.py` `fake_github`, add `find_issue=AsyncMock(return_value=None)` to both branches.
  - Run `.venv/bin/pytest -q`; all pass. COMPLETE (2026-11-01): 3 new tests red (ImportError of `reports_link` at collection) then green; full suite 524 passed; review fix: `file_candidate` docstring summary now says it returns the filed (or already-filed) issue.

### 3. Hook-level dedup: a repeated filing and a retry after a timed-out create
Prove the end-to-end hook files one issue and reuses it on re-entry, Project item included.

**To-do:**
- [x] In `tests/test_bot.py`, add a stateful fake: a helper `recording_github()` returning a `SimpleNamespace` whose `create_issue` (AsyncMock with a side-effect function) appends `(body, FiledIssue(n, url, node))` to a list and returns the issue, whose `find_issue` is an AsyncMock whose side-effect function `(target, matches)` returns the first recorded issue whose body `matches`, else None, and with `ensure_label`, `add_to_project=AsyncMock(return_value="PVTI_1")`, `set_track` AsyncMocks.
  - `test_filing_same_candidate_twice_creates_one_issue`: call `filing_hook(github)(message, candidate)` twice with the same `make_message()` / `make_candidate(...)` (Project route, `track` set); `create_issue` awaited once; both runs post `filed_reply` with the same issue URL; `add_to_project` is awaited twice with the same `FiledIssue` (one Project item, since GitHub returns the existing item for the same content id) and `set_track` with `"PVTI_1"` both times.
  - `test_retry_after_timed_out_create_finds_the_issue`: first `create_issue` call records the issue then raises `GitHubError("issue", None)`; first run posts `FILING_ERROR_REPLY`; second run with the same candidate awaits `create_issue` no more (still once total), posts `filed_reply` with the recorded issue's URL, and runs the roadmap step.
  - Both use `assert_no_member_text(caplog)` with INFO capture.
  - These should pass on Step 2's code; if either fails, fix `file_candidate`/`filing_hook` before ticking. Run `.venv/bin/pytest tests/test_bot.py -q`. COMPLETE (2026-11-01): both tests pass on Step 2's code with no production change; tests/test_bot.py 75 passed, full suite 526 passed.

### 4. One File per intake session (closes F3)
Share one mutable `Report` across every preview of an intake session; refuse a second File.

**To-do:**
- [x] Red, in `tests/test_intake.py` (import `ALREADY_FILED_REPLY`):
  - `test_edit_submit_after_file_refuses`: `view = await submitted_preview(route, hook, make_interaction())`; `modal = await reopened_modal(view, make_interaction)`; `await view.file_button.callback(make_interaction())`; `edit_interaction = make_interaction(interaction_id=4343)` (so the logged id differs from the previews' default 4242); `await edited_submit(modal, edit_interaction)` → `edit_interaction.response.edit_message` awaited once with `content=ALREADY_FILED_REPLY, view=None`; `hook` awaited once; with `caplog.at_level(logging.INFO)` around the Edit submit, `intake_messages(caplog, logging.INFO)` contains `f"refused edit of filed bug interaction_id={edit_interaction.id}"` and `assert_no_member_text(caplog)` passes.
  - `test_file_on_sibling_preview_after_file_refuses` (two Edits from V1): open `modal_a` and `modal_b` from V1; submit `modal_a` → V2 (the `view` kwarg of that edit), submit `modal_b` → V3; File V3 → hook awaited once; File V2 with `make_interaction(interaction_id=4343)` → its `response.edit_message` awaited with `content=ALREADY_FILED_REPLY, view=None`, hook still awaited once, V2 `is_finished()`; with INFO capture around that press, `intake_messages(caplog, logging.INFO)` contains `f"refused second file bug interaction_id={<that interaction>.id}"` and `assert_no_member_text(caplog)` passes.
  - `test_concurrent_file_on_sibling_previews_files_once`: build V2 and V3 as above; give V3's File interaction an `edit_message` side effect that does `await asyncio.sleep(0)` and then sets `response.is_done.return_value = True` (as `test_file_only_once` does); `await asyncio.gather(v3.file_button.callback(first), v2.file_button.callback(second))` → hook awaited once, both views `is_finished()`.
  - `test_timeout_after_sibling_filed_does_nothing`: as above, after File on V3 call `await v2.on_timeout()` → V2's `interaction.edit_original_response` not awaited.
  - `test_edit_carries_report_to_new_preview`: the view from an Edit submit has `report is view.report` of the original.
  - Keep `test_edit_submit_after_expiry_still_previews` (DD-6) passing unchanged: expiry is not filing.
  - Run `.venv/bin/pytest tests/test_intake.py -q`; confirm it fails (an ImportError of `ALREADY_FILED_REPLY` at collection is the expected red).
- [x] Green, in `issue_bot/intake.py`:
  - Add the fixed text `ALREADY_FILED_REPLY = "This report was already filed, so nothing more was posted. Check the channel for its link."` with the other replies.
  - Add `@dataclass class Report:` (docstring "One intake session: a fresh submit and every preview its Edits open. ``filed`` is set at the first **File** press, so the session files once (F12); it marks the press, not a successful filing, so a File whose summary post failed still ends the session.") with `filed: bool = False`, near `Draft`.
  - `PreviewView.__init__` gains a trailing `report: Report | None = None` and sets `self.report = report if report is not None else Report()`; in the class docstring say **File** files the report once across every preview sharing its ``report``.
  - Extend the module docstring: previews of one report share a ``Report``, so once one is filed a second **File** or an Edit submit gets ``ALREADY_FILED_REPLY``.
  - `file_button`: after `if self._closed: return`, add, with no await before the flag changes:
    ```python
    if self.report.filed:
        self._closed = True
        self.stop()
        logger.info("refused second file %s interaction_id=%s", self.issue_type, interaction.id)
        await interaction.response.edit_message(content=ALREADY_FILED_REPLY, view=None)
        return
    self.report.filed = True
    ```
    keeping the existing `_closed = True; self.stop()` and comment.
  - `on_timeout`: `if self._closed or self.report.filed: return` (a sibling preview filed the report, so "nothing was filed" would be false).
  - `IntakeModal.on_submit`: first thing, before the fresh-submit defer and the blank-title check, add `if self.preview is not None and self.preview.report.filed:` → log `refused edit of filed %s interaction_id=%s`, `await interaction.response.edit_message(content=ALREADY_FILED_REPLY, view=None)`, `return`. Pass `report=self.preview.report if self.preview is not None else None` to the new `PreviewView(...)`.
  - Run `.venv/bin/pytest -q`; all pass.
- [x] Refactor: confirm no new log line carries member text (`grep -n 'logger\.' issue_bot/intake.py issue_bot/issues.py issue_bot/github.py` and read the new ones); `grep -rnE '1137236302358659185|969373970|chores4irl|c4i-github-issues' --include='*.py' issue_bot` prints nothing. COMPLETE (2026-11-01): 5 new tests red (ImportError of `ALREADY_FILED_REPLY` at collection) then green; full suite 531 passed; the two new log lines carry type and interaction id only; invariant grep prints nothing; review fix: rewrapped the `PreviewView` docstring.

### 5. Docs
Record the new behaviour where members and operators read it.

**To-do:**
- [x] `README.md` *Known limits*: replace "No retry or dedup until Phase 4, so a timeout can leave an issue filed after an error reply." with "No automatic retry until F13: a timeout can leave an issue filed after an error reply. Before filing, the bot looks for an issue already linking the same summary message among the repo's 100 newest issues and pull requests, so F13's automatic retry will reuse it rather than file again; running the command again is a new report, so check the repo first." Replace the F3 bullet ("A reporter who presses **File** in one Discord client while an **Edit** form is open …") with "A report is filed once: after **File**, an **Edit** submitted from another Discord client, or **File** on another preview of the same report, gets \"This report was already filed\" instead. This holds within one bot process; a restart drops open previews anyway." In *Reporting* step 3, after "files the report, once.", add: "Once a report is filed, **File** on another of its previews, or an **Edit** submitted afterwards, shows \"This report was already filed\" instead." Add "F12 (each report filed once)" to the intro sentence listing the features that exist.
- [x] `docs/SMOKE-TEST.md`: add a troubleshooting row for the log line `could not look up an existing issue for … stage=lookup status=…` (or `stage=token`, when the installation token itself failed; the create that follows then fails too): the bot filed anyway (DD-3); a 403/404 means the token can't read issues in that repo (Issues: write covers reading); once F13 retries filings, a retry would not be deduplicated while the lookup fails. Leave the existing "rather than re-running, which files a second issue" wording (a rerun is a new report). In §2 *Local run* step 1, add that the log shows no `could not look up an existing issue` WARNING for that filing: this run is what proves the Issues: write token can list the repo's issues (pass1-DD-1).
- [x] `docs/SMOKE-TEST.md` §2: append step 7: "Run `/bug`, submit, press **Edit** in one Discord client and **File** in another, then submit the Edit. The preview shows \"This report was already filed, so nothing more was posted. Check the channel for its link.\", one issue is filed, and the log shows `refused edit of filed bug …`." In § *What it writes*, change the Success checks bullet's "two issues in the scratch repo (three with the optional `@someone` check)" to "three issues in the scratch repo (four with the optional `@someone` check)"; the refused Edit writes nothing more. (pass1-DD-7)
- [x] Run `grep -n 'dedup\|twice\|second issue' README.md docs/*.md` and confirm no stale claim remains (expected matches: the SMOKE-TEST troubleshooting rows saying re-running files a second issue, and the new lookup row's "deduplicated"; any README.md match is stale). COMPLETE (2026-11-01): grep shows only the expected SMOKE-TEST re-run rows and the new row's "deduplicated"; no README match. Review fixes: README says the refusal follows a **File** press even when that filing failed (pass1-DD-3), and that a failed lookup is a WARNING then filing; the lookup row says `stage=token` most likely fails the create, a 401's token is refetched for this filing's create, other statuses are GitHub-side errors, and only after `stage=lookup` is the issue filed normally. Suite 531 passed.

### 6. Verify All Tests Pass

Run the full test suites to confirm nothing is broken:

**To-do:**
- [ ] Run `.venv/bin/pytest` and confirm all tests pass, the new Step 1-4 tests included
- [ ] Re-check Standing invariants: invariant 1's grep prints nothing; every new `logger.` call logs only type, ids, URLs, error type, stage and status
- [ ] Investigate and fix any failures before marking the plan finished

## Manual checks (for the user, not boxes)
- Live: with the user's go-ahead only (CLAUDE.md), in a test channel open `/bug`, press **Edit** in one client, **File** in another, then submit the Edit: the preview shows "This report was already filed" and one issue exists, and the log shows no `could not look up an existing issue` WARNING (live evidence the list call works, pass1-DD-1). It writes one summary message and thread in the test channel and one issue (plus a Project item on a Project route) in the test route's repo; close the issue and remove its test-Project item afterwards (SMOKE-TEST §5); a first filing with a band also creates that `complexity:<band>` label if the repo lacks it. The GitHub reuse path itself is covered by tests only.

- [ ] Copy the "Manual checks" bullets verbatim into the final report.

## Status
finished: false
