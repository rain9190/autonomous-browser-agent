"""Opt-in local Chromium plumbing test: no model or API request."""
import json
import os
from pathlib import Path

import pytest


@pytest.mark.skipif(os.environ.get("RUN_BROWSER_TESTS") != "1", reason="Opt-in local Chromium test")
def test_real_disabled_textbox_timeout_and_restore():
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    from browsergym.utils.obs import flatten_axtree_to_str
    from browser_agent.actions import textbox_ids
    from browser_agent.recovery import DisabledTextboxOnce

    root = Path(__file__).resolve().parents[1]
    html = root / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    mapping = DisabledTextboxOnce()
    env = gym.make("browsergym/miniwob.enter-text", headless=True, action_mapping=mapping,
                   task_kwargs={"base_url": html.as_uri() + "/"})
    try:
        observation, _ = env.reset(seed=42)
        bid, = textbox_ids(flatten_axtree_to_str(observation["axtree_object"]))
        action = json.dumps({"action": "fill", "bid": bid, "text": "plumbing probe"})
        observation, reward, terminated, truncated, _ = env.step(action)
        error = observation["last_action_error"]
        assert error.startswith("TimeoutError:") and "Locator.fill" in error and "exceeded" in error
        assert mapping.injected and not terminated and not truncated
        target = env.unwrapped.page.get_by_test_id(bid)
        assert target.is_enabled() and target.input_value() == ""
        observation, _, terminated, truncated, _ = env.step(action)
        assert not observation["last_action_error"]
        assert target.input_value() == "plumbing probe"
        assert not terminated and not truncated
    finally:
        env.close()
