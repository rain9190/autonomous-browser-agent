# Form Assistant for Chrome

A small side panel that fills supported questions in the tab where you click its icon.
The website stays visible. The normal screen has a details textbox, Fill form, Stop and
one status line. Missing-answer and overwrite questions appear only when needed.

## Install

Extract this update into the existing autonomous-browser-agent repository. Keep the
extension folder there; Chrome loads its files from that location.

In the activated project terminal:

```bash
python -m pytest tests -q
python -m extension_service.server
```

The service prints a **connection code**, not your API key. Keep the terminal running.
The code changes each time you restart the service. The existing ignored `.env.local`
OPENAI_API_KEY configuration is reused only when a user starts filling.

In Chrome:

1. Open `chrome://extensions`.
2. Enable **Developer mode**, then **Load unpacked**.
3. Choose `/Users/adwaiy/Projects/autonomous-browser-agent/extension`.
4. Pin **Form Assistant** using Chrome's extensions menu.
5. Open `http://127.0.0.1:8766/practice` and click the extension icon on that tab.
6. Paste the connection code into the panel and click **Connect**.

Connection is tucked behind the small settings button after setup. A restarted service
requires the new code. Stop the service with Ctrl-C when finished. This is a local unpacked
extension, not a Chrome Web Store release; no new dependency or BrowserGym upgrade is needed.

## First live test

Paste this synthetic information in the panel:

```text
Name: Alex Example
Email: alex@example.com
Organization: Example University
Session: Afternoon
Attend Day 1 and Day 2.
Dietary preference: Vegetarian.
Leave optional comments blank.
```

Click **Fill form**. Watch the current practice tab fill, advance to section two and
finish with **Ready for review**. Submission on this practice page is disabled. A normal
successful run needs two model requests; clarification or repair may require more.

To check missing information, omit the Email line. The panel should ask for it before
editing that section. To check overwrite protection, first type a different name in the
form: the panel must offer **Replace** or **Keep existing**. Stop should halt further
interactions; it does not undo previous entries. A request already sent to OpenAI can still
be billed after Stop.

For your real Google Form, open the full responder page first, then click the icon. Use
synthetic details initially. The provided Event registration form includes a required
pay-on-arrival acknowledgement. It must remain unchecked and produce **Needs your review**.
Do not claim all six answers were automated. No real form has been filled or submitted by
our automated tests.

## Page-wide field detection (version 0.2)

The side panel is plain white with standard text and buttons. It has no app logo,
coloured branding, animated status dot or disclosure sentence under the instructions.
Data processing still works as described in the privacy section below.

The detector inspects visible fields throughout the current HTTP/HTTPS page, including
controls outside a form and across multiple forms. It also traverses accessible same-origin
frames and open shadow roots. Search inputs and ordinary contenteditable text regions are
text candidates. Labels, placeholders, titles, names and IDs help identify a field; otherwise
it receives a positional name such as Text box 4. No field is rejected solely for lacking
a formal label. Matching is still model-driven and must be checked by the user.

A visible textbox is a candidate, not an instruction to put the same text in every box.
For example: “Type Paris in the search box and leave the other fields blank”, or “Fill every
empty textbox with Example”. Header searches and other unrelated fields can now be observed
too; be specific about the fields you intend to fill. Unknown facts are not invented.

## Scope

- Accessible HTML text/paragraph/search/email/tel/number/URL inputs, editable text regions,
  ordinary native dropdowns, and labelled radio/checkbox groups.
- Google Forms text, radio, checkbox and supported dropdown questions.
- Supported **Next** transitions that update the page without a full reload. Generic
  native Next buttons with submit semantics are rejected. No arbitrary link/button tool.
- Questions are observed again after an action and values are compared with the proposed
  answers. One bounded repair is available. This is not a semantic guarantee that the
  model matched every fact to the right question; review remains necessary.
- Existing nonempty answers need explicit permission before replacement. Keep existing
  leaves that question for review. A matching existing answer can be verified without edits.

Cross-origin/sandboxed frames, closed shadow roots, files, custom date pickers, CAPTCHA,
passwords, signatures and sensitive declarations are outside the initial scope. Disabled and
read-only fields are left for review. Unlabelled editable textboxes are included using
metadata or a positional name. Closed/custom editors may not expose an editable surface.
Multiple forms are scanned together. Automatic Next requires one unambiguous form or the
Google question adapter; mixed or ambiguous navigation is left for review.
Supported labels/navigation are initially English. Conditional forms and custom widgets need
site-specific testing. A whole-document navigation during Next stops safely rather than
silently resuming on a new page. Switching away from the target tab stops subsequent actions
when the next browser command checks the active tab. Keep the target tab active while running.

## Architecture and privacy

Chrome Manifest V3: activeTab, scripting, sidePanel and session storage. The production
manifest requests host access only to the local service at `http://127.0.0.1:8766/*`.
The toolbar click grants temporary access to the selected page; no all-sites permission,
continuous screen capture, cookie access or history permission is requested.

The extension's packaged isolated content script supplies a DOM adapter. It reads visible field candidates across the
selected page and accessible embedded regions, not the whole desktop. The existing LangGraph observe → decide → validate →
execute → verify workflow now accepts that adapter, so the same Pydantic planner and
provenance/action validation drive the current browser tab. Model output is never executed
as JavaScript. Only fixed observe, field edit and exact Next commands exist.

The Python service binds to loopback. Requests require a random per-launch connection token
and an extension identity; ordinary website origins are refused. The token is kept in Chrome
session storage, with no answers or instructions persisted there. A single task runs at a
time. The OpenAI key remains in Python and is never sent to the extension or website.

Relevant question labels/options/current answers and your supplied details/clarifications
are sent to OpenAI. Password/file values and recognised sensitive controls are excluded.
The application writes no answer/profile logs. Model requests use store=False, though the
provider and destination have their own data policies. Browser autofill, website scripts,
autosave and ordinary Chrome history behaviour remain those of your existing browser.
This extension does not have the separate browser's request-blocking boundary: it never
chooses Submit, and it prevents native submit events while the run is active, but it cannot
guarantee a website will not send data as a side effect of typing or Next. Use trusted forms.

Limits: 24 model calls, 60 counted interactions, 40 observed questions, eight sections,
10-minute task deadline, 3-minute clarification wait and 18-second browser command timeout.
Each API request has a 20-second timeout and SDK retries disabled. These are resource limits,
not a monetary billing cap. Closing the panel attempts to stop the run; if the connection is
lost, the pending browser command expires. Stop cannot recall a request already in flight.

## Verification and remaining acceptance

Offline tests cover the real LangGraph bridge, value read-back, explicit overwrite/keep,
cancellation, stale responses, malformed observations, protected-value redaction and
local-service authentication/origin restrictions. Chromium tests load the actual extension
and local service in a temporary profile with a fake model. They exercise both practice
sections, missing-answer continuation, native control updates and no submission. Additional
DOM checks cover overwrite refusal, Stop, Google-style dropdowns/radio choices and payment exclusion.

Seven local browser checks passed, including the page-wide scan, rich text read-back,
open shadow roots, same-origin frames and independent same-named choice groups. These
checks use local fixtures, not a guarantee about every production website.

The automated harness grants only its temporary localhost page access to replace the manual
Chrome-toolbar activeTab gesture and opens the panel as an extension window. Therefore the
normal toolbar installation, actual sidebar placement, and paid OpenAI planning on a real
website remain manual acceptance steps. Automated browser success is not a universal form
compatibility or live-model success claim.

The old browser app and frozen benchmark evidence are preserved. No benchmark scores are
changed by this extension.

Official implementation references: [Chrome side panels](https://developer.chrome.com/docs/extensions/reference/api/sidePanel),
[temporary active-tab permission](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab),
[Playwright extension testing](https://playwright.dev/python/docs/chrome-extensions).
