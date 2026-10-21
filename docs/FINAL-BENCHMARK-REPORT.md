# Final Phase 4 benchmark report — frozen protocol v1.0

The iterative agent completed **57/60 instances (95.0%)**, versus **55/60 (91.7%)**
for a fixed one-shot plan. The observed difference is **two instances / 3.3 percentage
points**, not evidence of a general reliability advantage. Both used the same model,
per-task action budgets, local benchmark and deterministic action validation.

In the dynamic-discovery task `click-collapsible-2`, iterative completed 3/3 and one-shot
0/3. One-shot failed after executing its three-action plans. This is consistent with the
benefit of observing newly revealed targets; full action-level explanations cannot be
reconstructed from these exports. One-shot also outperformed iterative on three instances
across checkbox/radio tasks. Neither strategy dominated every task.

Controlled timeout recovery completed 6/6 with recovery enabled versus 0/6 disabled.
These were deliberately induced failures, with matching initial and first-failure
signatures. They do not establish recovery rates for naturally occurring website failures.

## Audit and coverage

- Protocol commit `317eba5`; frozen agent commit `27e004f7230959ee2bd41d147565c6f4527d8567`.
- 20 task IDs, three reserved seeds each (1009, 1013, 1019), 60 planning pairs / 120 episodes.
- Two recovery tasks × three seeds: six pairs / 12 episodes. Total 132 episodes, 66 pairs.
- All 22 scheduled batches found exactly once. No duplicated final task batches, missing
  episodes, mismatched pairs or interrupted batches were found in the saved results.
- Episode files equal their entries in pair files. All 22 summaries recompute exactly.
- Each run config has the frozen agent source hashes, model, package versions and budget.
  The current integrity checker passed. Configured alternating arm order was checked;
  the exports do not independently timestamp each arm's actual start order.
- The freeze file fingerprints supporting task/core/common assets and installed BrowserGym
  sources. Their current content matches. Run configs did not capture every supporting
  asset hash at execution, so this is not proof of historical filesystem immutability.
- No model calls, browser launches, retries or code/prompt/budget changes were made for
  this analysis. Development runs are excluded. Only one existing result directory matched
  each scheduled batch; no best-of-attempt selection was performed.

The primary metric is `terminal_full_credit_reward_1_v1`; partial positive checkbox
rewards are failures. All recorded successes have exported reward 1; failed planning
records have reward 0. No partial-credit episodes were reported. Exported episode files
omit terminal/truncated flags, so the audit relies on the frozen worker's completion check
rather than independently re-deriving those flags.

## Planning results

| Measure | One-shot | Iterative |
|---|---:|---:|
| Scheduled and matched episodes | 60 | 60 |
| Full-credit successes | 55 | 57 |
| Success rate / task-macro success rate | 91.7% | 95.0% |
| Reported API calls | 60 | 114 |
| Mean calls per episode | 1.00 | 1.90 |
| Mean browser actions per episode | 1.70 | 1.88 |
| Mean elapsed time per episode | 4.06 s | 5.03 s |
| Reported input tokens | 35,721 | 83,735* |
| Reported output tokens | 2,106 | 2,127* |
| Potentially incomplete usage episodes | 0 | 1 |

*The invalid-action/plan episode records one attempted call but zero reported tokens.
Its usage flag is retained. Token totals may be incomplete; zero does not establish zero
billable usage. API-call counts are local adapter reports, not a billing reconciliation.
Timing includes failed and successful episodes and environment/cleanup overhead; it is
not a success-normalized measure. Arm order is imperfectly balanced with three seeds.
No monetary-cost estimate is made.

Paired outcomes: **52 both succeeded, 5 iterative-only, 3 one-shot-only, 0 both failed**.
Task-macro and pooled rates coincide because all tasks have the same three seeds.
There are no missing scheduled episodes, so scheduled-coverage and matched rates also coincide.

| Task | Budget | One-shot | Iterative |
|---|---:|---:|---:|
| click-test | 2 | 3/3 | 3/3 |
| click-button | 2 | 3/3 | 3/3 |
| click-button-sequence | 2 | 3/3 | 3/3 |
| enter-text | 2 | 3/3 | 3/3 |
| login-user | 3 | 3/3 | 3/3 |
| enter-text-2 | 2 | 3/3 | 3/3 |
| click-test-2 | 2 | 3/3 | 3/3 |
| click-test-transfer | 2 | 3/3 | 3/3 |
| click-link | 2 | 3/3 | 3/3 |
| click-checkboxes | 7 | 3/3 | 2/3 |
| click-checkboxes-soft | 6 | 3/3 | 2/3 |
| click-option | 3 | 3/3 | 2/3 |
| choose-list | 3 | 3/3 | 3/3 |
| click-dialog | 2 | 3/3 | 3/3 |
| click-dialog-2 | 2 | 2/3 | 3/3 |
| click-collapsible | 4 | 3/3 | 3/3 |
| click-collapsible-2 | 6 | 0/3 | 3/3 |
| click-tab | 2 | 3/3 | 3/3 |
| click-tab-2-easy | 4 | 3/3 | 3/3 |
| click-tab-2-medium | 5 | 2/3 | 3/3 |

### Declared interaction families

The protocol declares 19 family labels, most with just one task ID. These labels help
show coverage but do not establish independent capabilities. Related task variants remain
correlated, and a 20-task count must not be described as 20 independent skills.

| Family | Task IDs | Episodes per arm | One-shot successes | Iterative successes |
|---|---:|---:|---:|---:|
| dialog_controls | 1 | 3 | 3 | 3 |
| dialog_label_matching | 1 | 3 | 2 | 3 |
| disclosure_sequence | 1 | 3 | 3 | 3 |
| dynamic_discovery | 1 | 3 | 0 | 3 |
| dynamic_tab_state | 1 | 3 | 2 | 3 |
| form_entry | 1 | 3 | 3 | 3 |
| label_matching | 1 | 3 | 3 | 3 |
| link_selection | 1 | 3 | 3 | 3 |
| multi_field_form | 1 | 3 | 3 | 3 |
| multi_selection | 1 | 3 | 3 | 2 |
| native_select | 1 | 3 | 3 | 3 |
| ordered_actions | 1 | 3 | 3 | 3 |
| radio_selection | 1 | 3 | 3 | 2 |
| semantic_selection | 1 | 3 | 3 | 2 |
| single_click | 2 | 6 | 6 | 6 |
| single_click_variant | 1 | 3 | 3 | 3 |
| tab_search | 1 | 3 | 3 | 3 |
| tab_selection | 1 | 3 | 3 | 3 |
| text_transformation | 1 | 3 | 3 | 3 |

## Eight planning failures: what the evidence supports

| Task / seed | Arm | Recorded reason | Executed actions | Supported interpretation |
|---|---|---|---:|---|
| click-checkboxes / 1013 | Iterative | step_budget_exhausted | 7 | No full-credit completion within the fixed action allowance |
| click-checkboxes-soft / 1019 | Iterative | step_budget_exhausted | 6 | No full-credit completion within the fixed action allowance |
| click-option / 1009 | Iterative | invalid_model_action_or_plan | 0 | Action/plan processing failed before a browser action; exact validation cause unavailable |
| click-dialog-2 / 1009 | One-shot | episode_ended_without_success | 1 | Episode ended without full credit; selected control unavailable in export |
| click-collapsible-2 / 1009 | One-shot | plan_exhausted | 3 | Fixed plan ended before completion |
| click-collapsible-2 / 1013 | One-shot | plan_exhausted | 3 | Fixed plan ended before completion |
| click-collapsible-2 / 1019 | One-shot | plan_exhausted | 3 | Fixed plan ended before completion |
| click-tab-2-medium / 1013 | One-shot | episode_ended_without_success | 1 | Episode ended without full credit; selected control unavailable in export |

The worker maps ValueError during the agent phase to `invalid_model_action_or_plan`.
This broad category does not prove which schema, target-role or parsing rule failed.
Likewise, budget exhaustion does not prove repeated clicks, a prompt defect or stale state.
The exports omit action histories, goals, intermediate observations and raw model outputs.
Do not invent those causes, or replay these final instances to replace the recorded failures.
Any later debugging run must be separately labelled post-benchmark development.

## Controlled recovery results

| Task | Pairs | Off successes | On successes | Mean off/on calls | Mean off/on duration |
|---|---:|---:|---:|---|---|
| enter-text | 3 | 0/3 | 3/3 | 1 / 3 | 3.56 / 8.14 s |
| login-user | 3 | 0/3 | 3/3 | 1 / 4 | 3.52 / 9.69 s |
| Combined | 6 | 0/6 | 6/6 | 1 / 3.5 | 3.54 / 8.92 s |

All recovery pairs confirm the same injected first-fill failure signature within each pair.
The on arm used one recovery per episode. Recovery added a mean 2.5 requests and 5.38 seconds
per episode over fail-fast off. The off failures are expected under this intervention.
There were no mismatched or excluded pairs. Keep this result separate from no-fault planning.

## Resource totals and limitations

**201 reported API calls** out of the 291-call planned envelope: 174 planning, 27 recovery.
Reported tokens across all experiments: **137,900 input and 4,747 output**, with the one
flagged planning episode's usage potentially incomplete. Total recorded episode durations
sum to about 620.48 seconds; this is not wall-clock project time or a monetary bill.

The sample is only three instances per task, using related variants of local MiniWoB.
Seeds hold out instances, not tasks; the default transfer mode is not evidence of unseen-task
transfer. The model is not guaranteed deterministic. Current versions are frozen, but browser
binary/OS hashes were not captured. Some tab targets are initially visible, and choose-list's
development seeds were already selected correctly; successful task labels alone do not prove
that every possible interaction was exercised. No real sites or accounts were tested.
The optional action-history ablation was explicitly omitted in protocol v1.0.

The result supports a practical tradeoff: one-shot used fewer requests on this fixed suite;
iterative completed two more instances overall and handled the dynamic-discovery subset.
The small difference is descriptive, not a statistical significance claim or a general
ranking of agent architectures.

## Evidence and reproduction

See [audited totals](evidence/final-v1/audit-summary.json),
[all episode metrics](evidence/final-v1/episode-metrics.csv),
[eight failure records](evidence/final-v1/planning-failures.json), and
[original-file provenance hashes](evidence/final-v1/provenance.json).
Each P01–P20 / R01–R02 directory preserves the original config, pairs, summary and episode
JSON files without rewriting them. The frozen protocol is copied into `evidence/final-v1/protocol`.

After installing this report bundle in the repository, this read-only analysis can be
reproduced into a NEW output directory (it refuses to overwrite an existing audit):

```bash
python -B scripts/audit_final_v1.py --root . --output results/final-v1-audit-reproduction
```

The command performs no browser/API work. It checks the current freeze, requires unique
scheduled results, recomputes summaries and exports structured evidence. The narrative report
is a separate interpretation of that evidence and is not regenerated by the audit script.

Phase 4's fixed evaluation and report are complete. The next project phase is a lightweight
demo and portfolio packaging. Improved logging, loop detection and targeted diagnostics are
future development ideas; they were not added retroactively to the frozen benchmark.
