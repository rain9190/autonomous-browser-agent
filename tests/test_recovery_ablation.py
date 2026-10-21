import json

import pytest

from browser_agent.ablate_recovery import parse_ablation, run_ablation, matching_failures, run_arm
from browser_agent.comparison_worker import CountedEnv, MODEL
from browser_agent.compare import invalid


def raw(arm, seed=31):
    on = arm == "recovery_on"
    return {"arm": arm, "task": "enter-text", "seed": seed, "model": MODEL,
            "max_steps": 3, "max_recoveries": int(on), "success": on,
            "reason": "benchmark_success" if on else "browser_action_error",
            "reward": int(on), "terminated": on, "truncated": False,
            "steps": 3 if on else 1, "api_calls": 3 if on else 1,
            "input_tokens": 900 if on else 300, "output_tokens": 42 if on else 14,
            "api_usage_may_be_incomplete": False, "duration_seconds": 8.0 if on else 4.0,
            "initial_observation_sha256": "a" * 64,
            "controlled_failure_scenario": "disabled_textbox_timeout",
            "failure_injection_confirmed": True, "injected_failure_signature": "b" * 64,
            "recoveries_used": int(on)}


def fake(arm, task, seed, max_steps):
    report = raw(arm, seed)
    return parse_ablation(json.dumps(report), int(not report["success"]), arm, task, seed,
                          max_steps, "disabled_textbox_timeout")


def test_matched_ablation_measures_benefit_and_cost(tmp_path):
    result = run_ablation("enter-text", [31, 47], 3, "disabled_textbox_timeout", tmp_path / "eval", fake)
    assert result["complete"] and result["matched_pairs"] == 2
    assert result["paired_outcomes"]["recovery_on_only"] == 2
    assert result["success_rate_difference_percentage_points"] == 100
    assert result["mean_additional_api_calls"] == 2
    assert result["mean_additional_duration_seconds"] == 4
    assert result["api_call_ceiling"] == 12 and result["reported_api_calls"] == 8
    assert result["per_arm_on_matched_pairs"]["recovery_off"]["failure_reasons"] == {"browser_action_error": 2}
    config = json.loads((tmp_path / "eval/config.json").read_text())
    assert config["max_recoveries"] == {"recovery_off": 0, "recovery_on": 1}


@pytest.mark.parametrize("change", [{"max_recoveries": 0}, {"recoveries_used": 2},
    {"controlled_failure_scenario": "changed_textbox_id"}, {"model": "different"},
    {"injected_failure_signature": "bad"}, {"max_steps": 4}])
def test_wrong_arm_or_condition_cannot_pass(change):
    result = parse_ablation(json.dumps({**raw("recovery_on"), **change}), 0,
        "recovery_on", "enter-text", 31, 3, "disabled_textbox_timeout")
    assert not result["success"] and result["reason"] == "invalid_report"


def test_different_failure_states_are_excluded(tmp_path):
    def runner(*args):
        result = fake(*args)
        if args[0] == "recovery_on":
            result["injected_failure_signature"] = "c" * 64
        return result
    result = run_ablation("enter-text", [31], 3, "disabled_textbox_timeout", tmp_path / "eval", runner)
    assert not result["complete"] and result["matched_pairs"] == 0
    assert result["success_rate_difference_percentage_points"] is None


def test_non_triggered_failure_is_not_treated_as_recovery_evidence(tmp_path):
    def runner(*args):
        result = fake(*args)
        result["failure_injection_confirmed"] = False
        result["injected_failure_signature"] = None
        return result
    result = run_ablation("enter-text", [31], 3, "disabled_textbox_timeout", tmp_path / "eval", runner)
    assert not result["complete"] and result["matched_pairs"] == 0


def test_budget_checked_before_launching(tmp_path):
    with pytest.raises(ValueError, match="24-call"):
        run_ablation("enter-text", list(range(5)), 3, "disabled_textbox_timeout", tmp_path / "eval")
    assert not (tmp_path / "eval").exists()


def test_insufficient_action_budget_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        run_ablation("login-user", [31], 3, "disabled_textbox_timeout", tmp_path / "eval")


def test_api_error_stops_and_remains_unknown(tmp_path):
    result = run_ablation("enter-text", [31, 47], 3, "disabled_textbox_timeout", tmp_path / "eval",
        lambda a, t, s, b: invalid(a, t, s, b, "api_error"))
    assert not result["complete"] and result["unattempted_pairs"] == 1
    assert result["episodes_with_unknown_or_incomplete_usage"] == 1


def test_off_success_after_confirmed_error_is_rejected():
    report = {**raw("recovery_off"), "success": True, "reason": "benchmark_success",
              "reward": 1, "terminated": True}
    assert parse_ablation(json.dumps(report), 0, "recovery_off", "enter-text", 31, 3,
                          "disabled_textbox_timeout")["reason"] == "invalid_report"


def test_counted_env_records_only_safe_first_failure_evidence(monkeypatch):
    monkeypatch.setattr("browser_agent.comparison_worker.fingerprint", lambda _: ("d" * 64, "private tree"))
    class Env:
        def step(self, _):
            return {"last_action_error": "TimeoutError: Locator.fill: Timeout 300ms exceeded. private"}, 0, False, False, {}
    wrapped = CountedEnv(Env())
    wrapped.step('{"action":"fill","bid":"14","text":"synthetic password"}')
    assert wrapped.first_failure["fill_timeout"]
    assert "private" not in json.dumps(wrapped.first_failure)
    assert "password" not in json.dumps(wrapped.first_failure)


def test_worker_command_carries_same_scenario_and_budget(monkeypatch):
    class Process:
        returncode = 1
        def communicate(self, timeout=None):
            return json.dumps(raw("recovery_off")), ""
    def spawn(command, **kwargs):
        assert command[-4:] == ["--max-steps", "3", "--scenario", "disabled_textbox_timeout"]
        assert "recovery_off" in command
        return Process()
    monkeypatch.setattr("browser_agent.ablate_recovery.subprocess.Popen", spawn)
    result = run_arm("recovery_off", "enter-text", 31, 3, "disabled_textbox_timeout")
    assert result["failure_injection_confirmed"] and not result["success"]
