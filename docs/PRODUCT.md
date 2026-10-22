# Browser Agent — simple instruction-driven application

## Use it

In the activated project environment, run `python -m app.demo`, then open
http://127.0.0.1:8765. If an old server is running, stop it with Ctrl-C before restarting.
The homepage has only the task composer, Run/Stop, status, optional activity and a short
scope note. It does not load benchmark metrics.

Try “Type quantum computing in the Wikipedia search box, without submitting.”
The first live check should visibly type your phrase in a fresh Wikipedia browser window.
Then try “Search Wikipedia for black holes and open the article.” The agent should type,
submit, and if necessary choose an observed search result. These are examples, not exact
phrases required by the implementation: a structured model call extracts the query and
objective from your instruction.

## What drives the run

The new app/web_agent.py uses Pydantic task/action schemas and a five-node LangGraph
observe → decide → validate → execute → verify workflow, following the evaluated agent's
design. It reuses the installed libraries and model snapshot but does not modify or claim
the measured success rate of the frozen browser_agent implementation. Real-site observations
and actions require a separate adapter. This is an explicit Wikipedia search adapter, not
a generic arbitrary-website policy.

The model parses a task into query and type/search/open objective. It then chooses fill,
submit or open-result actions using current search-field state, visible result links and
history. Action text must equal the parsed query, and results must be observed. Validation
checks the target again before execution. One execution error can prompt fresh observation
within the original budget. Stop interrupts execution rather than entering a retry loop.

## Completion checks and limits

- Type: exact requested text is present in the visible search input.
- Search: an observed search submission led to the requested search URL or an article.
- Open: an observed search submission led to an article (Wikipedia main namespace), either
  directly or by opening a search-result link. The title and URL are returned.

These checks establish browser state and search provenance. They do not independently prove
semantic relevance of every selected article. Query interpretation and relevant-result
selection remain model decisions. If an ambiguous query opens a disambiguation page or a
wrong topic, it can satisfy the namespace check; inspect the returned title before relying
on it. No summaries, factual research or answer correctness are claimed by this version.

The task cap is seven model requests total: one intent call and at most six action calls.
Requests have 20-second timeout, no automatic SDK retry, store=False, max 256 output tokens.
Input and query sizes are bounded. A task deadline is 200 seconds with a 210-second parent
watchdog. At most one task runs at a time. Requests already sent can incur usage after Stop.
There are no additional calls while retaining the finished browser window for inspection.

Browser contexts are fresh and nonpersistent. Navigation is limited to English Wikipedia
articles/search; editing, account pages and other origins are blocked. Only search inputs
and observed search results are actionable. GET/HEAD resource requests to en.wikipedia.org
and upload.wikimedia.org are permitted, with read-only query actions on the API. No form
submission except the observed Wikipedia search field is supported. This is a constrained
local development application, not a comprehensive hostile-site security sandbox.

The homepage binds to loopback, checks Host/Origin and a per-server token, and never displays
API credentials or raw exceptions. User tasks are passed to the worker via stdin, not a shell
or command-line interpolation. Page text stays untrusted. A fresh browser opens per task;
the finished page stays open up to five minutes, until closed, Stop or another run.

The old benchmark screen remains at `python -m app.demo --benchmark` and the fixed Books
trial remains at `python -m website_trial.books`. Neither is run by the new main screen.
Frozen benchmark sources, hashes and final evidence remain unchanged.

## Checks

Run offline tests and the frozen-file checker after installation. Offline tests use fake
pages and fake models, testing variable queries, all three task objectives, scope guards,
Stop propagation and old-worker race protection. No real-site success is claimed until the
user shares a live product result. Site DOM, network restrictions, CAPTCHA or layout changes
may prevent a live run. The application stops instead of claiming success on an exception.

First acceptance check: type a new phrase via the interface, observe it in the Wikipedia
search field, then confirm Stop closes the browser. Next check: search/open a different topic.
All product checks are new development evidence, not replacements for reserved-seed results.
