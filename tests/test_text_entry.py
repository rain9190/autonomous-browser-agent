import ast
import json

import pytest
from pydantic import ValidationError

from browser_agent.actions import Action, action_mapping, textbox_ids, validate_action
from browser_agent.workflow import build_workflow


def test_fill_targets_only_current_textboxes():
    assert textbox_ids("[1] textbox ''\n[2] button 'Submit'\n[3] link 'Other'") == {"1"}
    action = validate_action({"action": "fill", "bid": "1", "text": "Ada"}, {"2"}, {"1"})
    assert action.text == "Ada"


@pytest.mark.parametrize("raw", [
    {"action": "fill", "bid": "1"},
    {"action": "fill", "bid": "1", "text": ""},
    {"action": "fill", "bid": "1", "text": "x" * 257},
    {"action": "fill", "bid": "1", "text": 42},
    {"action": "click", "bid": "2", "text": "Ada"},
    {"action": "fill", "bid": "2", "text": "Ada"},
    {"action": "click", "bid": "1"},
    {"action": "fill", "bid": "missing", "text": "Ada"},
    {"action": "fill", "bid": "1", "text": "Ada", "code": "ignored?"},
])
def test_reject_invalid_text_actions(raw):
    with pytest.raises((ValidationError, ValueError)):
        validate_action(raw, {"2"}, {"1"})


def test_text_is_a_literal_never_executable_code():
    text = "'); __import__('os').system('bad') #\n\\Unicode: नमस्ते"
    code = action_mapping(json.dumps({"action": "fill", "bid": "1", "text": text}))
    parsed = ast.parse(code)
    assert len(parsed.body) == 1
    call = parsed.body[0].value
    assert call.func.attr == "fill"
    assert ast.literal_eval(call.args[0]) == text


def test_fill_length_boundary_and_click_compatibility():
    assert Action(action="fill", bid="1", text="x" * 256).text == "x" * 256
    assert action_mapping('{"action":"click","bid":"2"}') == "page.get_by_test_id('2').click(timeout=5000)"


class TextEnv:
    def __init__(self):
        self.actions = []
        self.value = ""

    def step(self, payload):
        action = json.loads(payload)
        self.actions.append(action)
        if action["action"] == "fill":
            self.value = action["text"]
        done = action["action"] == "click"
        observation = {"goal": 'Enter "Ada" and press Submit',
                       "axtree_object": {"value": self.value}, "last_action_error": ""}
        return observation, float(done and self.value == "Ada"), done, False, {}


class TextModel:
    def __init__(self):
        self.trees = []
        self.histories = []

    def decide(self, goal, tree, history):
        self.trees.append(tree)
        self.histories.append(list(history))
        if not history:
            return {"action": "fill", "bid": "1", "text": "Ada"}
        return {"action": "click", "bid": "2"}


def test_fill_then_submit_with_fresh_value(monkeypatch):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str",
        lambda obs: f"[1] textbox value={obs['value']!r}\n[2] button 'Submit'")
    env, model = TextEnv(), TextModel()
    result = build_workflow(env, model).invoke({"observation": {
        "goal": 'Enter "Ada" and press Submit', "axtree_object": {"value": ""}}, "steps": 0})
    assert result["success"] and result["steps"] == 2
    assert [a["action"] for a in env.actions] == ["fill", "click"]
    assert "Ada" in model.trees[1]
    assert model.histories[1] == [{"action": "fill", "bid": "1", "text": "Ada"}]
