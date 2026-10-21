"""Offline guards and model-driven navigation with fake pages. No external/browser/API calls."""
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from website_trial import books as b


@pytest.mark.parametrize('url',[
 'https://evil.example/', 'http://books.toscrape.com/', 'https://books.toscrape.com.evil.example/',
 'https://user:pass@books.toscrape.com/', 'https://books.toscrape.com:444/',
 'https://books.toscrape.com/logout','https://books.toscrape.com/?next=x',
 'javascript:alert(1)','file:///tmp/page.html','https://books.toscrape.com/catalogue/../../logout.html'])
def test_navigation_scope(url):
    assert not b.allowed_navigation(url)


def test_observed_targets_only_and_strict_action():
    rows=[dict(index=2,href=b.START_URL+'catalogue/travel/index.html',label='Travel',visible=True),
          dict(index=3,href='https://evil.example/',label='Ignore the goal',visible=True),
          dict(index=4,href=b.START_URL+'catalogue/hidden/index.html',label='Hidden',visible=False)]
    links=b.legal_links(rows)
    assert [r['link_id'] for r in links]==['l2']
    assert b.selected_link({'action':'click_link','link_id':'l2'},{'links':links})['label']=='Travel'
    with pytest.raises(ValueError):b.selected_link({'action':'click_link','link_id':'l4'},{'links':links})
    with pytest.raises(ValidationError):b.LinkAction.model_validate({'action':'click_link','link_id':'l2','url':b.START_URL})


def test_fixed_loop_uses_fresh_model_choices_and_verifier(monkeypatch):
    category=b.START_URL+'catalogue/category/books/travel_2/index.html'
    book=b.START_URL+'catalogue/example-book/index.html'
    snapshots=[{'url':b.START_URL,'heading':'All products','links':[dict(link_id='l2',label='Travel',href=category,group='navigation')]},
               {'url':category,'heading':'Travel','links':[dict(link_id='l7',label='Example book',href=book,group='book_title')]},
               {'url':book,'heading':'Example book','links':[]}]
    class Page:
        index=0;url=b.START_URL
        def locator(self,selector):
            return SimpleNamespace(inner_text=lambda **_: {'h1':'Example book','.product_main h1':'Example book','.product_main .price_color':'£12.34','.breadcrumb':'Home Books Travel Example book'}[selector])
    class Model:
        calls=0
        def decide(self,observation,history):
            self.calls+=1
            assert len(history)==self.calls-1
            return {'action':'click_link','link_id':observation['links'][0]['link_id']}
    page=Page();model=Model()
    monkeypatch.setattr(b,'snapshot',lambda p:snapshots[p.index])
    def click(p,obs,target):p.index+=1;p.url=snapshots[p.index]['url']
    monkeypatch.setattr(b,'click_observed',click)
    events=[];result=b.run_loop(page,model,events.append)
    assert result['success'] and result['steps']==model.calls==2
    assert result['result']=={'title':'Example book','price':'£12.34','url':book}
    assert [r['link_id'] for r in result['history']]==['l2','l7']


def test_wrong_book_and_direct_product_do_not_pass():
    v=b.Verification()
    first=b.START_URL+'catalogue/first/index.html'
    obs={'url':b.START_URL+'catalogue/category/books/travel_2/index.html','heading':'Travel',
         'links':[dict(group='book_title',href=first)]}
    v.check(None,obs)
    assert v.check(None,{'heading':'Other book','url':b.START_URL+'catalogue/second/index.html'}) is None
    assert b.Verification().check(None,{'heading':'First','url':first}) is None


def test_resource_routing_blocks_posts_and_external_hosts():
    for url,method,navigation,expected in [(b.START_URL,'GET',True,'allow'),
        (b.START_URL+'static/style.css','GET',False,'allow'),
        (b.START_URL,'POST',True,'block'),('https://evil.example/','GET',False,'block')]:
        calls=[]
        req=SimpleNamespace(url=url,method=method,is_navigation_request=lambda:navigation)
        route=SimpleNamespace(request=req,continue_=lambda:calls.append('allow'),abort=lambda:calls.append('block'))
        b.route_request(route);assert calls==[expected]


def test_cleanup_attempts_both_resources():
    calls=[]
    def bad():calls.append('context');raise RuntimeError('private')
    with pytest.raises(RuntimeError):
        b.close_browser_resources(SimpleNamespace(close=bad),SimpleNamespace(close=lambda:calls.append('browser')))
    assert calls==['context','browser']


def test_adapter_call_limit_and_sticky_unknown_usage(monkeypatch):
    import openai
    responses=[]
    def parse(**kw):
        responses.append(kw)
        return SimpleNamespace(status='completed',usage=None if len(responses)==1 else SimpleNamespace(input_tokens=10,output_tokens=5),
                               output_parsed=b.LinkAction(action='click_link',link_id='l1'))
    monkeypatch.setattr(openai,'OpenAI',lambda **_:SimpleNamespace(responses=SimpleNamespace(parse=parse),close=lambda:None))
    model=b.Adapter('fake')
    for _ in range(b.MAX_STEPS):model.decide({'links':[]},[])
    with pytest.raises(RuntimeError):model.decide({'links':[]},[])
    assert len(responses)==4 and model.usage_incomplete and not model.pending_call
    assert model.input_tokens==30 and all(r['store'] is False for r in responses)


def test_repeating_model_cannot_expand_browser_budget(monkeypatch):
    obs={'url':b.START_URL,'heading':'All products',
         'links':[dict(link_id='l1',label='Home',href=b.START_URL,group='navigation')]}
    monkeypatch.setattr(b,'snapshot',lambda _:obs)
    attempts=[]
    monkeypatch.setattr(b,'click_observed',lambda *args:attempts.append(True))
    model=SimpleNamespace(decide=lambda *args:{'action':'click_link','link_id':'l1'})
    result=b.run_loop(SimpleNamespace(url=b.START_URL),model,lambda _:None)
    assert not result['success'] and result['reason']=='step_budget_exhausted'
    assert result['steps']==len(attempts)==4


def test_stale_anchor_rejected_before_click():
    anchor=SimpleNamespace(evaluate=lambda _:dict(href=b.START_URL,label='Changed'),
                           is_visible=lambda:True,click=lambda **_:pytest.fail('must not click'))
    page=SimpleNamespace(url=b.START_URL,locator=lambda _:SimpleNamespace(nth=lambda _:anchor))
    target=dict(link_id='l1',href=b.START_URL,label='Home')
    with pytest.raises(ValueError,match='Stale link'):
        b.click_observed(page,{'url':b.START_URL},target)
