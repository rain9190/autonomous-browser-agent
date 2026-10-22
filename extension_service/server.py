"""Authenticated loopback bridge. No browser profile, remote code or saved answer logs."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field
from form_assistant.engine import Adapter,workflow,needs_manual
from form_assistant import dom

ROOT=Path(__file__).resolve().parents[1]
EXTENSION_ORIGIN=re.compile(r'^chrome-extension://[a-p]{32}$')

class Question(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    field_id:str=Field(pattern=r'^q\d{1,2}$')
    label:str=Field(min_length=1,max_length=600)
    kind:str=Field(pattern=r'^(text|radio|checkbox|select|unsupported)$')
    options:list[str]=Field(max_length=30)
    value:str|list[str]|None
    required:bool
    errors:list[str]=Field(max_length=30)


def clean_observation(raw):
    if not isinstance(raw,dict) or set(raw)!={'fields','signature','has_next','at_end'}:raise ValueError('Invalid form observation')
    if not isinstance(raw['fields'],list) or not 1<=len(raw['fields'])<=40:raise ValueError('Unsupported question count')
    if type(raw['has_next']) is not bool or type(raw['at_end']) is not bool:raise ValueError('Invalid form navigation')
    fields=[Question.model_validate(f).model_dump() for f in raw['fields']]
    if len({f['field_id'] for f in fields})!=len(fields):raise ValueError('Duplicate field IDs')
    for f in fields:
        if any(len(x)>500 for x in f['options']) or len(set(f['options']))!=len(f['options']):raise ValueError('Unsupported options')
        if len(json.dumps(f['value']))>12000:raise ValueError('Existing answer too large')
        if needs_manual(f):f['kind']='unsupported';f['value']=None
    import hashlib
    signature=hashlib.sha256(json.dumps([(f['field_id'],f['label'],f['kind'],f['options']) for f in fields]).encode()).hexdigest()
    # Keep browser identity separately. Never use a model's idea of the page signature.
    return {'fields':fields,'signature':signature,'has_next':raw['has_next'],'at_end':raw['at_end']},raw['signature']


class Bridge:
    def __init__(self,session):self.session=session;self.browser_signature=None;self.replacements=set()
    def observe(self,page):
        obs,self.browser_signature=clean_observation(self.session.command('observe'))
        return obs
    def apply(self,page,field,answer):
        self.session.command('apply',field=field,answer=answer.model_dump(),allow_replace=field['field_id'] in self.replacements)
    def next_section(self,page,signature):
        self.session.command('next',signature=self.browser_signature)
    matches=staticmethod(dom.matches)
    populated=staticmethod(dom.populated)
    operation_cost=staticmethod(dom.operation_cost)


class Session:
    def __init__(self,facts,model_factory,origin):
        self.id=secrets.token_urlsafe(18);self.facts=facts;self.model_factory=model_factory;self.origin=origin
        self.condition=threading.Condition();self.stopped=False;self.done=False;self.pending=None;self.response=None
        self.waiting=None;self.answer_value=None;self.message='Reading the form';self.manual=[];self.ready=False
        self.checked=0;self.deadline=time.monotonic()+600;self.calls=0;self.usage_incomplete=False
        self.serial=0;self.error=False
    def ensure_running(self):
        if self.stopped:raise InterruptedError('Stopped')
        if time.monotonic()>self.deadline:raise TimeoutError('Time limit reached')
    def command(self,op,**data):
        with self.condition:
            self.ensure_running();self.serial+=1;cid=str(self.serial)
            self.pending={'id':cid,'op':op,'run_id':self.id,**data};self.response=None
            until=min(self.deadline,time.monotonic()+18)
            while self.response is None:
                self.ensure_running()
                if time.monotonic()>=until:raise TimeoutError('Browser did not respond')
                self.condition.wait(min(0.25,max(0.01,until-time.monotonic())))
            response=self.response;self.pending=None;self.response=None
        if response.get('error'):raise ValueError('Browser action could not be verified')
        return response
    def respond(self,cid,result):
        with self.condition:
            self.ensure_running()
            if not self.pending or self.pending['id']!=cid or self.response is not None:raise ValueError('This browser command has expired')
            if not isinstance(result,dict):raise ValueError('Invalid browser response')
            self.response=result;self.condition.notify_all()
    def ask(self,label,options,kind='answer'):
        with self.condition:
            self.ensure_running();self.waiting={'id':secrets.token_urlsafe(12),'label':label,'options':options,'kind':kind}
            self.answer_value=None;self.message='Your answer is needed' if kind=='answer' else 'An answer is already filled'
            until=min(self.deadline,time.monotonic()+180)
            while self.answer_value is None:
                self.ensure_running()
                if time.monotonic()>=until:raise TimeoutError('Answer wait expired')
                self.condition.wait(0.25)
            answer=self.answer_value;self.answer_value=None;self.waiting=None
            return answer
    def answer(self,qid,value):
        with self.condition:
            self.ensure_running()
            if not self.waiting or self.waiting['id']!=qid or self.answer_value is not None:raise ValueError('This question has expired')
            if not isinstance(value,str) or not 1<=len(value.strip())<=2000:raise ValueError('Enter a shorter answer')
            if self.waiting['kind']=='overwrite' and value not in ('Replace','Keep'):raise ValueError('Choose Replace or Keep')
            self.answer_value=value.strip();self.condition.notify_all()
    def stop(self):
        with self.condition:
            self.stopped=True;self.pending=None;self.waiting=None;self.facts='';self.message='Stopped';self.condition.notify_all()
    def snapshot(self):
        with self.condition:return {'id':self.id,'running':not(self.done or self.stopped),'message':self.message,
            'command':self.pending if not self.stopped else None,'question':self.waiting,'ready':self.ready,'manual':self.manual,
            'checked':self.checked,'calls':self.calls,'error':self.error,'usage_incomplete':self.usage_incomplete}
    def emit(self,kind,**data):
        with self.condition:
            self.ensure_running();self.message=data.get('message','Working')
    def run(self):
        model=None;bridge=Bridge(self)
        try:
            model=self.model_factory()
            def confirm(field):
                # Permission is scoped to this field on this observed section.
                decision=self.ask(field['label'],['Replace','Keep'],'overwrite')=='Replace'
                if decision:bridge.replacements.add(field['field_id'])
                return decision
            graph=workflow(None,model,self.emit,self.ask,browser=bridge,confirm=confirm)
            result=graph.invoke({'facts':self.facts,'pages':1,'checked':0},{'recursion_limit':125})
            with self.condition:
                self.ensure_running();self.ready=result['reason']=='ready_for_review';self.manual=result.get('manual',[])
                self.checked=result.get('checked',0)
                self.message='Ready for review' if self.ready else ('Needs your review' if self.manual else 'Partly filled — please review')
        except InterruptedError:pass
        except Exception:
            with self.condition:
                if not self.stopped:self.error=True;self.message='Stopped — the form could not be verified. Review the page and try again.'
        finally:
            if model:
                self.calls=model.calls;self.usage_incomplete=model.usage_incomplete
                model.close()
            with self.condition:
                self.done=True;self.pending=None;self.waiting=None;self.facts='';self.response=None;self.answer_value=None;self.condition.notify_all()


def production_model():
    from dotenv import dotenv_values
    values=dotenv_values(ROOT/'.env.local')
    key=values.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not key:raise ValueError('API key configuration missing')
    return Adapter(key)


class Service:
    def __init__(self,model_factory=production_model):
        self.lock=threading.Lock();self.session=None;self.model_factory=model_factory
    def start(self,body):
        if not isinstance(body,dict) or set(body)!={'facts','origin'}:raise ValueError('Invalid run request')
        facts=body['facts'];origin=body['origin']
        if not isinstance(facts,str) or not 3<=len(facts.strip())<=6000:raise ValueError('Add your details (up to 6,000 characters)')
        if not isinstance(origin,str) or len(origin)>300:raise ValueError('Invalid page origin')
        p=urlsplit(origin)
        if p.username or p.password or p.path or p.query or p.fragment or not p.hostname or p.scheme not in ('https','http'):raise ValueError('Use an HTTP or HTTPS page')
        with self.lock:
            if self.session and not(self.session.done or self.session.stopped):raise ValueError('Stop the current run first')
            session=Session(facts.strip(),self.model_factory,origin);self.session=session
            threading.Thread(target=session.run,daemon=True).start()
            return {'id':session.id}
    def get(self,sid):
        with self.lock:
            if not self.session or sid!=self.session.id:raise ValueError('This run has expired')
            return self.session


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def origin(self):return self.headers.get('Origin','')
    def allowed_origin(self):
        client=self.headers.get('X-Extension-ID','')
        expected='chrome-extension://'+client
        return bool(re.fullmatch(r'[a-p]{32}',client)) and self.origin() in ('',expected)
    def reply(self,code,data):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if self.allowed_origin():self.send_header('Access-Control-Allow-Origin',self.origin());self.send_header('Vary','Origin')
        self.send_header('Content-Length',str(len(raw)));self.end_headers()
        try:self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass
    def valid_host(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
    def do_OPTIONS(self):
        if not self.valid_host() or not EXTENSION_ORIGIN.fullmatch(self.origin()):return self.reply(403,{'error':'Local extension access only'})
        self.send_response(204);self.send_header('Access-Control-Allow-Origin',self.origin())
        self.send_header('Access-Control-Allow-Methods','POST, OPTIONS');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type, X-Extension-ID')
        self.send_header('Vary','Origin');self.end_headers()
    def do_GET(self):
        if self.path=='/practice' and self.valid_host():
            raw=(ROOT/'form_assistant/practice.html').read_bytes();self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        else:self.reply(405,{'error':'Use the extension'})
    def do_POST(self):
        if not self.valid_host() or not self.allowed_origin():return self.reply(403,{'error':'Local extension access only'})
        if not secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+self.server.token):return self.reply(401,{'error':'Connect using the code in the terminal'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if self.headers.get('Content-Type')!='application/json' or not 0<n<=140000:raise ValueError('Invalid request size or type')
            body=json.loads(self.rfile.read(n))
            if self.path=='/connect' and body=={}:result={'ok':True}
            elif self.path=='/start':result=self.server.service.start(body)
            elif isinstance(body,dict) and self.path in ('/state','/respond','/answer','/stop'):
                session=self.server.service.get(body.get('id'))
                if self.path=='/state' and set(body)=={'id'}:result=session.snapshot()
                elif self.path=='/respond' and set(body)=={'id','command_id','result'}:session.respond(body['command_id'],body['result']);result={'ok':True}
                elif self.path=='/answer' and set(body)=={'id','question_id','answer'}:session.answer(body['question_id'],body['answer']);result={'ok':True}
                elif self.path=='/stop' and set(body)=={'id'}:session.stop();result={'ok':True}
                else:raise ValueError('Invalid request')
            else:return self.reply(404,{'error':'Not found'})
            return self.reply(200,result)
        except (ValueError,TypeError,KeyError):return self.reply(400,{'error':'The request is invalid or has expired'})
        except Exception:return self.reply(500,{'error':'Local service error'})


def make_server(port=8766,model_factory=production_model):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.token=secrets.token_urlsafe(24);server.service=Service(model_factory)
    server.daemon_threads=True
    return server


def main():
    parser=argparse.ArgumentParser(description='Connect Form Assistant to Chrome');parser.parse_args()
    server=make_server()
    print('Form Assistant is ready. Keep this terminal open.',flush=True)
    print('Connection code: '+server.token,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        if server.service.session:server.service.session.stop()
        server.server_close()

if __name__=='__main__':main()
