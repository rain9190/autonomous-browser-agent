# Feasibility results

All 15 new MiniWoB candidates loaded at development seeds 61 and 67: **30 successful
observation probes**, with no model calls or browser actions.

| Group | Tasks | Main issue |
| --- | ---: | --- |
| Text/button/dialog variants | 5 | Needed execution checks |
| Checkbox/radio/select tasks | 4 | Needed selection actions and full-credit scoring |
| Tabs/accordions | 5 | Needed panel actions and fresh observations |
| Standalone link task | 1 | Clickable spans lacked link/button roles |

No observed tree exceeded the then-current 8,000-character limit. Link-style spans appeared
in `click-link`, `click-tab-2-easy` and `click-tab-2-medium` on both seeds.

The source summaries were saved under `results/feasibility-20261021T195029Z-18b29bbe` and
`results/feasibility-20261021T195321Z-5017b6df`. These checks established initial visibility,
not task success. Final seeds weren't used at this stage.
