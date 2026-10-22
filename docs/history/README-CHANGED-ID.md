# Recovering after an element ID changes

This scenario removes the textbox's BrowserGym ID before the first fill. The stale
locator times out, and a fresh observation should expose a new ID for the same field.

```bash
python -m browser_agent --task enter-text --seed 11 --max-steps 3 --max-recoveries 1 --changed-textbox-id-once
```

The result checks that the old target disappeared and the successful retry used the newly
observed ID. It preserves the node's HTML ID, value and handlers. This is a controlled
stale-target test, not a general navigation-recovery feature.
