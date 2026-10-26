# Push Review: feature/clarifying-questions

## Review 1
Generated: 2026-10-26 10:12
Comparison: origin/main d70159bf701d7db926a8606e86d7468c3c2528da..b34a1e00409863462362b805ba1561e502726b5c
Verdict: **PUSHED WITH MINOR FINDINGS**

### Results by Reviewer

#### 1. Safety & Security — PASS
No secrets, and mentions are defanged and suppressed in both the preview and the issue body. The single-file guard prevents double filing. New log lines carry only the issue type, ids and the Discord status/code.

#### 2. Correctness — PASS
No logic errors in config validation, modal prefill, the preview/File/Edit/expiry flow, or body rendering. The reviewer checked the discord.py 2.7.1 timeout setter and `edit_message` on a modal submit against the source. README, SMOKE-TEST.md and CLAUDE.md match the code.

#### 3. Simplicity & Conciseness — PASS
No dead code or over-engineering. Minor notes:
- the close-and-stop pair is repeated in three places;
- `on_submit` branches on `self.preview is None` three times;
- the "could not send reply" log block is duplicated;
- `TargetConfig.__post_init__` re-validates what `_route_questions` already checked;
- the style check builds a set on every call.

#### 4. Test Coverage — PASS
New behaviour is covered with behavioural assertions. One gap: no test presses File on the superseded preview after a successful Edit submit.

#### 5. Completeness & Cleanup — PASS
No debug code, TODOs or stubs. Minor notes: the `public/` gitignore entry is unrelated to F3 (the owner asked for it at session start); `IntakeModal.on_submit` touches `PreviewView`'s private `_closed` and calls its `stop()`.

#### 6. Consistency & Style — PASS
The code follows the project's conventions. One minor note: a test comprehension uses the single-letter name `t`.

#### 7. Integration Risk — PASS
The breaking route-file change is validated at startup (exit 2) and documented. All callers of the changed signatures are updated. Minor notes: `_keep_deadline` relies on discord.py 2.7.1 internals, which the exact pin covers; the `IssueCandidate.body` → `answers` change is a shared-interface change.

#### 8. Error Handling & Silent Failures — PASS
No silent failures, and the broad catches log only the type and ids. Minor notes:
- a failed first preview send leaves the reporter with no reply;
- `previewed` is logged before the send or edit lands;
- a click on a closed preview neither answers nor logs;
- `TargetConfig.__post_init__` uses one generic message for several failures.

#### 9. Type Design — PASS
Sound, with minor notes:
- the close-once invariant is split across two classes;
- `Question`'s invariants are enforced only in the loader;
- the (label, answer) tuples are positional and implicit.

### To-Do: Required Changes

- [ ] **Add a `PreviewView.close()` method** — `issue_bot/intake.py` — Fold `self._closed = True; self.stop()` into one method. Call it from `file_button`, `on_timeout` and `IntakeModal.on_submit`'s edit path, so no other class sets `_closed` directly (Simplicity, Completeness, Type Design).
- [ ] **Split `IntakeModal.on_submit` into fresh and edit helpers** — `issue_bot/intake.py` — Move the three `self.preview is None` branches into `_submit_fresh` / `_submit_edit` (Simplicity).
- [ ] **Reuse one helper for the "could not send … reply" log** — `issue_bot/intake.py` — Factor the shared HTTPException logging used by `_reply`, `_report_error` and the preview send (Simplicity).
- [ ] **Tell the reporter when the first preview send fails** — `issue_bot/intake.py` `IntakeModal.on_submit` — After logging the HTTPException, try `_reply(INTAKE_ERROR_REPLY)`, so the deferred "thinking" state doesn't just time out (Error Handling).
- [ ] **Log `previewed` only after the send or edit succeeds** — `issue_bot/intake.py` — Move the log line after `followup.send` / `edit_message` (Error Handling).
- [ ] **Answer a click on a closed preview** — `issue_bot/intake.py` `file_button`/`edit_button` — Optionally reply privately with fixed text, or log the ignored click by type and ids, instead of returning silently (Error Handling).
- [ ] **Test that the superseded preview's File does nothing after an Edit submit** — `tests/test_intake.py` — After a successful edit submit, press the old view's `file_button` and assert the hook is not awaited (Test Coverage).
- [ ] **Rename the single-letter comprehension variable** — `tests/test_config.py` — Change `{t.value for t in IssueType}` to `issue_type` (Consistency).
- [ ] **Decide where `Question` invariants live** — `issue_bot/config.py` — Either validate label length and uniqueness and the style type in `Question`/`TargetConfig.__post_init__`, or document that only the loader enforces them. Drop the double validation, or keep it on purpose (Type Design, Simplicity, Error Handling).
- [ ] **Precompute the style value set** — `issue_bot/config.py` — Use a module constant, or a try of `QuestionStyle(style)`, instead of building `{member.value …}` on every call (Simplicity).
