"""Instruction-driven product boundaries and LangGraph behavior. No live model/browser."""
from types import SimpleNamespace
import pytest
from app.product import validate_instruction,Runs
from app.web_agent import Task,Action,validate,completed,workflow,allowed_url


@pytest.mark.parametrize('body',[None,{}, {'instruction':''},{'instruction':True},{'instruction':'x'*801},{'instruction':'Search cats','url':'https://example.com'}])
def test_input_bounds(body):
    with pytest.raises(ValueError):validate_instruction(body)


def test_input_is_not_a_preset_sentence_catalogue():
    assert validate_instruction({'instruction':'Type my unusual phrase 9472 in the search box'})=='Type my unusual phrase 9472 in the search box'


@pytest.mark.parametrize('url',['https://evil.example/wiki/Cat','http://en.wikipedia.org/wiki/Cat',
    'https://en.wikipedia.org/wiki/Special:UserLogin','https://en.wikipedia.org/wiki/Special%3AUserLogin',
    'https://en.wikipedia.org/w/index.php?title=Cat&action=edit','https://en.wikipedia.org/wiki/Cat?veaction=edit'])
def test_navigation_boundary(url):assert not allowed_url(url)


def test_schema_validation_and_objective_checks():
    task=Task(supported=True,goal='type',query='a new query')
    obs={'search_visible':True,'search_value':'a new query','results':[],'article':False,'url':'https://en.wikipedia.org/wiki/Main_Page'}
    assert completed(task,obs,False)
    with pytest.raises(ValueError):validate({'action':'fill','target':'search','text':'changed query'},obs,task)
    with pytest.raises(ValueError):validate({'action':'open','target':'r9','text':None},obs,task)
    assert not completed(Task(supported=True,goal='open',query='cats'),{**obs,'article':True},False)


@pytest.mark.parametrize('goal,expected_steps',[('type',1),('search',2),('open',2)])
def test_same_graph_handles_variable_tasks(monkeypatch,goal,expected_steps):
    import app.web_agent as module
    task=Task(supported=True,goal=goal,query='Industrial engineering')
    page=SimpleNamespace(value='',article=False,url='https://en.wikipedia.org/wiki/Main_Page')
    def observation(p):return {'url':p.url,'heading':'Industrial engineering' if p.article else 'Main Page',
        'search_visible':True,'search_value':p.value,'results':[],'article':p.article}
    def execute(p,a,obs):
        if a.action=='fill':p.value=a.text
        else:p.article=True;p.url='https://en.wikipedia.org/wiki/Industrial_engineering'
    class Model:
        def decide(self,t,obs,history):
            return Action(action='submit' if obs['search_value']==t.query else 'fill',target='search',
                          text=None if obs['search_value']==t.query else t.query)
    monkeypatch.setattr(module,'observe',observation);monkeypatch.setattr(module,'execute',execute)
    result=workflow(page,Model(),lambda *a,**k:None).invoke({'task':task,'steps':0,'history':[],'submitted':False}, {'recursion_limit':35})
    assert result['done'] and result['steps']==expected_steps


def test_stop_interrupt_is_not_swallowed_as_recoverable_error(monkeypatch):
    import app.web_agent as module
    task=Task(supported=True,goal='type',query='test')
    obs={'url':'https://en.wikipedia.org/wiki/Main_Page','heading':'Main Page','search_visible':True,'search_value':'','results':[],'article':False}
    monkeypatch.setattr(module,'observe',lambda _:obs)
    def interrupted(*_):raise InterruptedError()
    monkeypatch.setattr(module,'execute',interrupted)
    model=SimpleNamespace(decide=lambda *args:Action(action='fill',target='search',text='test'))
    with pytest.raises(InterruptedError):
        workflow(None,model,lambda *a,**k:None).invoke({'task':task,'steps':0,'history':[]}, {'recursion_limit':35})


def test_old_worker_cannot_overwrite_new_run_state():
    manager=Runs();old=object();current=object();manager.process=current;manager.running=True
    manager.append(old,{'type':'error','message':'old error'})
    assert manager.running and manager.events==[]
    manager.append(current,{'type':'result','success':True,'message':'Done'})
    assert not manager.running and len(manager.events)==1
