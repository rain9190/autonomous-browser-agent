# Initial browser feasibility audit — development instances

All fifteen new primary candidates loaded on development seeds 61 and 67:
30 successful reset/observation probes, no model calls or browser actions.
No candidate was promoted to supported status by these checks.

Saved source reports:

- results/feasibility-20261021T195029Z-18b29bbe/summary.json (seed 61)
- results/feasibility-20261021T195321Z-5017b6df/summary.json (seed 67)

Both summaries report complete=true, zero unattempted, no interruption,
api_calls=0 and actions_executed=0. No tree exceeded the 8,000-character agent
limit; maximum observed length was 619 characters on seed 61 and 617 on seed 67.
This is not a guarantee for every randomized instance or after UI interactions.

| Candidate group | Count | Observed implications |
|---|---:|---|
| New text/button/dialog variants | 5 | Existing textbox/button roles; still require allowlist and task execution checks |
| Checkbox/radio/native-select tasks | 4 | Roles are exposed; need strict selection schemas/mapping and full-credit scoring |
| Tab/accordion tasks | 5 | Tab roles need support; hidden-target discovery needs post-action observation checks |
| Standalone click-link | 1 | Visible clickable spans lack usable link/button AX roles |

Generic link-styled spans appeared in click-link, click-tab-2-easy and
click-tab-2-medium on both seeds (four visible spans per task instance). Some
other hidden targets may appear only after interaction; this audit did not open
panels or click tabs. DOM control counts varied with seed for checkbox, radio
and select tasks, as expected from their source generators. These findings
support implementing semantic selection actions, not loosening all click targets.

Reserved final seeds 1009, 1013 and 1019 were not used by this audit. The next
correctness gate is the shared full-credit metric, then minimal action support
and development task execution. Protocol 0.1 remains not frozen; only the five
original task families have established agent execution evidence.
