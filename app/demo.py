"""Dependency-free loopback demo. Run: python -m app.demo"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
from urllib.parse import urlsplit

from .scenarios import SCENARIOS, validate_request
ROOT = Path(__file__).resolve().parents[1]


def command(name, seed):
    if name not in SCENARIOS or type(seed) is not int or seed not in (61, 67):
        raise ValueError('Unsupported demo run')
    return [sys.executable, '-B', '-m', 'app.demo_worker', '--scenario', name, '--seed', str(seed)]


class Runs:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.events = []
        self.running = False

    def add(self, event):
        with self.lock:
            self.events = (self.events + [event])[-100:]

    def start(self, body):
        name, seed = validate_request(body)
        with self.lock:
            if self.running:
                raise ValueError('A live run is already active')
            self.events = [{'type': 'started', 'scenario': name, 'seed': seed}]
            self.process = subprocess.Popen(command(name, seed), cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True)
            self.running = True
        threading.Thread(target=self.collect, args=(SCENARIOS[name]['steps'],), daemon=True).start()

    def collect(self, steps):
        process = self.process
        timer = threading.Timer(max(90, 25 * steps + 15) + 10, self.cancel)
        timer.daemon = True
        timer.start()
        try:
            for line in process.stdout:
                if len(line) > 8000:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get('type') in ('goal','trace','result','error'):
                    self.add(event)
            code = process.wait()
            self.add({'type': 'finished', 'exit_code': code})
        finally:
            timer.cancel()
            with self.lock:
                self.running = False
                self.process = None

    def cancel(self):
        with self.lock:
            process = self.process
            if process is None or process.poll() is not None:
                return
            self.events.append({'type': 'stopped', 'message': 'Stopped; usage may be incomplete'})
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def snapshot(self):
        with self.lock:
            return {'running': self.running, 'events': list(self.events)}


def recorded():
    folder = ROOT / 'docs/evidence/final-v1'
    if not (folder/'audit-summary.json').is_file():
        return {'available': False, 'message': 'Install the final report bundle to view recorded evidence.'}
    audit = json.loads((folder/'audit-summary.json').read_text())
    rows = json.loads((folder/'episode-metrics.json').read_text())
    fields = ('batch','task','seed','arm','success','reason','steps','api_calls','duration_seconds','api_usage_may_be_incomplete')
    return {'available': True, 'totals': audit['totals'], 'rows': [{k:r[k] for k in fields} for r in rows]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, code, body, mime='application/json'):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error':'Local access only'})
        path = urlsplit(self.path).path
        if path == '/':
            page = (ROOT/'app/index.html').read_text().replace('__TOKEN__',self.server.token)
            return self.reply(200, page, 'text/html')
        if path == '/recorded':
            return self.reply(200, recorded())
        if path == '/state':
            return self.reply(200, self.server.runs.snapshot())
        self.reply(404, {'error':'Not found'})

    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-Demo-Token') != self.server.token:
            return self.reply(403, {'error':'Local page token required'})
        origin = self.headers.get('Origin')
        if origin not in (None, f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            return self.reply(403, {'error':'Local origin required'})
        if self.headers.get('Content-Type') != 'application/json':
            return self.reply(400, {'error':'JSON required'})
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 4096:
                raise ValueError('Request too large or empty')
            body = json.loads(self.rfile.read(length))
            if self.path == '/run':
                self.server.runs.start(body)
            elif self.path == '/stop' and body == {}:
                self.server.runs.cancel()
            else:
                return self.reply(404, {'error':'Not found'})
        except (ValueError, TypeError):
            return self.reply(400, {'error':'Enter a supported instruction; only one run can be active.'})
        except OSError:
            return self.reply(500, {'error':'Could not start the local worker'})
        self.reply(200, {'ok':True})


def benchmark_main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    if not 1024<=args.port<=65535:
        parser.error('Choose a port from 1024 to 65535')
    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.token = secrets.token_urlsafe(32)
    server.runs = Runs()
    print(f'Demo: http://127.0.0.1:{args.port} — recorded view makes no API calls',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.runs.cancel()
        server.server_close()


def main():
    if '--benchmark' in sys.argv:
        sys.argv.remove('--benchmark')
        benchmark_main()
    else:
        if '--wikipedia' in sys.argv:
            sys.argv.remove('--wikipedia')
            from .product import main as launch
        else:
            from form_assistant.server import main as launch
        launch()


if __name__=='__main__':
    main()
