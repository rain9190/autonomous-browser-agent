# Early milestones — 21 October 2026

The first version grew from a manual click test into an LLM-driven LangGraph loop with
clicks, text entry, multi-step budgets and simulated fill recovery. It had 87 offline
tests at this checkpoint. This is a historical report, not the current test count.

## Saved development runs

| Run | Successes | API calls |
| --- | ---: | ---: |
| Four-task regression, seeds 7 and 123 | 8/8 | 12 |
| Earlier login baseline, seeds 7/42/123 | 3/3 | 9 |
| Simulated text-fill recovery, seeds 7/42/123 | 3/3 | 9 |
| Simulated login recovery, seeds 7/42/123 | 3/3 | 12 |

These were separate runs on a small, reused set of seeds. The recovery cases deliberately
failed the first fill; they weren't natural browser failures. The login baseline predates
the recovery changes, so these results shouldn't be pooled into a general success rate.

[Regression](evidence/baseline-regression.json) ·
[Login baseline](evidence/baseline-login.json) ·
[Text recovery](evidence/simulated-text-recovery.json) ·
[Login recovery](evidence/simulated-login-recovery.json)

The original environment was Python 3.11.9 with BrowserGym 0.14.3. Current dependency pins
are in [requirements.txt](../requirements.txt). Later results are in the
[final report](FINAL-BENCHMARK-REPORT.md).
