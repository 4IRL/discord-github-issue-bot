# Push Review: feature/complexity-triage

## Review 1
Generated: 2026-10-27 18:48
Comparison: origin/main 64b37eab624250b497d3c8ac116fa9e49a69899b..1bfa93181942c4edb8af392e780e193f54af68c7
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No security issues. The label name is fixed text built from the enum and sent in a JSON body. No secrets were added. The new log lines carry only the type, ids, stage and status, and the band buttons log nothing.

#### 2. Correctness — PASS
No logic errors: `rate()` caps at XL, StrEnum formatting is right, the button wiring in `View.__init__` works, overrides persist across Edit, and the label falls back as designed.

#### 3. Simplicity & Conciseness — PASS
- minor: the four S/M/L/XL callbacks and the hand-built `_band_buttons` dict repeat one shape (`issue_bot/intake.py`). A loop is optional; the decorator style matches File/Edit.
- minor: `file_candidate` indexes the label list by position (`labels[1]`, `labels[:1]`) (`issue_bot/issues.py`).
- minor: `rate()` sums two booleans and builds `list(Complexity)` on every call (`issue_bot/complexity.py`).

#### 4. Test Coverage — PASS
- minor: no single test runs press L → Edit-submit → File and checks that `complexity:L` is filed. The two halves are tested separately.
- minor: the `ensure_label` raise test covers 500 only, not 403/404, so the (201, 422) success set isn't pinned.

#### 5. Completeness & Cleanup — PASS
- minor: `docs/COMPLEXITY.md`'s Points column (1/2/3/5) is never explained, and no code uses it.

#### 6. Consistency & Style — PASS
- minor: positional label indexing in `file_candidate` (same as #3).
- minor: the boolean sum in `rate()` (same as #3).

#### 7. Integration Risk — PASS
- minor: positional label indexing would silently target the wrong label if `issue_labels` grows (e.g. F6).
- minor: every 422 is cached as "already exists". This is accepted and documented (plan review DD-3); optionally check `already_exists` later.

#### 8. Error Handling & Silent Failures — PASS
Matches the owner-approved plan: a typed `GitHubError("label", …)`, a non-fatal WARNING fallback, and no response text in errors.

#### 9. Type Design — PASS
- minor: `Draft`'s invariant (when not overridden, complexity equals suggested) is held only by its two construction sites.
- minor: nothing guarantees `STARTING_BAND` covers every `IssueType`; a new type would raise KeyError in `rate()`.

### To-Do: Required Changes

- [ ] **Replace positional label indexing in `file_candidate`** — `issue_bot/issues.py` — compute `type_label = candidate.target.labels[candidate.type]` and `band_label = complexity_label(candidate.complexity)`, call `ensure_label(candidate.target, band_label)`, and file `[type_label, band_label]`, or `[type_label]` on `GitHubError`. Keep `issue_labels` as the one formatter for the full list.
- [ ] **Add an end-to-end override → Edit → File test** — `tests/test_intake.py` — press L, Edit-submit with new answers, press File, and assert `create_issue` got labels ending `"complexity:L"`.
- [ ] **Parametrize the `ensure_label` raise test over 403, 404 and 500** — `tests/test_github.py`.
- [ ] **Explain or drop the Points column** — `docs/COMPLEXITY.md` — say the points are the effort weights used for planning (S=1, M=2, L=3, XL=5), or remove the column.
- [ ] **Pin `STARTING_BAND` coverage** — `tests/test_complexity.py` — assert `set(STARTING_BAND) == set(IssueType)`.
- [ ] **Make `rate()`'s step count explicit** — `issue_bot/complexity.py` — e.g. a module-level `BANDS = tuple(Complexity)` and `sum(length >= limit for limit in (RAISE_ONE_AT, RAISE_TWO_AT))`. Optional readability change.
- [ ] **Decide whether to loop-build the band buttons** — `issue_bot/intake.py` — optional; keep the decorators if they stay consistent with File/Edit.
- [ ] **Optionally guard `Draft`'s not-overridden invariant** — `issue_bot/intake.py` — a `__post_init__` check that `overridden or complexity == suggested`.
