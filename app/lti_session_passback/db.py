CONSUMERS = {
    'secretconsumerkey':
    {
        'secret': 'supersecretconsumersecret',
        'timestamp_and_nonce': []
    }
}

SESSIONS = {}
SOLUTIONS = {}


### Consumers block ###

def get_secret(key):
    return CONSUMERS.get(str(key), {}).get('secret', '')


def is_key_valid(key):
    return key in CONSUMERS


def has_timestamp_and_nonce(key, timestamp, nonce):
    return (timestamp, nonce) in CONSUMERS[key]['timestamp_and_nonce']


def add_timestamp_and_nonce(key, timestamp, nonce):
    CONSUMERS[key]['timestamp_and_nonce'].append((timestamp, nonce))


### Sessions block ###

def get_session(session_id): return SESSIONS.get(session_id, {})


def add_session(session_id, task, passback_params, admin=False): 
    session = get_session(session_id)
    if session:
        session['tasks'][task] = dict(passback_params=passback_params)
        session['admin'] = admin
    else:
        SESSIONS[session_id] = {'tasks': {task: {'passback_params': passback_params}}, 'admin': admin}
    print(SESSIONS)


### Solution block ###

def get_solution(solution_id):
    return SOLUTIONS.get(solution_id, {})


def add_solution(solution_id, username, task_id, score, passback_params, is_passbacked=False):
    SOLUTIONS[solution_id] = {
        '_id': solution_id,
        'login': username,
        'task_id': task_id,
        'score': score,
        'passback_params': passback_params,
        'is_passbacked': is_passbacked
    }


def get_unsend_solution():
    return (SOLUTIONS[solution_id] for solution_id in SOLUTIONS if not SOLUTIONS[solution_id].get('is_passbacked', True))


def set_passbacked_flag(solution_id, flag):
    SOLUTIONS[solution_id]['is_passbacked'] = flag
