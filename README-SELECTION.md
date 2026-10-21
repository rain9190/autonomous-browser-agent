# Phase 4: validated native selection actions

The two development audits exposed native checkbox/radio/combobox roles and
options. Full-credit scoring is installed. This update adds only the selection
support required for those tasks, not tabs, arbitrary links, navigation or a new
budget policy.

## First verification

    python -m pytest tests -q
    RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser_selection.py -q

Expected offline suite: 211 passed, five browser checks skipped. The second
command should pass three real Chromium plumbing checks, without model calls
or submissions. They verify setting a checkbox twice does not toggle it, it can
be explicitly unset, radio setting is idempotent and exclusive within its group,
and native dropdown selection by exact observed label works repeatedly.

Only after these pass, run a single development episode:

    python -m browser_agent --task choose-list --seed 61 --max-steps 2

Expected: select the requested option (unless already selected), then Submit,
with full-credit reward 1.0 and at most two API calls. Do not run reserved final
seeds. Failed episodes remain data, not reasons to select easier seeds.

## Actions

All action objects have action, bid, nullable text and nullable checked.
Structured API output requires every field; internal backward-compatible click/
fill payloads may omit nullable fields. Extra fields and wrong types are rejected.

- click: observed button; text=null and checked=null.
- fill: observed textbox; nonempty text at most 256 chars; checked=null.
- set_checked: observed checkbox; checked is a strict boolean; text=null.
- check_radio: observed radio; text=null and checked=null; no unchecked radio action.
- select_option: observed combobox; text is an exact, unique option label listed
  under that combobox in the current accessibility tree; checked=null.

Dropdown labels are read from AX option strings with literal-only parsing (no
execution). Child options are scoped by indentation; a label in another select
or a duplicate label is rejected. This label-based implementation deliberately
rejects ambiguous labels instead of guessing option values. Native select labels
are shown in observations; hidden task ground truth is not consulted.

Selection mapping also checks native element type before using fixed Playwright
set_checked/check/select_option methods. Only quoted ID/text literals and a
validated boolean vary. A custom ARIA combobox is not automatically supported;
select_option currently requires a native single-select HTML SELECT. Existing
click/fill mappings are unchanged. Selection does not widen the click role set.

The iterative graph validates against fresh observations; the one-shot executor
validates the fixed next plan action against current observations without
replanning. Both use the same schema, role/label checks and full-credit metric.
Prompts explain nullable fields and idempotent selection; model and API settings
are unchanged. Recovery remains limited to eligible fill errors.

## Provisional development task exposure

The CLIs/runner task list now includes choose-list, click-option and
click-checkboxes-soft for development validation. They are not counted as
live-verified supported tasks until episodes are checked. Their protocol statuses
remain candidate. The manifest is intentionally not silently promoted or frozen.
Current six-action limits are unchanged. click-checkboxes (ordinary, not soft)
can need seven actions and is NOT added to the agent CLI in this update, though
its registered native-control environment is used by the no-API plumbing test.

Existing five task families and default evaluation tasks are unchanged. Normal
checkbox support under a reviewed seven-action policy, tab-role clicks and
narrow clickable-span observations remain follow-up work. Do not claim the full
20-task plan is implemented by adding these three development task IDs.

## Verification status and files

211 offline tests passed: all previous 188 plus 23 selection cases. They cover
schema null/type rules, role mismatch, scoped/duplicate dropdown labels, literal
quoting, native guards, idempotent method selection, graph select/submit flow and
strict SDK schema generation. Five real-browser checks are opt-in; none were run
while preparing this update. No API calls were made during preparation.

Updated: actions.py, workflow.py, model.py, oneshot.py, evaluate.py and __main__.py.
Added: tests/test_selection.py, tests/test_browser_selection.py and this document.
No metrics, budgets, credentials, dependencies or vendor files are changed.
