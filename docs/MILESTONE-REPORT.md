# Milestone report — 21 October 2026

## Outcome

The project progressed from a manual BrowserGym click smoke test to an API-driven
LangGraph agent supporting validated clicks, text entry, ordered execution,
configurable budgets, progress records and bounded simulated fill recovery.

The latest offline suite has 87 passing tests, verified during preparation of
the recovery-evaluation update. Live runs were executed by the user on a MacBook
Air M4. This report checked the saved evaluation summaries against the results
shared in chat. Documentation preparation made no additional live API calls.

## Selected evidence

These are distinct evaluation runs, not a pooled statistical success estimate.
The 100% figures describe only the listed task/seed pairs.

| Evaluation | Tasks and seeds | Passed | API calls / ceiling | Input / output tokens |
|---|---|---:|---:|---:|
| Baseline regression after recovery support | Four click/text tasks × seeds 7, 123 | 8/8 | 12/16 | 3,574 / 169 |
| Earlier baseline login milestone | `login-user`, seeds 7, 42, 123 | 3/3 | 9/9 | 3,212 / 130 |
| Injected fill recovery | `enter-text`, seeds 7, 42, 123 | 3/3 | 9/9 | 2,763 / 129 |
| Injected fill recovery in a longer task | `login-user`, seeds 7, 42, 123 | 3/3 | 12/12 | 4,696 / 175 |

All four saved summaries report complete runs, zero unattempted episodes,
no interruption, and zero episodes with unknown API usage. Both recovery suites
confirm three injections and three recovered episodes. Together they demonstrate
6/6 controlled injected recoveries across two tasks and three seeds.

The baseline login suite predates the recovery changes. The eight-episode
regression followed recovery support but preceded the final recovery-evaluator
wrapper. Current-code natural baseline login and a baseline suite after that
last wrapper update have not been separately established by the selected live
evidence. Later wrapper changes passed offline tests and their recovery suites.

Curated summary copies, containing no key or filled strings:

- [Baseline regression, 8 episodes](evidence/baseline-regression.json)
- [Earlier baseline login, 3 episodes](evidence/baseline-login.json)
- [Text recovery, 3 episodes](evidence/simulated-text-recovery.json)
- [Login recovery, 3 episodes](evidence/simulated-login-recovery.json)
- [Evidence provenance](evidence/manifest.json)

The original summaries remain under ignored `results/` directories. Evidence
copies preserve their original fields; older baseline files predate the explicit
`evaluation_mode` field. The provenance manifest supplies their classification.

## Milestones and verification

| Milestone | Verification available |
|---|---|
| Day 1 manual click | Successful user-operated smoke test; original script retained |
| Autonomous click | Three successful seeds; schema, adapter and graph checks |
| Button choice and sequence | Live button/sequence success; two-pass workflow trace |
| Evaluation infrastructure | Unique folders, sanitized records, timeout cleanup and budget tests |
| Text entry | Exact benchmark text then Submit; successful live evaluation and regression |
| Configurable multi-step budget | Three-action login evaluation, progress and budget enforcement tests |
| Controlled fill recovery | Failed attempts excluded from successful history; injected demo and baseline regression |
| Recovery evaluation | Separate modes, injection confirmation, recovery metrics and six successful controlled episodes |

Offline test count grew from 15 to 87 as capabilities were added. These tests
exercise fake models/environments and parser/process controls. They are not 87
live browser episodes, and passing them does not guarantee API access or balance.

## Environment checked

| Component | Version |
|---|---|
| Python | 3.11.9 |
| BrowserGym core | 0.14.3 |
| BrowserGym MiniWoB | 0.14.3 |
| OpenAI Python SDK | 3.35.1 |
| LangGraph | 1.2.16 |
| Pydantic | 2.14.1 |
| python-dotenv | 1.2.4 |
| pytest | 9.1.1 |
| API model | `gpt-4.1-mini-2025-04-14` |

These are versions inspected in the existing `.venv`, not a transitive dependency
lock. The existing vendor checkout and installed Chromium were reused. No Git
repository was present at the project root when documentation was prepared, so
there is no verified commit identifier for the reported runs. User-created ZIP
backups and historical update bundles provide file snapshots, not Git provenance.
The evidence manifest also records SHA-256 hashes of the current project Python
files at documentation preparation. These identify that snapshot, not the exact
source used by the earlier live runs.

## Interpretation and remaining limits

Baseline success and simulated recovery are different measurements. Recovery
requires an explicitly injected pre-fill failure, a fresh observation and a
subsequent benchmark-confirmed success. It does not demonstrate recovery from
natural timeouts, detached elements, partial mutations, navigation failures or
arbitrary exceptions. Repeating fill is limited to the local benchmark setting;
click errors are not automatically retried.

The tested seeds are a very small, repeatedly used set, not a held-out or broad
random sample. Repeated runs on overlapping seeds should not be counted as
independent evidence of generalization. Only five local task families and two
action types are supported. No real websites or accounts were evaluated.

Progress establishes reported action execution separately from terminal benchmark
success. It does not independently prove that each field value matches the goal
before submission. Intermediate reward and error-free execution alone cannot
establish success.

Call, output and input limits are operational bounds, not billing caps. Reported
tokens are usage returned by successful requests; error paths can have unknown
usage. No monetary cost is inferred here. Synthetic values can appear in ignored
single-run action histories; curated evaluation evidence excludes them.

## Recommended next work

1. Preserve the working code in version control after checking secret exclusions;
   this report does not initialize or publish a repository.
2. Establish a current-code baseline including login, then use separate unseen
   seeds for future capability evaluation without repeatedly tuning to them.
3. Add controlled natural browser-error scenarios, such as a field temporarily
   unavailable, and verify that partial effects cannot cause duplicated actions.
4. Expand actions or tasks only with corresponding validation, failure tests,
   and distinct baseline/recovery measurements.

Existing command examples are in the [project README](../README.md). This
documentation records verified milestones without initiating more paid runs.
