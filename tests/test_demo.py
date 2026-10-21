"""Demo boundaries and event filtering; no sockets, browser, credentials or model calls."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from app.scenarios import validate_request
from app.demo import command, Handler, Runs
from app.demo_worker import trace_event


@pytest.mark.parametrize('body', [None, {}, {'instruction':'visit my bank','seed':61},
    {'instruction':'text','seed':1009}, {'instruction':'text','seed':True},
    {'instruction':'text','seed':61,'url':'https://example.com'},
    {'instruction':['text'],'seed':61}])
def test_reject_unscoped_demo_requests(body):
    with pytest.raises(ValueError):validate_request(body)


def test_supported_instruction_and_fixed_command():
    assert validate_request({'instruction':'  TYPE THE REQUESTED TEXT AND SUBMIT  ','seed':67}) == ('text',67)
    args=command('text',61)
    assert args[-6:]==['-m','app.demo_worker','--scenario','text','--seed','61']
    assert '-B' in args
    with pytest.raises(ValueError): command('text; shell',61)


def test_trace_events_strip_proposal_and_typed_values():
    assert trace_event('decide',{'proposal':{'text':'private'}})=={'node':'decide'}
    update={'progress':[dict(step=1,action='fill',bid='14',execution_ok=True,
        benchmark_success=False,error_kind=None,text='private')], 'reason':'continue','remaining_steps':1}
    event=trace_event('verify',update)
    assert event['action']=='fill' and 'private' not in json.dumps(event)


def test_run_manager_does_not_spawn_second_worker(monkeypatch):
    runs=Runs();runs.running=True
    monkeypatch.setattr('app.demo.subprocess.Popen',lambda *a,**k:pytest.fail('must not spawn'))
    with pytest.raises(ValueError):runs.start({'instruction':'text','seed':61})


def test_http_boundary_checks_before_execution():
    h=object.__new__(Handler)
    h.server=SimpleNamespace(server_port=8765,token='expected',runs=SimpleNamespace(start=lambda _:pytest.fail('must not start')))
    replies=[];h.reply=lambda *args:replies.append(args)
    h.headers={'Host':'evil.example:8765','X-Demo-Token':'expected'}
    h.do_POST();assert replies[-1][0]==403
    h.headers={'Host':'127.0.0.1:8765','X-Demo-Token':'wrong'}
    h.do_POST();assert replies[-1][0]==403
    h.headers={'Host':'127.0.0.1:8765','X-Demo-Token':'expected','Origin':'https://evil.example'}
    h.do_POST();assert replies[-1][0]==403


def test_worker_streams_and_closes_without_api(monkeypatch,capsys):
    import gymnasium as gym
    import dotenv
    import browser_agent.model as models
    import browser_agent.workflow as workflows
    import app.demo_worker as worker
    flags=[]
    class Model:
        calls=2;input_tokens=100;output_tokens=20
        def __init__(self,*_,**__):pass
        def close(self):flags.append('model_closed')
    class Env:
        def reset(self,**_):return {'goal':'Type Ada and Submit','axtree_object':{}},{}
        def close(self):flags.append('env_closed')
    last=dict(step=2,action='click',bid='15',execution_ok=True,benchmark_success=True,error_kind=None)
    class Graph:
        def stream(self,*_,**__):
            yield {'observe':{'tree':'private'}}
            yield {'verify':{'success':True,'reason':'benchmark_success','reward':1.0,'steps':2,
                'progress':[last],'remaining_steps':0,'recoveries_used':0}}
    monkeypatch.setattr(worker.sys,'argv',['worker','--scenario','text','--seed','61'])
    monkeypatch.setattr(worker.signal,'signal',lambda *_:None)
    monkeypatch.setattr(worker.signal,'alarm',lambda *_:None)
    monkeypatch.setattr(worker.Path,'is_file',lambda _:True)
    monkeypatch.setattr(dotenv,'load_dotenv',lambda *a,**k:None)
    monkeypatch.setenv('OPENAI_API_KEY','fake-demo-key')
    monkeypatch.setattr(models,'ModelAdapter',Model)
    monkeypatch.setattr(gym,'make',lambda *a,**k:Env())
    monkeypatch.setattr(workflows,'build_workflow',lambda *a,**k:Graph())
    assert worker.main()==0
    output=capsys.readouterr().out
    assert 'fake-demo-key' not in output and 'private' not in output
    events=[json.loads(line) for line in output.splitlines()]
    assert events[-1]['type']=='result' and events[-1]['success']
    assert flags==['env_closed','model_closed']
