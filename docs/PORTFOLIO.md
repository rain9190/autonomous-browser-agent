# CV and interview notes

## Project listing

**Autonomous Browser Agent — Form Assistant**  
Python · LangGraph · OpenAI API · Pydantic · JavaScript · Chrome Extensions · Playwright

Built a Chrome assistant that maps natural-language instructions and supplied details to
visible website fields, executes validated actions, checks their results and leaves submission
to the user. Developed and evaluated its underlying browser workflow on local MiniWoB tasks.

## Suggested CV bullets

- Built a Chrome form-filling assistant with a Python/LangGraph backend, structured action
  validation, DOM observation, inline clarification, overwrite confirmation and cancellation.
- Extended field discovery across standalone inputs, editable text regions, multiple forms,
  open shadow roots and accessible same-origin frames; verified browser flows with seven
  local Chromium checks using simulated model responses.
- Evaluated one-shot versus iterative planning over 120 MiniWoB episodes: iterative achieved
  57/60 successes (95.0%) versus 55/60 (91.7%); preserved a separate matched controlled-recovery
  study and audited 132 episode records.

Use two or three bullets depending on available space. Keep the words “MiniWoB” and “local”
when citing the benchmark; 95% is not a real-website form success rate. Do not claim the model
was trained, production deployment, universal form support or real-world reliability.

## Interview explanation

**Why use a browser agent?** It provides instruction-driven assistance on the page the user
already has open. It can interact with supported fields without a separate integration for
each form provider. A dedicated API can be more reliable when one known service is the entire
product; browser operation is a deliberate interface/generalization tradeoff here.

**Why LangGraph?** It separates observation, structured decision, validation, execution and
verification, with explicit edges for clarification, bounded retry and the next section.

**What is validated?** Plan shape, observed target/option membership, supplied-text provenance,
field identity, current values, budgets and permission to overwrite. These do not independently
prove every semantic mapping is correct; the user still reviews the form.

**What did the experiments establish?** On a small frozen local benchmark, iteration completed
two more instances overall while using more calls. One bounded retry recovered six induced
fill timeouts. Neither experiment establishes universal architecture superiority or production
reliability. Failures and an incomplete-usage flag were retained.

**What would come next?** Measure live-model outcomes on explicitly supported public forms,
record compatibility by control type, improve custom-editor handling, test installation on a
fresh machine and package the local service for easier startup.
