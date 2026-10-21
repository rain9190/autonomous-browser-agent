import ast
import json
from functools import partial

import pytest

from browser_agent.evaluate import parse_result, run_suite
from browser_agent.evaluate_recovery import parse_recovery_result, recovery_summary, run_recovery_episode
from browser_agent.recovery import DisabledTextboxOnce


def report():
    return {"task": "enter-text", "seed": 11, "success": True,
            "reason": "benchmark_success", "terminated": True, "truncated": False,
            "reward": 1, "steps": 3, "api_calls": 3, "input_tokens": 900, "output_tokens": 40,
            "max_steps": 3, "max_recoveries": 1, "recoveries_used": 1,
            "simulated_failure_requested": True, "simulated_failure_injected": True,
            "controlled_failure_scenario": "disabled_textbox_timeout", "controlled_timeout_confirmed": True,
            "progress": [
                {"step": 1, "action": "fill", "execution_ok": False, "error_kind": "playwright_fill_timeout"},
                {"step": 2, "action": "fill", "execution_ok": True, "error_kind": None},
                {"step": 3, "action": "click", "execution_ok": True, "error_kind": None}]}


def test_timeout_template_restores_field_and_quotes_text():
    mapping = DisabledTextboxOnce()
    text = "'); unsafe() #\nनमस्ते"
    code = mapping(json.dumps({"action": "fill", "bid": "field", "text": text}))
    parsed = ast.parse(code)
    block = next(n for n in parsed.body if isinstance(n, ast.Try))
    fill = block.body[1].value
    assert fill.func.attr == "fill" and ast.literal_eval(fill.args[0]) == text
    assert fill.keywords[0].value.value == 300
    assert "disabled = true" in block.body[0].value.args[0].value
    assert "disabled = false" in block.finalbody[0].value.args[0].value
    assert mapping.injected
    assert ".fill('Ada'" in mapping('{"action":"fill","bid":"field","text":"Ada"}')


def test_click_does_not_trigger_timeout_injection():
    mapping = DisabledTextboxOnce()
    assert ".click(" in mapping('{"action":"click","bid":"submit"}')
    assert not mapping.injected


def test_actual_timeout_report_stays_distinct_from_other_modes():
    raw = json.dumps(report())
    result = parse_recovery_result(raw, 0, "enter-text", 11, 3, "disabled_textbox_timeout")
    assert result["recovered_success"] and result["browser_timeout_confirmed"]
    assert result["evaluation_mode"] == "controlled_browser_timeout_recovery"
    assert parse_recovery_result(raw, 0, "enter-text", 11, 3)["status"] == "invalid_report"
    assert parse_result(raw, 0, "enter-text", 11, 3)["status"] == "invalid_report"


@pytest.mark.parametrize("field,value", [("controlled_timeout_confirmed", False),
    ("controlled_failure_scenario", "python_exception"), ("simulated_failure_injected", False)])
def test_missing_timeout_evidence_cannot_pass(field, value):
    raw = json.dumps({**report(), field: value})
    assert not parse_recovery_result(raw, 0, "enter-text", 11, 3, "disabled_textbox_timeout")["success"]


def test_generic_error_is_not_a_playwright_timeout():
    raw = report()
    raw["progress"][0]["error_kind"] = "browser_action_error"
    result = parse_recovery_result(json.dumps(raw), 0, "enter-text", 11, 3, "disabled_textbox_timeout")
    assert result["status"] == "invalid_report"


def test_summary_tracks_only_confirmed_browser_timeouts(tmp_path):
    def runner(task, seed, max_steps):
        raw = {**report(), "seed": seed}
        return parse_recovery_result(json.dumps(raw), 0, task, seed, max_steps, "disabled_textbox_timeout")
    summary = run_suite(["enter-text"], [11, 29], tmp_path / "eval", runner, max_steps=3,
                        summary_builder=partial(recovery_summary, scenario="disabled_textbox_timeout"))
    assert summary["confirmed_browser_timeout_episodes"] == 2
    assert summary["recovered_episodes"] == 2 and summary["api_call_ceiling"] == 6
    assert summary["evaluation_mode"] == "controlled_browser_timeout_recovery"


def test_timeout_scenario_subprocess_flag(monkeypatch):
    class Process:
        returncode = 0
        def communicate(self, timeout=None):
            return json.dumps(report()), ""
    def spawn(command, **kwargs):
        assert command[-1] == "--disabled-textbox-timeout-once"
        assert "--simulate-fill-error-once" not in command
        return Process()
    monkeypatch.setattr("browser_agent.evaluate_recovery.subprocess.Popen", spawn)
    assert run_recovery_episode("enter-text", 11, 3, "disabled_textbox_timeout")["browser_timeout_confirmed"]
