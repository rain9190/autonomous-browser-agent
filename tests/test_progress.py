import json
from types import SimpleNamespace

import pytest

from browser_agent.budget import Budget
from browser_agent.evaluate import parse_result, run_episode, run_suite
from browser_agent.model import ModelAdapter
from browser_agent.workflow import build_workflow


@pytest.mark.parametrize("value", [0, 8, -1, True, 2.5])
def test_invalid_budget(value):
    with pytest.raises(ValueError):
        Budget(value)


class FormEnv:
    def __init__(self):
        self.actions = []
        self.fields = {"user": "", "password": ""}

    def step(self, payload):
        action = json.loads(payload)
        self.actions.append(action)
        if action["action"] == "fill":
            self.fields[action["bid"]] = action["text"]
        done = action["action"] == "click"
        won = done and self.fields == {"user": "ada", "password": "p@ss"}
        return {"goal": "Fill username ada and password p@ss then Login",
                "axtree_object": dict(self.fields), "last_action_error": ""}, float(won), done, False, {}


class FormModel:
    def decide(self, goal, tree, history):
        return [
            {"action": "fill", "bid": "user", "text": "ada"},
            {"action": "fill", "bid": "password", "text": "p@ss"},
            {"action": "click", "bid": "login"},
        ][len(history)]


def form_run(monkeypatch, max_steps):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str",
        lambda obs: f"[user] textbox 'Username' value={obs['user']!r}\n[password] textbox 'Password'\n[login] button 'Login'")
    env = FormEnv()
    state = build_workflow(env, FormModel(), max_steps=max_steps).invoke({
        "observation": {"goal": "Fill both fields then Login", "axtree_object": env.fields},
        "steps": 0}, {"recursion_limit": 5 * max_steps + 2})
    return state, env


def test_three_actions_with_progress(monkeypatch):
    state, env = form_run(monkeypatch, 3)
    assert state["success"] and len(env.actions) == 3
    assert state["remaining_steps"] == 0
    assert [row["benchmark_success"] for row in state["progress"]] == [False, False, True]
    assert all(row["execution_ok"] for row in state["progress"])
    assert all("text" not in row for row in state["progress"])


def test_default_budget_stops_before_third_action(monkeypatch):
    state, env = form_run(monkeypatch, 2)
    assert not state["success"] and len(env.actions) == 2
    assert state["reason"] == "step_budget_exhausted"
    assert state["remaining_steps"] == 0


def test_adapter_three_call_budget_and_remaining_context():
    adapter = ModelAdapter("fake-key", max_steps=3)
    adapter.close()
    requests = []
    def parse(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(status="completed", usage=None,
                               output_parsed=SimpleNamespace(model_dump=lambda **_: {"action": "click", "bid": "1"}))
    adapter.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    for _ in range(3):
        adapter.decide("goal", "[1] button")
    with pytest.raises(RuntimeError):
        adapter.decide("goal", "[1] button")
    assert [json.loads(r["input"])["remaining_api_calls_including_this"] for r in requests] == [3, 2, 1]


def test_evaluator_propagates_budget(monkeypatch):
    class Process:
        returncode = 0
        def communicate(self, timeout=None):
            assert timeout == Budget(3).run_timeout + 10
            return json.dumps({"task": "login-user", "seed": 7, "success": True,
                "reason": "benchmark_success", "terminated": True, "truncated": False,
                "reward": 1, "steps": 3, "api_calls": 3,
                "input_tokens": 300, "output_tokens": 30}), ""
    def spawn(command, **kwargs):
        assert command[-2:] == ["--max-steps", "3"]
        return Process()
    monkeypatch.setattr("browser_agent.evaluate.subprocess.Popen", spawn)
    assert run_episode("login-user", 7, 3)["success"]


def test_suite_call_ceiling_before_start(tmp_path):
    with pytest.raises(ValueError, match="24-call"):
        run_suite(["login-user"], list(range(5)), tmp_path / "eval", max_steps=6)
    assert not (tmp_path / "eval").exists()


def test_three_step_suite_summary(tmp_path):
    def runner(task, seed, max_steps):
        assert max_steps == 3
        return {"task": task, "seed": seed, "status": "success", "success": True,
                "api_calls": 3, "input_tokens": 300, "output_tokens": 30}
    summary = run_suite(["login-user"], [7, 123], tmp_path / "eval", runner, max_steps=3)
    assert summary["complete"] and summary["api_call_ceiling"] == 6
    assert summary["reported_api_calls"] == 6
