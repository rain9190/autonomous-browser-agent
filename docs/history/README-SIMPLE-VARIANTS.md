# Extra text, click and dialog tasks

This enabled `enter-text-2`, `click-test-2`, `click-test-transfer`, `click-dialog` and
`click-dialog-2` in the existing runners. They use the existing click/fill actions and
validation, rather than new execution permissions.

```bash
python -m browser_agent --task enter-text-2 --seed 61 --max-steps 2
```

These were development checks at seeds 61/67. “Transfer” is the benchmark task's name,
not evidence that the agent generalises to unseen websites.
