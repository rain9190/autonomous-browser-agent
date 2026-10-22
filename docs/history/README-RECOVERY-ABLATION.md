# Phase 4: matched recovery-on/off ablation

## Project purpose

One-shot and iterative agents both solved the six initial simple matched
instances; iterative used additional calls/time. The next research question is
whether bounded recovery improves success when a browser action fails. This
experiment changes the recovery allowance in the SAME iterative agent instead
of comparing different planners or unrelated failure runs.

    python -m pytest tests -q
    python -m browser_agent.ablate_recovery --task enter-text --seeds 31 47 --max-steps 3 --scenario disabled_textbox_timeout

Expected tests: 148 passed, two opt-in browser checks skipped. The live command
runs two pairs (four episodes), with equal three-action and three-call ceilings
for each arm: at most twelve API calls total. Recovery_off deliberately stops
after the first reported fill failure; recovery_on may take a fresh observation,
retry the fill, then submit. Successful recovery would normally use three calls
against off's one, but those outcomes must be measured, not assumed.

A browser_action_error from recovery_off is an EXPECTED experimental outcome,
not a reason to repair it or selectively rerun it. All benchmark outcomes are
kept. Completion of the experiment does not require both arms to succeed.

## Fixed protocol

Both arms use ModelAdapter and the same LangGraph workflow, model snapshot,
local MiniWoB assets, seed, action schema/mapping and all step/call/input/output/
time limits. Both receive the same controlled failure scenario on their first
fill. Their maximum allowance is the same; actual use may differ because the
no-recovery system stops early. max_recoveries=0 versus 1 is the intervention.
No additional model output or call allowance is awarded to the recovery arm.
Recovery-specific context after a failure is part of that recovery mechanism.

Each pair requires matching initial goal/tree hashes AND a matching first-failure
signature. The latter hashes the scenario, fill target/type, timeout category,
and post-failure observation fingerprint. Raw error details, typed values and
page text are not saved in the signature. If the model chooses different first
fill targets or the resulting observed states differ, that pair is excluded and
complete=false. A missing failure trigger also cannot count as ablation evidence.
The full excluded records remain available for inspection.

For disabled_textbox_timeout, both mappings disable the first fill target,
attempt Playwright fill with a 300ms timeout, then restore it in finally. The
browser emits the actual error. This is an induced experimental condition, not
a natural production incident. Hash equality checks observable state, not every
possible hidden browser/timing variable. Alternating arm order is counterbalancing,
not randomization. The tiny seed set is exploratory, not a final held-out test.

## Output and interpretation

Each run creates results/recovery-ablation-TIMESTAMP-ID/ with config.json,
sanitized per-arm records, pairs.json and summary.json. Mode is
paired_recovery_ablation. Summary reports matched counts, paired outcomes,
per-arm success and mean steps/calls/end-to-end time/reported tokens, success-rate
difference in percentage points, and mean additional calls/time for recovery.
The shared worker's duration includes environment setup and cleanup consistently
for both arms. Reported tokens are not a verified billing total; incomplete usage
is flagged, and no dollar cost is inferred without current pricing.

API/configuration/environment errors stop the experiment and preserve partial
results; external process-group timeouts and Ctrl-C cleanup remain. Unknown usage
is marked explicitly. Every configuration is checked against a twenty-four-call
planned ceiling before any episode starts. Failure matching excludes mismatches
rather than presenting them as a causal recovery benefit. A claimed effect applies
only to this matched controlled condition, not broad website reliability.

A complete experiment returns zero even though recovery_off fails tasks. Read
complete, matched_pairs, paired_outcomes, the per-arm results and usage warnings.
Do not interpret process exit status alone as agent success. Baseline behavior
without any induced failure is measured separately by previous experiments.

The CLI also permits changed_textbox_id and login-user (login requires at least
four actions per arm). These are future configurations, not extra acceptance
runs required before interpreting the first experiment.

## Implementation and verification

148 offline tests passed (133 prior checks plus 15 ablation cases). New checks
cover equal budgets, allowance validation, paired failure matching, exclusion of
non-triggered faults, failed off outcomes, summaries, API-error stopping and
safe error evidence. No live API or browser experiment was run in preparation.

Updated comparison_worker.py to support recovery arms with a required controlled
scenario; normal oneshot/iterative arms still require scenario=none. Updated
compare.py with optional arm names, pair-matching hook, summary builder and call
ceiling; defaults and previous comparison behavior remain unchanged and tested.
Added ablate_recovery.py and tests/test_recovery_ablation.py. Working model,
action schema, LangGraph workflow, secrets, dependencies and vendor assets are
unchanged. This update does not add another recovery capability.

Next dependency: inspect the first matched ablation results. Then consolidate the
findings and fix the broader task/seed evaluation protocol, rather than adding
more recovery scenarios. Task coverage, a second meaningful ablation, final
analysis and the lightweight interface remain in the original project scope.
