"""Visible browser worker. Events omit filled values; inputs stay in session memory."""
import json
import os
from pathlib import Path
import select
import signal
import sys
import time
from uuid import uuid4
from .policy import request_body,request_allowed,validate_url,MAX_CALLS
from .engine import Adapter,workflow
ROOT=Path(__file__).resolve().parents[1]


def emit(kind,**data):print(json.dumps({'type':kind,**data}),flush=True)


def stop(*_):raise InterruptedError('Stopped')


def ask(label,options):
    qid=uuid4().hex
    emit('question',id=qid,label=label,options=options)
    ready,_,_=select.select([sys.stdin],[],[],180)
    if not ready:raise TimeoutError('Answer timeout')
    line=sys.stdin.readline(10000)
    data=json.loads(line)
    if data.get('id')!=qid or not isinstance(data.get('answer'),str) or not 1<=len(data['answer'].strip())<=2000:
        raise ValueError('Invalid answer')
    emit('answered',id=qid)
    return data['answer'].strip()


def main():
    body=json.loads(sys.stdin.readline(16000));origin=body.pop('practice_origin')
    body=request_body(body,origin)
    from dotenv import load_dotenv
    from playwright.sync_api import sync_playwright
    from openai import APIStatusError,APIConnectionError
    load_dotenv(ROOT/'.env.local',override=False)
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key:emit('error',message='Your local API key is missing.');return 1
    model=None;result_sent=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGALRM,stop)
    signal.alarm(600)
    try:
        model=Adapter(key)
        with sync_playwright() as pw:
            browser=context=None
            try:
                emit('status',message='Opening the form')
                browser=pw.chromium.launch(headless=False)
                context=browser.new_context(accept_downloads=False,service_workers='block',viewport={'width':1280,'height':900})
                def route(r):
                    req=r.request
                    r.continue_() if request_allowed(req.url,req.method,req.is_navigation_request(),origin) else r.abort()
                context.route('**/*',route)
                page=context.new_page();page.on('popup',lambda p:p.close())
                page.goto(body['url'],wait_until='domcontentloaded',timeout=25000)
                validate_url(page.url,origin)
                # Google Forms initially renders disabled placeholders while scripts load.
                page.locator('input:not([type=hidden]):visible:not([disabled]),textarea:visible:not([disabled]),[role=radio]:visible:not([aria-disabled=true]),[role=checkbox]:visible:not([aria-disabled=true]),[role=listbox]:visible:not([aria-disabled=true])').first.wait_for(state='visible',timeout=20000)
                state=workflow(page,model,emit,ask).invoke({'facts':body['instruction'],'pages':1,'actions':0,'ledger':{},'checked':0,'retries':0},
                                                         {'recursion_limit':5*MAX_CALLS+5})
                reason=state['reason'];ready=reason=='ready_for_review';manual=state.get('manual',[])
                if ready:message=f'Ready for review. {state.get("checked",0)} answers checked. Nothing was submitted.'
                elif reason=='manual_review':message=f'Your supplied answers are filled. {len(manual)} question(s) need your manual review. Nothing was submitted.'
                else:message='The form is partly completed. I could not verify every required answer. Please review it in the browser.'
                signal.alarm(0)
                emit('result',ready=ready,message=message,manual=manual,checked=state.get('checked',0),calls=model.calls,
                     usage_incomplete=model.usage_incomplete)
                result_sent=True
                until=time.monotonic()+600
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
        emit('stopped',message='Stopped. Any entered answers remain with the site; an in-flight API request may still incur usage.')
        return 1
    except APIStatusError as exc:
        emit('error',message=f'The model service returned HTTP {exc.status_code}. Check your API access or billing.')
        return 1
    except APIConnectionError:
        emit('error',message='Could not reach the model service. Your form may be partly filled.')
        return 1
    except Exception:
        if not result_sent:emit('error',message='I could not complete this form safely. It may require sign-in, have unsupported questions, or have changed. Any completed answers need review.')
        return 1
    finally:
        signal.alarm(0)
        if model:
            try:model.close()
            except Exception:pass
    return 0


if __name__=='__main__':raise SystemExit(main())
