# Link-like benchmark spans

Four local tasks use visible `span.alink` elements without ordinary link/button roles:
`click-link`, `click-collapsible-2`, `click-tab-2-easy` and `click-tab-2-medium`.
A narrow DOM adapter adds their visible labels and IDs to observations.

```bash
python -m browser_agent --task click-link --seed 61 --max-steps 2
```

Only those allowlisted task pages use this supplement. Hidden panel targets stay hidden,
and ordinary containers remain invalid. The change doesn't enable arbitrary span clicks
on real websites.
