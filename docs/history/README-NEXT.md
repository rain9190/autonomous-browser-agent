# Next click milestones

Run from the existing project and activated virtual environment:

    python -m pytest tests/test_day2.py tests/test_next_milestone.py -q
    python -m browser_agent --task click-test --seed 42
    python -m browser_agent --task click-button --seed 42
    python -m browser_agent --task click-button-sequence --seed 42

18 offline tests passed on the existing installed package versions. No live API
calls or browser runs were made while preparing this update.

click-button asks the agent to match a requested label among generated content.
The number of candidate buttons varies by seed. click-button-sequence requires
ONE followed by TWO. No button ID or sequence decision is hardcoded in the
model adapter. Previous validated clicks are included in its next request.

The runner accepts only these three local tasks. Defaults remain click-test and
seed 42. The same two-request/two-click, timeout, input-size, and output-token
limits apply. History is also bounded. Each click gets a new observation and
validation against the currently observed buttons. Errors stop execution.

Reports now include task name and action history, and are saved as
results/day2-TASK-seedSEED.json. Repeating the same task/seed overwrites its
report. Reports contain no API key. The bundle does not include env files,
credentials, dependencies, vendor files, or previous run results.

The update replaces browser_agent/model.py, workflow.py, __main__.py and the
existing offline tests (whose fake model now accepts optional history), and adds
tests/test_next_milestone.py. Existing actions.py and __init__.py are unchanged.
