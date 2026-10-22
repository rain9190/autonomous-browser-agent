"""Opt-in local Chromium tests of real DOM actions; fake plans, zero API calls."""
import os
from pathlib import Path
import pytest
from form_assistant.schema import Plan,Answer
from form_assistant.engine import workflow
from form_assistant import dom

pytestmark=pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS')!='1',reason='Opt-in local Chromium')


def test_multi_page_practice_form_fills_and_stops_before_submit():
    from playwright.sync_api import sync_playwright
    values={'Name':'Alex','Email':'alex@example.com','Organization':'Example University','Session':['Afternoon'],
            'What days will you attend?':['Day 1','Day 2'],'Dietary restrictions':['Vegetarian']}
    facts='Alex alex@example.com Example University Afternoon Day 1 Day 2 Vegetarian'
    class Model:
        def plan(self,obs,facts):
            answers=[]
            for f in obs['fields']:
                value=values.get(f['label'])
                answers.append(Answer(field_id=f['field_id'],status='fill' if value else 'leave',
                    text=value if isinstance(value,str) else None,choices=value if isinstance(value,list) else [],
                    evidence=(value if isinstance(value,str) else ' '.join(value)) if value else None))
            return Plan(answers=answers)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.goto((Path(__file__).parents[1]/'form_assistant/practice.html').resolve().as_uri())
            s=workflow(page,Model(),lambda *a,**k:None,lambda *a:pytest.fail('no missing answers')).invoke(
                {'facts':facts,'pages':1,'checked':0}, {'recursion_limit':20})
            assert s['reason']=='ready_for_review' and s['checked']==6 and s['pages']==2
            assert page.get_by_role('button',name='Submit',exact=True).is_disabled()
            assert page.get_by_role('radio',name='Vegetarian',exact=True).is_checked()
            assert page.get_by_role('checkbox',name='Day 1',exact=True).is_checked()
            assert not page.get_by_role('checkbox',name='Day 3',exact=True).is_checked()
        finally:browser.close()


def test_google_style_radio_with_other_text_field_remains_supported():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('''<div role="listitem"><div class="M7eMe">Dietary restrictions <span class="vnumgf">*</span></div>
              <div role="radiogroup"><div role="radio" tabindex="0" aria-checked="false" data-value="None" onclick="this.setAttribute('aria-checked','true')">None</div>
              <div role="radio" tabindex="0" aria-checked="false" data-value="Vegetarian" onclick="this.setAttribute('aria-checked','true')">Vegetarian</div>
              <div role="radio" aria-checked="false" data-value="__other_option__">Other <input type="text"></div></div></div><button>Submit</button>''')
            f=dom.observe(page)['fields'][0]
            assert f['kind']=='radio' and f['required']
            a=Answer(field_id=f['field_id'],status='fill',text=None,choices=['Vegetarian'],evidence='Vegetarian')
            dom.apply(page,f,a)
            assert dom.matches(dom.observe(page)['fields'][0],a)
        finally:browser.close()


def test_simple_ui_can_pause_for_an_answer_and_continue(tmp_path):
    import io
    import json
    import threading
    import secrets
    from types import SimpleNamespace
    from http.server import ThreadingHTTPServer
    from playwright.sync_api import sync_playwright,expect
    from form_assistant.server import Handler,Runs
    from form_assistant.policy import request_body
    class FakeRuns(Runs):
        def start(self,body):
            request_body(body,self.origin)
            self.process=SimpleNamespace(poll=lambda:None,stdin=io.StringIO())
            self.running=True
            self.waiting={'type':'question','id':'q-test','label':'Email','options':[]}
            self.events=[self.waiting]
        def answer(self,body):
            super().answer(body)
            self.running=False
            self.events=[{'type':'result','ready':True,'message':'Ready for review. Nothing was submitted.','manual':[]}]
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    origin=f'http://127.0.0.1:{server.server_port}'
    server.token=secrets.token_urlsafe(20);server.runs=FakeRuns(origin)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            try:
                page=browser.new_page(viewport={'width':1200,'height':1000});page.goto(origin)
                expect(page.get_by_role('heading',name='Leave the form filling to us.')).to_be_visible()
                assert page.get_by_text('Frozen evaluation results',exact=False).count()==0
                page.screenshot(path=str(Path(__file__).parents[3]/'outputs/form-assistant-preview.png'),full_page=True)
                page.get_by_role('button',name='Try a practice form',exact=True).click()
                page.get_by_role('button',name='Fill form',exact=True).click()
                expect(page.locator('#question')).to_be_visible(timeout=5000)
                page.locator('#answer').fill('alex@example.com')
                page.get_by_role('button',name='Continue',exact=True).click()
                expect(page.locator('#message')).to_have_text('Ready for review. Nothing was submitted.',timeout=5000)
                assert 'alex@example.com' in server.runs.process.stdin.getvalue()
                assert 'alex@example.com' not in json.dumps(server.runs.events)
            finally:browser.close()
    finally:server.shutdown();server.server_close();thread.join(timeout=2)


def test_google_style_dropdown_opens_selects_and_reads_back():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('''<div role="listitem"><div class="M7eMe">Session <span class="vnumgf">*</span></div>
              <div role="listbox" tabindex="0" onclick="this.querySelector('.menu').hidden=false"><span class="current">Choose</span><div class="menu" hidden>
              <div role="option" aria-selected="true" data-value="Choose">Choose</div>
              <div role="option" aria-selected="false" data-value="Morning" onclick="choose(this,event)">Morning</div>
              <div role="option" aria-selected="false" data-value="Afternoon" onclick="choose(this,event)">Afternoon</div>
              </div></div></div><button>Submit</button><script>function choose(el,e){e.stopPropagation();let box=el.closest('[role=listbox]');box.querySelectorAll('[role=option]').forEach(x=>x.setAttribute('aria-selected','false'));el.setAttribute('aria-selected','true');box.querySelector('.current').textContent=el.textContent;box.querySelector('.menu').hidden=true;}</script>''')
            f=dom.observe(page)['fields'][0]
            assert f['kind']=='select' and f['options']==['Morning','Afternoon']
            a=Answer(field_id=f['field_id'],status='fill',text=None,choices=['Afternoon'],evidence='Afternoon')
            dom.apply(page,f,a)
            assert dom.matches(dom.observe(page)['fields'][0],a)
        finally:browser.close()
