# Early comparison results

These were development experiments before the [final benchmark](FINAL-BENCHMARK-REPORT.md).
They used `gpt-4.1-mini-2025-04-14` and matched initial observations within each pair.

## One-shot vs iterative

At seeds 11 and 29, both approaches passed every tested instance:

| Task | One-shot / iterative successes | Average calls |
| --- | --- | --- |
| Text entry | 2/2 / 2/2 | 1 / 2 |
| Ordered clicks | 2/2 / 2/2 | 1 / 2 |
| Login | 2/2 / 2/2 | 1 / 3 |

A single plan was enough for these initially visible workflows. Replanning used extra
calls without improving success in this small sample.

## Recovery on vs off

On `enter-text`, seeds 31 and 47, the first fill was deliberately made to time out.
Recovery enabled passed **2/2**, versus **0/2** disabled. Both had the same three-action
allowance. Actual calls averaged three with recovery and one without it.

This showed the retry mechanism working, not recovery from arbitrary real-world failures.
All pairs were retained. These development seeds weren't the final held-out instances.

Saved summaries: [text](evidence/phase4/text-comparison/summary.json),
[sequence](evidence/phase4/sequence-comparison/summary.json),
[login](evidence/phase4/login-comparison/summary.json),
[recovery](evidence/phase4/timeout-ablation/summary.json).
