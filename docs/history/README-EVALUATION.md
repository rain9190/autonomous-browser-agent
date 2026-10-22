# Multi-seed evaluation

The evaluator runs task/seed combinations in separate processes and saves episode records
plus a summary in a new `results/eval-*` folder.

```bash
python -m browser_agent.evaluate --tasks click-button click-button-sequence --seeds 7 42 123
```

Benchmark failures count as failures. Timeouts and infrastructure errors leave a partial
summary rather than an overall pass. The runner uses per-process deadlines and preserves
completed records on interruption. Live evaluations use API credits.

The early evaluator update had 35 offline tests. Later paired experiments are covered in
[the final report](../FINAL-BENCHMARK-REPORT.md).
