# Phase 5 release checklist

## Prepared

- Local interface for saved evidence and bounded development runs.
- Actual graph-stage and per-action verification viewer; no invented historical traces.
- Current README, architecture diagram, measured results and explicit setup limits.
- Portfolio bullets, interview explanation and demo walkthrough.
- Offline instruction/seed guards, fixed command, concurrency guard, request boundaries,
  event filtering and fake-worker cleanup tests.
- Frozen agent source unchanged; verify with `python scripts/check_benchmark_plan.py`.

## Remaining

- User smoke-check the interface and first live development run; retain the actual outcome.
- Check Stop/Ctrl-C on the user's Mac; optionally record a short demo.
- Clean-environment reproduction remains unverified: direct pins are not a transitive lock,
  and the existing vendor/Chromium setup is required.
- GitHub push and public sharing have not been requested or performed.
- No project license has been selected by the owner. Choose before public distribution;
  preserve third-party vendor licensing.
- Review old README-* files before any archival move; this update deletes or moves no files.

Use explicit paths for staging. Avoid `git add .` with vendor, environment files and
unreviewed historical notes present. Review staged names before sharing. This checklist
is not authorization to publish remotely.
