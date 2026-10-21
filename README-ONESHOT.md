# One-shot comparison baseline

## First live check

    python -m pytest tests -q
    python -m browser_agent.run_oneshot --task enter-text --seed 11 --max-steps 2

Expected tests: 117 passed, two opt-in browser checks skipped.
Expected live behavior, if the model plans correctly: one model call returns a
fill and Submit click; deterministic execution earns benchmark reward 1.0.
The expected report has evaluation_mode=oneshot, api_calls=1 and steps=2.
A failed benchmark is a legitimate result; do not repeatedly retry until it wins
or silently remove failed episodes from comparison.

## What is held fixed

OneShotAdapter reuses the existing ModelAdapter's model, OpenAI endpoint,
20-second request timeout and zero retry configuration. Default model remains
gpt-4.1-mini-2025-04-14. Existing click/fill schemas, literal action mapping,
observed-role validation, task allowlist, local vendor assets, max_steps and
wall-clock limits are reused. No recovery scenario is enabled in this runner.

The plan is one strict object containing 1–6 actions. The chosen action budget
is checked before executing any action; malformed or over-budget plans are
rejected. All planned IDs must be explicitly represented. Every action is
validated against the current observation before execution. Deterministic
checks may reject an action but cannot change its ID, change its text, repair
its plan or call the model. Browser errors stop, and success is benchmark-based.

The model receives only the initial goal and accessibility tree. It does not
receive later observations. Fresh observations are still used by Python for
safety and completion checking; removing these checks would make the comparison
unsafe and confound verification with planning. Execution stops immediately if
the benchmark already succeeds or the episode ends.

The one-shot request may generate at most 256*max_steps output tokens, matching
the iterative agent's aggregate output ceiling at the same action budget.
The per-request output limits differ deliberately because one-shot must express
the entire plan at once. Actual input/output token use and latency must still be
measured: different prompt/schema overhead is not assumed to be equal cost.
One-shot has exactly one request allowance; the iterative system can use up to
max_steps. Both have the same maximum browser-action allowance.

## Results

Every live one-shot run saves a unique results/oneshot-TASK-seedSEED-TIMESTAMP-ID.json.
It contains mode, model, task/seed, action budget, benchmark status, actions,
usage and duration. Like existing single-run reports, action history contains
synthetic typed strings. Keep results private/ignored; comparison summaries
should omit them. API or run errors are reported without raw exception text.
api_usage_may_be_incomplete marks cases where returned token totals may exclude
failed/billable requests; zero returned usage is not a no-charge guarantee.

The initial goal and tree are hashed into initial_observation_sha256 to support
later paired-instance checks. A matching seed alone must not be treated as proof
of an identical observed instance. The paired comparison runner has not yet
been added; its next step is to capture the same fingerprint for the iterative
arm, run fixed configurations, and report both outcomes including failures.

The existing browser_agent.evaluate baseline command still means the iterative
agent with recovery disabled. It has NOT been repurposed into a one-shot evaluator.
Use browser_agent.run_oneshot explicitly. Do not feed its reports into the older
baseline parser as if they came from the iterative arm.

## Verification status

117 offline tests passed, including all 104 prior tests. New checks cover
fixed-plan execution, stale target stopping, no retry, full-plan schema/action
budget rejection before execution, early benchmark stopping, refusal handling,
request count and input/output bounds. Strict SDK JSON-schema generation was
checked. No live API calls or browser episodes were run during preparation.

Added only: browser_agent/oneshot.py, browser_agent/run_oneshot.py,
tests/test_oneshot.py and this README. Existing working agent files, credentials,
dependencies, vendor assets, and evaluation commands are unchanged.
