# Allowed-target catalogue

A development radio-choice run stopped with `observed_role_mismatch`. The rejected action
wasn't retained, so its exact cause couldn't be reconstructed.

The update gave both planners an explicit list of legal IDs for each action, built from
the already-visible accessibility tree. It didn't add hidden answers or translate invalid
actions into valid ones. Existing role checks still reject mismatches.

```bash
python -m browser_agent --task click-option --seed 67 --max-steps 3
```

The prompt change applies to both arms in later comparisons; earlier records stay unchanged.
