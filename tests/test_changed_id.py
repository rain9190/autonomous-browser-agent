import ast
import json

import pytest

from browser_agent.evaluate import parse_result
from browser_agent.evaluate_recovery import parse_recovery_result, recovery_summary, run_recovery_episode
from browser_agent.recovery import ChangedTextboxIdOnce


def report():
    return {"task": "enter-text", "seed": 11, "success": True,
            "reason": "benchmark_success", "terminated": True, "truncated": False,
            "reward": 1, "steps": 3, "api_calls": 3, "input_tokens": 900, "output_tokens": 40,
            "max_steps": 3, "max_recoveries": 1, "recoveries_used": 1,
            "simulated_failure_requested": True, "simulated_failure_injected": True,
            "controlled_failure_scenario": "changed_textbox_id", "controlled_timeout_confirmed": True,
            "changed_id_confirmed": True, "fresh_id_recovery_confirmed": True,
            "progress": [
                {"step": 1, "action": "fill", "bid": "14", "execution_ok": False,
                 "error_kind": "playwright_fill_timeout", "failed_fill_target_absent": True},
                {"step": 2, "action": "fill", "bid": "20", "execution_ok": True},
                {"step": 3, "action": "click", "bid": "15", "execution_ok": True}]}


def test_mapping_invalidates_locator_once_and_preserves_dom_identity():
    mapping = ChangedTextboxIdOnce()
    text = "'); unsafe() #\nUnicode नमस्ते"
    code = mapping(json.dumps({"action": "fill", "bid": "14", "text": text}))
    tree = ast.parse(code)
    assert "removeAttribute('bid')" in tree.body[1].value.args[0].value
    assert ast.literal_eval(tree.body[2].value.args[0]) == text
    assert mapping.injected and mapping.old_bid == "14"
    assert "removeAttribute" not in mapping('{"action":"fill","bid":"20","text":"Ada"}')


def test_click_does_not_mutate_identifier():
    mapping = ChangedTextboxIdOnce()
    assert ".click(" in mapping('{"action":"click","bid":"15"}')
    assert not mapping.injected and mapping.old_bid is None


def test_confirmed_new_id_recovery_has_separate_mode():
    raw = json.dumps(report())
    result = parse_recovery_result(raw, 0, "enter-text", 11, 3, "changed_textbox_id")
    assert result["recovered_success"] and result["fresh_id_recovery_confirmed"]
    assert result["evaluation_mode"] == "controlled_changed_id_recovery"
    summary = recovery_summary([result], 1, 3, "changed_textbox_id")
    assert summary["confirmed_changed_id_episodes"] == summary["fresh_id_recovered_episodes"] == 1
    assert parse_result(raw, 0, "enter-text", 11, 3)["status"] == "invalid_report"
    assert parse_recovery_result(raw, 0, "enter-text", 11, 3, "disabled_textbox_timeout")["status"] == "invalid_report"


@pytest.mark.parametrize("mutation", ["old_id_used", "old_id_present", "no_confirmation", "no_timeout"])
def test_reject_false_new_id_success(mutation):
    data = report()
    if mutation == "old_id_used":
        data["progress"][1]["bid"] = "14"
    elif mutation == "old_id_present":
        data["progress"][0]["failed_fill_target_absent"] = False
    elif mutation == "no_confirmation":
        data["changed_id_confirmed"] = False
    else:
        data["controlled_timeout_confirmed"] = False
    result = parse_recovery_result(json.dumps(data), 0, "enter-text", 11, 3, "changed_textbox_id")
    assert not result["success"] and result["status"] == "invalid_report"


def test_changed_id_flag_reaches_subprocess(monkeypatch):
    class Process:
        returncode = 0
        def communicate(self, timeout=None):
            return json.dumps(report()), ""
    def spawn(command, **kwargs):
        assert command[-1] == "--changed-textbox-id-once"
        return Process()
    monkeypatch.setattr("browser_agent.evaluate_recovery.subprocess.Popen", spawn)
    assert run_recovery_episode("enter-text", 11, 3, "changed_textbox_id")["recovered_success"]
