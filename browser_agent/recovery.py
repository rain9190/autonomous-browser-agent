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
