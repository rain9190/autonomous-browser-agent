import json
from types import SimpleNamespace

import pytest

from browser_agent.actions import Action, action_catalog, selection_targets, validate_action
from browser_agent.diagnostics import describe_error
from browser_agent.model import ModelAdapter
from browser_agent.oneshot import ActionPlan, OneShotAdapter

TREE = "[1] LabelText ''\n  [2] radio 'Choice', checked='false'\n[3] button 'Submit'\n[4] checkbox 'Other'\n[5] textbox ''"


def test_catalog_exposes_legal_control_ids_not_label_parents():
    catalog = action_catalog(TREE)
    assert catalog["click"] == ["3"] and catalog["check_radio"] == ["2"]
    assert catalog["set_checked"] == ["4"] and catalog["fill"] == ["5"]
    assert "1" not in json.dumps(catalog)


def test_catalog_omits_ambiguous_option_labels():
    catalog = action_catalog("[1] combobox\n  [2] option 'A'\n  [3] option 'A'\n  [4] option 'B'")
    assert catalog["select_option"] == {"1": ["B"]}


def test_wrong_radio_action_is_still_rejected_with_safe_metadata():
    with pytest.raises(ValueError) as error:
        validate_action({"action": "click", "bid": "2"}, {"3"}, {"5"}, selection_targets(TREE))
    report = describe_error(error.value)
    assert report == {"category": "observed_role_mismatch", "requested_action": "click",
                      "target_bid": "2", "observed_target_roles": ["radio"]}
    assert "Choice" not in json.dumps(report)


@pytest.mark.parametrize("oneshot", [False, True])
def test_both_models_receive_identical_legal_catalog(oneshot):
    adapter = OneShotAdapter("fake-key") if oneshot else ModelAdapter("fake-key")
    adapter.close()
    requests = []
    def parse(**kwargs):
        requests.append(kwargs)
        output = (ActionPlan(actions=[Action(action="check_radio", bid="2")]) if oneshot
                  else Action(action="check_radio", bid="2"))
        return SimpleNamespace(status="completed", usage=None, output_parsed=output)
    adapter.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    if oneshot:
        adapter.plan("Select requested choice", TREE)
    else:
        adapter.decide("Select requested choice", TREE)
    assert json.loads(requests[0]["input"])["allowed_targets"] == action_catalog(TREE)
    assert adapter.calls == 1


@pytest.mark.parametrize("oneshot", [False, True])
def test_catalog_size_guard_precedes_network(monkeypatch, oneshot):
    module = "browser_agent.oneshot" if oneshot else "browser_agent.model"
    monkeypatch.setattr(module + ".action_catalog", lambda _: {"click": ["x" * 9000]})
    adapter = OneShotAdapter("fake-key") if oneshot else ModelAdapter("fake-key")
    try:
        with pytest.raises(ValueError, match="catalogue"):
            adapter.plan("goal", TREE) if oneshot else adapter.decide("goal", TREE)
        assert adapter.calls == 0
    finally:
        adapter.close()
