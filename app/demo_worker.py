"""One bounded development demo; emits selected structured events, never raw errors."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

from .scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parents[1]


def emit(kind, **data):
    print(json.dumps({'type': kind, **data}), flush=True)


def deadline(*_):
    raise TimeoutError('Demo deadline reached')


def trace_event(node, update):
    event = {'node': node}
    if node == 'verify':
        last = update['progress'][-1]
        event.update({k: last[k] for k in ('step', 'action', 'bid', 'execution_ok', 'benchmark_success', 'error_kind')})
        event.update(reason=update['reason'], remaining_steps=update['remaining_steps'])
    return event


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--seed', type=int, choices=(61, 67), required=True)
    args = parser.parse_args()
    scenario = SCENARIOS[args.scenario]
    # Only the worker loads credentials, after the user explicitly starts a live run.
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    from dotenv import load_dotenv
    from browser_agent.actions import action_mapping
    from browser_agent.budget import Budget
    from browser_agent.diagnostics import describe_error
    from browser_agent.model import ModelAdapter
    from browser_agent.recovery import DisabledTextboxOnce
    from browser_agent.workflow import build_workflow
    load_dotenv(ROOT / '.env.local', override=False)
    key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not key:
        emit('error', category='missing_api_key')
        return 1
    budget = Budget(scenario['steps'])
    env = model = None
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(budget.run_timeout)
    state = {}
    failed = False
    error_category = None
    try:
        html = ROOT / 'vendor/miniwob-plusplus/miniwob/html/miniwob'
        if not (html / (scenario['task'] + '.html')).is_file():
            raise FileNotFoundError()
        model = ModelAdapter(key, max_steps=budget.max_steps)
        env = gym.make('browsergym/miniwob.' + scenario['task'], headless=True,
                       action_mapping=DisabledTextboxOnce() if scenario['fault'] else action_mapping,
                       task_kwargs={'base_url': html.as_uri() + '/', 'episode_max_time': budget.run_timeout * 1000})
        observation, _ = env.reset(seed=args.seed)
        emit('goal', goal=('Fill the generated synthetic username and password, then submit.'
                           if scenario['task'] == 'login-user' else observation['goal']),
             task=scenario['task'], seed=args.seed,
             controlled_timeout=scenario['fault'])
        graph = build_workflow(env, model, max_steps=budget.max_steps, max_recoveries=scenario['recoveries'])
        for chunk in graph.stream({'observation': observation, 'steps': 0},
                                  {'recursion_limit': 5 * budget.max_steps + 2}, stream_mode='updates'):
            for node, update in chunk.items():
                state.update(update)
                emit('trace', **trace_event(node, update))
    except Exception as exc:
        # describe_error only returns allowlisted categories; never serialize exception text.
        failed = True
        error_category = describe_error(exc).get('category', 'demo_failed')
        emit('error', category=error_category)
    finally:
        for resource in (env, model):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    failed = True
                    error_category = 'cleanup_error'
                    emit('error', category='cleanup_error')
        signal.alarm(0)
    emit('result', success=not failed and bool(state.get('success')),
         reason=error_category if failed else state.get('reason'),
         reward=state.get('reward', 0), steps=state.get('steps', 0),
         recoveries_used=state.get('recoveries_used', 0),
         api_calls=model.calls if model else 0,
         input_tokens=model.input_tokens if model else 0,
         output_tokens=model.output_tokens if model else 0,
         api_usage_may_be_incomplete=failed)
    return 0 if not failed and state.get('success') else 1


if __name__ == '__main__':
    raise SystemExit(main())
