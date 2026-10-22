# Final project details

## Identity and purpose

**Project:** Autonomous Browser Agent — Form Assistant.
**Deliverable:** a locally loaded Chrome extension plus Python model service.
**Product version:** 0.2.0, local prototype.
**Use case:** reduce repetitive entry on registration, enquiry and ordinary application forms
by mapping user-supplied facts to visible fields, then leaving the final review to the user.

The user opens a website, invokes the assistant, supplies instructions/details, clicks Fill
form and watches the current page update. The panel asks for missing information or overwrite
permission only when necessary. Stop interrupts subsequent actions. The assistant has no
Submit tool. It does not continuously watch the desktop.

## What was built

- Chrome Manifest V3 side panel with activeTab access, a packaged isolated DOM adapter,
  and a plain instructions/buttons/status interface.
- Detection of visible fields throughout the current page, including search inputs,
  standalone textboxes, multiple forms, ordinary contenteditable regions, open shadow roots
  and accessible same-origin frames. Missing labels fall back to metadata or a positional name.
- Existing Google Forms question handling, native radio/checkbox/dropdown control, and
  supported in-page Next transitions.
- A shared LangGraph observe → decide → validate → execute → verify workflow, strict
  Pydantic plans, evidence checks against supplied information, fixed operations, read-back,
  bounded retry, inline clarification and explicit overwrite confirmation.
- An authenticated loopback Python service with session cancellation, browser-command and
  clarification timeouts, and model/action/field/section limits. The OpenAI key stays in Python.
- A frozen BrowserGym/MiniWoB research suite, paired planning comparisons, controlled recovery
  experiments, audited exports and preserved source/protocol fingerprints.

The project uses an existing hosted language model. No model training or fine-tuning was
performed. Product browser interaction uses the DOM; benchmark automation uses Playwright
and BrowserGym. The plain interface exposes neither the benchmark dashboard nor raw logs.

## Verified evidence

| Evidence | Result | Scope |
| --- | --- | --- |
| Final regression suite after isolated cleanup | 340 passed; 21 opt-in browser checks skipped | Includes four cleanup checks; no paid model acceptance |
| Targeted extension Chromium checks | 7 passed | Local fixtures and simulated model responses |
| Frozen iterative planning | 57/60; 95.0% | Local MiniWoB, 20 task IDs × three seeds |
| Frozen one-shot planning | 55/60; 91.7% | Same paired local instances |
| Controlled recovery enabled / disabled | 6/6 versus 0/6 | Intentionally induced first-fill timeouts |
| Final experiment records | 132 episodes; 66 matched pairs | 120 planning + 12 recovery episodes |

Final experiments reported 201 API calls; one planning episode has potentially incomplete
usage reporting. The planning difference is small and task dependent; it is not a claim of
statistical significance. Controlled recovery is not a production uptime measurement.
See the unchanged [audited report](FINAL-BENCHMARK-REPORT.md).

The supplied public Google Form was previously inspected read-only. That is compatibility
inspection, not proof that the extension has completed real forms with the live model.
The extension toolbar installation and live real-website acceptance remain user-run checks.
Earlier benchmark-interface runs were user-verified separately, as recorded in
[DEMO-VERIFICATION.md](DEMO-VERIFICATION.md).

## Limits and remaining work

The extension cannot guarantee every form: closed shadow roots, cross-origin/sandboxed frames,
CAPTCHA, files, sensitive declarations, read-only fields and some rich editors remain outside
scope. Next transitions that reload the document stop rather than silently resume. Website
scripts may autosave or send data when a field changes, despite the lack of a Submit tool.
Human review remains necessary for meaning, field matching and the website's business rules.

The prepared deliverable is a usable local prototype with automated fixture coverage.
A broad live-website evaluation, clean-machine installation, distributable service packaging
and Chrome Web Store release are future work. No public deployment, license selection or
repository publication is implied by finalizing these local files.
