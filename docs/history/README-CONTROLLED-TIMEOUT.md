# Controlled Playwright fill timeout

## Validate locally, then use the model

    python -m pytest tests -q

Expected: 96 passed, 1 skipped. The skipped check launches Chromium and must be
explicitly enabled; it is not a failed test.

    RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser_timeout.py -q

Expected: 1 passed. This is an actual local BrowserGym/Chromium plumbing test,
with no OpenAI client or API request. It deliberately disables a textbox,
attempts a fill with a 300ms timeout, checks the actual Locator.fill timeout,
confirms the field is enabled and empty afterward, then fills successfully.
It does not attempt autonomous reasoning or claim benchmark completion.

Only after that passes:

    python -m browser_agent --task enter-text --seed 11 --max-steps 3 --max-recoveries 1 --disabled-textbox-timeout-once

Expected: one actual Playwright timeout on the disabled field, a successful
model-chosen fill after a fresh observation, then Submit. Expected success=true,
reward=1.0, steps=3, api_calls=3, recoveries_used=1,
controlled_failure_scenario=disabled_textbox_timeout,
controlled_timeout_confirmed=true. First progress entry should have
execution_ok=false and error_kind=playwright_fill_timeout.

## Mechanism and classification

DisabledTextboxOnce emits fixed trusted action code for the first validated fill.
It checks that the field is initially enabled, disables it, calls Playwright fill
with timeout=300, and restores it in a finally block. IDs and text remain quoted
validated literals. This scenario does not explicitly raise a timeout: Playwright
must produce it because the field cannot accept input. Finally restoration also
runs if filling fails for another reason, although DOM disappearance can prevent
restoration; such a case must not be counted as verified scenario success.

This is still a deliberately induced, controlled failure. It is a more realistic
browser-action error than the earlier injected Python exception, not evidence of
recovery from naturally occurring incidents, network issues, or arbitrary partial
side effects. The failure allowance stays within max_steps/max API calls.
Click errors, API errors and invalid actions still stop rather than retry.

The existing --simulate-fill-error-once flag retains the original Python-exception
scenario. It is mutually exclusive with --disabled-textbox-timeout-once. Both
require local enter-text or login-user and use the simulated-failure requested/
injected markers to keep them out of baseline evaluation. New reports add an
explicit controlled_failure_scenario and include it in their filenames.
The timeout category is derived from BrowserGym's captured exception type and
Locator.fill timeout text; raw diagnostics are not persisted in progress.

## Later multi-seed evaluation

After the first autonomous run passes:

    python -m browser_agent.evaluate_recovery --scenario disabled_textbox_timeout --seeds 11 29

This is two episodes with a six-call ceiling. Results use a unique
results/browser-timeout-eval-... folder and
mode controlled_browser_timeout_recovery. The parser requires actual fill-timeout
confirmation as well as injection, progress and benchmark success. It rejects
these reports in both baseline and Python-exception recovery mode. Summary fields
include confirmed_browser_timeout_episodes and recovered_episodes.

The older recovery evaluator command without --scenario retains its defaults and
its simulated_fill_recovery label. No default test mode or paid workload changes.

## Verification status

96 offline tests passed, including the 87 prior checks. The new checks cover the
fixed disable/fill/finally template, literal quoting, one-shot behavior, mode
separation, timeout confirmation, summaries and scenario propagation. One opt-in
real-browser test is included but was not run while preparing this update. No live
API request or autonomous browser run was made during preparation.

Changed: recovery.py, workflow.py, __main__.py, evaluate_recovery.py.
Added: tests/test_controlled_timeout.py and tests/test_browser_timeout.py.
No API key, dependency, action schema, baseline evaluator or vendor changes.
