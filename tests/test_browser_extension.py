"""Opt-in local Chromium tests. Fake model; never call OpenAI or submit a real form."""
import json
import os
from pathlib import Path
import shutil
import threading
import pytest
from form_assistant.schema import Plan,Answer
from extension_service.server import make_server

pytestmark=pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS')!='1',reason='Opt-in local Chromium')
ROOT=Path(__file__).parents[1]

class PracticeModel:
    def __init__(self):self.calls=0;self.usage_incomplete=False
    def plan(self,obs,facts):
        self.calls+=1
        values={'Name':'Alex','Email':'alex@example.com','Organization':'Example University','Session':['Afternoon'],
            'What days will you attend?':['Day 1','Day 2'],'Dietary restrictions':['Vegetarian']}
        answers=[]
        for f in obs['fields']:
            v=values.get(f['label'])
            if f['label']=='Email' and 'alex@example.com' not in facts:
                answers.append(Answer(field_id=f['field_id'],status='ask',text=None,choices=[],evidence=None));continue
            answers.append(Answer(field_id=f['field_id'],status='fill' if v else 'leave',text=v if isinstance(v,str) else None,
                choices=v if isinstance(v,list) else [],evidence=v if isinstance(v,str) else (' '.join(v) if v else None)))
        return Plan(answers=answers)
    def close(self):pass


@pytest.mark.parametrize('missing_email',[False,True])
def test_packaged_extension_and_local_service_fill_two_sections(tmp_path,missing_email):
    from playwright.sync_api import sync_playwright,expect
    server=make_server(0,PracticeModel);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    origin=f'http://127.0.0.1:{server.server_port}'
    ext=tmp_path/'extension';shutil.copytree(ROOT/'extension',ext)
    # Automated test grants only this temporary local origin, replacing the user's
    # toolbar activeTab gesture. Production manifest has no website host permission.
    manifest=json.loads((ext/'manifest.json').read_text());manifest['host_permissions']=[origin+'/*']
    manifest['content_security_policy']['extension_pages']=f"script-src 'self'; object-src 'none'; connect-src {origin}"
    (ext/'manifest.json').write_text(json.dumps(manifest))
    p=ext/'panel.js';p.write_text(p.read_text().replace('http://127.0.0.1:8766',origin))
    try:
        with sync_playwright() as pw:
            context=pw.chromium.launch_persistent_context(str(tmp_path/'profile'),channel='chromium',headless=False,
                args=['--headless=new',f'--disable-extensions-except={ext}',f'--load-extension={ext}'])
            try:
                worker=context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
                eid=worker.url.split('/')[2]
                for _ in range(50):
                    if worker.evaluate('Boolean(globalThis.__formAssistantBackgroundReady)'):break
                    context.pages[0].wait_for_timeout(100)
                assert worker.evaluate('Boolean(globalThis.__formAssistantBackgroundReady)')
                form=context.pages[0];form.goto(origin+'/practice')
                # Keep the target active in its own window while exercising panel DOM.
                tab=worker.evaluate("async()=>{const tabs=await chrome.tabs.query({});return tabs.find(t=>t.url.includes('/practice'));}")
                worker.evaluate("async t=>{await chrome.storage.session.set({target:{id:t.id,origin:new URL(t.url).origin,title:t.title}});await chrome.windows.create({url:chrome.runtime.getURL('panel.html'),type:'popup',width:410,height:760});}",tab)
                panel=context.wait_for_event('page') if len(context.pages)<2 else context.pages[-1]
                panel.wait_for_url(f'chrome-extension://{eid}/panel.html')
                panel.locator('#code').fill(server.token);panel.get_by_role('button',name='Connect',exact=True).click()
                expect(panel.locator('#connection')).to_be_hidden()
                panel.locator('#details').fill('Name: Alex\n'+('' if missing_email else 'Email: alex@example.com\n')+'Organization: Example University\nSession: Afternoon\nDay 1 Day 2\nVegetarian')
                panel.get_by_role('button',name='Fill form',exact=False).click()
                if missing_email:
                    expect(panel.locator('#question')).to_be_visible(timeout=8000)
                    assert form.get_by_role('textbox',name='Name',exact=True).input_value()==''
                    panel.locator('#answer').fill('alex@example.com')
                    panel.get_by_role('button',name='Continue',exact=True).click()
                expect(panel.locator('#status')).to_have_text('Ready for review',timeout=20000)
                assert server.service.session.checked==6 and server.service.session.calls==(3 if missing_email else 2)
                expect(form.get_by_role('radio',name='Vegetarian',exact=True)).to_be_checked()
                expect(form.get_by_role('checkbox',name='Day 1',exact=True)).to_be_checked()
                expect(form.get_by_role('button',name='Submit',exact=True)).to_be_disabled()
                assert server.service.session.facts==''
                panel.locator('#details').fill('')
                panel.set_viewport_size({'width':390,'height':730})
                panel.screenshot(path=str(ROOT.parents[1]/'outputs/form-extension-simple-preview.png'))
            finally:context.close()
    finally:server.shutdown();server.server_close();thread.join(2)


def test_content_adapter_stops_and_refuses_unapproved_overwrite(tmp_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('<form><label>Name<input value="Original"></label><button>Submit</button></form>')
            page.evaluate("window.chrome={runtime:{id:'test',onMessage:{addListener(fn){window.handler=fn;}}}}")
            page.add_script_tag(path=str(ROOT/'extension/content.js'))
            def command(c):return page.evaluate("c=>new Promise(resolve=>window.handler({type:'form-assistant',command:c},{id:'test'},resolve))",c)
            command({'op':'begin','run_id':'run'})
            obs=command({'op':'observe','run_id':'run'});f=obs['fields'][0]
            a={'field_id':'q0','status':'fill','text':'Alex','choices':[],'evidence':'Alex'}
            assert 'error' in command({'op':'apply','run_id':'run','field':f,'answer':a,'allow_replace':False})
            assert page.locator('input').input_value()=='Original'
            assert command({'op':'apply','run_id':'run','field':f,'answer':a,'allow_replace':True})=={'ok':True}
            command({'op':'stop','run_id':'run'})
            assert 'error' in command({'op':'observe','run_id':'run'})
        finally:browser.close()


def test_content_adapter_handles_google_choices_and_leaves_payment_manual():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('''<div role="listitem"><div class="M7eMe">Dietary restrictions</div>
            <div role="radiogroup"><div role="radio" tabindex="0" data-value="Vegetarian" aria-checked="false" onclick="this.setAttribute('aria-checked','true')">Vegetarian</div>
            <div role="radio" data-value="__other_option__" aria-checked="false">Other <input></div></div></div>
            <div role="listitem"><div class="M7eMe">Session</div><div role="listbox" tabindex="0" onclick="this.querySelector('.menu').hidden=false">
            <span class="current">Choose</span><div class="menu" hidden><div role="option" data-value="Choose" aria-selected="true">Choose</div>
            <div role="option" data-value="Afternoon" aria-selected="false" onclick="event.stopPropagation();this.parentElement.querySelectorAll('[role=option]').forEach(x=>x.setAttribute('aria-selected','false'));this.setAttribute('aria-selected','true');this.closest('[role=listbox]').querySelector('.current').textContent='Afternoon';this.parentElement.hidden=true">Afternoon</div></div></div></div>
            <div role="listitem"><div class="M7eMe">I will pay upon arrival</div><div role="checkbox" data-value="Yes" aria-checked="false">Yes</div></div>''')
            page.evaluate("window.chrome={runtime:{id:'test',onMessage:{addListener(fn){window.handler=fn;}}}}")
            page.add_script_tag(path=str(ROOT/'extension/content.js'))
            def command(c):return page.evaluate("c=>new Promise(resolve=>window.handler({type:'form-assistant',command:c},{id:'test'},resolve))",c)
            command({'op':'begin','run_id':'run'})
            obs=command({'op':'observe','run_id':'run'})
            assert [f['kind'] for f in obs['fields']]==['radio','select','unsupported']
            assert obs['fields'][2]['value'] is None
            for f,choice in zip(obs['fields'],['Vegetarian','Afternoon']):
                a={'field_id':f['field_id'],'status':'fill','text':None,'choices':[choice],'evidence':choice}
                assert command({'op':'apply','run_id':'run','field':f,'answer':a,'allow_replace':False})=={'ok':True}
            f=obs['fields'][2];a={'field_id':f['field_id'],'status':'fill','text':None,'choices':['Yes'],'evidence':'Yes'}
            assert 'error' in command({'op':'apply','run_id':'run','field':f,'answer':a,'allow_replace':True})
            assert page.get_by_role('checkbox').get_attribute('aria-checked')=='false'
        finally:browser.close()


def adapter(page):
    page.evaluate("window.chrome={runtime:{id:'test',onMessage:{addListener(fn){window.handler=fn;}}}}")
    page.add_script_tag(path=str(ROOT/'extension/content.js'))
    def command(c):return page.evaluate("c=>new Promise(resolve=>window.handler({type:'form-assistant',command:c},{id:'test'},resolve))",c)
    assert command({'op':'begin','run_id':'run'})=={'ok':True}
    return command


def test_all_page_textboxes_are_candidates_across_forms_and_editable_regions():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('''
            <form><label>Name<input></label></form>
            <form><label>Email<input type="email"></label></form>
            <input type="search" placeholder="Search">
            <input><textarea title="Notes"></textarea>
            <div role="textbox" aria-label="Message" contenteditable="true"></div>
            <label>Hidden<input style="display:none"></label>
            <label>Password<input type="password" value="never-send-this"></label>
            <label>Read only<input readonly value="fixed"></label>''')
            command=adapter(page);obs=command({'op':'observe','run_id':'run'})
            assert 'error' not in obs
            assert [f['label'] for f in obs['fields']]==['Name','Email','Search','Text box 4','Notes','Message','Password','Read only']
            assert obs['fields'][6]['kind']=='unsupported' and obs['fields'][6]['value'] is None
            assert obs['fields'][7]['kind']=='unsupported'
            for f in obs['fields'][:6]:
                text='Hello\nWorld' if f['label']=='Message' else ('alex@example.com' if f['label']=='Email' else 'Alex')
                a={'field_id':f['field_id'],'status':'fill','text':text,'choices':[],'evidence':text}
                assert command({'op':'apply','run_id':'run','field':f,'answer':a,'allow_replace':False})=={'ok':True}
            actual=command({'op':'observe','run_id':'run'})
            assert actual['fields'][2]['value']=='Alex' and actual['fields'][3]['value']=='Alex'
            assert actual['fields'][5]['value']=='Hello\nWorld'
            assert page.locator('input[type=password]').input_value()=='never-send-this'
        finally:browser.close()


def test_open_shadow_roots_and_same_origin_frames_are_read_and_filled():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('''<label>Main<input></label><div id="host"></div>
            <iframe srcdoc="<label>Frame<input></label>"></iframe>
            <iframe hidden srcdoc="<label>Invisible<input></label>"></iframe>''')
            page.evaluate("document.getElementById('host').attachShadow({mode:'open'}).innerHTML='<span id=title>Shadow</span><input aria-labelledby=title>'")
            page.wait_for_function("document.querySelector('iframe').contentDocument.querySelector('input')")
            command=adapter(page);obs=command({'op':'observe','run_id':'run'})
            assert [f['label'] for f in obs['fields']]==['Main','Shadow','Frame']
            for f in obs['fields']:
                a={'field_id':f['field_id'],'status':'fill','text':'Alex','choices':[],'evidence':'Alex'}
                assert command({'op':'apply','run_id':'run','field':f,'answer':a,'allow_replace':False})=={'ok':True}
            assert page.frame_locator('iframe').nth(0).locator('input').input_value()=='Alex'
            assert page.locator('#host input').input_value()=='Alex'
        finally:browser.close()


def test_same_named_choice_groups_on_different_forms_are_not_merged():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('''
            <form><fieldset><legend>First choice</legend><label><input type=radio name=choice>A</label><label><input type=radio name=choice>B</label></fieldset></form>
            <form><fieldset><legend>Second choice</legend><label><input type=radio name=choice>C</label><label><input type=radio name=choice>D</label></fieldset></form>''')
            command=adapter(page);obs=command({'op':'observe','run_id':'run'})
            assert [f['options'] for f in obs['fields']]==[['A','B'],['C','D']]
            assert obs['at_end'] and not obs['has_next']
        finally:browser.close()
