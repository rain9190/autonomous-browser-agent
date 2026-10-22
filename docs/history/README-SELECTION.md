# Native selection controls

This added explicit checkbox, radio and dropdown handling. Targets and option labels must
come from the current observation. Setting an already-correct checkbox doesn't toggle it.

```bash
python -m browser_agent --task choose-list --seed 61 --max-steps 2
```

The initial browser checks covered selecting, unsetting and repeating selections. The
agent still uses full-credit scoring and fixed action templates; generic page elements
don't become clickable just because these controls are supported.
