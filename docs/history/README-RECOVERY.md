# First fill-recovery test

The first simulator failed one fill before changing the page. The agent could observe
again, retry within its existing budget, and finish the task.

```bash
python -m browser_agent --task enter-text --seed 42 --max-steps 3 --max-recoveries 1 --simulate-fill-error-once
```

Recovery defaults to off. Only eligible fill failures can retry; click errors, invalid
actions and API errors stop. Failed attempts are recorded separately and still count
against the action allowance. This demonstrates a controlled retry, not recovery from
all browser errors.
