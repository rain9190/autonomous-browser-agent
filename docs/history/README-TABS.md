# Tabs and accordion headers

The `activate_tab` action handles observed tabs that control a panel. That includes the
accordion headers in these MiniWoB tasks.

```bash
python -m browser_agent --task click-collapsible --seed 61 --max-steps 4
```

The agent expands the requested section, observes again, then chooses the now-visible
target. A tab must have the right role and controls relationship; arbitrary containers
and links remain excluded. Local browser checks cover tab activation and accordion state.
