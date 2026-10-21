from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from browser_agent.oneshot import ActionPlan, OneShotAdapter, execute_plan


def plan():
    return {"actions": [{"action": "fill", "bid": "field", "text": "Ada"},
                        {"action": "click", "bid": "submit"}]}


class Env:
    def __init__(self, stale=False, error=False, reward=1, truncated=False):
        self.calls = 0
        self.stale, self.error, self.reward, self.truncated = stale, error, reward, truncated

    def step(self, payload):
        self.calls += 1
        done = self.calls == 2
        return {"axtree_object": {"stale": self.stale},
                "last_action_error": "private error" if self.error else ""}, self.reward if done else 0, done, self.truncated, {}


@pytest.fixture
def observation(monkeypatch):
    monkeypatch.setattr("browser_agent.oneshot.flatten_axtree_to_str", lambda obs:
        "[field] textbox\n" + ("[replacement] button" if obs.get("stale") else "[submit] button"))
    return {"axtree_object": {}}


def test_plan_executes_without_replanning(observation):
    env = Env()
    result = execute_plan(env, observation, plan())
    assert result["success"] and env.calls == result["steps"] == 2
    assert [r["action"] for r in result["history"]] == ["fill", "click"]


def test_stale_planned_target_stops_instead_of_retargeting(observation):
    env = Env(stale=True)
    result = execute_plan(env, observation, plan())
    assert not result["success"] and result["reason"] == "planned_target_invalid"
    assert env.calls == 1


def test_over_budget_plan_executes_nothing(observation):
    env = Env()
    with pytest.raises(ValueError):
        execute_plan(env, observation, plan(), max_steps=1)
    assert env.calls == 0


def test_invalid_later_schema_executes_nothing(observation):
    env = Env()
    raw = plan()
    raw["actions"][1]["action"] = "shell"
    with pytest.raises(ValidationError):
        execute_plan(env, observation, raw)
    assert env.calls == 0


def test_action_error_stops_without_retry(observation):
    env = Env(error=True)
    result = execute_plan(env, observation, plan())
    assert result["reason"] == "browser_action_error" and env.calls == 1
    assert result["history"] == []


@pytest.mark.parametrize("reward,truncated", [(0, False), (1, True)])
def test_no_false_benchmark_success(observation, reward, truncated):
    result = execute_plan(Env(reward=reward, truncated=truncated), observation, plan())
    assert not result["success"]


def test_early_success_does_not_execute_remaining_actions(observation):
    class Early:
        calls = 0
        def step(self, _):
            self.calls += 1
            return {"axtree_object": {}, "last_action_error": ""}, 1, True, False, {}
    env = Early()
    result = execute_plan(env, observation, plan())
    assert result["success"] and env.calls == 1


@pytest.mark.parametrize("raw", [{"actions": []}, {"actions": [{"action": "click", "bid": "x"}] * 7}])
def test_plan_schema_bounds(raw):
    with pytest.raises(ValidationError):
        ActionPlan.model_validate(raw)


def test_adapter_one_call_and_aggregate_output_allowance():
    adapter = OneShotAdapter("fake-key", max_steps=3)
    adapter.close()
    requests = []
    def parse(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(status="completed", usage=SimpleNamespace(input_tokens=100, output_tokens=30),
                               output_parsed=ActionPlan.model_validate(plan()))
    adapter.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    assert len(adapter.plan("goal", "tree")["actions"]) == 2
    with pytest.raises(RuntimeError):
        adapter.plan("goal", "tree")
    assert len(requests) == 1 and requests[0]["max_output_tokens"] == 768
    assert requests[0]["store"] is False
    assert adapter.input_tokens == 100 and adapter.output_tokens == 30


def test_adapter_refusal_does_not_retry():
    adapter = OneShotAdapter("fake-key")
    adapter.close()
    adapter.client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **_: SimpleNamespace(
        status="completed", usage=None, output_parsed=None)))
    with pytest.raises(RuntimeError):
        adapter.plan("goal", "tree")
    assert adapter.calls == 1


def test_input_limit_prevents_api_call():
    adapter = OneShotAdapter("fake-key")
    try:
        with pytest.raises(ValueError):
            adapter.plan("goal", "x" * 8001)
        assert adapter.calls == 0
    finally:
        adapter.close()
