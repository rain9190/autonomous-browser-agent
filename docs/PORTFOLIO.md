# CV notes

**Autonomous Browser Agent — Form Assistant**  
Python · LangGraph · OpenAI API · Pydantic · JavaScript · Playwright

- Built a Chrome assistant that fills web fields from natural-language instructions,
  with missing-answer prompts, overwrite confirmation and a Stop button.
- Added structured action validation and read-back checks, with seven local browser
  tests covering ordinary controls, editable regions and accessible embedded fields.
- Compared planning strategies across 120 MiniWoB episodes: iterative passed 57/60
  (95.0%), versus 55/60 for one-shot. Audited 132 records including recovery experiments.

The benchmark is local MiniWoB, not a 95% success claim across real websites. The model
was used through an API, not trained for this project.

For an interview, explain the observe → decide → validate → execute → verify loop, why
field checks are needed even with valid JSON, and the extra requests that iteration costs.

[Results](FINAL-BENCHMARK-REPORT.md) · [Project overview](PROJECT-DETAILS.md)
