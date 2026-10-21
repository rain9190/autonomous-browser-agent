# Portfolio notes

## Summary

Built a bounded browser agent for local BrowserGym/MiniWoB tasks with Python, Pydantic,
OpenAI structured output and a LangGraph observe–decide–validate–execute–verify loop.
Compared fixed one-shot plans with iterative decisions under a frozen 20-task, three-seed
protocol, with matched controlled-recovery experiments and a local trace-viewing demo.

## Resume bullets grounded in evidence

- Built a LangGraph browser agent with Pydantic action validation, observed-target checks,
  fixed Playwright templates, explicit resource budgets and bounded fill recovery.
- Evaluated 120 planning episodes across 20 local MiniWoB task IDs: iterative completed
  57/60 (95.0%) versus one-shot 55/60 (91.7%), using 114 versus 60 reported API calls.
- Audited 132 episode records with source/version fingerprints and matched initial states;
  controlled timeout recovery completed 6/6 enabled versus 0/6 disabled, retaining failures
  and one incomplete-usage flag in the evidence report.

Do not call the small difference statistically significant or describe induced-fault recovery
as production reliability. A fresh live demo is separate from frozen benchmark evidence.

## Interview explanation

**Why a graph?** Each node has one responsibility: normalize observations, make a structured
decision, validate legal actions and targets, execute a trusted template, then verify progress
and completion. Conditional edges support another observation or an eligible fill recovery;
terminal outcomes and budgets stop the loop.

**Why validate targets?** Valid JSON can still choose a stale ID or the wrong element type.
Schema checks and current observed-role membership address different failures. Fixed action
templates avoid executing arbitrary model-generated code, but do not guarantee task success.

**What did iteration buy?** It completed three dynamic-discovery instances where one-shot
plans failed. Overall it completed two more instances while using more requests, and also
failed three instances one-shot completed. This is a task-dependent tradeoff, not a universal
architecture ranking.

**What did recovery prove?** One bounded retry after an induced first-fill timeout recovered
six matched instances. This did not test spontaneous outages, partial side effects or every
action type. Click errors still stop because their side effects may be ambiguous.

**What would you improve?** Final exports lacked action histories and intermediate observations,
limiting diagnosis. Add redacted per-step evidence and loop detection on development tasks in
a new version. Validate against new instances rather than tuning to the final held-out data.

**How did you manage spending?** Explicit action/call/output/input/deadline bounds, zero hidden
SDK retries, small serial batches and usage flags. Final experiments reported 201 calls against
a planned ceiling of 291. Request controls are not hard monetary billing caps.

## Two-minute recording

Show measured results and an included failure, explain the README architecture diagram,
run a two-call development text-entry demo, then explain dynamic observations and controlled
recovery. Report the actual live outcome; do not present saved evidence as live execution.
