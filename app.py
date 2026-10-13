"""Local-first Interview Studio. Run: python app.py --open."""
import argparse
import base64
import http.cookies
import json
import logging
import mimetypes
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from studio.interview import evaluate, followup, generate_questions, report_markdown
from studio.models import ModelError, ModelSettings, call_json
from studio.resumes import clean_text, extract_document, parse_resume
from studio.storage import Store, identifier, now, summarize

ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger('studio')


class Studio:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.store = Store(self.root / 'data' / 'studio.sqlite3')
        self.settings = ModelSettings(self.root)
        self.locks, self.locks_guard = {}, threading.Lock()

    def item_lock(self, key):
        with self.locks_guard:
            return self.locks.setdefault(key, threading.Lock())

    def bootstrap(self, owner):
        resumes = self.store.list('resumes', owner)
        sessions = self.store.list('sessions', owner)
        summaries = [summarize(s) for s in sessions]
        dimensions = {}
        scores = []
        for s in sessions:
            for q in s['questions']:
                if q.get('result'):
                    scores.append(q['result']['total'])
                    for d in q['result']['dimensions']:
                        dimensions.setdefault(d['label'], []).append(d['score'])
        education, skills = {}, {}
        for r in resumes:
            degree = r['parsed']['education'] or '未提供'
            education[degree] = education.get(degree, 0) + 1
            for skill in r['parsed']['skills']:
                skills[skill] = skills.get(skill, 0) + 1
        return {'settings': self.settings.public(), 'resumes': [self.resume_summary(r) for r in resumes],
                'sessions': summaries, 'weak_points': self.store.weak_points(owner),
                'stats': {'resumes': len(resumes), 'sessions': len(sessions), 'answered': len(scores),
                          'average': round(sum(scores)/len(scores), 1) if scores else None,
                          'dimensions': {k: round(sum(v)/len(v), 1) for k, v in dimensions.items()},
                          'education': education, 'skills': dict(sorted(skills.items(), key=lambda p: -p[1])[:10])}}

    @staticmethod
    def resume_summary(r):
        return {k: r[k] for k in ['id', 'title', 'filename', 'created_at', 'updated_at', 'warnings']} | {
            'parsed': {k: v for k, v in r['parsed'].items() if k != 'chunks'}}

    def import_resume(self, owner, payload):
        filename = str(payload.get('filename', '粘贴的简历')).replace('\\', '/').split('/')[-1][:150]
        if 'file_data' in payload:
            try:
                data = base64.b64decode(payload['file_data'], validate=True)
            except (ValueError, TypeError):
                raise ValueError('文件传输失败，请重新选择文件。') from None
            text, warnings = extract_document(filename, data)
        else:
            text, warnings = clean_text(str(payload.get('text', ''))), []
        title = str(payload.get('title', '')).strip()[:100] or Path(filename).stem
        parsed = parse_resume(text)
        if title == '粘贴的简历' and parsed['name']:
            title = parsed['name'] + '的简历'
        value = {'id': identifier(), 'title': title, 'filename': filename, 'text': text,
                 'parsed': parsed, 'warnings': warnings, 'created_at': now(), 'updated_at': now()}
        return self.store.put('resumes', value, owner)

    def new_session(self, owner, payload):
        resume = self.store.get('resumes', payload.get('resume_id', ''), owner)
        role = str(payload.get('role', '')).strip()[:100]
        if not role:
            raise ValueError('请填写或选择目标岗位。')
        count = payload.get('count', 6)
        if type(count) is not int or count not in (6, 8, 10):
            raise ValueError('练习题数请选择 6、8 或 10。')
        jd = str(payload.get('job_description', '')).strip()[:6000]
        difficulty = str(payload.get('difficulty', '标准'))[:30]
        config = self.settings.snapshot()
        memory = self.store.weak_points(owner)
        questions, engine, warning = generate_questions(resume, role, jd, count, difficulty, memory, config)
        session = {'id': identifier(), 'resume_id': resume['id'], 'resume_name': resume['title'],
                   'resume_snapshot': resume, 'role': role, 'job_description': jd, 'difficulty': difficulty,
                   'questions': questions, 'current_index': 0, 'status': 'active', 'engine': engine,
                   'model': config['model'] if engine == 'online' else '', 'notice': warning,
                   'memory_used': memory, 'created_at': now(), 'updated_at': now()}
        return self.store.put('sessions', session, owner)

    def mutate_session(self, owner, session_id, action, payload):
        lock = self.item_lock(session_id)
        if not lock.acquire(blocking=False):
            raise BlockingIOError('此练习正在处理中，请等待当前请求完成。')
        try:
            request_id = str(payload.get('request_id', ''))[:100]
            cached = self.store.cached(owner, session_id + ':' + request_id) if request_id else None
            if cached:
                return cached
            session = self.store.get('sessions', session_id, owner)
            if session['status'] == 'completed':
                raise ValueError('这次练习已完成，请开始新的练习。')
            question = session['questions'][session['current_index']]
            if payload.get('question_id') != question['id']:
                raise ValueError('当前题目已变化，请刷新后继续。')
            if action == 'answer':
                if question['stage'] not in ('initial', 'followup'):
                    raise ValueError('本题已评分，请继续下一题或重新作答。')
                answer = str(payload.get('answer', '')).strip()
                direct = payload.get('evaluate_now') is True
                if not answer and not (direct and question['answers']):
                    raise ValueError('请先输入回答。')
                if answer and not 10 <= len(answer) <= 10000:
                    raise ValueError('回答请保持在 10 到 10,000 字之间。')
                if answer:
                    question['answers'].append({'text': answer, 'kind': question['stage'], 'time': now()})
                config = self.settings.snapshot()
                if question['stage'] == 'initial' and not direct:
                    fq, engine, warning = followup(session['resume_snapshot'], question, answer, config)
                    question.update(stage='followup', followup=fq, followup_engine=engine, notice=warning)
                else:
                    question['result'] = evaluate(session['resume_snapshot'], question, config)
                    question['stage'] = 'evaluated'
            elif action == 'next':
                if question['stage'] not in ('evaluated', 'skipped'):
                    raise ValueError('请先完成本题评分，或选择跳过。')
                if session['current_index'] + 1 >= len(session['questions']):
                    session['status'] = 'completed'
                else:
                    session['current_index'] += 1
            elif action == 'skip':
                if question['stage'] == 'evaluated':
                    raise ValueError('已评分题目请使用继续按钮。')
                question['stage'] = 'skipped'
                if session['current_index'] + 1 >= len(session['questions']):
                    session['status'] = 'completed'
                else:
                    session['current_index'] += 1
            elif action == 'retry':
                if question['stage'] != 'evaluated':
                    raise ValueError('本题评分后可以重新作答。')
                question['attempts'].append({'answers': question['answers'], 'followup': question['followup'],
                                             'result': question['result']})
                question.update(stage='initial', answers=[], followup='', result=None)
            else:
                raise ValueError('不支持的操作。')
            return self.store.put_with_request(session, owner, session_id + ':' + request_id if request_id else '')
        finally:
            lock.release()


def handler_factory(studio):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'InterviewStudio/1.0'

        def log_message(self, fmt, *args):
            # Do not log resume text, answer bodies, credentials or external URLs.
            LOGGER.info('%s %s', self.command, self.path.split('?')[0])

        def owner(self):
            cookie = http.cookies.SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie', ''))
                token = cookie.get('studio_owner')
                if token and re.fullmatch('[a-f0-9]{32}', token.value):
                    return token.value
            except http.cookies.CookieError:
                pass
            return None

        def send(self, data, status=200, content_type='application/json; charset=utf-8', extra=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header('X-Frame-Options', 'DENY')
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def host_valid(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.host_valid():
                return self.send({'error': '仅支持本机访问。'}, 403)
            path = urllib.parse.urlparse(self.path).path
            owner = self.owner()
            try:
                if path in ('/', '/index.html'):
                    extra = {} if owner else {'Set-Cookie': f'studio_owner={identifier()}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000'}
                    return self.send((studio.root / 'web' / 'index.html').read_bytes(), content_type='text/html; charset=utf-8', extra=extra)
                if path in ('/assets/app.js', '/assets/style.css', '/assets/icon.svg'):
                    file = studio.root / 'web' / path.rsplit('/', 1)[-1]
                    return self.send(file.read_bytes(), content_type=mimetypes.guess_type(file)[0] or 'application/octet-stream')
                if path == '/api/health':
                    return self.send({'ok': True, 'version': '1.0.0', 'app': 'interview-studio'})
                if not owner:
                    return self.send({'error': '请从首页打开应用。'}, 401)
                if path == '/api/bootstrap':
                    return self.send(studio.bootstrap(owner))
                if path == '/api/sample':
                    return self.send({'text': (studio.root / 'samples' / '示例简历.md').read_text(encoding='utf-8')})
                match = re.fullmatch(r'/api/(resumes|sessions)/([a-f0-9]{32})(/export)?', path)
                if match:
                    table, item_id, export = match.groups()
                    value = studio.store.get(table, item_id, owner)
                    if export and table == 'sessions':
                        fmt = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('format', ['md'])[0]
                        if fmt == 'json':
                            # Include attempts, engines and evidence, never model credentials.
                            return self.send(value, extra={'Content-Disposition': 'attachment; filename="interview-report.json"'})
                        return self.send(report_markdown(value).encode('utf-8-sig'), content_type='text/markdown; charset=utf-8',
                                         extra={'Content-Disposition': 'attachment; filename="interview-report.md"'})
                    return self.send(value)
                return self.send({'error': '页面或记录不存在。'}, 404)
            except KeyError:
                return self.send({'error': '记录不存在或不属于当前浏览器。'}, 404)
            except Exception:
                LOGGER.exception('GET failed')
                return self.send({'error': '读取失败，请重试。'}, 500)

        def do_POST(self):
            origin = self.headers.get('Origin')
            allowed = (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}')
            if not self.host_valid() or origin and origin not in allowed or self.headers.get('X-Studio-Request') != '1':
                return self.send({'error': '请求来源验证失败，请在本机应用页面操作。'}, 403)
            owner = self.owner()
            if not owner:
                return self.send({'error': '请先打开应用首页。'}, 401)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 18 * 1024 * 1024:
                    return self.send({'error': '请求大小不符合要求。'}, 413)
                if not self.headers.get('Content-Type', '').startswith('application/json'):
                    return self.send({'error': '需要 JSON 请求。'}, 415)
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError('请求格式不正确。')
                path = urllib.parse.urlparse(self.path).path
                if path == '/api/resumes':
                    return self.send(studio.import_resume(owner, payload))
                if path == '/api/sessions':
                    with studio.item_lock('new:' + owner):
                        return self.send(studio.new_session(owner, payload))
                if path == '/api/settings':
                    return self.send(studio.settings.update(payload))
                if path == '/api/settings/test':
                    config = studio.settings.snapshot()
                    if config['mode'] != 'online':
                        raise ValueError('请先保存在线模型配置。')
                    response = call_json(config, '连接测试，只返回 {"ok":true}。', {'test': 'connection'}, 40)
                    if response.get('ok') is not True:
                        raise ModelError('模型返回的连接测试结果不符合要求')
                    return self.send({'ok': True, 'message': '连接成功，模型可以返回结构化结果。'})
                match = re.fullmatch(r'/api/(sessions|resumes)/([a-f0-9]{32})/(answer|next|skip|retry|update|delete)', path)
                if match:
                    table, item_id, action = match.groups()
                    if action == 'delete':
                        with studio.item_lock(item_id):
                            studio.store.get(table, item_id, owner)
                            studio.store.delete(table, item_id, owner)
                        return self.send({'ok': True})
                    if table == 'resumes' and action == 'update':
                        r = studio.store.get('resumes', item_id, owner)
                        r['text'] = clean_text(str(payload.get('text', '')))
                        r['title'] = str(payload.get('title', r['title'])).strip()[:100] or r['title']
                        r['parsed'] = parse_resume(r['text'])
                        return self.send(studio.store.put('resumes', r, owner))
                    if table == 'sessions':
                        return self.send(studio.mutate_session(owner, item_id, action, payload))
                return self.send({'error': '操作不存在。'}, 404)
            except (ValueError, ModelError) as e:
                return self.send({'error': str(e)}, 400)
            except KeyError:
                return self.send({'error': '记录不存在或不属于当前浏览器。'}, 404)
            except BlockingIOError as e:
                return self.send({'error': str(e)}, 409)
            except Exception:
                LOGGER.exception('POST failed')
                return self.send({'error': '操作未完成，请重试。已保存的记录不会丢失。'}, 500)
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    studio = Studio()
    (ROOT / 'data').mkdir(exist_ok=True)
    logging.basicConfig(filename=ROOT / 'data' / 'app.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_factory(studio))
    except OSError:
        print(f'Port {args.port} is already in use. Open http://127.0.0.1:{args.port} or select another port.')
        if args.open:
            webbrowser.open(f'http://127.0.0.1:{args.port}')
        return
    server.daemon_threads = True
    print(f'Interview Studio: http://127.0.0.1:{args.port}')
    if args.open:
        webbrowser.open(f'http://127.0.0.1:{args.port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
