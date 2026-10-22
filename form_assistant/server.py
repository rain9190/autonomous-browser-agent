"""Loopback UI, one worker at a time, with private stdin answer continuation."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from app.demo import Handler as BaseHandler
from app.product import Runs as ProductRuns
from .policy import request_body
ROOT=Path(__file__).resolve().parents[1]


class Runs(ProductRuns):
    def __init__(self,origin):
        super().__init__();self.origin=origin;self.waiting=None
    def start(self,body):
        data=request_body(body,self.origin)
        with self.lock:
            if self.running:raise ValueError('A form is already being filled')
            if self.process and self.process.poll() is None:self.terminate(self.process)
            p=subprocess.Popen([sys.executable,'-B','-m','form_assistant.worker'],cwd=ROOT,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True)
            self.process=p;self.running=True;self.waiting=None
            self.events=[{'type':'status','message':'Starting your form'}]
            try:p.stdin.write(json.dumps(data,ensure_ascii=False)+'\n');p.stdin.flush()
            except OSError:self.terminate(p);self.running=False;raise
        threading.Thread(target=self.collect,args=(p,),daemon=True).start()
    def append(self,p,event):
        with self.lock:
            if self.process is not p:return
            self.events=(self.events+[event])[-60:]
            if event['type']=='question':self.waiting=event
            if event['type']=='answered':self.waiting=None
            if event['type'] in ('result','error','stopped'):self.running=False;self.waiting=None
    def answer(self,body):
        with self.lock:
            if not isinstance(body,dict) or set(body)!={'id','answer'} or not self.running or not self.waiting or body['id']!=self.waiting['id']:
                raise ValueError('This question is no longer waiting for an answer')
            if not isinstance(body['answer'],str) or not 1<=len(body['answer'].strip())<=2000:raise ValueError('Enter an answer up to 2,000 characters')
            self.process.stdin.write(json.dumps(body,ensure_ascii=False)+'\n');self.process.stdin.flush();self.waiting=None
    def collect(self,p):
        timer=threading.Timer(660,lambda:self.timeout(p));timer.daemon=True;timer.start();terminal=False
        try:
            for line in p.stdout:
                if len(line)>12000:continue
                try:event=json.loads(line)
                except ValueError:continue
                if not isinstance(event,dict) or event.get('type') not in ('status','question','answered','result','error','stopped'):continue
                if event['type'] in ('result','error','stopped'):terminal=True;timer.cancel()
                self.append(p,event)
            p.wait()
            if not terminal:self.append(p,{'type':'error','message':'The browser closed before the form was completed.'})
        finally:
            timer.cancel()
            try:p.stdin.close()
            except OSError:pass
            with self.lock:
                if self.process is p:self.running=False;self.process=None;self.waiting=None
    def cancel(self):
        super().cancel()
        with self.lock:self.waiting=None
    def snapshot(self):
        with self.lock:return {'running':self.running,'browser_open':self.process is not None and self.process.poll() is None,
                              'waiting':self.waiting,'events':list(self.events)}


class Handler(BaseHandler):
    def do_GET(self):
        if not self.valid_host():return self.reply(403,{'error':'Local access only'})
        if self.path=='/':return self.reply(200,(ROOT/'form_assistant/index.html').read_text().replace('__TOKEN__',self.server.token),'text/html')
        if self.path=='/state':return self.reply(200,self.server.runs.snapshot())
        if self.path=='/practice':return self.reply(200,(ROOT/'form_assistant/practice.html').read_text(),'text/html')
        self.reply(404,{'error':'Not found'})
    def do_POST(self):
        port=self.server.server_port
        if not self.valid_host() or self.headers.get('X-Demo-Token')!=self.server.token:return self.reply(403,{'error':'Local page token required'})
        if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{port}',f'http://localhost:{port}'):return self.reply(403,{'error':'Local origin required'})
        try:
            if self.headers.get('Content-Type')!='application/json':raise ValueError('JSON required')
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=18000:raise ValueError('Request too large')
            body=json.loads(self.rfile.read(size))
            if self.path=='/run':self.server.runs.start(body)
            elif self.path=='/answer':self.server.runs.answer(body)
            elif self.path=='/stop' and body=={}:self.server.runs.cancel()
            else:return self.reply(404,{'error':'Not found'})
        except (ValueError,TypeError,KeyError) as e:
            # These messages are produced only by local request validation, not remote exceptions.
            return self.reply(400,{'error':str(e) if isinstance(e,ValueError) and len(str(e))<160 else 'Invalid request'})
        except OSError:return self.reply(500,{'error':'The worker could not be reached. Stop and start a new run.'})
        self.reply(200,{'ok':True})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Choose a port from 1024 to 65535')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.token=secrets.token_urlsafe(32)
    server.runs=Runs(f'http://127.0.0.1:{args.port}')
    print(f'Form Assistant: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.runs.cancel();server.server_close()


if __name__=='__main__':main()
