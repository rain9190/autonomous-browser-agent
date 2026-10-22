# Recovery across seeds

A separate evaluator checked the injected first-fill failure over several instances:

```bash
python -m browser_agent.evaluate_recovery
```

The original defaults were `enter-text`, seeds 7/42/123, three steps and one recovery.
Each recovered success needed a confirmed injection, a retry and benchmark completion.
Results were labelled `simulated_fill_recovery` and kept separate from ordinary baselines.

The runner saves per-episode records and a summary in a unique `results/` folder.
These deliberately injected errors are different from natural website failures.
