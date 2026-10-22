# Multi-seed simulated recovery evaluation

    python -m pytest tests -q
    python -m browser_agent.evaluate_recovery

Defaults: enter-text, seeds 7/42/123, max_steps=3, max_recoveries=1.
Each episode deliberately fails its first fill before any page mutation.
The expected recovery is fill failure → fill → Submit. Three episodes allow
at most nine model requests, including the failed attempts. No SDK retries.

Each run creates a unique results/recovery-eval-TIMESTAMP-ID folder. Per-episode
records and summary.json are labeled evaluation_mode=simulated_fill_recovery.
The summary separately reports confirmed_injected_episodes, recovered_episodes,
recovery_success_rate_on_attempted, recovery_success_rate_on_confirmed_injections,
and recoveries_used, as well as existing budget/usage/completeness fields.

A recovered success requires both benchmark success and a confirmed injected
fill failure with one recovery used. A report missing simulation confirmation,
with inconsistent progress/budget/task/seed, or claiming success without recovery
is not counted as success. Simulated results remain distinct from baseline data;
the existing baseline parser continues rejecting simulated reports. Baseline
summaries now explicitly carry evaluation_mode=baseline.

Failures after injection count as unsuccessful recovery. Infrastructure errors
stop the suite and leave unattempted episodes explicit. A report lost to a
transport/process error has unknown injection/usage status, not an assumed zero
billable call count. Per-episode saved records omit filled strings, raw stdout,
stderr and browser diagnostics. Existing single-run reports still contain the
synthetic action history, under filenames marked sim1.

At most twelve episodes and twenty-four planned calls are allowed. External
process deadlines and process-group cleanup are retained, including Ctrl-C.
A partial suite is not an overall pass. Exit status zero requires every planned
episode to be a recovered success. A null confirmed-injection rate means none
were confirmed; it is not a 100% rate.

Optional later test (a different task; not required for the first run):

    python -m browser_agent.evaluate_recovery --task login-user --seeds 7 42 123 --max-steps 4

This needs four actions per episode because of the injected failed fill, at
most twelve requests total. The CLI rejects login-user with a three-step budget.

Verification: 87 offline tests passed (72 previous and 15 new). New tests cover
simulation/baseline separation, strict confirmation, failure denominators,
partial summaries, subprocess flags and external-timeout cleanup. No live API
calls or browser episodes were run while preparing the update.

Updated: evaluate.py adds an injectable summary builder and baseline mode label.
Added: evaluate_recovery.py, tests/test_recovery_evaluation.py. The working model,
action schema, workflow, secret files, dependencies and vendor files are unchanged.

These measurements test controlled injected fill failures only, not naturally
occurring browser failures or general browser reliability.
