# Text-entry milestone

Run from the existing repository and activated .venv:

    python -m pytest tests -q
    python -m browser_agent --task enter-text --seed 42

Expected: fill the observed textbox with the requested name, observe the updated
page, then click Submit; success=true, reward=1.0, steps=2, api_calls=2.
The MiniWoB task generates the requested string. It is not hardcoded in the
agent or model prompt. The offline test fixture uses Ada as synthetic test data.

After the first live success:

    python -m browser_agent.evaluate --tasks enter-text --seeds 7 42 123

This evaluates three episodes, at most six model requests. For a full regression:

    python -m browser_agent.evaluate --tasks click-test click-button click-button-sequence enter-text --seeds 7 123

This runs eight episodes, at most sixteen requests. The default evaluator still
runs the original six click-only episodes to preserve the previous default cost.

Controls: two actions/calls per episode, 20-second API timeout, no SDK retries,
90-second in-process alarm, 100-second external timeout during evaluation,
256 output tokens per call, bounded observations and history. Fill text has a
256-character limit and must be nonempty. Click text must be null. The structured
API schema uses a single object with action, bid and nullable text. Application
validation enforces the action-specific text rules and observed element role.
Only button IDs may be clicked; only textbox IDs may be filled. Unknown/stale IDs
are blocked. A fresh observation follows filling before the next model decision.

BrowserGym internally executes its mapping. This project's mapping emits only
fixed Playwright click/fill templates with Python-quoted literal arguments. Text
containing quotes, newlines, Unicode or code-looking strings remains data; no
model-generated code is executed. The preserved ClickAction class supports older
fixtures; Action is the click/fill schema used by the real adapter.

The local enter-text benchmark was inspected: an exact string match followed by
Submit determines success. No external websites, arbitrary navigation or file
operations have been added. Action history in the single-episode report includes
the synthetic typed text. Do not use these reports for real sensitive form data.
Evaluation reports continue to save only known summary fields.

Verification: 48 offline tests passed, including all 35 prior tests and 13 new
text-entry tests. SDK schema generation was checked locally. No live model or
browser run was made while preparing this update; the user runs that next.

Updated files: browser_agent/actions.py, model.py, workflow.py, __main__.py,
evaluate.py. Added: tests/test_text_entry.py and this document. No credentials,
environment files, dependency changes or vendor files are included.
