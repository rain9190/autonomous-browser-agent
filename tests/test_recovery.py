import ast
import json

import pytest

from browser_agent.evaluate import parse_result
from browser_agent.recovery import FillFailureOnce
from browser_agent.workflow import build_workflow


class FlakyForm:
    def __init__(self, failures=1, click_error=False, terminal_error=False, raise_error=False):
        self.failures = failures
        self.click_error = click_error
        self.terminal_error = terminal_error
        self.raise_error = raise_error
        self.calls = 0
        self.value = ""
        self.bid = "old"

    def observation(self, error=""):
        return {"goal": 'Enter "Ada" and Submit', "axtree_object": {
            "bid": self.bid, "value": self.value}, "last_action_error": error}

    def step(self, payload):
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("unexpected environment exception")
        action = json.loads(payload)
        if action["action"] == "fill":
            assert action["bid"] == self.bid
            if self.failures:
                self.failures -= 1
                self.bid = "fresh"
                return self.observation("private browser diagnostic"), 0, self.terminal_error, False, {}
            self.value = action["text"]
            return self.observation(), 0, False, False, {}
        if self.click_error:
            return self.observation("click timed out"), 0, False, False, {}
        return self.observation(), float(self.value == "Ada"), True, False, {}


class Model:
    def __init__(self):
        self.requests = []

    def decide(self, goal, tree, history, recovery_context=None):
        self.requests.append({"tree": tree, "history": list(history), "recovery": recovery_context})
        if not history:
            bid = "fresh" if "[fresh]" in tree else "old"
            return {"action": "fill", "bid": bid, "text": "Ada"}
        return {"action": "click", "bid": "submit"}


def run(monkeypatch, env, steps=3, recoveries=1):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str",
        lambda obs: f"[{obs['bid']}] textbox value={obs['value']!r}\n[submit] button 'Submit'")
    model = Model()
    result = build_workflow(env, model, steps, recoveries).invoke({
        "observation": env.observation(), "steps": 0}, {"recursion_limit": 5 * steps + 2})
    return result, model


def test_recover_with_fresh_id_and_no_false_history(monkeypatch):
    env = FlakyForm()
    state, model = run(monkeypatch, env)
    assert state["success"] and state["steps"] == env.calls == 3
    assert state["recoveries_used"] == 1
    assert [x["execution_ok"] for x in state["progress"]] == [False, True, True]
    assert model.requests[1]["history"] == []
    assert model.requests[1]["recovery"] == {
        "action": "fill", "bid": "old", "status": "previous_fill_failed"}
    assert "[fresh]" in model.requests[1]["tree"]
    assert [a["bid"] for a in state["history"]] == ["fresh", "submit"]
    assert "private browser diagnostic" not in json.dumps(state["failed_actions"])
    assert model.requests[2]["recovery"] is None


def test_default_recovery_disabled(monkeypatch):
    state, model = run(monkeypatch, FlakyForm(), recoveries=0)
    assert not state["success"] and state["steps"] == 1
    assert state["reason"] == "browser_action_error"
    assert len(model.requests) == 1


def test_recovery_cap_stops_repeated_failure(monkeypatch):
    state, model = run(monkeypatch, FlakyForm(failures=10), steps=6)
    assert not state["success"] and state["steps"] == 2
    assert state["recoveries_used"] == 1 and len(model.requests) == 2


def test_retry_consumes_original_step_budget(monkeypatch):
    state, model = run(monkeypatch, FlakyForm(), steps=2)
    assert not state["success"] and state["reason"] == "step_budget_exhausted"
    assert state["remaining_steps"] == 0 and len(model.requests) == 2


def test_click_failure_is_never_retried(monkeypatch):
    state, model = run(monkeypatch, FlakyForm(failures=0, click_error=True), steps=6)
    assert not state["success"] and state["steps"] == 2
    assert state["recoveries_used"] == 0 and len(model.requests) == 2


def test_terminal_failure_is_never_retried(monkeypatch):
    state, model = run(monkeypatch, FlakyForm(terminal_error=True))
    assert state["steps"] == 1 and state["recoveries_used"] == 0


def test_unexpected_exception_is_not_retried(monkeypatch):
    env = FlakyForm(raise_error=True)
    with pytest.raises(RuntimeError):
        run(monkeypatch, env)
    assert env.calls == 1


@pytest.mark.parametrize("value", [-1, 3, True, 1.5])
def test_invalid_recovery_cap(value):
    with pytest.raises(ValueError):
        build_workflow(None, None, max_recoveries=value)


def test_failure_simulator_fails_one_fill_only():
    mapping = FillFailureOnce()
    click = '{"action":"click","bid":"submit"}'
    fill = '{"action":"fill","bid":"field","text":"Ada"}'
    assert ".click(" in mapping(click) and not mapping.injected
    assert isinstance(ast.parse(mapping(fill)).body[0], ast.Raise)
    assert mapping.injected
    assert ".fill('Ada'" in mapping(fill)


def test_simulated_run_cannot_enter_normal_evaluation():
    result = parse_result(json.dumps({"simulated_failure_requested": True}), 0, "enter-text", 42)
    assert result["status"] == "invalid_report" and not result["success"]
