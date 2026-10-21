# Full-credit completion metric before task expansion

Phase 4, correctness gate after the development-only browser feasibility audit.
Both development seeds (61 and 67) loaded all fifteen new candidates with no
model calls or actions and no trees exceeding the current input limit. The same
three tasks expose generic link-styled spans. This update fixes metric semantics
before checkbox or other graded tasks are added to the agent allowlist.

    python -m pytest tests -q

Expected: 188 passed, two opt-in browser checks skipped. No paid run is needed
to verify these deterministic metric tests. Agent actions, permissions, task
allowlists and action/call budgets are unchanged; only the existing five task
families remain supported.

## Shared rule

metrics.full_credit_success requires a finite real reward equal to 1.0 within
absolute tolerance 1e-9 (zero relative tolerance), terminated=True,
truncated=False and no final action error. Booleans, strings, NaN/inf, zero,
negative and genuinely fractional rewards cannot satisfy this rule.
The policy identifier is terminal_full_credit_reward_1_v1.

For the reward-normalized MiniWoB candidates, raw score 1.0 means full credit.
Some checkbox sources also award positive fractional reward when one or more
boxes are wrong. That positive reward remains useful, but it is not exact task
completion. New reports preserve reward and positive_reward_terminal separately
from success and completion_metric. Positive fractional terminal results have
reason partial_credit_terminal and count as failed full-credit episodes.
A final action error or truncation prevents both completion indicators.
This does not redefine the benchmark's graded scoring; it defines the project's
primary exact-completion metric and retains the raw graded signal.

## Consistent use

The iterative graph, one-shot executor and all their evaluator paths use the
same helper. Single-run CLIs and comparison workers include the metric label.
Baseline/paired parsers check reported status and positive-reward consistency,
preserve raw reward, and reject a fractional success claim. Recovery evaluators
inherit these checks through the shared parsers. Summaries count partial-credit
episodes separately. Paired comparisons also require equal metric labels.

Older source reports/evidence files are not edited. Legacy unversioned reports
with full reward remain readable and are labeled legacy_unversioned on parse,
not silently relabeled as a newly produced record. Explicit unsupported metric
labels are rejected. Historical comparisons used binary tasks where successes
were reward 1.0, so this rule does not overturn the results already reported.
It would affect future graded tasks; do not pool metrics without identifying the
policy and rechecking historical raw rewards.

## Tests and scope

188 offline tests passed (163 prior plus 25 new cases). They cover fractional
reward, tolerance boundaries, error/truncation/nonterminal guards, malformed
numeric values, identical iterative/one-shot behavior, parser rejection of false
success claims, raw partial-reward preservation, legacy handling and mixed-metric
pair exclusion. No browser probe or live model call was run in preparation.

Added metrics.py and tests/test_full_credit.py. Updated workflow.py, oneshot.py,
__main__.py, run_oneshot.py, comparison_worker.py, evaluate.py and compare.py.
No schema, model adapter, recovery policy, six-step budget cap, dependency,
credential, vendor asset or protocol task-plan change.

Next: implement idempotent checkbox/radio selection and native-select arguments
with observed-role validation, then separately address tabs and narrowly scoped
clickable-span metadata. Do not add all generic AX nodes to the click allowlist.
The seven-action budget requirement for click-checkboxes remains a separate
reviewed change. Final seeds remain reserved and the protocol is still a draft.
