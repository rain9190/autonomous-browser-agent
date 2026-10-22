# Bounded fill recovery

    python -m pytest tests -q
    python -m browser_agent --task enter-text --seed 42 --max-steps 3 --max-recoveries 1 --simulate-fill-error-once

Expected demo: first fill fails before touching the page, a fresh observation is
returned by BrowserGym, the model selects a fill again, then submits. Expected
success=true, steps=3, api_calls=3, recoveries_used=1, and progress execution_ok
values [false, true, true]. The simulator deliberately returns a fixed trusted
raise statement for the first validated fill mapping, before any page action.
BrowserGym's installed step handler catches that exception and extracts a fresh
observation. It is not a random failure and does not establish recovery success
against every natural browser error. Both simulated_failure_requested and
simulated_failure_injected are reported so the demo is clearly identifiable.

Recovery defaults to zero. --max-recoveries accepts 0, 1, or 2. Only a nonterminal
fill action with last_action_error, unused action allowance, and unused recovery
allowance may return to observe. Fill replaces the field value and is suitable
for retrying on this local benchmark. Click errors always stop to avoid duplicate
side effects. API errors, invalid schemas or element roles, environment exceptions,
and exhausted budgets also stop. No API retry, exception retry, navigation or
new action type is introduced. The existing 1–6 action/API call cap applies to
all attempts including failed fills. Recovery cannot increase it.

Successful-action history now excludes actions with reported errors. A separate
failed_actions list stores only type/ID; raw browser errors and filled text are
not sent as error context. The next model decision receives a bounded structured
context indicating a failed fill, successful prior actions, remaining API budget,
and the fresh accessibility tree. Actual field state is authoritative, including
when an error may have occurred after a partial fill. Progress records preserve
all attempts and distinguish execution from benchmark confirmation.

Single-run filenames include recovery allowance and simulation flag. These
reports remain separate from natural baseline evaluations. The normal evaluator
continues running with zero recovery and no simulation; it explicitly rejects
reports marked as simulation. Recovery is currently a single-run option, not an
evaluator CLI option. Repeated same-configuration runs still overwrite their
single-episode report; baseline evaluator folders remain unique.

72 offline tests passed, including the 59 previous tests plus 13 recovery cases.
No live API requests or browser episodes were run during update preparation.
After the synthetic recovery demo succeeds, run the normal regression suite as
before to verify default behavior has not changed.

Changed: workflow.py, model.py, __main__.py, evaluate.py.
Added: recovery.py, tests/test_recovery.py. No credentials, dependency or vendor
changes are included.
