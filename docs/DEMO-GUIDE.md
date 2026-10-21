# Demo walkthrough

## Recorded evidence: no credits

Run `python -m app.demo` in the activated repository terminal, then open
http://127.0.0.1:8765. Leave the terminal running. The page should show one-shot 55/60,
iterative 57/60, and controlled recovery on 6/6. Explain that planning used 60 versus 114
reported requests. The eight planning failures remain visible in the episode filter.
Saved exports lack action traces, so this panel shows metrics rather than invented decisions.
If evidence is unavailable, install the final report bundle first.

## First live check: at most two calls

Choose **Type the requested text and submit**, seed 61, then click **Run live** once.
Watch observe → decide → validate → execute → verify, followed by the next decision and
submission. Full credit requires verified benchmark completion, not merely executed actions.
Chromium is headless: the interface shows a workflow trace, not live video or screenshots.
Filled text and synthetic login credentials are omitted from events. The instruction selects
one supported scenario; the benchmark supplies exact synthetic text and labels.

## Optional demonstrations: additional credits

- **Find the requested link inside the sections**: at most six calls; show fresh observations
  after revealing targets. Do not promise success.
- **Complete text entry with a controlled timeout**: at most three calls; the first fill is
  deliberately made to time out, then one recovery is allowed within the budget.
- **Complete the synthetic login form**: at most three calls; generated values stay out of
  the displayed instruction and trace.

A failure is a valid demo outcome. Use development seeds 61/67 only. Live events stay in
memory and reset for a new run; they never replace frozen evidence. Closing the browser tab
alone does not cancel the worker. Use Stop or Ctrl-C in the server terminal. Stop kills the
worker process group, may prevent graceful cleanup, and flags incomplete usage. The deadline
also stops an overlong worker. Do not expose this single-user development server externally.

## Verified user runs and remaining checks

On 22 October 2026, the user shared screenshots confirming that the saved overview loaded
and both live seed-61 checks completed with full credit and worker exit 0:

- Text entry: fill [14], click [15]; two calls, two action attempts, zero recoveries.
- Controlled timeout: failed fill [14], successful fill [14], click [15]; three calls,
  three action attempts, one recovery. The failed attempt consumed budget as intended.

See [DEMO-VERIFICATION.md](DEMO-VERIFICATION.md). These were actual user-run interface
checks, separate from the 132 final benchmark episodes. They were not rerun for documentation.

Still unconfirmed by the screenshots: the expanded 132-row table/filter, Stop during an
active run, prevention of concurrent runs in the live UI, and restart behavior. Offline tests
cover several boundaries but do not substitute for those manual interface checks.
