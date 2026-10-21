"""Opt-in tab/accordion plumbing checks, no model/API calls."""
import json
import os
from pathlib import Path
import re

import pytest


@pytest.mark.skipif(os.environ.get("RUN_BROWSER_TESTS") != "1", reason="Opt-in local Chromium test")
@pytest.mark.parametrize("task", ["click-tab", "click-collapsible"])
def test_tab_widget_activation(task):
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    from browsergym.utils.obs import flatten_axtree_to_str
    from browser_agent.actions import action_mapping, button_ids, tab_ids, validate_action
    from browser_agent.metrics import full_credit_success
    html = Path(__file__).resolve().parents[1] / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    env = gym.make(f"browsergym/miniwob.{task}", headless=True, action_mapping=action_mapping,
                   task_kwargs={"base_url": html.as_uri() + "/"})
    try:
        observation, _ = env.reset(seed=61)
        tree = flatten_axtree_to_str(observation["axtree_object"])
        tabs = tab_ids(tree)
        if task == "click-tab":
            number = re.search(r"Tab #(\d+)", observation["goal"]).group(1)
            bid = next(bid for bid in tabs if env.unwrapped.page.get_by_test_id(bid).inner_text().strip() == f"Tab #{number}")
        else:
            bid, = tabs
        raw = {"action": "activate_tab", "bid": bid}
        validate_action(raw, button_ids(tree), set(), tabs=tabs)
        observation, reward, terminated, truncated, _ = env.step(json.dumps(raw))
        assert not observation["last_action_error"]
        if task == "click-collapsible":
            assert not terminated
            assert env.unwrapped.page.get_by_test_id(bid).get_attribute("aria-expanded") == "true"
            fresh_tree = flatten_axtree_to_str(observation["axtree_object"])
            submit, = button_ids(fresh_tree)
            observation, reward, terminated, truncated, _ = env.step(json.dumps({"action": "click", "bid": submit}))
        assert full_credit_success(reward, bool(terminated), bool(truncated), observation["last_action_error"])
    finally:
        env.close()
