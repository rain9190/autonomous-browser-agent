"""Safe error categories: no exception bodies, raw values or model output."""
from pydantic import ValidationError
from .actions import ObservedRoleMismatch

MESSAGES = {
    "The selected ID does not match the observed action role": "observed_role_mismatch",
    "Select requires one unambiguous observed option label": "option_label_unobserved_or_ambiguous",
    "Fill/select require nonempty text": "required_action_text_missing",
    "This action must have null text": "unexpected_action_text",
    "Set_checked requires a boolean checked value": "required_checked_state_missing",
    "Only set_checked may supply checked": "unexpected_checked_state",
    "Action catalogue exceeds input budget": "action_catalogue_budget_exceeded",
    "Observation exceeds input budget": "model_input_budget_exceeded",
    "Accessibility tree exceeds input budget": "tree_budget_exceeded",
    "Action history exceeds input budget": "history_budget_exceeded",
    "No supported elements in the observation": "no_supported_observed_elements",
}
FIELDS = {"action", "bid", "text", "checked", "actions"}
TYPES = {"missing", "extra_forbidden", "literal_error", "string_type", "bool_type",
         "string_pattern_mismatch", "string_too_long", "value_error", "json_invalid"}


def describe_error(exc):
    if isinstance(exc, ObservedRoleMismatch):
        return {"category": "observed_role_mismatch", "requested_action": exc.requested_action,
                "target_bid": exc.target_bid, "observed_target_roles": exc.observed_roles}
    if isinstance(exc, ValidationError):
        details = []
        for error in exc.errors(include_input=False, include_url=False)[:5]:
            fields = [part for part in error.get("loc", ()) if part in FIELDS]
            category = MESSAGES.get(str(error.get("ctx", {}).get("error", "")))
            category = category or (error["type"] if error["type"] in TYPES else "schema_error")
            details.append({"field": fields[-1] if fields else "root_or_other", "category": category})
        return {"category": "action_schema_validation_failed", "details": details}
    if isinstance(exc, ValueError):
        return {"category": MESSAGES.get(str(exc), "unclassified_value_error")}
    if isinstance(exc, TimeoutError):
        return {"category": "run_timeout"}
    return {"category": "unclassified_run_error"}
