# Phase 4: matched one-shot versus iterative comparison

## Purpose and project position

Setup, the working agent and the first reliability milestones are complete for
five small task families. The one-shot baseline now also works on an initial
text-entry instance. This is Phase 4 (comparative benchmarking), step 2: build
and verify a matched comparison. The original project asks whether iterative
observation improves task success over one-shot planning, and at what cost.
This runner starts answering that question. It does not expand recovery features.

## First paired smoke experiment

    python -m pytest tests -q
    python -m browser_agent.compare --tasks enter-text --seeds 11 29 --max-steps 2

Expected tests: 133 passed, two opt-in browser checks skipped.
The live command runs two task/seed pairs, each with both arms: four browser
episodes total. At most six model calls (one-shot at most one per episode,
iterative at most two). The action budget is two in BOTH arms. No recovery or
failure injection is used. Do not rerun only failed episodes to improve a score.

If no arguments are given, enter-text and click-button-sequence are each run at
seeds 11 and 29: four pairs/eight episodes, at most twelve API calls.
An experiment cannot exceed twenty-four planned model calls; over-budget CLI
configurations are rejected before browser/API work. A two-seed login comparison
would use --tasks login-user --seeds 11 29 --max-steps 3 (eight-call ceiling).

## Matched protocol

Both arms are launched by the same isolated comparison worker with the same
OpenAI model snapshot (gpt-4.1-mini-2025-04-14), local task assets, seed,
observation flattening, action schemas/mapping, deterministic safety checks,
benchmark success rule, action budget and wall-clock budget. Both disable SDK
retries and recovery. Arm order alternates by pair to reduce a simple ordering
bias. It is counterbalanced, not a randomized or blinded experiment.

One-shot sees only the initial goal/tree, produces one fixed plan, and cannot
replan. Iterative sees refreshed observations and action history at each decision.
This information/call difference is what is being compared, not accidentally
held equal. One-shot's single request has an output ceiling of 256*max_steps;
iterative allows 256 per request, for the same maximum aggregate output allowance.
Input usage, schema overhead, actual output, API calls and time may differ and
are measured rather than assumed equal. Both retain a twenty-second per-request
timeout and a shared total run allowance.

Both arms hash the initial goal and flattened accessibility tree using identical
serialization. Only complete pairs with matching fingerprints and no
infrastructure errors enter paired success/cost summaries. Same seed alone is
not sufficient. A matching initial fingerprint does not establish equality of
all future timing effects or random transitions. Mismatches are retained as
excluded pairs and make complete=false; they are not silently pooled.

## Reports and interpretation

Every run creates results/comparison-TIMESTAMP-ID/ containing:

- config.json: tasks, seeds, model, budget, ordering, inspected package versions,
  and SHA-256 hashes of the current project Python files.
- One sanitized record per attempted arm, including initial fingerprint, status,
  attempted actions, model calls, reported tokens and end-to-end duration.
- pairs.json: paired outcomes and matching/exclusion flags.
- summary.json: completeness, matched count, paired win/tie counts, success rates
  and mean metrics on matched pairs, plus all-attempt reported usage.

No goal text, filled strings, action history, raw stdout/stderr or credentials are
saved by this runner. Both one-shot and iterative use the same timed worker;
duration includes environment startup, model/agent work and cleanup, but excludes
the parent process launching Python. It is end-to-end time, not model-only latency.

The worker counts attempted actions even if a later graph/schema error aborts.
Invalid actions/plans and browser/benchmark failures remain failed outcomes where
an initial fingerprint is available. API/configuration/environment/agent-runtime
errors stop further spending and make the experiment incomplete. Ctrl-C terminates
the active process group and preserves records/summary with unknown usage marked.
Returned token totals can omit failed requests: summaries explicitly count
unknown or potentially incomplete usage and do not imply a zero charge.

Mean token metrics are means of REPORTED usage, not verified billing totals.
No currency estimate is made until current model pricing is deliberately attached.
Task-level records permit inspection of failures and exclude no inconvenient
benchmark results. Source hashes identify current files, including uncommitted
comparison code; they do not imply that every file is in a Git commit.

A completed comparison can include failed tasks: exit zero means the planned
experiment completed on matched pairs, NOT that both agents solved every task.
Read paired_outcomes (both_succeeded, both_failed, oneshot_only, iterative_only)
and per_arm_on_matched_pairs. A tie on these simple tasks is a valid finding.
The sample is exploratory, small and uses development seeds; it is not a held-out
final evaluation or evidence of general browser-agent superiority.

## Verification and next dependency

133 offline tests passed (117 prior checks and 16 new comparisons checks), with
two opt-in Chromium tests skipped. New checks cover strict result parsing,
model/budget checks, mismatched observations, counterbalanced ordering, failed
outcomes, partial runs, unknown usage, process-group timeout cleanup and action
attempt counting. No live API or browser experiment ran during preparation.

Added: browser_agent/comparison_worker.py, browser_agent/compare.py,
tests/test_comparison.py and this README. Existing agents, API credentials,
dependencies and other evaluators are unchanged.

Next: verify the first paired run, then fix a broader task/seed protocol and run
matched comparisons/ablations. The existing baseline evaluator still means the
iterative agent with recovery disabled; this paired runner explicitly identifies
the oneshot and iterative arms. More tasks, recovery ablations, final analysis
and the lightweight demo remain in the original project scope.
