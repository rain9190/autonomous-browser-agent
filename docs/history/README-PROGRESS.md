# Three-action benchmark and configurable budget

    python -m pytest tests -q
    python -m browser_agent --task login-user --seed 42 --max-steps 3

Expected live behavior: fill generated username, fill generated password, click
Login. The order of the two fills may differ; benchmark success requires both
exact values. This is the existing local MiniWoB task, with synthetic generated
credentials. No real login service is involved. Goal strings are interpreted by
the model; username/password values and element IDs are not hardcoded.

Budget defaults stay at two actions and two API calls. --max-steps accepts 1–6,
sets both caps, and adjusts graph recursion, bounded history, timeouts and the
evaluation call ceiling consistently. The model sees remaining API allowance.
No SDK retries are added. Each call retains the existing 256-output-token and
observation-size caps. History is capped at six actions and 4,000 JSON characters.

Progress rows contain step number, action type, element ID, execution_ok and
benchmark_success. A fill being executed does not establish that its value is
correct. A fresh page observation is provided to the next decision; only positive
terminal benchmark reward without error/truncation establishes success. Rows
omit typed text, although the existing action history still includes synthetic
filled strings. Reports add max_steps and remaining_steps; filenames now include
the budget to avoid overwriting runs with a different allowance.

The in-process run deadline is max(90, 25*max_steps+15) seconds. The local
benchmark episode limit uses the same duration. The evaluator uses an external
process-group deadline ten seconds later and preserves prior timeout behavior.

After the initial login-user run succeeds:

    python -m browser_agent.evaluate --tasks login-user --seeds 7 42 123 --max-steps 3

Three episodes, at most nine requests. The evaluator remains limited to twelve
episodes and now also caps planned calls at 24. Over-budget configurations are
rejected before launching any episode. Its previous defaults are unchanged.

59 offline tests passed (the 48 prior checks plus 11 budget/progress checks).
They verify three-action completion, stopping after two actions when configured,
progress semantics, request-count enforcement, subprocess budget propagation,
and evaluation budget accounting. No live API calls or browser episodes were
run while preparing this bundle; live validation is the next user-run step.

This update replaces model.py, workflow.py, __main__.py and evaluate.py; adds
budget.py and tests/test_progress.py. Existing schema, action mapping, secret
files, vendor assets and installed dependencies are unchanged.
