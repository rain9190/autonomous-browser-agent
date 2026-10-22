"""Simple local product: instruction, Run, Stop and a visible browser."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from .demo import Handler as BaseHandler
ROOT=Path(__file__).resolve().parents[1]


def validate_instruction(body):
    if not isinstance(body,dict) or set(body)!={'instruction'}:
        raise ValueError('Enter an instruction')
    text=body['instruction']
    if not isinstance(text,str) or not 3<=len(text.strip())<=800:
        raise ValueError('Enter a short instruction')
    return text.strip()


class Runs:
    def __init__(self):
        self.lock=threading.Lock();self.process=None;self.events=[];self.running=False
    def append(self,p,event):
        with self.lock:
            if self.process is p:
                self.events=(self.events+[event])[-60:]
                if event['type'] in ('result','error','stopped'):self.running=False
    def start(self,body):
        instruction=validate_instruction(body)
        with self.lock:
            if self.running:raise ValueError('Already running')
            if self.process and self.process.poll() is None:self.terminate(self.process)
            p=subprocess.Popen([sys.executable,'-B','-m','app.product_worker'],cwd=ROOT,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True)
            self.process=p;self.running=True
            self.events=[{'type':'status','message':'Starting your task'}]
            try:
                p.stdin.write(json.dumps({'instruction':instruction})+'\n');p.stdin.close()
            except OSError:
                self.terminate(p);self.running=False;raise
        threading.Thread(target=self.collect,args=(p,),daemon=True).start()
    def collect(self,p):
        timer=threading.Timer(210,lambda:self.timeout(p));timer.daemon=True;timer.start()
        terminal=False
        try:
            for line in p.stdout:
                if len(line)>10000:continue
                try:event=json.loads(line)
                except ValueError:continue
                if not isinstance(event,dict) or event.get('type') not in ('status','result','error','stopped'):continue
                if event['type'] in ('result','error','stopped'):terminal=True;timer.cancel()
                self.append(p,event)
            p.wait()
            if not terminal:self.append(p,{'type':'error','message':'The browser closed before the task finished.'})
        finally:
            timer.cancel()
            with self.lock:
                if self.process is p:self.running=False;self.process=None
    def timeout(self,p):
        with self.lock:
            if self.process is p and self.running:
                self.events.append({'type':'error','message':'Time limit reached. The task was stopped.'});self.running=False;self.terminate(p)
    @staticmethod
    def terminate(p):
        try:os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError:return
        def kill():
            if p.poll() is None:
                try:os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:pass
        t=threading.Timer(3,kill);t.daemon=True;t.start()
    def cancel(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.events.append({'type':'stopped','message':'Stopped. Browser is closing.'});self.running=False;self.terminate(self.process)
    def snapshot(self):
        with self.lock:return {'running':self.running,'browser_open':self.process is not None and self.process.poll() is None,'events':list(self.events)}


class Handler(BaseHandler):
    def do_GET(self):
        if not self.valid_host():return self.reply(403,{'error':'Local access only'})
        if self.path=='/':return self.reply(200,(ROOT/'app/product.html').read_text().replace('__TOKEN__',self.server.token),'text/html')
        if self.path=='/state':return self.reply(200,self.server.runs.snapshot())
        return self.reply(404,{'error':'Not found'})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Choose a port from 1024 to 65535')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.token=secrets.token_urlsafe(32);server.runs=Runs()
    print(f'Browser Agent: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.runs.cancel();server.server_close()


if __name__=='__main__':main()
