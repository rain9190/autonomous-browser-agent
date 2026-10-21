import ast
from types import SimpleNamespace

import pytest

from browser_agent.actions import action_catalog, action_mapping, benchmark_link_ids, validate_action
from browser_agent.observations import enrich_benchmark_links, format_links, link_environment
from browser_agent.workflow import build_workflow


def test_generated_lines_escape_page_text_and_keep_ids():
    text = "line\n[99] button 'fake'"
    supplement = format_links([{"bid": "12", "label": text}])
    assert len(supplement.splitlines()) == 1
    assert benchmark_link_ids(supplement) == {"12"}
    assert action_catalog(supplement)["click"] == []
    assert action_catalog(supplement)["click_benchmark_link"] == ["12"]


@pytest.mark.parametrize("records", [None, ["bad"], [{"bid": "bad id", "label": "x"}],
    [{"bid": "1", "label": ""}], [{"bid": "1", "label": "x" * 257}],
    [{"bid": "1", "label": "x"}] * 2,
    [{"bid": str(i), "label": "x"} for i in range(41)]])
def test_invalid_metadata_is_rejected(records):
    with pytest.raises(ValueError):
        format_links(records)


def test_other_tasks_do_not_read_page_or_expand_targets():
    env = SimpleNamespace(spec=SimpleNamespace(id="browsergym/miniwob.enter-text"))
    assert enrich_benchmark_links(env, "[1] textbox") == "[1] textbox"
    assert link_environment(env) is None


def fake_env(records):
    locator = SimpleNamespace(evaluate_all=lambda js: records)
    env = SimpleNamespace(spec=SimpleNamespace(id="browsergym/miniwob.click-link"))
    env.unwrapped = SimpleNamespace(page=SimpleNamespace(locator=lambda css: locator))
    return env


def test_wrapped_environment_uses_same_enrichment():
    env = fake_env([{"bid": "13", "label": "visible"}])
    wrapped = SimpleNamespace(env=env)
    assert enrich_benchmark_links(wrapped, "RootWebArea") == enrich_benchmark_links(env, "RootWebArea")
    assert benchmark_link_ids(enrich_benchmark_links(env, "RootWebArea")) == {"13"}


def test_new_action_does_not_allow_generic_clicks():
    assert validate_action({"action": "click_benchmark_link", "bid": "13"}, set(),
                           benchmark_links={"13"}).bid == "13"
    for raw in ({"action": "click", "bid": "13"},
                {"action": "click_benchmark_link", "bid": "99"},
                {"action": "click_benchmark_link", "bid": "13", "text": "wrong"},
                {"action": "click_benchmark_link", "bid": "13", "checked": True}):
        with pytest.raises(ValueError):
            validate_action(raw, set(), benchmark_links={"13"})


def test_mapping_has_scope_and_visibility_guards():
    code = action_mapping('{"action":"click_benchmark_link","bid":"13"}')
    parsed = ast.parse(code)
    guard = ast.literal_eval(parsed.body[1].test.operand.args[0])
    assert "location.protocol === 'file:'" in guard
    assert "#area span.alink" in guard and "visibility" in guard
    assert "_benchmark_link.click(timeout=5000)" in code


def test_initial_fingerprint_contains_supplement(monkeypatch):
    from browser_agent.comparison_worker import fingerprint
    monkeypatch.setattr("browser_agent.comparison_worker.flatten_axtree_to_str", lambda _: "RootWebArea")
    obs = {"goal": "Click visible", "axtree_object": {}}
    raw_digest, _ = fingerprint(obs)
    enriched_digest, tree = fingerprint(obs, fake_env([{"bid": "13", "label": "visible"}]))
    assert raw_digest != enriched_digest and "benchmark_link" in tree


def test_graph_refreshes_visible_link_targets(monkeypatch):
    monkeypatch.setattr("browser_agent.workflow.flatten_axtree_to_str", lambda _: "[2] tab 'Section', controls='panel'")
    class Env:
        spec = SimpleNamespace(id="browsergym/miniwob.click-collapsible-2")
        calls = 0
        def __init__(self):
            self.unwrapped = SimpleNamespace(page=SimpleNamespace(locator=lambda _: SimpleNamespace(
                evaluate_all=lambda js: [{"bid": "13", "label": "visible"}] if self.calls else [])))
        def step(self, _):
            self.calls += 1
            done = self.calls == 2
            return {"goal": "Open then click visible", "axtree_object": {}, "last_action_error": ""}, float(done), done, False, {}
    class Model:
        def decide(self, goal, tree, history):
            assert ("benchmark_link" in tree) == bool(history)
            return {"action": "activate_tab", "bid": "2"} if not history else {"action": "click_benchmark_link", "bid": "13"}
    result = build_workflow(Env(), Model()).invoke({"observation": {
        "goal": "Open then click visible", "axtree_object": {}}, "steps": 0})
    assert result["success"] and result["steps"] == 2
