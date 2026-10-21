"""Small explicit instruction set for the local benchmark demo."""
SCENARIOS = {
    'text': {'instruction': 'Type the requested text and submit', 'task': 'enter-text', 'steps': 2, 'recoveries': 0, 'fault': False},
    'login': {'instruction': 'Complete the synthetic login form', 'task': 'login-user', 'steps': 3, 'recoveries': 0, 'fault': False},
    'discover': {'instruction': 'Find the requested link inside the sections', 'task': 'click-collapsible-2', 'steps': 6, 'recoveries': 0, 'fault': False},
    'recover': {'instruction': 'Complete text entry with a controlled timeout', 'task': 'enter-text', 'steps': 3, 'recoveries': 1, 'fault': True},
}


def resolve_instruction(value):
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError('Choose one of the four supported instructions')
    normalized = ' '.join(value.casefold().split())
    for name, scenario in SCENARIOS.items():
        if normalized in (name, scenario['instruction'].casefold()):
            return name
    raise ValueError('Choose one of the four supported instructions')


def validate_request(body):
    if not isinstance(body, dict) or set(body) != {'instruction', 'seed'}:
        raise ValueError('Expected an instruction and development seed')
    name = resolve_instruction(body['instruction'])
    if type(body['seed']) is not int or body['seed'] not in (61, 67):
        raise ValueError('Demo seeds are 61 and 67 only')
    return name, body['seed']
