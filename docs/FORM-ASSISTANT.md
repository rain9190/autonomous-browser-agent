# Form Assistant — first complete implementation

## Start and use

Run `python -m app.demo` in the activated repository environment and open
http://127.0.0.1:8765. Stop an old server with Ctrl-C before restarting.
The default homepage is now the simple Form Assistant. The old Wikipedia screen is
available with `python -m app.demo --wikipedia`; the benchmark screen remains available
with `--benchmark`. Neither old workflow runs from the form homepage.

The screen has a form URL, one textbox for instructions/details, Fill form, Stop and status.
An inline question appears only when a required answer is missing. Activity is collapsed.
There is no evaluation dashboard in the product. A fresh visible Chromium window shows the
actual field interactions. At completion it stays open for up to ten minutes for review.

First click **Try a practice form**, then **Fill form**. Sample details are synthetic and
submission is disabled on this local form. It exercises two sections, text/email inputs,
a dropdown, multiple checkboxes and a radio question. Normally this requires two planning
calls; missing-answer/retry cases can require more. The hard allowance is 24 model calls.

To test missing-answer handling, delete the Email line from the practice sample. The app
should ask for Email inline; after your reply it replans and continues. Replies and details
stay in memory and are not saved as a profile or recorded in activity events.

## Supported real forms

Public Google Forms responder URLs, including forms.gle links, are accepted. Sign-in,
account pages, arbitrary domains, file URLs and editing links are rejected. We inspected
the user's public Event registration form without entering answers: the adapter detected
Name, Email, Organization, attendance checkboxes and dietary radio choices. It also detected
the required pay-on-arrival acknowledgement and correctly marked it manual-review-only.
That is a read-only compatibility check, not a successful live LLM fill claim.

The adapter supports short/paragraph text, ordinary radio/checkbox choices, dropdowns and
supported Next-based sections. Values are read back after entry. Next and Submit are distinct;
there is no Submit action. Forms that depend on a POST to formResponse even to advance may
be blocked by the review-first policy. The app stops instead of allowing that submission.
Not all Google Forms layouts, branching patterns or validation rules have been tested.

The actual public test form's description contains old template dates and a pay-on-arrival
statement. Treat it as a user-authorised test form, not evidence of a real current event.
Use synthetic details first. The assistant must leave the payment acknowledgement unchecked;
the expected outcome is partial completion with manual review, not a fully ready form.

## Answer selection and checking

A page-level Pydantic Plan maps observed field IDs to fill/ask/leave. The model must return
one entry for every observed question, exact observed option labels, and evidence excerpts
from supplied information. Text values must be present in that information. This prevents
free invention of text but does not independently prove every semantic field mapping or
choice interpretation. Final human review is still necessary.

Missing required answers cause an inline question. Corrections are task-local and re-planning
uses fresh observations. Unspecified optional fields may be left blank. Already correct values
are checked without unnecessary edits. Checkbox selections are set idempotently, including
unchecking unwanted options, and field values/options are compared with the requested plan.

The LangGraph workflow is observe → decide → validate → execute → verify. It retains compact
page state, an answer ledger, checked count, budgets and error state. Next triggers a new page
observation. One bounded repair opportunity re-observes failed field actions; persistent errors
stop. Replanning after clarification remains under the original call/time limits.

Unsupported controls, selected Other-with-text, payment/consent/terms/credentials and other
protected declarations are manual review. Files, CAPTCHA, legal signatures and complicated
booking calendars are not automated. A missing or ambiguous fact must not be guessed.

## Completion states

- **Ready for review:** supported supplied answers were checked, no observed ordinary required
  question remains empty/invalid, and a final Submit button was observed. It was not clicked.
- **Manual review:** supplied ordinary answers are filled, but protected or unsupported questions
  remain. The app lists their labels. On an early section this can prevent further progression.
- **Partly completed / error:** a field, navigation or budget could not be verified. Completed
  answers may remain on the destination website. Stop cannot undo them.

The checked count refers to answer read-backs in visited sections, not a server-side guarantee
of persistence or a semantic guarantee. Current-page required/format errors are inspected;
not every custom server validation rule can be determined before submission.

## Privacy and resource controls

The existing ignored `.env.local` key is used only when the user starts a live run. It is never
passed to the form. Relevant question text, current answers, user instructions and clarifications
are sent to the OpenAI model; do not describe this as local-only processing. The destination
form may autosave while typing. No full answer/profile log is written by the application;
stdout events omit entered values and raw exception bodies. Browser sites and the API have
separate data-handling behaviour. Use synthetic information for initial tests.

Browser context is fresh/nonpersistent, service workers blocked, no saved account credentials,
downloads disabled. Requests are restricted to respondent pages and required Google resources;
formResponse/submit endpoints are blocked. Some background form functions may consequently fail.
This is a constrained local application, not a comprehensive hostile-page security sandbox.

Limits: 24 model calls, 60 counted edit/navigation interactions (dropdown selection conservatively
counts two; checkbox changes count individually), 40 distinct observed questions, eight sections,
a 600-second task deadline and 660-second parent watchdog. Waiting for one answer is capped at
180 seconds and counts toward that deadline. Each request has 20-second timeout, max_retries=0,
store=False, at most 4096 output tokens and bounded input. These are not monetary billing caps.
The parent closes the task on Stop, with a forced kill fallback; in-flight usage can be incomplete.

## Verification performed during preparation

- Offline unit tests cover URL/request scope, answer provenance, unobserved choices, protected
  payment questions, missing-answer continuation and stale question IDs.
- Four local Chromium tests use fake model responses: a real two-page practice DOM run,
  Google-style radio/Other and dropdown controls, and the UI question/continue flow. No API calls or submissions.
- Read-only Chromium inspection of the supplied real form detected all six questions and
  the manual-review acknowledgement, with zero entered answers or submissions.
- Frozen MiniWoB source and final benchmark evidence are unchanged. Product runs do not
  contribute to the previous 57/60 benchmark score.

The live model-driven acceptance run is deliberately left for the user, consistent with the
project's established workflow. Its actual success or failure must be recorded before claiming
real-form completion. A successful practice run alone is not a universal real-form guarantee.
