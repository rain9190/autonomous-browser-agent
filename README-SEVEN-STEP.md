# Seven-step checkbox development milestone

Enables click-checkboxes in all task runners through the shared evaluation list and the single iterative CLI. The source can create up to six checkboxes; checking six and submitting needs seven actions. Full-credit terminal reward 1 remains required; partial checkbox rewards do not count as success.

Raises the explicit episode maximum from six to seven consistently across Budget, one-shot plan schema, iterative/one-shot CLIs, comparison workers, recovery evaluator and ablation CLI. Default remains two actions; no automatic budget escalation. Existing model call caps, 4000-character history cap, observation caps, fixed action validation, max_retries=0 and 24-call suite/comparison caps remain. Seven-step timeout is 190 seconds; subprocess grace remains ten seconds. One-shot remains one API call, output allowance 256 tokens per permitted action.

Offline tests verify a six-checkbox plus Submit sequence in both modes, stopping at six, rejecting an over-budget plan before any execution, and rejecting four seven-step episodes against the 24-call cap. Existing upper-bound tests now reject eight steps/actions.

Install then run python -m pytest tests -q. Live development check: python -m browser_agent --task click-checkboxes --seed 61 --max-steps 7. At most seven API calls. Do not run reserved final seeds 1009, 1013, 1019 yet. This update does not freeze or execute the benchmark protocol, nor establish live success.
