import ast
import json

import pytest
from pydantic import ValidationError

from browser_agent.actions import Action, action_mapping, selection_targets, validate_action
from browser_agent.workflow import build_workflow

TREE = """RootWebArea 'Form'
    [1] checkbox 'Alpha', checked=False
    [2] radio 'Beta', checked=False
    [3] combobox ''
        [4] option 'First', selected=True
        [5] option "O'Brien", selected=False
    [6] button 'Submit'
    [7] textbox ''
"""


def test_selection_roles_and_quoted_option_labels():
    targets = selection_targets(TREE)
    assert targets == {"checkbox": {"1"}, "radio": {"2"},
                       "select_options": {"3": ["First", "O'Brien"]}}


@pytest.mark.parametrize("raw", [
    {"action": "set_checked", "bid": "1", "checked": True},
    {"action": "set_checked", "bid": "1", "checked": False},
    {"action": "check_radio", "bid": "2"},
    {"action": "select_option", "bid": "3", "text": "O'Brien"},
])
def test_valid_selection(raw):
    assert validate_action(raw, {"6"}, {"7"}, selection_targets(TREE)).bid == raw["bid"]


@pytest.mark.parametrize("raw", [
    {"action": "set_checked", "bid": "1"},
    {"action": "set_checked", "bid": "1", "checked": "true"},
    {"action": "set_checked", "bid": "1", "checked": 1},
    {"action": "set_checked", "bid": "1", "checked": True, "text": "bad"},
    {"action": "check_radio", "bid": "2", "checked": False},
    {"action": "select_option", "bid": "3"},
    {"action": "select_option", "bid": "3", "text": "missing"},
    {"action": "select_option", "bid": "3", "text": "First", "checked": True},
    {"action": "click", "bid": "1"},
    {"action": "fill", "bid": "3", "text": "First"},
    {"action": "set_checked", "bid": "2", "checked": True},
    {"action": "check_radio", "bid": "1"},
    {"action": "select_option", "bid": "4", "text": "First"},
])
def test_invalid_schema_role_or_label(raw):
    with pytest.raises((ValidationError, ValueError)):
        validate_action(raw, {"6"}, {"7"}, selection_targets(TREE))


def test_options_belong_to_correct_parent_and_duplicates_rejected():
    tree = "[1] combobox\n  [2] option 'A'\n[3] combobox\n  [4] option 'B'\n  [5] option 'B'"
    targets = selection_targets(tree)
    assert targets["select_options"] == {"1": ["A"], "3": ["B", "B"]}
    with pytest.raises(ValueError):
        validate_action({"action": "select_option", "bid": "1", "text": "B"}, set(), set(), targets)
    with pytest.raises(ValueError):
        validate_action({"action": "select_option", "bid": "3", "text": "B"}, set(), set(), targets)


def test_selection_mapping_has_native_guard_and_literal_label():
    label = "'); unsafe() #\nनमस्ते"
    code = action_mapping(json.dumps({"action": "select_option", "bid": "3", "text": label}))
    parsed = ast.parse(code)
    assert isinstance(parsed.body[1], ast.If)
    call = parsed.body[-1].value
    assert call.func.attr == "select_option"
    assert ast.literal_eval(call.keywords[0].value) == label
    assert "el.tagName === 'SELECT'" in code


def test_checkbox_and_radio_mapping_are_idempotent_methods():
    assert ".set_checked(True," in action_mapping('{"action":"set_checked","bid":"1","checked":true}')
    assert ".set_checked(False," in action_mapping('{"action":"set_checked","bid":"1","checked":false}')
    assert ".check(" in action_mapping('{"action":"check_radio","bid":"2"}')


def test_graph_select_then_submit(monkeypatch):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str", lambda _: TREE)
    class Model:
        def decide(self, goal, tree, history):
            return {"action": "select_option", "bid": "3", "text": "O'Brien"} if not history else {"action": "click", "bid": "6"}
    class Env:
        calls = 0
        def step(self, payload):
            self.calls += 1
            done = json.loads(payload)["action"] == "click"
            return {"goal": "Select O'Brien and Submit", "axtree_object": {}, "last_action_error": ""}, float(done), done, False, {}
    env = Env()
    state = build_workflow(env, Model()).invoke({"observation": {
        "goal": "Select O'Brien and Submit", "axtree_object": {}}, "steps": 0})
    assert state["success"] and env.calls == 2
    assert state["history"][0]["action"] == "select_option"


def test_sdk_strict_schema_requires_nullable_checked():
    from openai.lib._pydantic import to_strict_json_schema
    schema = to_strict_json_schema(Action)
    assert set(schema["required"]) == {"action", "bid", "text", "checked"}
    assert schema["additionalProperties"] is False
