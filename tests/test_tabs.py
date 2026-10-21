import ast

import pytest

from browser_agent.actions import Action, action_catalog, action_mapping, tab_ids, validate_action
from browser_agent.workflow import build_workflow

TREE = """[1] tablist ''
  [2] tab 'Section', expanded=False, controls='panel'
  [3] tab 'Submit', expanded=False
    [4] button 'Submit'
  [5] link 'Other'
[6] generic 'Unrelated'
[7] tabpanel 'Section'
"""


def test_only_panel_controlling_tabs_are_eligible():
    assert tab_ids(TREE) == {"2"}
    assert action_catalog(TREE)["activate_tab"] == ["2"]
    assert action_catalog(TREE)["click"] == ["4"]


def test_tab_action_requires_its_own_role():
    action = validate_action({"action": "activate_tab", "bid": "2"}, {"4"}, set(), tabs=tab_ids(TREE))
    assert action.action == "activate_tab"


@pytest.mark.parametrize("raw", [
    {"action": "click", "bid": "2"},
    {"action": "activate_tab", "bid": "3"},
    {"action": "activate_tab", "bid": "4"},
    {"action": "activate_tab", "bid": "5"},
    {"action": "activate_tab", "bid": "6"},
    {"action": "activate_tab", "bid": "2", "text": "anything"},
    {"action": "activate_tab", "bid": "2", "checked": True},
])
def test_wrong_roles_and_arguments_remain_blocked(raw):
    with pytest.raises(ValueError):
        validate_action(raw, {"4"}, set(), tabs=tab_ids(TREE))


def test_fixed_mapping_checks_panel_and_scopes_anchor():
    code = action_mapping('{"action":"activate_tab","bid":"2"}')
    ast.parse(code)
    assert "get_by_test_id('2')" in code
    assert "aria-controls" in code and "document.getElementById" in code
    assert "_tab_target.locator('a.ui-tabs-anchor')" in code
    assert "Ambiguous tab anchor" in code


def test_graph_observes_new_button_after_tab_action(monkeypatch):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str", lambda obs:
        "[2] tab 'Section', controls='panel'" if not obs["open"] else
        "[2] tab 'Section', expanded=True, controls='panel'\n[4] button 'Submit'")
    class Model:
        def decide(self, goal, tree, history):
            return {"action": "activate_tab", "bid": "2"} if not history else {"action": "click", "bid": "4"}
    class Env:
        calls = 0
        def step(self, _):
            self.calls += 1
            done = self.calls == 2
            return {"goal": "Expand then Submit", "axtree_object": {"open": True},
                    "last_action_error": ""}, float(done), done, False, {}
    result = build_workflow(Env(), Model()).invoke({"observation": {
        "goal": "Expand then Submit", "axtree_object": {"open": False}}, "steps": 0})
    assert result["success"] and result["steps"] == 2
    assert [a["action"] for a in result["history"]] == ["activate_tab", "click"]


def test_tab_action_requires_no_new_schema_arguments():
    from openai.lib._pydantic import to_strict_json_schema
    schema = to_strict_json_schema(Action)
    assert "activate_tab" in schema["properties"]["action"]["enum"]
    assert set(schema["required"]) == {"action", "bid", "text", "checked"}
