# Development selection failure: explicit legal-target catalogue

Seed-67 click-option failed validation twice, with category observed_role_mismatch.
The saved observation contains the requested native radio and a Submit button,
and selection_targets extracts the radio correctly. The failed action itself was
not retained, so its exact action/ID combination and cause are not established.
Do not claim these failed development attempts were fixed or passed retroactively.

The update supplies both iterative and one-shot models with allowed_targets,
a bounded catalogue computed from the SAME already-visible accessibility tree.
It lists legal IDs separately for click, fill, set_checked and check_radio, plus
unambiguous observed dropdown labels per combobox. LabelText parents, generic
nodes and unavailable controls do not become actionable. No task answer or ground
truth is added, and no wrong action is automatically translated to a valid one.
The prompts explicitly tell the model to use the catalogue for action/ID choice.
Existing role validation remains unchanged in strength. A mismatch still stops.

Both model arms receive the same helper. This changes their prompts and token
usage, so future comparisons must use the new versions in both arms; preserve
previous measured results as historical evidence with their source hashes.
The catalogue is capped at 8,000 serialized characters in addition to existing
input bounds, before a request is made. Model, output budgets, retries and action
permissions are unchanged. No API calls were made during preparation.

If a mismatch recurs, diagnostics can now report only requested_action, target_bid
and recognized observed target roles, rather than raw model output, field values,
page text or exception bodies. The failed-run artifact remains uniquely named.
Unknown IDs have an empty recognized-role list. This diagnostic data cannot
reconstruct the previously discarded proposals.

    python -m pytest tests -q
    python -m browser_agent --task click-option --seed 67 --max-steps 3

Expected offline suite: 225 passed, five opt-in browser checks skipped. The live
command is a single DEVELOPMENT diagnostic retry with at most three calls, not
an unreported replacement for the earlier failures. If it passes, record the
changed prompt configuration and prior failures; if it fails, inspect the safe
mismatch metadata. Do not retry repeatedly until success or use final seeds.

The checkbox command previously ended with 6~ and never ran. When returning to
that task, use --max-steps 6 without the trailing tilde, one command at a time.

Added seven tests for catalogue roles, ambiguous labels, strong role rejection,
shared model input and catalogue size limits. Existing 218 checks remain passing.
Files changed: actions.py, model.py, oneshot.py, diagnostics.py. Added
 tests/test_action_catalog.py and this README. No dependencies, budgets, task
allowlists, benchmark assets or reserved-final protocol changed.
