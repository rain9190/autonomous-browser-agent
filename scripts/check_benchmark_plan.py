"""Verify frozen files, versions, task registry and coverage; no browser/API calls."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    manifest = json.loads((root / 'docs/benchmark/freeze-manifest.json').read_text())
    for name, expected in manifest['file_sha256'].items():
        if digest(root / name) != expected:
            raise ValueError('Frozen file changed: ' + name)
    current = {str(p.relative_to(root)) for p in (root / 'browser_agent').glob('*.py')}
    if current != {p for p in manifest['file_sha256'] if p.startswith('browser_agent/')}:
        raise ValueError('Agent source file set changed')
    for package, expected in manifest['package_versions'].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError('Package version changed: ' + package)
    for name, expected in manifest['installed_package_source_sha256'].items():
        dist = 'browsergym-miniwob' if name.startswith('browsergym/miniwob/') else 'browsergym-core'
        path = Path(importlib.metadata.distribution(dist).locate_file(name))
        if digest(path) != expected:
            raise ValueError('Installed package source changed: ' + name)
    if sys.version.split()[0] != manifest['python_version']:
        raise ValueError('Python version changed')
    plan = json.loads((root / 'docs/benchmark/task-plan.json').read_text())
    batches = json.loads((root / 'docs/benchmark/final-batches.json').read_text())['batches']
    primary = [t for t in plan['tasks'] if t['selection'] == 'primary']
    if len(primary) != 20 or plan['implemented_task_count'] != 20:
        raise ValueError('Expected 20 implemented primary tasks')
    if len({t['task'] for t in primary}) != 20:
        raise ValueError('Duplicate tasks')
    final = plan['reserved_final_seeds']
    if final != [1009, 1013, 1019] or set(final) & set(plan['development_seeds'] + plan['previously_used_seeds']):
        raise ValueError('Seed split changed')
    from browser_agent.evaluate import TASKS
    from browser_agent.budget import Budget
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    if set(TASKS) != {t['task'] for t in primary}:
        raise ValueError('Runtime allowlist differs from protocol')
    for task in plan['tasks']:
        path = root / 'vendor/miniwob-plusplus/miniwob/html/miniwob' / (task['task'] + '.html')
        if digest(path) != task['task_html_sha256']:
            raise ValueError('Task HTML changed: ' + task['task'])
        gym.spec('browsergym/miniwob.' + task['task'])
    seen = set()
    for batch in batches:
        Budget(batch['max_steps'])
        if batch['seeds'] != final or batch['api_call_ceiling'] > 24:
            raise ValueError('Invalid batch limits')
        task = batch['tasks'][0]
        kind = batch['kind']
        key = (kind, task)
        if key in seen:
            raise ValueError('Duplicate batch')
        seen.add(key)
        if kind == 'planning':
            expected_budget = next(t['action_budget'] for t in primary if t['task'] == task)
            expected_calls = 3 * (1 + expected_budget)
        elif kind == 'recovery' and task in ('enter-text', 'login-user'):
            expected_budget = 3 if task == 'enter-text' else 4
            expected_calls = 6 * expected_budget
        else:
            raise ValueError('Unknown batch')
        if batch['max_steps'] != expected_budget or batch['api_call_ceiling'] != expected_calls:
            raise ValueError('Budget arithmetic mismatch')
    expected = {('planning', t['task']) for t in primary} | {('recovery', t) for t in ('enter-text', 'login-user')}
    if seen != expected or sum(b['api_call_ceiling'] for b in batches) != 291:
        raise ValueError('Incomplete or incorrect schedule')
    return {'freeze_integrity': 'passed', 'protocol_version': '1.0',
            'agent_commit': plan['agent_commit'], 'primary_tasks': 20,
            'planning_pairs': 60, 'recovery_pairs': 6, 'batches': len(batches),
            'planned_api_call_ceiling': 291, 'final_evaluation_status': 'NOT_RUN_BY_THIS_CHECK',
            'api_calls_made': 0, 'browsers_launched': 0}


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    try:
        print(json.dumps(verify(root), indent=2))
    except (ValueError, OSError, KeyError, StopIteration, importlib.metadata.PackageNotFoundError) as exc:
        print(json.dumps({'freeze_integrity': 'failed', 'reason': str(exc), 'api_calls_made': 0, 'browsers_launched': 0}, indent=2))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
