# Day 2: autonomous MiniWoB click-test

This adds an actual API model adapter and a LangGraph workflow:
observe → decide → validate → execute → verify. A nonterminal result returns
to observe, up to two browser actions and two API calls. No human chooses the ID.

## Run from the existing repository

```bash
source .venv/bin/activate
python -m pytest tests/test_day2.py -q
python -m browser_agent --seed 42
```

The live command uses the existing local vendor MiniWoB checkout and Chromium
installation. It loads OPENAI_API_KEY from the environment or .env.local without
printing it. Do not source, print, commit, or share that file. The template
.env.example contains no key. .env.local should have permissions 600.

Success requires positive benchmark reward, a terminated episode, no action
error, and no truncation. A successful click with zero reward does not pass.
The command exits 0 only on verified success. It prints a compact report and
writes results/day2-last-run.json; the report contains no key or raw page text.

## Files

- browser_agent/actions.py: strict Pydantic click schema and observed button ID validation.
- browser_agent/model.py: OpenAI Responses structured-output adapter.
- browser_agent/workflow.py: five explicit LangGraph nodes and bounded loop.
- browser_agent/__main__.py: local benchmark configuration, cleanup, safe error reporting.
- tests/test_day2.py: offline tests using fake model and environment.
- requirements-day2.txt: exact versions checked in the existing environment.

## Controls and limits

The model receives only the benchmark goal and accessibility tree. The adapter
uses gpt-4.1-mini-2025-04-14, the official OpenAI endpoint, no SDK retries, a
20-second request timeout, at most two calls, and at most 256 output tokens per
call. Each request accepts at most 1,000 goal characters and 8,000 tree characters.
These bound requests and output; they are not a dollar-denominated billing cap.
Input token totals include schema and prompt overhead. Actual usage is reported
after completed requests. Failed calls may still be billable.

The runner has a 90-second Unix alarm and a 60-second benchmark episode limit.
The alarm is an in-process safeguard, not an external process watchdog.
Validation or API errors stop the run rather than asking the model to repair
actions indefinitely. Fresh observations precede each decision. Only IDs from
button-role accessibility nodes are executable.

No eval or exec is used in this project code. BrowserGym itself executes its
action mapping internally: this mapping accepts only validated JSON and emits
one fixed Playwright click template with a quoted ID. Arbitrary model code,
navigation, file uploads, and multi-action strings cannot reach that mapping.
BrowserGym configures Playwright test IDs to use its `bid` attribute.

## Verification so far

15 offline tests passed with OpenAI SDK 3.35.1, LangGraph 1.2.16,
Pydantic 2.14.1 and pytest 9.1.1. BrowserGym core and MiniWoB are 0.14.3.
Responses.parse and StateGraph imports/signatures were checked locally.
No live model request or browser episode has been run for Day 2 yet.
API key creation does not establish API credit balance or model access.

If the run returns HTTP 429, check the API account's billing/usage limits.
HTTP 401 suggests a credential issue; HTTP 403/404 may indicate model or project
access. Do not paste the key when sharing errors. Avoid enabling SDK debug logs.

Official references checked for this implementation:

- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/models/gpt-4.1-mini
- https://docs.langchain.com/oss/python/langgraph/graph-api
