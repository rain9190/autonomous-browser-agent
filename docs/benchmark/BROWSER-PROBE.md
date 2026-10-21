# Development-only browser feasibility probe

Project position: Phase 4, acceptance gate 2 of the draft benchmark protocol.
Source/registration audit passed. This probe checks initial browser observations
before expanding action support or counting candidate tasks as implemented.

    python -m pytest tests -q
    python scripts/probe_benchmark_tasks.py --seed 61

Expected offline suite: 163 passed, two opt-in browser checks skipped. The probe
runs all fifteen new primary candidates at the declared development seed 61.
It launches local Chromium per task, resets, reads the accessibility tree and
fixed DOM control metadata, then closes. There is no model client, API call,
action execution, form submission or env-file load. This does not measure success.

Default fifteen-task audit can take a few minutes. Each isolated task worker has
a forty-five-second external deadline with process-group cleanup. Any failed or
timed-out probe stops the audit to allow diagnosis; failures are retained.
Ctrl-C preserves completed records and a partial summary. Only declared primary
tasks and development seeds 61/67 are accepted. Reserved final seeds and all
other seed values are rejected before starting workers, including worker mode.

Optional smaller subset for diagnosis only:

    python scripts/probe_benchmark_tasks.py --seed 61 --tasks click-link choose-list

No task is promoted based only on a successful observation. The underlying
agent allowlists, schemas, action budgets and metrics remain unchanged.

Records are saved to unique results/feasibility-TIMESTAMP-ID/ directories.
summary.json includes planned/attempted/observed counts, completeness, per-task
bid-bearing accessibility role counts, native checkbox/radio/select counts,
link-styled spans without link/button AX roles, and input-size warnings.
Per-task files contain the synthetic development goal, initial tree up to 16,000
characters, a fingerprint and at most 100 DOM control records. The actual tree
length is recorded so an input over the current 8,000-character agent cap is
flagged rather than silently treated as supported. DOM truncation is also flagged.
WOB_DATA_MODE is read as configuration metadata, relevant to the transfer task.

DOM metadata includes native tag/type, labels, explicit ARIA roles, selected
options, checked/disabled state, visibility and observed bid-to-AX-role mapping.
Visibility is an initial geometry/style approximation, not an actionability test.
Some DOM-only controls may be hidden or absent from the AX tree. They remain
marked as such: this audit data must not be handed to a model as hidden target
information. No benchmark expected-answer variables or reward internals are read.
The fixed DOM reads do not widen agent permissions or permit generic-node clicks.

Offline verification: fifteen new tests cover split/task guards, observation
metadata correlation, truncation warnings, report persistence, stopped audits,
interruption and external timeout cleanup. All 148 previous offline tests still
pass. Actual browser probes were NOT run while preparing this bundle; the user
runs them next. Zero API requests were made in preparation.

Added only: scripts/probe_benchmark_tasks.py, tests/test_benchmark_probe.py and
this document. No existing agent, protocol manifest, dependencies, credentials,
vendor assets or paid experiment configuration are modified.

Next dependency: inspect the audit results, document role/observation blockers,
and implement the primary full-credit metric plus the smallest necessary action
support. The final protocol remains a draft and reserved seeds stay unused.
