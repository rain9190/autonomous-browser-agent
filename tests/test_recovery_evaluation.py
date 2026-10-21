import json

import pytest

from browser_agent.evaluate import parse_result, run_suite
from browser_agent.evaluate_recovery import (
    parse_recovery_result, recovery_summary, run_recovery_episode,
)


def report(success=True):
    return {"task": "enter-text", "seed": 7, "success": success,
            "reason": "benchmark_success" if success else "step_budget_exhausted",
            "terminated": success, "truncated": False, "reward": 1 if success else 0,
            "steps": 3, "api_calls": 3, "input_tokens": 900, "output_tokens": 40,
            "max_steps": 3, "max_recoveries": 1, "recoveries_used": 1,
            "simulated_failure_requested": True, "simulated_failure_injected": True,
            "progress": [
                {"step": 1, "action": "fill", "execution_ok": False},
                {"step": 2, "action": "fill", "execution_ok": True},
                {"step": 3, "action": "click", "execution_ok": True},
            ]}


def test_valid_recovery_report_and_baseline_separation():
    raw = json.dumps(report())
    result = parse_recovery_result(raw, 0, "enter-text", 7, 3)
    assert result["recovered_success"] and result["injection_confirmed"]
    assert result["evaluation_mode"] == "simulated_fill_recovery"
    assert parse_result(raw, 0, "enter-text", 7, 3)["status"] == "invalid_report"


@pytest.mark.parametrize("change", [
    {"simulated_failure_injected": False}, {"simulated_failure_requested": False},
    {"recoveries_used": 0}, {"recoveries_used": 2}, {"max_steps": 6},
    {"max_recoveries": 2}, {"progress": []}, {"seed": 123},
])
def test_unconfirmed_or_mismatched_report_is_not_success(change):
    raw = json.dumps({**report(), **change})
    result = parse_recovery_result(raw, 0, "enter-text", 7, 3)
    assert not result["success"] and not result["recovered_success"]
    assert result["status"] == "invalid_report"


def test_confirmed_failure_counts_in_recovery_denominator():
    result = parse_recovery_result(json.dumps(report(False)), 1, "enter-text", 7, 3)
    assert result["injection_confirmed"] and not result["recovered_success"]
    assert result["status"] == "benchmark_failure"


def test_infrastructure_error_usage_stays_unknown():
    result = parse_recovery_result("API request failed (HTTP 429); private", 1, "enter-text", 7, 3)
    assert result["status"] == "api_quota_or_rate_limit"
    assert result["api_calls"] is None and not result["injection_confirmed"]
    assert "private" not in json.dumps(result)


def test_suite_summary_and_records_are_labeled(tmp_path):
    def runner(task, seed, max_steps):
        raw = {**report(), "seed": seed}
        return parse_recovery_result(json.dumps(raw), 0, task, seed, max_steps)
    output = tmp_path / "recovery-eval"
    summary = run_suite(["enter-text"], [7, 42, 123], output, runner,
                        max_steps=3, summary_builder=recovery_summary)
    assert summary["evaluation_mode"] == "simulated_fill_recovery"
    assert summary["confirmed_injected_episodes"] == summary["recovered_episodes"] == 3
    assert summary["recoveries_used"] == 3 and summary["api_call_ceiling"] == 9
    assert summary["recovery_success_rate_on_attempted"] == 1
    assert summary["recovery_success_rate_on_confirmed_injections"] == 1
    assert all(json.loads(p.read_text())["evaluation_mode"] == "simulated_fill_recovery"
               for p in output.glob("*.json"))


def test_partial_suite_does_not_claim_complete_success(tmp_path):
    result = {"task": "enter-text", "seed": 7, "success": False,
              "status": "connection_error", "api_calls": None,
              "input_tokens": None, "output_tokens": None,
              "injection_confirmed": False, "recovered_success": False}
    summary = run_suite(["enter-text"], [7, 42], tmp_path / "eval",
                        lambda *a, **k: result, max_steps=3,
                        summary_builder=recovery_summary)
    assert not summary["complete"] and summary["unattempted"] == 1
    assert summary["recovery_success_rate_on_attempted"] == 0
    assert summary["recovery_success_rate_on_confirmed_injections"] is None


def test_subprocess_receives_simulation_flags(monkeypatch):
    class Process:
        returncode = 0
        def communicate(self, timeout=None):
            return json.dumps(report()), "private stderr"
    def spawn(command, **kwargs):
        assert command[-3:] == ["--max-recoveries", "1", "--simulate-fill-error-once"]
        assert "shell" not in kwargs and kwargs["start_new_session"]
        return Process()
    monkeypatch.setattr("browser_agent.evaluate_recovery.subprocess.Popen", spawn)
    assert run_recovery_episode("enter-text", 7)["recovered_success"]


def test_external_timeout_cleans_up_process_group(monkeypatch):
    import subprocess
    class Process:
        pid = 98765
        calls = 0
        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("test", timeout)
            return "", ""
    killed = []
    monkeypatch.setattr("browser_agent.evaluate_recovery.subprocess.Popen", lambda *a, **k: Process())
    monkeypatch.setattr("browser_agent.evaluate_recovery.os.killpg", lambda *a: killed.append(a))
    result = run_recovery_episode("enter-text", 7)
    assert result["status"] == "timeout" and not result["recovered_success"]
    assert killed[0][0] == 98765
