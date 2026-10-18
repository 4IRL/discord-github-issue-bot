# Push Review: feature/channel-listener

## Review 1
Generated: 2026-10-17 20:13
Comparison: origin/main 9f6ffa330ef6ae462aa235f4eb1b2f234de62a39..f59d3a5e53a1d14b4815d7b388d94926d760e1b7
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No secrets, injection or unsafe operations. The token is hidden from repr, config errors never echo values, GITHUB_REPO is validated, on_error and the default hook keep member text out of logs, and the Docker image runs non-root with secrets excluded.

#### 2. Correctness — PASS
- (minor) `issue_bot/bot.py` on_ready: fires again after Gateway reconnects, so the "startup" channel check and "connected as" log repeat on each reconnect.

#### 3. Simplicity & Conciseness — PASS
- (minor) `issue_bot/config.py`: from_env locals passed straight to the constructor could be inlined.
- (minor) `issue_bot/config.py` _positive_int: the try/except ValueError is only reachable for Python's >4300-digit int limit; merge or comment it.
- (minor) `issue_bot/bot.py`: the CandidateHook indirection has one implementation (justified by F2/F5).

#### 4. Test Coverage — PASS
- (minor) No end-to-end test that a raising hook dispatched through discord's `_run_event` is logged by on_error without member text.
- (minor) Padded numeric IDs (`" 123 "`) and `x/..` / `../x` repo rejection are not asserted explicitly.

#### 5. Completeness & Cleanup — PASS
- (minor) `plans/META-PLAN.md` "Where the work stands" still says "Nothing is built yet" (fixed at the F1 fold-back).

#### 6. Consistency & Style — PASS
- (minor) Only `config.py` uses `from __future__ import annotations`.
- (minor) `issue_bot/tags.py` puts constants after the classes; IssueType/ParsedTag lack docstrings.
- (minor) `log_candidate`'s unused `message` parameter could be `_message`.

#### 7. Integration Risk — PASS
Greenfield bot with no existing callers. Env keys are documented, dependencies pinned, Dockerfile and .dockerignore consistent.

#### 8. Error Handling & Silent Failures — PASS
- (minor) on_error's line carries no message id, so a failed capture can't be tied to its Discord message (an id is not member text).
- (minor) A missing intake channel at startup is only a WARNING. Consider ERROR, since the bot can't work in that state.

#### 9. Type Design — PASS
- (minor) TargetConfig invariants (a label per IssueType, read-only labels, owner/name repo) are enforced only in from_env, not in __post_init__.
- (minor) ParsedTag's non-empty-alphanumeric title invariant is enforced only by parse_tag.

### To-Do: Required Changes

- [ ] **Run the startup channel check once** — `issue_bot/bot.py` — Guard on_ready's channel_problems check and "connected as" log with a once-flag (or move to setup_hook-time state) so Gateway reconnects don't repeat it; add a test calling on_ready twice.
- [ ] **Escalate a missing intake channel to ERROR** — `issue_bot/bot.py` channel_problems/on_ready, `tests/test_bot.py` — Log the "not found or not visible" problem at ERROR (name/category/guild mismatches stay WARNING); update the on_ready test.
- [ ] **Add the message id to on_error for on_message** — `issue_bot/bot.py` on_error, `tests/test_bot.py` — When `args[0]` has an integer `id`, append `message_id=<id>`; keep no traceback/message/text. Test it.
- [ ] **Test a raising hook through discord dispatch** — `tests/test_bot.py` — Run a hook raising `RuntimeError("Secret title words")` via `await bot._run_event(bot.on_message, "on_message", msg)`; assert one ERROR from `issue_bot.bot` and no record containing the text.
- [ ] **Assert padded IDs and dot-segment repos** — `tests/test_config.py` — Add cases: `DISCORD_CHANNEL_ID=" 555 "` parses to 555; `GITHUB_REPO` `"x/.."` and `"../x"` raise `GITHUB_REPO must be owner/name` (if not already parametrized).
- [ ] **Enforce TargetConfig invariants at construction** — `issue_bot/config.py` — Add `__post_init__` checking `set(labels) == set(IssueType)` and wrapping labels in `MappingProxyType` (via object.__setattr__); add a test constructing TargetConfig directly with a missing label.
- [ ] **Simplify _positive_int** — `issue_bot/config.py` — Merge the regex and ValueError paths into one "must be an integer" branch, or add a one-line comment on why the try/except stays (int digit limit).
- [ ] **Inline from_env locals** — `issue_bot/config.py` — Pass simple lookups directly into the `cls(...)` calls; keep the validated github_repo local.
- [ ] **Align module layout** — `issue_bot/tags.py` — Move TAG_PATTERN/EMPTY_BRACKETS/TITLE_EDGE above the classes and add one-line docstrings to IssueType and ParsedTag.
- [ ] **Signal the unused hook parameter** — `issue_bot/bot.py` log_candidate — Rename `message` to `_message`.
- [ ] **Refresh META-PLAN's "Nothing is built yet"** — `plans/META-PLAN.md` — Reword "Where the work stands" during the F1 fold-back (Phase C).

## Review 2
Generated: 2026-10-17 21:31
Comparison: origin/feature/channel-listener 3b21695d6386fd8fe4fc10d4b46f3b192ecae5ea..e8db4ecf76b91835c15e411fee73fb1fd51935cf
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
The malformed-message log carries only issue type, message id and URL; `IssueCandidate` keeps title/body/content/author_name repr-hidden; the new regexes are linear on Discord-sized input. No findings.

#### 2. Correctness — PASS
Parser logic is sound for CRLF, bolded or case-varied labels, `Titles:`/`Body text` non-labels, bracketed and repeated tags.
- (minor) `issue_bot/tags.py:63` — the first label wins even when empty: `!bug\nTitle:\nTitle: real` is malformed; an empty first `Body:` shadows a later one.
- (minor) `README.md:46` / `issue_bot/tags.py:6` — "or to a later `Title:` line" is only true when Body comes before Title; after Title, a repeated `Title:` stays body text.
- (minor) `plans/feature/channel-listener/channel-listener.md:227` — amendment example `[#bug]` is stale; other Design-section `#bug` text too.
- (minor) `issue_bot/tags.py:71` — a tag removed from the start of a body line leaves a leading space, and a tag-only body line leaves a blank line.

#### 3. Simplicity & Conciseness — PASS
- (minor) `issue_bot/tags.py:57` — `fields` dict of lists plus the `body_lines` alias is indirection for a one-line title; keep title as a str and body as a list.
- (minor) `issue_bot/tags.py:62` — `name = ... if label else None` then `label is not None and ...` double-checks.
- (minor) `issue_bot/tags.py:39` — `BRACKETED_TAG` interpolates `TAG_PATTERN.pattern` four times; one optional-bracket regex would read better.

#### 4. Test Coverage — PASS
- (minor) `tests/test_bot.py` — no bot-level test that a malformed tagged message never reaches `on_candidate`.
- (minor) `tests/test_tags.py` — no CRLF case or tag-only line inside a multi-line Body.

#### 5. Completeness & Cleanup — PASS
- (minor) `plans/feature/channel-listener/channel-listener.md` — `[#bug]` in the amendment; overview (line 6) and env table (95-96) still say `#bug`/`#feature`.
- (minor) `issue_bot/tags.py:6` — docstring Body-termination wording (see Correctness).

#### 6. Consistency & Style — PASS
- (minor) `plans/feature/channel-listener/channel-listener.md` — stale `[#bug]` example; the edited Modules and IssueCandidate contract bullets exceed the ~90-column wrap.

#### 7. Integration Risk — PASS
No code callers broken (handler.py is the only `parse_tag`/`IssueCandidate` consumer); no env or dependency changes.
- (minor) Contract says F2 replies to malformed messages, but `candidate_from_message` returns `None` and `IssueBot` exposes no malformed hook, so F2 must extend F1's handler/bot API; neither the contract nor META-PLAN F2 says so.
- (minor) F1 plan Design section is stale against the amended contract: tags.py row (line 77) lists `ParsedTag(type, title)` and `ParsedTag | None`, IssueCandidate list (~142) has eight fields and says F5 uses raw `content` for the body.

#### 8. Error Handling & Silent Failures — PASS
No swallowed errors; the drop is logged ids-only and its user hint is deferred to F2.
- (minor) `issue_bot/handler.py` — log says "no Title: line" but also fires for an empty or symbol-only title; say "no usable Title: line".

#### 9. Type Design — PASS
Frozen DTOs, a union that forces callers to handle the malformed case, title invariant enforced at the only construction site. No findings.

### To-Do: Required Changes

- [x] **Let an empty first label yield to a later filled one** — `issue_bot/tags.py` `parse_tag` — When the first `Title:` (or `Body:`) is blank, let a later same-named label replace it (or document first-label-wins in README "Message format"); add a test for `!bug\nTitle:\nTitle: real`.
- [x] **Fix the Body-termination wording** — `issue_bot/tags.py` module docstring, `README.md` "Message format", plan amendment — Say Body runs to the end of the message, or, when Body comes before Title, to the `Title:` line.
- [x] **Trim tag-removal whitespace in Body** — `issue_bot/tags.py` — lstrip a body line only when tag removal changed it, and drop a body line that held only a tag; add CRLF and tag-only-body-line cases to `tests/test_tags.py`.
- [x] **Simplify parse_tag's field tracking** — `issue_bot/tags.py` — Keep `title: str | None` and `body_lines: list[str] | None` instead of the `fields` dict and alias; drop the `name = ... else None` double check. Applied as `title: str`, `body_lines: list[str]` and an `in_body` flag (a late `Title:` ends the Body without discarding it, so collecting and holding text are separate).
- [x] **Simplify BRACKETED_TAG** — `issue_bot/tags.py` — Use one regex with an optional bracket pair around the tag instead of four interpolations.
- [x] **Add a bot-level malformed test** — `tests/test_bot.py` — `on_message(make_message("!bug\nBody: x"))` with a recording hook; assert the hook is not awaited.
- [x] **Say "no usable Title: line" in the drop log** — `issue_bot/handler.py`, `tests/test_handler.py`, plan contract — Match the MalformedTag docstring.
- [ ] **Bring the F1 plan's Design section up to date** — `plans/feature/channel-listener/channel-listener.md` — `[#bug]`→`[!bug]` in the amendment; `!bug`/`!feature` in the overview (line 6) and env table (95-96); tags.py row (77) to `ParsedTag(type, title, body)`, `MalformedTag`, `ParsedTag | MalformedTag | None`; IssueCandidate list (~142) to nine fields with F5 using `body`; re-wrap the long contract bullets.
- [ ] **State that F2 must expose malformed messages** — `plans/feature/channel-listener/channel-listener.md` contract and `plans/META-PLAN.md` F2 section — Note F2 extends `candidate_from_message`/`IssueBot` (e.g. a malformed-message hook) because F1 only logs the drop.

6b: 0 misses (every finding sits in lines this push introduced or in text made stale by it; none existed at Review 1's head).

## Review 3
Generated: 2026-10-17 21:35
Comparison: origin/feature/channel-listener d54b76ab19f24749ad72d8c2b16af158be3fa797..890ae89904dd02a1740b1d4a5cc3a6218528fc81
Verdict: **PUSHED WITH MINOR FINDINGS**
Mode: docs-only

### Results by Reviewer

#### 2. Correctness — PASS
The F9 ★FOCUS change is consistent: FOCUS is marked in all five places, the effort tally of 19 matches, dependency cells follow the grammar and the owner-step claims agree.
- minor: `plans/META-PLAN.md` F1 Open risks (e) is stale. It says the F1 plan uses `c4i_issue_bot/` and `DEFAULT_*` constants, but F1 shipped `issue_bot`.
- minor: `plans/META-PLAN.md` dependency diagram: the Phase 1.5 row's "(independent of each other)" is ambiguous now that F9 also has a Focus row.
- minor: `plans/ROADMAP.md` Phase 1.5 sequencing still says it depends on Phase 1 hard, while F9 now runs after F1 only. F9's end state already commits to the note, so this is transient.

#### 5. Completeness & Cleanup — PASS
The re-ranking is consistent across sections. Only minor stale or wording items remain.
- minor: `plans/META-PLAN.md` F1 Open risks (e) is stale (same as Correctness).
- minor: `plans/META-PLAN.md` Where the work stands: "F6 is additionally gated" no longer follows another gate.
- minor: `plans/META-PLAN.md` Baseline still describes `main` as the scaffold. That is correct until F1 merges, then it must be refreshed at fold-back.

### To-Do: Required Changes

- [ ] **Mark F1 Open risks (e) resolved** — `plans/META-PLAN.md` F1 section — Say the plan was revised and F1 shipped the `issue_bot` package with no target defaults, or drop the item at F1's fold-back.
- [ ] **Clarify the diagram's independence note** — `plans/META-PLAN.md` "Dependencies & couplings" diagram — Change "(independent of each other)" to "(F8 and F9 independent of each other)", or drop the duplicate `F1 ──► ★ F9` edge from the Phase 1.5 row.
- [ ] **Drop "additionally" from the F6 gate sentence** — `plans/META-PLAN.md` "Where the work stands" — "F6 is gated on creating the new chores4irl roadmap Project."
- [ ] **Refresh the Baseline at F1's fold-back** — `plans/META-PLAN.md` Baseline — Describe `main` with F1's package, config, parser, handler, Dockerfile and tests once PR #2 merges.
- [ ] **Add the ROADMAP sequencing note during F9** — `plans/ROADMAP.md` Sequencing rationale — Note that the rename (Phase 1.5) went ahead of the rest of Phase 1, as F9's expected end state requires.

6b: 0 misses (the F1 risk (e) text and the ROADMAP Phase 1.5 sequencing sentence were not in Review 2's diff; the other findings are in lines this push introduced).
