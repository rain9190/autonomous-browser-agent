# Benchmark results

I compared one-shot plans with iterative decisions on local BrowserGym/MiniWoB tasks.
One-shot plans once; iterative observes the page again before choosing its next action.

Both used `gpt-4.1-mini-2025-04-14`, the same per-task action limits and full-credit scoring.
There were 20 tasks, each tested on seeds `1009`, `1013` and `1019`. The code and settings
were frozen before the runs.

## Planning

| | One-shot | Iterative |
| --- | ---: | ---: |
| Successful runs | 55/60 | 57/60 |
| Success rate | 91.7% | 95.0% |
| Reported API calls | 60 | 114 |
| Average time per run | 4.06 s | 5.03 s |

Both passed 52 instances. Iterative alone passed five; one-shot alone passed three.
On `click-collapsible-2`, iterative passed 3/3 and one-shot 0/3. One-shot did better
on three instances across the checkbox and radio tasks.

Iteration completed two more instances overall, but needed nearly twice as many calls.
Neither approach won on every task.

## Recovery

A separate test deliberately timed out the first fill on `enter-text` and `login-user`,
with three seeds each. Recovery passed **6/6** with one retry, versus **0/6** when disabled.
This measures an injected timeout, not naturally occurring website failures.

## Limits

The full study contains 132 episodes and 201 reported API calls. One iterative episode
has incomplete token reporting. Full action histories weren't exported, so some failures
can't be explained further from these records.

This is a small local benchmark. The 95% figure is not a real-website form-filling score
or proof that iteration is generally better.

[Audit summary](evidence/final-v1/audit-summary.json) ·
[Episode metrics](evidence/final-v1/episode-metrics.csv) ·
[Failures](evidence/final-v1/planning-failures.json) ·
[Frozen protocol](benchmark/PROTOCOL.md)
