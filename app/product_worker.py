"""Visible-browser worker for the simple product. No final benchmark runs."""
import json
import os
from pathlib import Path
import signal
import sys
import time
from urllib.parse import urlsplit
from .web_agent import Adapter,workflow,START_URL,allowed_url
ROOT=Path(__file__).resolve().parents[1]


def emit(kind,**data):print(json.dumps({'type':kind,**data}),flush=True)


def stop(*_):raise InterruptedError('Stopped')


def route_request(route):
    r=route.request;p=urlsplit(r.url)
    ok=r.method in ('GET','HEAD') and p.scheme=='https' and p.hostname in ('en.wikipedia.org','upload.wikimedia.org')
    if r.is_navigation_request():ok=ok and allowed_url(r.url)
    if p.path=='/w/api.php':
        from urllib.parse import parse_qs
        ok=ok and parse_qs(p.query).get('action',['query'])[0] in ('query','opensearch','parse')
    route.continue_() if ok else route.abort()


def main():
    data=json.loads(sys.stdin.readline(4096))
    instruction=data.get('instruction')
    if not isinstance(instruction,str) or not 3<=len(instruction.strip())<=800:
        emit('error',message='Enter a short Wikipedia task.');return 1
    from dotenv import load_dotenv
    from playwright.sync_api import sync_playwright
    from openai import APIStatusError,APIConnectionError
    load_dotenv(ROOT/'.env.local',override=False)
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key:emit('error',message='Set up your local API key before running a task.');return 1
    model=browser=context=None
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGALRM,stop)
    signal.alarm(200)
    try:
        model=Adapter(key)
        emit('status',message='Understanding your instruction')
        task=model.task(instruction)
        if not task.supported:
            emit('error',message='I can type in Wikipedia’s search box, search a topic, or search and open an article. Try one of those tasks.')
            return 1
        with sync_playwright() as pw:
            try:
                emit('status',message='Opening Wikipedia in a browser')
                browser=pw.chromium.launch(headless=False)
                context=browser.new_context(accept_downloads=False,service_workers='block',viewport={'width':1280,'height':900})
                context.route('**/*',route_request)
                page=context.new_page();page.on('popup',lambda p:p.close())
                page.goto(START_URL,wait_until='domcontentloaded',timeout=20000)
                state=workflow(page,model,emit).invoke({'task':task,'steps':0,'history':[],'submitted':False,'recoveries':0},
                                                     {'recursion_limit':35})
                obs=state['obs'];done=state.get('done',False)
                if done:
                    message=(f'Typed “{task.query}” in the search field.' if task.goal=='type' else
                             f'Opened “{obs["heading"]}” from your search for “{task.query}”.' if obs['article'] else
                             f'Searched Wikipedia for “{task.query}”.')
                else:message='I could not finish within the action limit. You can inspect the browser and try a different instruction.'
                signal.alarm(0)
                emit('result',success=done,message=message,url=obs['url'],steps=state['steps'],calls=model.calls,
                     usage_incomplete=model.uncertain)
                # No more model calls after the result; keep the actual website visible.
                until=time.monotonic()+300
                while browser.is_connected() and not page.is_closed() and time.monotonic()<until:
                    try:page.wait_for_timeout(500)
                    except Exception:
                        if page.is_closed() or not browser.is_connected():break
                        raise
            finally:
                for resource in (context,browser):
                    if resource:
                        try:resource.close()
                        except Exception:pass
    except InterruptedError:
        emit('stopped',message='Stopped. Any request already sent may still incur usage.')
        return 1
    except APIStatusError as e:
        emit('error',message=f'The model service returned HTTP {e.status_code}. Check your API access or billing.')
        return 1
    except APIConnectionError:
        emit('error',message='Could not reach the model service. Check your connection.')
        return 1
    except Exception:
        emit('error',message='The task stopped because the page or action could not be verified. The site may have changed or blocked the browser.')
        return 1
    finally:
        signal.alarm(0)
        if model:
            try:model.client.close()
            except Exception:pass
    return 0


if __name__=='__main__':raise SystemExit(main())
