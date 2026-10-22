# Small multi-seed evaluation

Activate the existing .venv, then run:

    python -m pytest tests -q
    python -m browser_agent.evaluate

Defaults: click-test, click-button, click-button-sequence at seeds 7 and 123.
Six serial episodes; at most 12 API calls with the current two-call episode
limit. No hidden retries. This is a request cap, not a dollar billing limit.
The runner enforces at most 12 distinct task/seed pairs (24 calls maximum).

Optional explicit selection:

    python -m browser_agent.evaluate --tasks click-button click-button-sequence --seeds 7 42 123

Each episode starts a separate process using the existing Python environment.
The runner allows 100 seconds per episode, beyond the existing 90-second
in-process alarm, and kills the process group on timeout or Ctrl-C. Timeout,
API, configuration, or invalid-report errors stop the suite. Benchmark failures
continue and count as failures in the attempted-episode success rate.

Each evaluation creates results/eval-TIMESTAMP-UNIQUEID/ with one sanitized JSON
record per completed attempt and summary.json. Existing single-episode reports
may still be overwritten by the underlying runner; evaluation records are kept
separately. This evaluator reads current subprocess output, never stale files.
Raw stdout/stderr, environment variables, and credentials are not saved.

The summary reports planned, attempted, unattempted, successes, success rate on
attempted episodes, per-task results, and reported API/token usage. Failed
requests can have unknown usage, which is explicitly counted rather than
claimed to be zero. Ctrl-C preserves previously completed records and a partial
summary. An incomplete suite must not be described as an overall pass.

Exit status 0 means all planned episodes passed; otherwise it is 1.

Verification: 35 offline tests passed using the existing .venv, including
subprocess timeout cleanup, safe reports, budget validation, failure accounting,
partial summaries and the previous 18 agent tests. No live API evaluation was
run while preparing this bundle. These six episodes are a small smoke evaluation,
not a statistically reliable estimate of general browser-agent capability.

This bundle only adds browser_agent/evaluate.py, tests/test_evaluate.py, and
this README. It does not alter the working model adapter or browser workflow.
