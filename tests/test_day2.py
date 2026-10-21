import ast
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from browser_agent.actions import action_mapping, button_ids, validate_action
from browser_agent.model import ModelAdapter
from browser_agent.workflow import build_workflow


@pytest.mark.parametrize("proposal", [
    {"action": "click", "bid": "1'); import os; #"},
    {"action": "click", "bid": "missing"},
    {"action": "navigate", "bid": "1"},
    {"action": "click", "bid": "1", "code": "anything"},
    {"action": "click", "bid": 1},
])
def test_reject_unsafe_action(proposal):
    with pytest.raises((ValidationError, ValueError)):
        validate_action(proposal, {"1"})


def test_mapping_emits_one_fixed_click():
    code = action_mapping('{"action":"click","bid":"12"}')
    parsed = ast.parse(code)
    assert len(parsed.body) == 1
    assert code == "page.get_by_test_id('12').click(timeout=5000)"
    with pytest.raises(ValidationError):
        action_mapping("click('12'); anything()")


def test_only_button_ids():
    assert button_ids("[1] button 'Click me'\n  [2] textbox 'Other'\n[3] link 'Go'") == {"1"}


class FakeModel:
    def __init__(self, bid="1"):
        self.calls = 0
        self.bid = bid

    def decide(self, goal, tree, history=None):
        self.calls += 1
        return {"action": "click", "bid": self.bid}


class FakeEnv:
    def __init__(self, reward=1, terminated=True, truncated=False, error=""):
        self.calls = 0
        self.reward, self.terminated, self.truncated = reward, terminated, truncated
        self.error = error

    def step(self, payload):
        self.calls += 1
        return ({"goal": "click", "axtree_object": {}, "last_action_error": self.error},
                self.reward, self.terminated, self.truncated, {})


def run_graph(monkeypatch, env, model):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str", lambda _: "[1] button 'Click me'")
    return build_workflow(env, model).invoke({"observation": {"goal": "click", "axtree_object": {}}, "steps": 0})


def test_graph_success_order(monkeypatch):
    model, env = FakeModel(), FakeEnv()
    result = run_graph(monkeypatch, env, model)
    assert result["success"]
    assert result["trace"] == ["observe", "decide", "validate", "execute", "verify"]
    assert model.calls == env.calls == 1


def test_unknown_id_never_executes(monkeypatch):
    env = FakeEnv()
    with pytest.raises(ValueError):
        run_graph(monkeypatch, env, FakeModel("999"))
    assert env.calls == 0


@pytest.mark.parametrize("reward,terminated,truncated,error", [
    (0, True, False, ""), (1, True, True, ""), (1, True, False, "failed"),
])
def test_no_false_success(monkeypatch, reward, terminated, truncated, error):
    env = FakeEnv(reward, terminated, truncated, error)
    assert not run_graph(monkeypatch, env, FakeModel())["success"]
    assert env.calls == 1


def test_step_budget(monkeypatch):
    model, env = FakeModel(), FakeEnv(0, False)
    result = run_graph(monkeypatch, env, model)
    assert result["reason"] == "step_budget_exhausted"
    assert env.calls == model.calls == 2


def test_adapter_request_and_call_budget():
    adapter = ModelAdapter("fake-test-key")
    adapter.close()
    calls = []
    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_parsed=validate_action(
            {"action": "click", "bid": "1"}, {"1"}),
            usage=SimpleNamespace(input_tokens=30, output_tokens=10))
    adapter.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    adapter.decide("click", "[1] button")
    adapter.decide("click", "[1] button")
    with pytest.raises(RuntimeError):
        adapter.decide("click", "[1] button")
    assert len(calls) == 2
    assert calls[0]["max_output_tokens"] == 256
    assert calls[0]["store"] is False
    assert adapter.input_tokens == 60


def test_input_budget_before_network():
    adapter = ModelAdapter("fake-test-key")
    try:
        with pytest.raises(ValueError):
            adapter.decide("click", "x" * 8001)
        assert adapter.calls == 0
    finally:
        adapter.close()
