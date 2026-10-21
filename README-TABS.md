# Phase 4: panel-controlling tabs and accordion headers

    python -m pytest tests -q
    RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser_tabs.py -q

Expected offline suite: 237 passed, seven opt-in browser tests skipped. The second
command runs two local Chromium tests with no model/API calls: activate the tab
named in the visible goal, and expand an accordion then submit. Those tests use
native widget state and the full-credit terminal metric. They were not run during
preparation; the user performs them before live autonomous validation.

After both browser checks pass:

    python -m browser_agent --task click-tab --seed 61 --max-steps 2

Expected: activate_tab then benchmark success, normally one action/API call.
The budget remains a ceiling, not a requirement to use every action.

Later autonomous accordion check:

    python -m browser_agent --task click-collapsible --seed 61 --max-steps 4

Expected: activate_tab on the Section header, observe expanded state, click the
actual Submit button. Both use development seed 61, not reserved final instances.
Failures must be retained rather than retried until a good outcome is obtained.

## Scope and validation

The existing action object gains activate_tab; text and checked must be null.
Eligible IDs must have the AX role tab AND a controls property. Arbitrary links,
link-styled spans, tabpanel/tablist containers and generic nodes are excluded.
The observed accordion task assigns an extra tab role to a Submit wrapper with
no controlled panel; that wrapper is not eligible. The real Submit button remains
a normal click target. Other action schemas and roles are unchanged.

Before executing, fixed mapping checks that the element has DOM role tab,
a tablist ancestor, a nonempty aria-controls, and an existing associated panel.
For a jQuery tab with exactly one a.ui-tabs-anchor descendant, it checks that the
anchor href matches that panel fragment, then clicks that scoped anchor. For an
accordion header with no such anchor, it clicks the header itself. Multiple
anchors or a mismatched panel link are errors. This deterministic widget adapter
is identical for both agents; it does not choose the correct target, translate a
stale ID, expose hidden target answers or permit arbitrary navigation.

The helper/catalogue and native guards reject incompatible controls; a legitimate
new tab widget lacking the expected semantics is currently unsupported, not an
excuse to click a generic node. Current targets are local allowlisted benchmark
pages only. Recovery remains fill-only; tab errors stop safely.

Both model prompts and legal-target catalogues include activate_tab. The iterative
workflow refreshes targets after opening a panel; the one-shot executor checks
its fixed plan against current observations without replanning. Same budgets,
full-credit metric and SDK controls remain. Prompt/catalogue changes mean future
comparisons should use these versions in BOTH arms, with source hashes retained.

## Task exposure

The CLI/evaluator task list provisionally adds click-tab and click-collapsible
for development validation. Existing default evaluation tasks remain unchanged.
The protocol manifest remains a draft; no task is silently marked live-verified
or promoted to the final set by this code change. The harder collapsible-2 and
tab-2 variants are not added until their clickable spans are handled separately.

## Verification and files

237 offline tests passed: prior 225 plus twelve cases covering panel-role
eligibility, wrong roles/arguments, fixed mapping, new-observation routing and
strict SDK schema. Seven total browser tests are opt-in, including two added here.
No browser episodes or model requests were run during preparation.

Updated: actions.py, workflow.py, model.py, oneshot.py, evaluate.py and __main__.py.
Added: tests/test_tabs.py, tests/test_browser_tabs.py and this document.
No budget, metric, dependency, credential, vendor or generic-span permission
changes. Next: user-run browser checks and development episodes, then a separate
narrow clickable-span implementation required by the audited task set.
