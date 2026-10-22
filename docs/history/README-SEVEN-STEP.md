# Seven-step checkbox task

`click-checkboxes` can require six selections followed by Submit, so the explicit episode
maximum increased from six to seven actions. The default stayed at two; budgets don't
increase automatically after a failure.

```bash
python -m browser_agent --task click-checkboxes --seed 61 --max-steps 7
```

The limit was updated across both planners and evaluation runners. Over-budget plans are
rejected before execution, and partial checkbox reward still doesn't count as success.
