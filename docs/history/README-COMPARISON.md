# Paired planning comparison

The comparison runner tests one-shot and iterative on the same task and seed. It checks
initial-observation fingerprints, uses equal browser-action budgets and alternates arm order.

```bash
python -m browser_agent.compare --tasks enter-text --seeds 11 29 --max-steps 2
```

That example runs two pairs, or four episodes, with at most six model calls. Reports save
both outcomes, timings and reported usage. Recovery is off for this comparison; incomplete
or mismatched pairs are identified separately.

The first small experiments and later fixed evaluation are recorded in
[early findings](../EXPERIMENT-FINDINGS.md) and [final results](../FINAL-BENCHMARK-REPORT.md).
