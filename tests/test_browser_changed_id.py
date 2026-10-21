"""Opt-in real Chromium check; no model or API calls."""
import json
import os
from pathlib import Path

import pytest


@pytest.mark.skipif(os.environ.get("RUN_BROWSER_TESTS") != "1", reason="Opt-in local Chromium test")
def test_browsergym_assigns_new_bid_after_failure():
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    from browsergym.utils.obs import flatten_axtree_to_str
    from browser_agent.actions import textbox_ids, validate_action
    from browser_agent.recovery import ChangedTextboxIdOnce

    html = Path(__file__).resolve().parents[1] / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    mapping = ChangedTextboxIdOnce()
    env = gym.make("browsergym/miniwob.enter-text", headless=True, action_mapping=mapping,
                   task_kwargs={"base_url": html.as_uri() + "/"})
    try:
        observation, _ = env.reset(seed=11)
        old, = textbox_ids(flatten_axtree_to_str(observation["axtree_object"]))
        native_id = env.unwrapped.page.get_by_test_id(old).get_attribute("id")
        observation, _, terminated, truncated, _ = env.step(json.dumps({
            "action": "fill", "bid": old, "text": "probe"}))
        error = observation["last_action_error"]
        assert error.startswith("TimeoutError:") and "Locator.fill" in error
        fresh_ids = textbox_ids(flatten_axtree_to_str(observation["axtree_object"]))
        fresh, = fresh_ids
        assert fresh != old and not terminated and not truncated
        assert env.unwrapped.page.get_by_test_id(old).count() == 0
        target = env.unwrapped.page.get_by_test_id(fresh)
        assert target.get_attribute("id") == native_id and target.input_value() == ""
        with pytest.raises(ValueError):
            validate_action({"action": "fill", "bid": old, "text": "probe"}, set(), fresh_ids)
        observation, _, _, _, _ = env.step(json.dumps({"action": "fill", "bid": fresh, "text": "probe"}))
        assert not observation["last_action_error"] and target.input_value() == "probe"
    finally:
        env.close()
