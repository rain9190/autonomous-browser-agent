# Project notes

**Autonomous Browser Agent — Form Assistant** is a Chrome extension backed by a local
Python service. It fills supported page fields from instructions and supplied details,
then leaves the final review and submission to the user.

## Main parts

- `extension/`: the side panel, page inspection and fixed field operations.
- `extension_service/`: the local browser/model connection.
- `form_assistant/`: planning, validation and the shared LangGraph workflow.
- `browser_agent/`: the earlier MiniWoB benchmark agent.
- `tests/` and `docs/evidence/`: checks and saved experiment results.

The stack is Python, LangGraph, OpenAI structured outputs, Pydantic and JavaScript.
The project uses a hosted model; it doesn't train or fine-tune one.

## What has been checked

- 340 regression tests passed after cleanup.
- Seven extension browser checks passed using local fixtures and simulated responses.
- The frozen MiniWoB comparison passed 57/60 iterative and 55/60 one-shot instances.
- A user-run Google Form example filled text fields and a radio choice, leaving the
  screenshot upload for manual review.

The real-form example is a working demonstration, not a measured website success rate.
[Benchmark details](FINAL-BENCHMARK-REPORT.md)

## Still to improve

Test more real forms, check installation on a fresh machine, and make the local service
easier to start. Some custom controls, uploads and inaccessible embedded fields remain
unsupported. The source is on GitHub; the extension isn't a Chrome Web Store release.

[Using the extension](EXTENSION.md) · [Development history](history/README.md)
