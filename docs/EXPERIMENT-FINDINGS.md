# Phase 4 exploratory findings

Report prepared **22 October 2026**. These findings consolidate user-run local
experiments; they are not a held-out final evaluation. No new API calls were
made to prepare this report.

## Position in the original project

The core agent and initial reliability work are implemented for five local
MiniWoB task families. Phase 4 now has a functioning one-shot baseline, paired
comparison runner, and first matched recovery ablation. Broader task coverage,
another meaningful ablation where feasible, final evaluation/analysis and the
lightweight demo remain. Completing these small experiments does not complete
the entire benchmarking phase.

## Finding 1: no iterative success advantage on the tested predictable tasks

Both systems succeeded on every one of six matched instances: three tasks at
seeds 11 and 29. Initial goal/accessibility-tree fingerprints matched in each
pair. Recovery and failure injection were disabled in both arms.

| Task | Success, one-shot / iterative | Mean calls | Mean duration, seconds | Mean input tokens | Mean output tokens |
|---|---|---|---|---|---|
| Text entry | 2/2 / 2/2 | 1 / 2 | 4.58 / 6.85 | 253 / 619 | 31 / 28 |
| Ordered clicks | 2/2 / 2/2 | 1 / 2 | 4.81 / 6.17 | 254 / 591.5 | 30 / 28 |
| Login form | 2/2 / 2/2 | 1 / 3 | 5.07 / 8.10 | 327 / 1,208 | 45 / 46 |

Every slash-separated metric is **one-shot / iterative**. Durations are rounded
for display; evidence retains original precision.

**Interpretation:** one initial plan was sufficient for these predictable,
initially visible workflows. Iterative decisions used additional calls and input
tokens and took longer, without improving the observed success rate. This does
not establish one-shot superiority on dynamic tasks or tasks with unknown future
elements. It also does not support a claim that LangGraph or iteration inherently
improves success.

The arms share the model snapshot, action budget for each task, validators,
benchmark success rule, local assets and run limits. One-shot receives a single
output allowance of `256 × max_steps`; iterative receives at most 256 output
tokens per call. Their maximum aggregate output allowance is equal, but prompts,
schema overhead, observation context and actual token use differ by design.
Python still checks current targets and benchmark completion for the fixed plan;
one-shot does not get model replanning or deterministic target substitution.

Evidence: [text](evidence/phase4/text-comparison/summary.json),
[sequence](evidence/phase4/sequence-comparison/summary.json),
[login](evidence/phase4/login-comparison/summary.json).

## Finding 2: bounded recovery enabled completion after a controlled fill timeout

The iterative agent ran with recovery disabled and enabled on `enter-text`, at
seeds 31 and 47. Both arms had the same three-action/three-call allowance and
the same deliberately disabled-field fill timeout. The only configured
intervention was `max_recoveries=0` versus `1`.

Each pair matched its initial observation AND the first-failure signature. That
signature includes the fill target/type, scenario, timeout category, and
post-failure observation hash. No pairs were excluded.

| Metric, per episode | Recovery off | Recovery on |
|---|---:|---:|
| Successes | 0/2 | 2/2 |
| Mean attempted actions | 1 | 3 |
| Mean API calls | 1 | 3 |
| Mean end-to-end duration, seconds | 3.917 | 8.5495 |
| Mean reported input tokens | 301 | 917.5 |
| Mean reported output tokens | 14 | 42.5 |

The observed difference was **100 percentage points** in success, with averages
of **two additional calls, 4.6325 additional seconds, 616.5 additional input
tokens and 28.5 additional output tokens** per recovery-enabled episode.
Both recovery-off failures were retained as `browser_action_error` outcomes.
The suite used eight calls against its twelve-call ceiling.

**Interpretation:** this confirms that the implemented recovery policy can
continue after a known, recoverable fill error and complete the tested task
within budget. The comparator is deliberately fail-fast, so its failure under
the injected condition is expected. This is a mechanism demonstration, not a
surprising general reliability result, a statistical population estimate, or
proof against naturally occurring browser errors.

Evidence: [recovery ablation](evidence/phase4/timeout-ablation/summary.json).

## Integrity, provenance and limits

- All four experiments were complete, with two matched pairs each, no unmatched
  pairs, no interruptions and no reported unknown/incomplete API usage.
- Both experiments alternate arm order by pair. This is counterbalancing, not
  randomization, blinding or control of network/API latency variation.
- Timings include environment setup, agent/model execution and cleanup in the
  worker; they are not model-only inference times.
- Model: `gpt-4.1-mini-2025-04-14`. The same model snapshot and deterministic
  safety/benchmark checks are used within each comparison.
- Initial-observation equality does not prove that every future hidden random
  state or timing effect is identical. Failure matching adds an observable-state
  check for the recovery intervention, not a guarantee about all browser state.
- Seeds and tasks were used during development. The six planning comparisons and
  two recovery comparisons are tiny exploratory samples. No significance claim,
  confidence interval or broad generalization is made.
- Token counts are reported API usage, not a verified monetary bill. This report
  does not invent currency costs or combine unrelated historical trials into a
  single project-wide success rate.
- Curated copies contain configurations, paired and per-arm records, summaries
  and a [hash manifest](evidence/phase4/manifest.json). They omit page text,
  action histories, typed values, raw logs and credentials.
- Per-run configurations include package versions and source hashes. The shared
  `model.py`, `actions.py`, `workflow.py`, `budget.py` and `oneshot.py` hashes agree
  across these four runs. Worker/runner changes are recorded by their individual
  configurations rather than implied to be identical historical files.
- The latest prepared suite passed **148 offline tests**, with two Chromium
  checks opt-in. This report did not rerun tests or paid experiments because it
  changes documentation/evidence only.

## Checkpoint and next work

Commit the one-shot baseline, comparison runner, recovery ablation, associated
tests, their READMEs and this report together. The earlier commits cover the
core agent and controlled recovery scenarios; comparative files were still
untracked when this report was prepared. Use explicit staging paths so ignored
credentials/results and untracked vendor assets are not accidentally included.

Next, inventory candidate benchmark tasks and select a fixed, varied set before
further evaluation. The original target is approximately 20–30 tasks subject to
feasibility; only five task families are currently supported. Record exclusions
and unsupported actions before inspecting final outcomes. Keep development seeds
separate from a final evaluation set, specify budgets by task, and predefine which
configurations are compared. Add another meaningful ablation only with a clear
hypothesis and equal safety constraints. Then generate the final analysis and
build the lightweight demo. Do not add more recovery scenarios simply to grow
the feature list.
