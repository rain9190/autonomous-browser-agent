# First autonomous click

The Day 2 version connected the OpenAI adapter to a five-step LangGraph loop. The model
picked an observed button ID; Python validated it and checked the benchmark result.
The initial offline suite had 15 tests.

```bash
python -m browser_agent --seed 42
```

This uses the local MiniWoB assets and API credits. A successful click alone isn't enough:
the benchmark must confirm completion. This was the starting point for the later
[comparison](../FINAL-BENCHMARK-REPORT.md).
