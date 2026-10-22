import json
import threading
import time
import urllib.request
import urllib.error
import pytest
from extension_service.server import Service,Session,clean_observation,make_server
from form_assistant.schema import Plan,Answer


def field(label='Name',value='',kind='text',options=None,required=True):
    return {'field_id':'q0','label':label,'kind':kind,'options':options or [],'value':value,'required':required,'errors':[]}

def observation(fields):return {'fields':fields,'signature':'browser-section','has_next':False,'at_end':True}

class Model:
    def __init__(self):self.calls=0;self.usage_incomplete=False
    def plan(self,obs,facts):
        self.calls+=1
        return Plan(answers=[Answer(field_id=f['field_id'],status='leave' if f['kind']=='unsupported' else 'fill',
            text=None if f['kind']=='unsupported' else 'Alex',choices=[],evidence=None if f['kind']=='unsupported' else 'Alex') for f in obs['fields']])
    def close(self):pass


def drive(session,current,overwrite='Replace'):
    seen=set();deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        state=session.snapshot()
        if state['question']:
            q=state['question'];session.answer(q['id'],overwrite)
        c=state['command']
        if c and c['id'] not in seen:
            seen.add(c['id'])
            if c['op']=='observe':session.respond(c['id'],observation([current.copy()]))
            elif c['op']=='apply':
                assert not current['value'] or c['allow_replace']
                current['value']=c['answer']['text'];session.respond(c['id'],{'ok':True})
            else:pytest.fail('unexpected command')
        if not state['running']:return state
        time.sleep(.005)
    pytest.fail('session did not finish')


def test_full_graph_observes_executes_and_checks_without_saving_facts():
    service=Service(Model);sid=service.start({'facts':'Name: Alex','origin':'https://example.com'})['id']
    session=service.get(sid);result=drive(session,field())
    assert result['ready'] and result['checked']==1 and result['calls']==1
    assert session.facts=='' and session.pending is None

@pytest.mark.parametrize('choice,ready,value',[('Replace',True,'Alex'),('Keep',False,'Original')])
def test_existing_answers_need_an_explicit_choice(choice,ready,value):
    session=Session('Name: Alex',Model,'https://example.com');thread=threading.Thread(target=session.run);thread.start()
    current=field(value='Original');result=drive(session,current,choice);thread.join(1)
    assert result['ready']==ready and current['value']==value
    if choice=='Keep':assert result['manual']==['Name']


def test_protected_values_are_removed_from_model_observations():
    obs,_=clean_observation(observation([field('Password',value='not-for-the-model')]))
    assert obs['fields'][0]['value'] is None and obs['fields'][0]['kind']=='unsupported'

@pytest.mark.parametrize('bad',[{'fields':[],'signature':'x','has_next':False,'at_end':True},observation([field(),field()]),observation([field(kind='click')])])
def test_malformed_observation_is_rejected(bad):
    with pytest.raises(ValueError):clean_observation(bad)


def test_stop_interrupts_a_pending_browser_command():
    session=Session('Name Alex',Model,'https://example.com');errors=[]
    def wait():
        try:session.command('observe')
        except InterruptedError:errors.append('stopped')
    t=threading.Thread(target=wait);t.start()
    time.sleep(.02);session.stop();t.join(1)
    assert errors==['stopped'] and session.snapshot()['command'] is None


def test_stale_answers_and_command_results_are_rejected():
    s=Session('Name Alex',Model,'https://example.com')
    with pytest.raises(ValueError):s.respond('old',{})
    with pytest.raises(ValueError):s.answer('old','Alex')

@pytest.mark.parametrize('origin',['file:///etc/passwd','chrome://settings','https://user:pass@example.com','https://example.com/private'])
def test_service_rejects_non_origin_or_insecure_targets(origin):
    with pytest.raises(ValueError):Service(Model).start({'facts':'Alex','origin':origin})


def test_loopback_service_requires_connection_code_and_extension_identity():
    server=make_server(0,Model);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        url=f'http://127.0.0.1:{server.server_port}/connect'
        def request(headers):
            req=urllib.request.Request(url,b'{}',headers={'Content-Type':'application/json',**headers})
            try:
                with urllib.request.urlopen(req) as r:return r.status,json.load(r)
            except urllib.error.HTTPError as e:return e.code,None
        headers={'X-Extension-ID':'a'*32,'Origin':'chrome-extension://'+'a'*32,'Authorization':'Bearer '+server.token}
        assert request(headers)[0]==200
        assert request({**headers,'Authorization':'Bearer wrong'})[0]==401
        assert request({**headers,'Origin':'https://malicious.example'})[0]==403
        assert request({'Authorization':'Bearer '+server.token})[0]==403
        assert request({k:v for k,v in headers.items() if k!='Origin'})[0]==200
    finally:server.shutdown();server.server_close();thread.join(1)


@pytest.mark.parametrize('origin',['http://example.com','https://example.com'])
def test_ordinary_browser_origins_are_accepted(origin):
    service=Service(Model);sid=service.start({'facts':'Name: Alex','origin':origin})['id']
    assert service.get(sid).origin==origin
    service.get(sid).stop()
