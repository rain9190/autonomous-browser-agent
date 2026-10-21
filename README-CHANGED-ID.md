# Changed BrowserGym element ID: bounded reliability check

This is the last small recovery milestone before one-shot baseline comparison
and matched experiments. It is not an extension of the original Day 2 scope.

## Run

    python -m pytest tests -q

Expected: 104 passed, 2 skipped. The two skipped tests are opt-in browser checks.

    RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser_changed_id.py -q

Expected: one passed, with local Chromium and no API calls. The test checks that
removing the old bid makes the stale fill locator time out, that BrowserGym emits
a different bid in a fresh observation, and that a stale action is rejected by
role validation. The DOM node, native HTML id, field value and event handlers are
preserved. A fill using the new observed bid must succeed.

After that check passes:

    python -m browser_agent --task enter-text --seed 11 --max-steps 3 --max-recoveries 1 --changed-textbox-id-once

Expected autonomous sequence: fill using old bid fails; next model decision uses
the freshly observed bid; Submit succeeds. Expected report: success=true,
steps=3, api_calls=3, recoveries_used=1, changed_id_confirmed=true,
fresh_id_recovery_confirmed=true, controlled_timeout_confirmed=true.
The first and second progress entries should show different fill bids.

## Mechanism

The one-shot controlled mapping removes only the BrowserGym bid attribute, then
attempts the original locator fill with timeout=300ms. There is no explicit
Python raise. Playwright must report its real fill timeout because the old ID no
longer exists. Installed BrowserGym's frame-marking code assigns a new monotonic
ID when observing an element without a bid. No replacement ID is given to the
model or hardcoded; it must select from the fresh accessibility tree. This is a
benchmark identifier change, not a replacement DOM node or a changed native id.

The scenario is deliberate and local, not a naturally occurring incident.
It preserves existing schemas, observed-role validation, model adapter and all
call/step/time limits. The old ID is never silently translated to the new ID.
The standard workflow handles eligible fill errors with max_recoveries enabled.
API, schema, unsafe action and click-error behavior is unchanged.

Progress adds failed_fill_target_absent, derived from the returned observation.
Single-run evidence distinguishes an absent old ID from a successful later fill
with a different ID. These flags are not sufficient alone to declare success:
positive terminal benchmark reward without truncation/error is still required.

## Later acceptance run

After the first autonomous check succeeds:

    python -m browser_agent.evaluate_recovery --scenario changed_textbox_id --seeds 11 29

Two episodes, at most six API calls. Output folders use changed-id-eval-... and
mode controlled_changed_id_recovery. The parser verifies actual timeout evidence,
absence of the failed ID, and use of a different ID before accepting a recovered
success. Old exception/disabled-field modes and the baseline parser reject these
reports. Summary adds confirmed_changed_id_episodes and fresh_id_recovered_episodes.

Then run the standard baseline regression and commit the tested update. After
this bounded milestone, prioritize the one-shot baseline and matched ablations;
no additional recovery scenario is required before that work begins.

## Verification

104 offline tests passed, including the previous 96 checks. Two browser tests
are opt-in and were not run during preparation. No live API calls or browser
episodes were run during preparation. The browser check is necessary to establish
that the installed BrowserGym observation path regenerates the ID as expected.

Changed: browser_agent/recovery.py, workflow.py, __main__.py,
evaluate_recovery.py. Added: tests/test_changed_id.py,
tests/test_browser_changed_id.py and this README. No dependency, vendor, API-key,
model adapter or baseline evaluator changes.
