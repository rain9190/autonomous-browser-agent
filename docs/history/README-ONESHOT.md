# One-shot baseline

The model sees the initial goal and page once, then returns a complete action plan.
Python still checks each target against the current page before executing it, but cannot
repair the plan or ask the model again.

```bash
python -m browser_agent.run_oneshot --task enter-text --seed 11 --max-steps 2
```

One-shot gets one model request and the same browser-action budget as iterative planning.
The output allowance scales with the action budget. Malformed plans, stale targets and
browser errors stop execution. This became the baseline for the
[paired comparison](README-COMPARISON.md).
