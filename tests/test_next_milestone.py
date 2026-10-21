import json
from types import SimpleNamespace

import pytest

from browser_agent.actions import ClickAction
from browser_agent.model import ModelAdapter
from browser_agent.workflow import build_workflow


class SequenceEnv:
    def __init__(self):
        self.clicks = []

    def step(self, payload):
        self.clicks.append(json.loads(payload)["bid"])
        done = len(self.clicks) == 2
        reward = float(done and self.clicks == ["one", "two_fresh"])
        return ({"goal": "Click ONE then TWO", "axtree_object": {"step": len(self.clicks)},
                 "last_action_error": ""}, reward, done, False, {})


class SequenceModel:
    def __init__(self, stale=False):
        self.histories = []
        self.stale = stale

    def decide(self, goal, tree, history=None):
        self.histories.append(list(history or []))
        bid = "one" if not history else ("two_old" if self.stale else "two_fresh")
        return {"action": "click", "bid": bid}


def tree(obs):
    return "[one] button 'ONE'\n[two_old] button 'TWO'" if obs["step"] == 0 else "[one] button 'ONE'\n[two_fresh] button 'TWO'"


def run(monkeypatch, env, model):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str", tree)
    return build_workflow(env, model).invoke({"observation": {
        "goal": "Click ONE then TWO", "axtree_object": {"step": 0}}, "steps": 0})


def test_sequence_uses_history_and_fresh_observation(monkeypatch):
    env, model = SequenceEnv(), SequenceModel()
    result = run(monkeypatch, env, model)
    assert result["success"] and result["steps"] == 2
    assert env.clicks == ["one", "two_fresh"]
    assert model.histories == [[], [{"action": "click", "bid": "one"}]]
    assert result["trace"] == ["observe", "decide", "validate", "execute", "verify"] * 2


def test_stale_second_id_is_blocked(monkeypatch):
    env = SequenceEnv()
    with pytest.raises(ValueError):
        run(monkeypatch, env, SequenceModel(stale=True))
    assert env.clicks == ["one"]


def test_api_receives_previous_actions():
    adapter = ModelAdapter("fake-test-key")
    adapter.close()
    requests = []
    def parse(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(status="completed", usage=None,
                               output_parsed=ClickAction(action="click", bid="two"))
    adapter.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    history = [{"action": "click", "bid": "one"}]
    adapter.decide("Click ONE then TWO", "[two] button 'TWO'", history)
    assert json.loads(requests[0]["input"])["previous_actions"] == history
