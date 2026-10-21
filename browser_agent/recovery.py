from .actions import Action, action_mapping


class FillFailureOnce:
    """Explicit demo: fail before the first fill; execute no page mutation."""

    def __init__(self):
        self.injected = False

    def __call__(self, payload):
        action = Action.model_validate_json(payload)
        if action.action == "fill" and not self.injected:
            self.injected = True
            # Fixed trusted template, never derived from model text.
            return "raise TimeoutError('Simulated pre-fill failure')"
        return action_mapping(payload)


class DisabledTextboxOnce:
    """Controlled real Playwright fill timeout; restore the field in finally."""

    def __init__(self):
        self.injected = False

    def __call__(self, payload):
        action = Action.model_validate_json(payload)
        if action.action != "fill" or self.injected:
            return action_mapping(payload)
        self.injected = True
        # All code/JS is fixed. Only validated, quoted literal ID/text vary.
        return (
            f"_recovery_target = page.get_by_test_id({action.bid!r})\n"
            "if _recovery_target.is_disabled():\n"
            "    raise ValueError('Controlled timeout requires an enabled field')\n"
            "try:\n"
            "    _recovery_target.evaluate('(el) => { el.disabled = true; }')\n"
            f"    _recovery_target.fill({action.text!r}, timeout=300)\n"
            "finally:\n"
            "    _recovery_target.evaluate('(el) => { el.disabled = false; }')\n"
        )
