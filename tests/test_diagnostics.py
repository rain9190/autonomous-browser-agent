import json

import pytest
from pydantic import ValidationError

from browser_agent.actions import Action
from browser_agent.diagnostics import describe_error


def test_known_role_error_is_classified():
    assert describe_error(ValueError("The selected ID does not match the observed action role"))["category"] == "observed_role_mismatch"


def test_unknown_exception_text_never_leaks():
    result = describe_error(ValueError("secret model text and key-like data"))
    assert result == {"category": "unclassified_value_error"}
    assert "secret" not in json.dumps(result)


def test_schema_validator_rule_is_classified():
    with pytest.raises(ValidationError) as error:
        Action(action="check_radio", bid="1", checked=True)
    result = describe_error(error.value)
    assert result["details"][0]["category"] == "unexpected_checked_state"


def test_bad_values_are_not_logged():
    with pytest.raises(ValidationError) as error:
        Action(action="fill", bid="1", text=12345)
    result = describe_error(error.value)
    assert result["details"][0]["field"] == "text"
    assert "12345" not in json.dumps(result)


def test_unknown_field_name_is_not_logged():
    with pytest.raises(ValidationError) as error:
        Action.model_validate({"action": "click", "bid": "1", "private_extra_field": "secret"})
    result = json.dumps(describe_error(error.value))
    assert "private_extra_field" not in result and "secret" not in result


def test_timeout_category():
    assert describe_error(TimeoutError("private details")) == {"category": "run_timeout"}


def test_evaluator_recognizes_safe_failed_run_report():
    from browser_agent.evaluate import parse_result
    report = {"status": "run_failed", "task": "click-option", "seed": 67,
              "success": False, "category": "observed_role_mismatch"}
    result = parse_result(json.dumps(report), 1, "click-option", 67, 3)
    assert result["status"] == "agent_validation_or_run_error" and not result["success"]
    report["category"] = "run_timeout"
    assert parse_result(json.dumps(report), 1, "click-option", 67, 3)["status"] == "timeout"
