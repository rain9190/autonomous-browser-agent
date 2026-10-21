"""Seven-action completion, hard stop and aggregate spending regressions; no API."""
import json
import pytest
from browser_agent.budget import Budget
from browser_agent.workflow import build_workflow
from browser_agent.oneshot import execute_plan
from browser_agent.evaluate import TASKS, run_suite

ACTIONS = [{"action": "set_checked", "bid": str(i), "checked": True} for i in range(6)] + [{"action": "click", "bid": "submit"}]
TREE = '\n'.join(f"[{i}] checkbox 'item{i}'" for i in range(6)) + "\n[submit] button 'Submit'"

class Env:
    def __init__(self):
        self.actions = []
    def step(self, payload):
        self.actions.append(json.loads(payload))
        done = self.actions[-1]['action'] == 'click'
        won = done and self.actions == ACTIONS
        return {'goal': 'Select all six and Submit', 'axtree_object': {}, 'last_action_error': ''}, float(won), done, False, {}

class Model:
    def decide(self, goal, tree, history):
        return ACTIONS[len(history)]

@pytest.mark.parametrize('steps,success', [(6, False), (7, True)])
def test_iterative_seven_actions_and_six_action_stop(monkeypatch, steps, success):
    monkeypatch.setattr('browser_agent.workflow.flatten_axtree_to_str', lambda _: TREE)
    env = Env()
    result = build_workflow(env, Model(), max_steps=steps).invoke(
        {'observation': {'goal': 'Select all six and Submit', 'axtree_object': {}}, 'steps': 0},
        {'recursion_limit': 5 * steps + 2})
    assert result['success'] is success
    assert result['steps'] == len(env.actions) == steps
    assert result['remaining_steps'] == 0
    if not success:
        assert result['reason'] == 'step_budget_exhausted'

def test_oneshot_seven_action_plan_and_smaller_budget(monkeypatch):
    monkeypatch.setattr('browser_agent.oneshot.flatten_axtree_to_str', lambda _: TREE)
    obs = {'axtree_object': {}}
    env = Env()
    with pytest.raises(ValueError):
        execute_plan(env, obs, {'actions': ACTIONS}, max_steps=6)
    assert not env.actions
    result = execute_plan(env, obs, {'actions': ACTIONS}, max_steps=7)
    assert result['success'] and result['steps'] == 7

def test_four_seven_step_episodes_exceed_unchanged_suite_cap(tmp_path):
    assert 'click-checkboxes' in TASKS
    assert Budget(7).run_timeout == 190
    with pytest.raises(ValueError, match='24-call'):
        run_suite(['click-checkboxes'], [61, 67, 71, 73], tmp_path/'unused', max_steps=7)
