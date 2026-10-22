import io
from types import SimpleNamespace
import pytest
from form_assistant.policy import validate_url,request_body,request_allowed
from form_assistant.schema import Plan,Answer
from form_assistant.engine import validate_plan,needs_manual,workflow
from form_assistant import dom

ORIGIN='http://127.0.0.1:8765'


@pytest.mark.parametrize('url',['http://docs.google.com/forms/d/e/id/viewform','https://evil.example/form',
 'https://docs.google.com.evil.example/forms/d/e/id/viewform','https://u:p@docs.google.com/forms/d/e/id/viewform',
 'https://docs.google.com/forms/d/e/id/edit','file:///etc/passwd','http://127.0.0.1:9999/private',
 'https://docs.google.com/forms/d/e/id/formResponse'])
def test_url_boundaries(url):
    with pytest.raises(ValueError):validate_url(url,ORIGIN)


def test_real_short_link_and_review_first_network_rules():
    assert validate_url('https://forms.gle/6qsMM6JhkyeGjmbS9',ORIGIN)
    assert request_body({'url':'practice','instruction':'Name Alex'},ORIGIN)['url']==ORIGIN+'/practice'
    assert not request_allowed('https://docs.google.com/forms/d/e/id/formResponse','POST',True,ORIGIN)
    assert request_allowed('https://docs.google.com/forms/d/e/id/viewform','GET',True,ORIGIN)
    assert not request_allowed('https://accounts.google.com/login','GET',True,ORIGIN)


def field(kind='text',label='Name',value='',required=True):
    return dict(field_id='q0',label=label,kind=kind,value=value,required=required,options=['Day 1','Day 2'],errors=[])


def answer(**kw):return Answer(field_id='q0',status='fill',text='Alex',choices=[],evidence='Alex',**kw)


def test_no_invented_values_or_unobserved_choices():
    obs={'fields':[field()]}
    a=answer()
    assert validate_plan(Plan(answers=[a]),obs,'Name: Alex')
    with pytest.raises(ValueError):validate_plan(Plan(answers=[a]),obs,'Name: Someone Else')
    a=Answer(field_id='q0',status='fill',text=None,choices=['Day 3'],evidence='Day 3')
    with pytest.raises(ValueError):validate_plan(Plan(answers=[a]),{'fields':[field('checkbox')]},'Day 3')


def test_payment_acknowledgement_cannot_be_checked_even_with_matching_text():
    f=field('checkbox','I understand that I will have to pay $$ upon arrival',[])
    assert needs_manual(f)
    a=Answer(field_id='q0',status='fill',text=None,choices=['Day 1'],evidence='Day 1')
    with pytest.raises(ValueError):validate_plan(Plan(answers=[a]),{'fields':[f]},'Day 1')


def test_checkbox_set_and_action_cost():
    f=field('checkbox',value=['Day 1'])
    a=Answer(field_id='q0',status='fill',text=None,choices=['Day 2'],evidence='Day 2')
    assert dom.operation_cost(f,a)==2
    assert not dom.matches(f,a)


def test_graph_asks_for_missing_answer_then_fills_and_verifies(monkeypatch):
    page=SimpleNamespace(value='');calls=[];questions=[]
    def obs(_):return {'fields':[field(value=page.value)],'signature':'page1','has_next':False,'at_end':True}
    monkeypatch.setattr(dom,'observe',obs)
    monkeypatch.setattr(dom,'apply',lambda p,f,a:setattr(page,'value',a.text))
    class Model:
        def plan(self,observation,facts):
            calls.append(facts)
            if 'Alex' not in facts:return Plan(answers=[Answer(field_id='q0',status='ask',text=None,choices=[],evidence=None)])
            return Plan(answers=[answer()])
    def ask(label,options):questions.append(label);return 'Alex'
    state=workflow(page,Model(),lambda *a,**k:None,ask).invoke({'facts':'Fill my form','pages':1}, {'recursion_limit':30})
    assert state['reason']=='ready_for_review' and state['checked']==1
    assert questions==['Name'] and len(calls)==2 and page.value=='Alex'


def test_manual_question_returns_partial_review_not_ready(monkeypatch):
    f=field('checkbox','I agree to pay',[])
    monkeypatch.setattr(dom,'observe',lambda _:dict(fields=[f],signature='p',has_next=False,at_end=True))
    model=SimpleNamespace(plan=lambda *args:Plan(answers=[Answer(field_id='q0',status='leave',text=None,choices=[],evidence=None)]))
    s=workflow(None,model,lambda *a,**k:None,lambda *a:pytest.fail('must not infer consent')).invoke({'facts':'Fill this','pages':1}, {'recursion_limit':10})
    assert s['reason']=='manual_review' and s['checked']==0


def test_answer_continuation_rejects_wrong_question_id():
    from form_assistant.server import Runs
    r=Runs(ORIGIN);r.running=True;r.waiting={'id':'new'}
    r.process=SimpleNamespace(stdin=io.StringIO())
    with pytest.raises(ValueError):r.answer({'id':'old','answer':'private'})
    assert r.process.stdin.getvalue()==''
    r.answer({'id':'new','answer':'Alex'})
    assert r.waiting is None and not any('Alex' in str(e) for e in r.events)
