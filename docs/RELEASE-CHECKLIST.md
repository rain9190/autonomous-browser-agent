# Phase 5 release checklist

## Prepared

- Local interface for saved evidence and bounded development runs.
- Actual graph-stage and per-action verification viewer; no invented historical traces.
- Current README, architecture diagram, measured results and explicit setup limits.
- Portfolio bullets, interview explanation and demo walkthrough.
- Offline instruction/seed guards, fixed command, concurrency guard, request boundaries,
  event filtering and fake-worker cleanup tests.
- Frozen agent source unchanged; verify with `python scripts/check_benchmark_plan.py`.

## User-verified on 22 October 2026

- Saved evaluation overview loaded: one-shot 55/60, iterative 57/60, recovery on 6/6.
- Text-entry interface run, seed 61: full credit, two calls, two action attempts, no recovery.
- Controlled-timeout interface run, seed 61: full credit, three calls, three action attempts,
  one recovery after the induced first-fill failure.
- Both workers exited 0. User returned to the terminal and committed demo `332f646`.
- Final read-only freeze check passed after the report and demo commits.

## Remaining

- Explicitly check Stop during an active run and restart behavior if needed; optionally record
  a short demo. Active cancellation was not established by the successful-run screenshots.
- Clean-environment reproduction remains unverified: direct pins are not a transitive lock,
  and the existing vendor/Chromium setup is required.
- GitHub push and public sharing have not been requested or performed.
- No project license has been selected by the owner. Choose before public distribution;
  preserve third-party vendor licensing.
- Review old README-* files before any archival move; this update deletes or moves no files.

Use explicit paths for staging. Avoid `git add .` with vendor, environment files and
unreviewed historical notes present. Review staged names before sharing. This checklist
is not authorization to publish remotely.
