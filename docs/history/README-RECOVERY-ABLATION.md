# Recovery on vs off

This comparison keeps the iterative agent, model, task, seed and action allowance the same.
Both arms get an induced fill timeout; only the recovery allowance changes from zero to one.

```bash
python -m browser_agent.ablate_recovery --task enter-text --seeds 31 47 --max-steps 3 --scenario disabled_textbox_timeout
```

The runner checks both the initial observation and first-failure signature. Recovery-off
is expected to fail fast, so its failures are retained. The experiment measures this retry
mechanism, not a general reliability improvement.

[Early findings](../EXPERIMENT-FINDINGS.md) · [Final results](../FINAL-BENCHMARK-REPORT.md)
