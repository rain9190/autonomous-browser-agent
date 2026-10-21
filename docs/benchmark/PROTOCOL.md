# Broader benchmark selection and evaluation protocol

**Version 0.1 draft — 22 October 2026. Not frozen or ready for full execution.**

## Project position and objective

This is Phase 4, protocol design after the first comparative experiments. Those
experiments showed tied success with lower one-shot overhead on six predictable
instances, and recovery benefit on two induced-error instances. They did not
establish broad task coverage. The original target is approximately 20–30 tasks,
subject to feasibility. This document proposes 20 task IDs; only five are
currently implemented/allowlisted. Do not call this a completed 20-task benchmark.

The immediate work is source/registration inventory, then browser feasibility
checks without model calls, then minimal capability additions. No final
evaluation is authorized or initiated merely by installing this document.

## Sources checked

The installed BrowserGym core/MiniWoB version is 0.14.3. Candidate task HTML and
associated reward logic were inspected from the existing vendor checkout.
Its Git HEAD was `7fd85d71a4b60325c6585396ec4f48377d049838` during preparation;
per-file SHA-256 hashes in [task-plan.json](task-plan.json) identify actual checked
HTML content, including any local modifications. All 20 primary candidates and
one reserve are registered in the installed Gym registry. Registration confirms
an entry point, not a successful browser episode or suitable accessibility roles.

The [CSV inventory](task-inventory.csv) and JSON plan are the machine-readable
record. The checker validates sources, registrations and seed/call arithmetic
without launching Chromium or calling OpenAI:

```bash
python scripts/check_benchmark_plan.py
```

## Provisional primary set

Budgets are proposed maximum browser actions AND iterative calls, identical
between arms for a given task. One-shot still has one model request. Budgets are
resource policies, not assertions that every instance can be solved within them.
They must be settled using development feasibility before freezing.

| Task | Proposed action budget | Required support / current state |
|---|---:|---|
| `click-test` | 2 | Existing button click |
| `click-button` | 2 | Existing label matching |
| `click-button-sequence` | 2 | Existing ordered clicks |
| `enter-text` | 2 | Existing fill then Submit |
| `login-user` | 3 | Existing two fills then Login |
| `enter-text-2` | 2 | Case conversion; same action types; needs allowlist/probe |
| `click-test-2` | 2 | Distractor button; needs allowlist/probe |
| `click-test-transfer` | 2 | Mode-dependent target; freeze and record WOB_DATA_MODE |
| `click-link` | 2 | Link-styled targets; inspect actual AX roles |
| `click-checkboxes` | 7 | Idempotent checkbox setting and full-credit metric |
| `click-checkboxes-soft` | 6 | Semantic checkbox matching and full-credit metric |
| `click-option` | 3 | Radio selection, then Submit; not a native dropdown |
| `choose-list` | 3 | Native select, matching value/label, then Submit |
| `click-dialog` | 2 | Close control; inspect accessible name/role |
| `click-dialog-2` | 2 | Requested dialog button |
| `click-collapsible` | 4 | Accordion control then Submit |
| `click-collapsible-2` | 6 | Hidden-target discovery across three sections |
| `click-tab` | 2 | Tab role requires validation support |
| `click-tab-2-easy` | 4 | Generated link-styled targets; inspect source/roles |
| `click-tab-2-medium` | 5 | Two-tab task with special second-panel reward behavior; inspect feasibility |

Several IDs are related variants, especially the click-test family. Report task
IDs and interaction families separately; 20 task IDs do not mean 20 independent
capabilities. Include family-level results to expose overrepresentation.

### Declared exclusions and reserve

- `click-checkboxes-large` is reserve/blocked: source selects 5–12 boxes, so exact
  completion can require 13 actions including Submit. This exceeds the current
  six-action policy and the proposed limited seven-action expansion. Do not
  select only easy seeds or count partial credit as completion to include it.
- `button-delay` has local HTML but is not registered in the installed BrowserGym
  version. It also requires an explicit timing policy. It is excluded before
  final results, not because the agent performed badly.
- Coordinate/vision-heavy drawing, dragging, date/calendar and flight-booking
  workflows are outside this proposed scope. No real services or accounts are used.

If a primary task is technically infeasible, record the reason and revise this
draft before final evaluation. Do not silently swap it after inspecting final
performance. If fewer than 20 prove feasible, report the reduced set honestly and
document the scope decision rather than pad it with successful variants.

## Required correctness work before new tasks run

**Graded reward:** the checkbox sources award `(correct - incorrect)/number` and
can return a positive reward despite a wrong box. The existing positive-terminal-
reward rule is appropriate for the binary tasks tested so far but is not an exact
completion measure for these graded tasks. Before promotion, introduce a primary
full-credit metric requiring terminal reward 1.0 (numeric tolerance 1e-9), no
truncation and no final action error. Preserve raw reward and the historical
positive-reward indicator as separate secondary measures. Do not relabel old
binary results or claim partial reward means every requested box was correct.

**Action limits:** normal checkbox tasks can require six checks plus Submit.
Supporting their full distribution requires a reviewed cap of seven rather than
the present six. Update every affected schema, history bound, API allowance,
recursion, timeout, evaluator/parser and batch ceiling consistently, with tests.
Installing this protocol does not increase any current runtime limit.

**Action/role support:** retain strict schemas and observed-target validation.
Add idempotent checkbox setting, radio selection and native select only as
needed. Some visually link-like items are spans and some jQuery controls have
tab roles. Inspect real observations/DOM metadata; do not simply permit all
generic nodes or arbitrary JS. Any metadata enrichment must use a fixed,
deterministic, narrow interface. Document its limits for both agent arms.

**Dynamic observations:** one-shot cannot invent future IDs or receive hidden
page state. A stale or unavailable planned target is a legitimate failed result;
do not add a deterministic repair mechanism only to help it. The iterative arm
can observe newly visible elements. Both retain the same safety checks.

## Development and final instances

| Split | Seeds | Use |
|---|---|---|
| Historical exploratory | 7, 11, 29, 31, 42, 47, 123 | Existing results; not final held-out evidence |
| New development | 61, 67 | Browser-role probes, capability development and budget feasibility |
| Reserved final | 1009, 1013, 1019 | Do not run or inspect task instances until the protocol/code freeze |

The seed split holds out instances, not task families. It is not a blinded or
independent benchmark collection. Do not tune prompts/budgets using reserved
instance observations, even without a model call. Complete initial fingerprints
and relevant mode/source/version settings must be recorded. Matching initial
observations does not prove all future hidden state or timing is identical.

## Comparisons and metrics to freeze

1. **Planning comparison:** one-shot versus iterative, recovery disabled and no
   fault injection, all promoted primary tasks and three reserved seeds. Same
   model snapshot, local source, per-task budget and deterministic safety/full-
   credit completion checks. Alternate order; retain every matched outcome.
2. **Recovery ablation:** iterative recovery off/on with the same induced disabled-
   textbox timeout, on `enter-text` (budget 3) and `login-user` (budget 4), at the
   same three reserved seeds. Confirm equal initial AND first-failure signatures.
   Keep these results separate from no-fault planning success rates.
3. **Optional second ablation:** structured action history off/on on a declared
   multi-step subset, preserving observations, budgets and safety. Define the
   subset and exact intervention BEFORE final execution. It is not yet finalized
   or implemented; omit transparently if time/budget does not permit it.

Primary metric: full-credit completion rate. Also report raw reward, task/family
breakdowns, paired wins/ties, actions, calls, end-to-end time, reported input/output
tokens, unknown usage, failure categories and coverage/matching exclusions. Give
macro averages by task as well as pooled episode rates; keep graded rewards
distinct. Monetary cost needs dated verified pricing and explicit assumptions;
request ceilings are not billing caps. No large-sample significance claim is
justified by three seeds per task, especially related task variants.

## Call envelope, not an instruction to spend

With the draft 20 tasks and budgets, the planning comparison ceiling is **249
model requests** for 120 browser episodes (20 tasks × three seeds × two arms).
The specified recovery ablation adds at most **42 requests** for 12 episodes.
Combined ceiling: **291 requests**, excluding development, technical reruns and
any optional second ablation. The exact ceiling must be recomputed if this draft
changes. No monetary estimate or paid execution is initiated here.

Keep each runnable batch within the existing 24-call planned limit. Use equal
budgets within a pair, even though fail-fast or one-shot may actually use fewer
requests. External deadlines, cleanup and zero hidden SDK retries remain.

## Freeze and acceptance gates

1. Validate this source/registration inventory without API or browser work.
2. Run development-only Chromium probes for each new task: observations, roles,
   reset behavior, reward semantics, modes and technical feasibility.
3. Implement the smallest required metric/action changes and regression tests.
   Keep unsupported tasks unallowlisted until their checks pass.
4. Finalize the task list, per-task budgets, metrics, exclusions, modes, batches,
   optional ablation decision and source/model versions. Commit a versioned
   protocol with status frozen. Do not begin the final seed set before this gate.
5. Run fixed final batches. Retain failures; never retry model-quality failures
   until they pass. API/transport/asset errors make a batch incomplete, not a
   success. Preserve all attempts and unknown costs; any technical rerun or
   protocol amendment must be documented before interpreting the result.
6. Analyze all scheduled coverage and exclusions, not only easy matched pairs.
   Label incomplete/mismatched experiments clearly. Summarize limitations, then
   finish the lightweight demo and portfolio documentation (Phase 5).

**Current acceptance:** the draft inventory checks only. This is a plan and
source audit, not a new capability release or a completed final evaluation.
