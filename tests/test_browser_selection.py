"""Opt-in native-control plumbing checks; no model/API calls or submissions."""
import json
import os
from pathlib import Path

import pytest


@pytest.mark.skipif(os.environ.get("RUN_BROWSER_TESTS") != "1", reason="Opt-in local Chromium test")
@pytest.mark.parametrize("task", ["click-checkboxes", "click-option", "choose-list"])
def test_native_selection_is_idempotent(task):
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    from browsergym.utils.obs import flatten_axtree_to_str
    from browser_agent.actions import action_mapping, selection_targets, validate_action
    html = Path(__file__).resolve().parents[1] / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    env = gym.make(f"browsergym/miniwob.{task}", headless=True, action_mapping=action_mapping,
                   task_kwargs={"base_url": html.as_uri() + "/"})
    try:
        observation, _ = env.reset(seed=61)
        targets = selection_targets(flatten_axtree_to_str(observation["axtree_object"]))
        if task == "click-checkboxes":
            bid = sorted(targets["checkbox"])[0]
            raw = {"action": "set_checked", "bid": bid, "checked": True}
        elif task == "click-option":
            bid = sorted(targets["radio"])[0]
            raw = {"action": "check_radio", "bid": bid}
        else:
            bid = next(iter(targets["select_options"]))
            labels = targets["select_options"][bid]
            current = env.unwrapped.page.get_by_test_id(bid).locator("option:checked").text_content()
            label = next(label for label in labels if label != current)
            raw = {"action": "select_option", "bid": bid, "text": label}
        action = validate_action(raw, set(), set(), targets)
        for _ in range(2):
            observation, _, terminated, truncated, _ = env.step(action.model_dump_json(exclude_none=True))
            assert not observation["last_action_error"] and not terminated and not truncated
        locator = env.unwrapped.page.get_by_test_id(bid)
        if task == "choose-list":
            assert locator.locator("option:checked").text_content() == raw["text"]
        else:
            assert locator.is_checked()
        if task == "click-checkboxes":
            observation, _, _, _, _ = env.step(json.dumps({**raw, "checked": False}))
            assert not observation["last_action_error"] and not locator.is_checked()
        elif task == "click-option":
            other = next(target for target in targets["radio"] if target != bid)
            raw_other = {"action": "check_radio", "bid": other}
            validate_action(raw_other, set(), set(), targets)
            observation, _, _, _, _ = env.step(json.dumps(raw_other))
            assert not observation["last_action_error"]
            assert env.unwrapped.page.get_by_test_id(other).is_checked() and not locator.is_checked()
    finally:
        env.close()
