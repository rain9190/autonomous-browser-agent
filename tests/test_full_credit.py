import json

import pytest

from browser_agent.compare import parse_arm
from browser_agent.comparison_worker import MODEL
from browser_agent.evaluate import parse_result
from browser_agent.metrics import COMPLETION_METRIC, full_credit_success, positive_reward_terminal
from browser_agent.oneshot import execute_plan
from browser_agent.workflow import build_workflow


@pytest.mark.parametrize("reward", [0.1, 0.5, 0.999, 0.0, -1.0, 2.0,
                                    float("nan"), float("inf"), True, "1"])
def test_non_full_rewards_are_not_success(reward):
    assert not full_credit_success(reward, True, False)


@pytest.mark.parametrize("reward", [1, 1.0, 1 - 5e-10, 1 + 5e-10])
def test_full_credit_tolerance(reward):
    assert full_credit_success(reward, True, False)


@pytest.mark.parametrize("terminated,truncated,error", [(False, False, False),
    (True, True, False), (True, False, True)])
def test_terminal_and_error_guards_remain(terminated, truncated, error):
    assert not full_credit_success(1.0, terminated, truncated, error)


class Env:
    calls = 0
    def step(self, _):
        self.calls += 1
        return {"axtree_object": {}, "last_action_error": ""}, 0.5, True, False, {}


def test_iterative_marks_fractional_reward_partial(monkeypatch):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str", lambda _: "[1] button 'Submit'")
    class Model:
        def decide(self, *_):
            return {"action": "click", "bid": "1"}
    result = build_workflow(Env(), Model()).invoke({"observation": {
        "goal": "Complete task", "axtree_object": {}}, "steps": 0})
    assert not result["success"] and result["positive_reward_terminal"]
    assert result["reason"] == "partial_credit_terminal" and result["reward"] == 0.5
    assert result["completion_metric"] == COMPLETION_METRIC


def test_oneshot_uses_same_rule(monkeypatch):
    monkeypatch.setattr("browser_agent.oneshot.flatten_axtree_to_str", lambda _: "[1] button 'Submit'")
    env = Env()
    result = execute_plan(env, {"axtree_object": {}}, {"actions": [{"action": "click", "bid": "1"}]})
    assert not result["success"] and result["positive_reward_terminal"]
    assert result["reason"] == "partial_credit_terminal" and env.calls == 1


def report():
    return {"arm": "iterative", "task": "click-test", "seed": 61, "max_steps": 2,
        "max_recoveries": 0, "model": MODEL, "success": False, "reason": "partial_credit_terminal",
        "reward": 0.5, "terminated": True, "truncated": False, "steps": 1, "api_calls": 1,
        "input_tokens": 100, "output_tokens": 10, "duration_seconds": 2,
        "api_usage_may_be_incomplete": False, "initial_observation_sha256": "a" * 64,
        "completion_metric": COMPLETION_METRIC, "positive_reward_terminal": True}


def test_parsers_preserve_raw_partial_reward_as_failure():
    raw = json.dumps(report())
    baseline = parse_result(raw, 1, "click-test", 61)
    paired = parse_arm(raw, 1, "iterative", "click-test", 61, 2)
    assert baseline["status"] == "benchmark_failure" and not baseline["success"]
    assert paired["reason"] == "partial_credit_terminal" and not paired["success"]
    assert baseline["reward"] == paired["reward"] == 0.5
    assert baseline["positive_reward_terminal"] and paired["positive_reward_terminal"]


def test_fractional_success_claim_is_rejected():
    raw = json.dumps({**report(), "success": True, "reason": "benchmark_success"})
    assert parse_result(raw, 0, "click-test", 61)["status"] == "invalid_report"
    assert parse_arm(raw, 0, "iterative", "click-test", 61, 2)["reason"] == "invalid_report"


def test_metric_mismatch_is_not_silently_pooled():
    raw = json.dumps({**report(), "completion_metric": "positive_reward_only"})
    assert parse_arm(raw, 1, "iterative", "click-test", 61, 2)["reason"] == "invalid_report"


def test_legacy_full_reward_report_remains_readable():
    data = {**report(), "success": True, "reward": 1.0, "reason": "benchmark_success"}
    data.pop("completion_metric")
    data.pop("positive_reward_terminal")
    parsed = parse_arm(json.dumps(data), 0, "iterative", "click-test", 61, 2)
    assert parsed["success"] and parsed["completion_metric"] == "legacy_unversioned"


def test_action_error_is_not_positive_terminal_completion():
    data = {**report(), "reward": 1.0, "reason": "browser_action_error", "positive_reward_terminal": False}
    assert not parse_result(json.dumps(data), 1, "click-test", 61)["positive_reward_terminal"]
    assert not positive_reward_terminal(1.0, True, False, error=True)


def test_pair_with_different_metric_versions_is_excluded(tmp_path):
    from browser_agent.compare import run_comparison
    def runner(arm, task, seed, budget):
        return {"arm": arm, "task": task, "seed": seed, "success": True,
                "reason": "benchmark_success", "initial_observation_sha256": "a" * 64,
                "completion_metric": COMPLETION_METRIC if arm == "iterative" else "legacy_unversioned",
                "steps": 1, "api_calls": 1, "input_tokens": 100, "output_tokens": 10,
                "duration_seconds": 1.0, "api_usage_may_be_incomplete": False}
    result = run_comparison(["click-test"], [61], 2, tmp_path / "eval", runner)
    assert not result["complete"] and result["matched_pairs"] == 0
