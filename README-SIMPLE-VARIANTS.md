# Simple task variants — development validation

Adds enter-text-2, click-test-2, click-test-transfer, click-dialog and click-dialog-2 to both iterative and one-shot task choices, evaluations and comparisons. Existing click/fill schemas, role validation, six-step ceiling and API controls are unchanged. No new prompt rules, hidden page data, dependencies or credential changes.

Source inspection: enter-text-2 requests a case conversion before submission; click-test-2 and click-test-transfer expose the target in the instruction; click-dialog closes the visible dialog; click-dialog-2 requests one of its visible buttons. Transfer is a task name, not evidence of generalization to unseen sites.

These are development candidates, not a frozen or completed benchmark. Use development seeds 61 and 67 only. Keep final seeds 1009, 1013 and 1019 unused. Do not change the benchmark protocol status merely because these task names are enabled.

Install, then run python -m pytest tests -q. Start live validation with python -m browser_agent --task enter-text-2 --seed 61 --max-steps 2 (at most two API calls). Inspect the result before running more tasks. Record failures as development evidence.
