# Benchmark results

I compared two ways of running the agent on local BrowserGym/MiniWoB tasks:

- **One-shot:** generate a plan once, then execute it.
- **Iterative:** observe the page again before deciding the next action.

Both used `gpt-4.1-mini-2025-04-14`, the same per-task action limits and full-credit scoring.
The test covered 20 tasks with three reserved seeds each: `1009`, `1013` and `1019`.
The code and evaluation settings were frozen before these runs.

## Planning

| | One-shot | Iterative |
| --- | ---: | ---: |
| Successful runs | 55/60 | 57/60 |
| Success rate | 91.7% | 95.0% |
| Reported API calls | 60 | 114 |
| Average time per run | 4.06 s | 5.03 s |

Both succeeded on 52 instances. Iterative alone succeeded on five; one-shot alone succeeded
on three. Iterative handled `click-collapsible-2` better (3/3 versus 0/3), but lost one
instance each on the two checkbox tasks and the radio-choice task.

The tradeoff was fairly simple: iteration completed two more instances overall, but used
nearly twice as many requests. Neither approach won on every task.

## Recovery

A separate test deliberately caused the first fill action to time out on `enter-text`
and `login-user`, using three seeds per task.

| Recovery | Successful runs |
| --- | ---: |
| Disabled | 0/6 |
| Enabled, with one retry | 6/6 |

This tests recovery from an injected timeout, not naturally occurring website failures.

## Limits and saved results

There were 132 episodes in total: 120 planning runs and 12 recovery runs. They reported
201 API calls. One iterative episode has incomplete token-usage reporting.

This is a small local benchmark with related task variants. The 95% figure is not a
real-website form-filling success rate or evidence that iteration is generally better.
The exports also lack full action histories, so some failure causes cannot be reconstructed.

Saved evidence: [audit summary](evidence/final-v1/audit-summary.json),
[episode metrics](evidence/final-v1/episode-metrics.csv),
[failure records](evidence/final-v1/planning-failures.json) and
[frozen protocol](benchmark/PROTOCOL.md).
