"""Opt-in benchmark-span plumbing, no model/API calls."""
import json
import os
from pathlib import Path
import re

import pytest


@pytest.fixture
def make_env():
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    from browser_agent.actions import action_mapping
    html = Path(__file__).resolve().parents[1] / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    envs = []
    def make(task):
        env = gym.make(f"browsergym/miniwob.{task}", headless=True, action_mapping=action_mapping,
                       task_kwargs={"base_url": html.as_uri() + "/"})
        envs.append(env)
        return env
    yield make
    for env in envs:
        env.close()


pytestmark = pytest.mark.skipif(os.environ.get("RUN_BROWSER_TESTS") != "1", reason="Opt-in local Chromium test")


def test_visible_span_can_complete_click_link(make_env):
    from browsergym.utils.obs import flatten_axtree_to_str
    from browser_agent.observations import enrich_benchmark_links
    from browser_agent.actions import benchmark_link_ids, validate_action
    from browser_agent.metrics import full_credit_success
    env = make_env("click-link")
    observation, _ = env.reset(seed=61)
    tree = enrich_benchmark_links(env, flatten_axtree_to_str(observation["axtree_object"]))
    target = re.search(r'"([^"]+)"', observation["goal"]).group(1)
    bid = next(bid for bid in benchmark_link_ids(tree)
               if env.unwrapped.page.get_by_test_id(bid).inner_text() == target)
    action = {"action": "click_benchmark_link", "bid": bid}
    validate_action(action, set(), benchmark_links=benchmark_link_ids(tree))
    observation, reward, terminated, truncated, _ = env.step(json.dumps(action))
    assert full_credit_success(reward, bool(terminated), bool(truncated), observation["last_action_error"])


def test_collapsed_links_stay_hidden_and_refresh_on_panel_change(make_env):
    from browsergym.utils.obs import flatten_axtree_to_str
    from browser_agent.observations import enrich_benchmark_links
    from browser_agent.actions import benchmark_link_ids, tab_ids
    env = make_env("click-collapsible-2")
    observation, _ = env.reset(seed=61)
    raw = flatten_axtree_to_str(observation["axtree_object"])
    assert not benchmark_link_ids(enrich_benchmark_links(env, raw))
    headers = sorted(tab_ids(raw))
    sets = []
    for header in headers[:2]:
        observation, _, terminated, truncated, _ = env.step(json.dumps({"action": "activate_tab", "bid": header}))
        assert not observation["last_action_error"] and not terminated and not truncated
        tree = enrich_benchmark_links(env, flatten_axtree_to_str(observation["axtree_object"]))
        sets.append(benchmark_link_ids(tree))
    assert sets[0] and sets[1] and sets[0].isdisjoint(sets[1])


def test_mapping_rejects_non_link_container(make_env):
    env = make_env("click-link")
    env.reset(seed=61)
    bid = env.unwrapped.page.locator("#area").get_attribute("bid")
    observation, _, terminated, truncated, _ = env.step(json.dumps({"action": "click_benchmark_link", "bid": bid}))
    assert observation["last_action_error"] and not terminated and not truncated
