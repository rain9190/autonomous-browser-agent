# Frozen benchmark protocol — version 1.0

Prepared 22 October 2026, before inspecting reserved final instances. Agent checkpoint:
`27e004f7230959ee2bd41d147565c6f4527d8567`. This protocol becomes the local run baseline
when its integrity check passes and the protocol files are committed. No final evaluation
is performed or authorized by installation alone.

## Objective and scope

Phase 4 compares a fixed one-shot plan against an iterative observe–decide–validate–execute–verify
agent. The primary set has 20 enabled local MiniWoB task IDs. Related variants are not
independent capabilities. This is an exploratory local benchmark, not evidence of reliable
real-site automation or unseen-task generalization. Earlier development results remain
separate from final evidence, including development failures before fixes.

The exact task order, families, HTML hashes and action budgets are in `task-plan.json`.
The budgets are unchanged from the draft: 2 for basic click/form/dialog variants;
3 for login-user, click-option and choose-list; 7 for click-checkboxes; 6 for
click-checkboxes-soft and click-collapsible-2; 4 for click-collapsible and
click-tab-2-easy; 5 for click-tab-2-medium. These are fixed resource policies, not a
guarantee that every instance is solvable. Default runtime remains two actions.

`click-checkboxes-large` stays excluded/reserve because up to 13 actions exceed policy.
`button-delay` stays excluded because it is unregistered locally and requires a timing policy.
No post-result substitutions, easier seeds, extra actions or task-specific prompt tuning.
The optional action-history ablation is omitted from version 1.0; it is not promised work
or part of the 291-call envelope.

## Frozen environment and observations

Model: `gpt-4.1-mini-2025-04-14`, both arms. Package and Python versions and source hashes
are in `freeze-manifest.json`. BrowserGym/MiniWoB 0.14.3, fixed local vendor sources.
Use the current installed Chromium/Playwright environment; do not upgrade during the run.
The manifest checks Playwright version, not the browser executable or OS. Timing remains
machine/load dependent and model responses can vary between runs.

Task URLs are local files. The vendored core uses `WOB_DATA_MODE='default'`; BrowserGym's
current setup does not override it. Transfer-task names are not claims of cross-domain
transfer. The manifest fingerprints the task and supporting core/common assets, plus installed
BrowserGym source files. Any changes require a documented versioned amendment before resuming.

Both arms receive the same goal, flattened accessibility tree and legal action catalogue.
For four link tasks, a fixed narrow interface appends visible local `span.alink` targets.
It never supplies hidden IDs, expected answers, reward internals, arbitrary page code or
real-site navigation. One-shot gets only its initial model observation; iterative gets a fresh
observation per decision. Both executors check each action against current visible roles.
One-shot execution may validate the next target against the current page but never replans,
repairs or substitutes it. Guessing a future hidden ID is prohibited in its instructions;
validation alone does not prove every proposed ID was initially visible. Report this limitation.

Safety: strict schemas; fixed trusted action mapping; no model-generated dynamic code execution.
Existing 8,000-character observation/catalogue and 4,000-character history caps remain.
No SDK retries (`max_retries=0`), request timeout 20 seconds. Episode deadline is
max(90, 25 × action_budget + 15) seconds, subprocess grace 10 seconds. One-shot uses one
request with output allowance 256 × action_budget; iterative at most action_budget requests
of 256 output tokens each. Count failed requests/attempts and unknown usage honestly.

## Splits and experiments

Historical seeds: 7, 11, 29, 31, 42, 47, 123. Development: 61 and 67.
Reserved final: **1009, 1013, 1019**. These hold out instances, not task types.
Do not inspect them until this protocol is verified and committed.

1. Planning: 20 tasks × three seeds × two arms = 120 episodes, 60 scheduled pairs.
   Recovery off, no fault injection. Equal per-task action budget and model snapshot.
   Each task is its own serial batch. Within each batch, order alternates: one-shot first
   on seed 1009, iterative first on 1013, one-shot first on 1019. Order balance is imperfect
   with three seeds; do not interpret timing differences as controlled causal estimates.
2. Controlled recovery: enter-text budget 3 and login-user budget 4, same three seeds,
   iterative recovery off (0) versus on (1), identical disabled-textbox timeout injection.
   12 episodes, six scheduled pairs. Initial observation and first-failure signatures
   must match. Off failing after the induced error is an expected intervention outcome.
   This measures recovery from a constructed fault, not natural-failure prevalence.

`final-batches.json` fixes all 22 batches in order. It is data, not an auto-running script.
Planning ceiling: 249 calls. Recovery ceiling: 42. Combined: **291 calls** for 132 episodes.
Each batch is at most 24 planned calls. This is a request ceiling, not a monetary cap.
Technical reruns are additional and require a separately documented decision.

## Success, matching and reporting

Primary metric `terminal_full_credit_reward_1_v1`: terminal, not truncated, no final
execution error, finite numeric reward 1.0 within absolute tolerance 1e-9. Positive partial
checkbox reward does not count as success. Preserve raw reward and positive-terminal flag.
Execution success alone is not benchmark completion.

Primary paired analysis requires matching initial goal/observation fingerprints and metric
versions; recovery additionally requires matching induced-failure signatures. Initial hashes
do not prove all later hidden state/timing is identical. Retain mismatches, failures and
incomplete coverage. Matched success rates are conditional; present scheduled coverage and
unmatched counts alongside them. For a supplementary conservative scheduled-coverage rate,
use successes / scheduled episodes and label missing episodes as missing, not model failures.
Report both arms' full scheduled denominators, matched denominators, per-task rates, task-macro
averages, family-level breakdowns, paired wins/ties, rewards, steps, calls, tokens, duration,
failure categories and unknown usage. Do not pool recovery with no-fault success.
Do not claim statistical significance from three seeds per task.

Infrastructure/API/transport/cleanup failures stop the batch. Preserve all attempt files;
do not rerun an entire completed batch or model-quality failure until it succeeds.
A mismatch or incomplete batch stays visible. Any justified technical rerun must receive a
separate attempt ID and written reason; no silent replacement, deduplication by best result,
or retrospective removal. The original scheduled analysis remains identifiable.
Stop if the integrity check fails. Amend the protocol and hashes explicitly if a code/source
fix becomes necessary; report results before/after separately instead of claiming one freeze.

## Run gate and next step

Run `python scripts/check_benchmark_plan.py` (read-only; no browser/API). Commit all protocol
files if it passes. Then start only the first scheduled batch when instructed; keep its result
folder. Do not paste all batch commands at once. Phase 4 is complete only after planned coverage,
exclusions, comparisons and a final report are accounted for. Phase 5 is demo/productization.
