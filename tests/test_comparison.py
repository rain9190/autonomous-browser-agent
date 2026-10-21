import json

import pytest

from browser_agent.compare import invalid, parse_arm, run_comparison, run_arm
from browser_agent.comparison_worker import MODEL, CountedEnv


def raw(arm="oneshot", success=True):
    return {"arm": arm, "task": "enter-text", "seed": 11,
            "model": MODEL, "max_steps": 2, "max_recoveries": 0,
            "success": success, "reason": "benchmark_success" if success else "plan_exhausted",
            "reward": 1 if success else 0, "terminated": success, "truncated": False,
            "steps": 2, "api_calls": 1 if arm == "oneshot" else 2,
            "input_tokens": 200, "output_tokens": 30, "api_usage_may_be_incomplete": False,
            "duration_seconds": 5.0, "initial_observation_sha256": "a" * 64}


def fake(arm, task, seed, max_steps):
    data = {**raw(arm), "task": task, "seed": seed, "max_steps": max_steps}
    return parse_arm(json.dumps(data), 0, arm, task, seed, max_steps)


def test_parser_sanitizes_report():
    result = parse_arm(json.dumps({**raw(), "history": "private"}), 0, "oneshot", "enter-text", 11, 2)
    assert result["success"] and "history" not in result


@pytest.mark.parametrize("change", [{"seed": 29}, {"model": "different"},
    {"api_calls": 2}, {"max_recoveries": 1}, {"initial_observation_sha256": "bad"},
    {"duration_seconds": -1}, {"reward": 0}])
def test_invalid_arm_cannot_pass(change):
    result = parse_arm(json.dumps({**raw(), **change}), 0, "oneshot", "enter-text", 11, 2)
    assert result["reason"] == "invalid_report" and not result["success"]


def test_pairs_are_matched_and_order_alternates(tmp_path):
    order = []
    def runner(arm, task, seed, max_steps):
        order.append(arm)
        return fake(arm, task, seed, max_steps)
    summary = run_comparison(["enter-text"], [11, 29], 2, tmp_path / "eval", runner)
    assert order == ["oneshot", "iterative", "iterative", "oneshot"]
    assert summary["complete"] and summary["matched_pairs"] == 2
    assert summary["api_call_ceiling"] == summary["reported_api_calls"] == 6
    assert summary["paired_outcomes"]["both_succeeded"] == 2
    assert (tmp_path / "eval/config.json").exists()


def test_initial_mismatch_is_not_compared(tmp_path):
    def runner(arm, task, seed, max_steps):
        data = fake(arm, task, seed, max_steps)
        data["initial_observation_sha256"] = ("a" if arm == "oneshot" else "b") * 64
        return data
    result = run_comparison(["enter-text"], [11], 2, tmp_path / "eval", runner)
    assert not result["complete"] and result["matched_pairs"] == 0
    assert result["per_arm_on_matched_pairs"]["oneshot"]["success_rate"] is None


def test_failed_task_is_retained_not_treated_as_runner_failure(tmp_path):
    def runner(arm, task, seed, max_steps):
        data = raw(arm, success=arm == "iterative")
        return parse_arm(json.dumps(data), int(not data["success"]), arm, task, seed, max_steps)
    result = run_comparison(["enter-text"], [11], 2, tmp_path / "eval", runner)
    assert result["complete"] and result["paired_outcomes"]["iterative_only"] == 1
    assert result["per_arm_on_matched_pairs"]["oneshot"]["success_rate"] == 0


def test_infrastructure_error_stops_and_preserves_usage_unknown(tmp_path):
    result = run_comparison(["enter-text"], [11, 29], 2, tmp_path / "eval",
        lambda a, t, s, b: invalid(a, t, s, b, "timeout"))
    assert not result["complete"] and result["unattempted_pairs"] == 1
    assert result["episodes_with_unknown_or_incomplete_usage"] == 1
    assert result["matched_pairs"] == 0


def test_budget_checked_before_any_process(tmp_path):
    with pytest.raises(ValueError, match="24-call"):
        run_comparison(["enter-text"], list(range(9)), 2, tmp_path / "eval")
    assert not (tmp_path / "eval").exists()


def test_interruption_preserves_summary(tmp_path):
    def interrupt(*_):
        raise KeyboardInterrupt()
    result = run_comparison(["enter-text"], [11], 2, tmp_path / "eval", interrupt)
    assert result["interrupted"] and not result["complete"]
    assert result["episodes_with_unknown_or_incomplete_usage"] == 1
    assert (tmp_path / "eval/summary.json").exists()


def test_counted_env_records_attempt_before_exception():
    class Broken:
        def step(self, _):
            raise RuntimeError()
    env = CountedEnv(Broken())
    with pytest.raises(RuntimeError):
        env.step("payload")
    assert env.steps == 1


def test_subprocess_timeout_kills_group(monkeypatch):
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
    monkeypatch.setattr("browser_agent.compare.subprocess.Popen", lambda *a, **k: Process())
    monkeypatch.setattr("browser_agent.compare.os.killpg", lambda *a: killed.append(a))
    result = run_arm("oneshot", "enter-text", 11, 2)
    assert result["reason"] == "timeout" and killed[0][0] == 98765
