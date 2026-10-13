import base64
import http.client
import io
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Studio, handler_factory
from studio.interview import evaluate, generate_questions, local_evaluate, safe_star, report_markdown
from studio.models import ModelError, ModelSettings, protect
from studio.resumes import extract_document, parse_resume, redact_contacts, retrieve
from studio.storage import identifier

SAMPLE = '''姓名：测试同学
教育背景：示例大学 计算机科学与技术 本科
项目经历1：图书借阅平台
我负责 Python 和 Flask 接口，使用 MySQL 保存借阅记录，通过 12 个测试用例验证功能。
技能：Python、Flask、MySQL、Git
'''
ANSWER = '在图书借阅项目中，我负责设计报名接口。首先检查重复请求，因为可能重复写入，所以使用唯一约束。最终通过12个测试用例验证，日志没有发现重复记录。'


class ResumeTests(unittest.TestCase):
    def test_text_encodings(self):
        for encoding in ('utf-8-sig', 'gb18030', 'utf-16'):
            text, warnings = extract_document('resume.txt', SAMPLE.encode(encoding))
            self.assertIn('图书借阅平台', text)

    def test_docx_tables_and_unicode(self):
        xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>姓名：测试同学 教育背景：本科</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>项目经历：Python 图书平台，负责接口测试。</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w') as z:
            z.writestr('word/document.xml', xml)
        text, _ = extract_document('简历.docx', b.getvalue())
        self.assertIn('接口测试', text)
        self.assertIn('测试同学', text)

    def test_bad_documents_rejected(self):
        for name, data in [('resume.doc', b'bad'), ('resume.docx', b'not a zip'), ('r.txt', b'')]:
            with self.assertRaises(ValueError):
                extract_document(name, data)

    def test_text_pdf(self):
        import pymupdf as fitz
        with fitz.open() as pdf:
            p = pdf.new_page()
            p.insert_text((60, 70), 'Resume: Python backend project. Implemented Flask API and tests.')
            raw = pdf.tobytes()
        text, _ = extract_document('resume.pdf', raw)
        self.assertIn('Flask API', text)

    def test_unknown_fields_not_invented(self):
        parsed = parse_resume('我使用 Python 开发了一个课程工具，并负责整理测试反馈与功能文档。')
        self.assertEqual(parsed['education'], '')
        self.assertEqual(parsed['name'], '')
        self.assertNotIn('工作年限', parsed)
        self.assertNotIn('预计薪酬', parsed)

    def test_course_and_prose_not_misclassified_as_projects(self):
        text = '课程：数据结构、操作系统、计算机网络。\n目前完成了功能验证，但还没有系统统计结果，需要补充测试。\n项目经历1：图书借阅平台\n我负责测试接口。'
        self.assertEqual([p['title'] for p in parse_resume(text)['projects']], ['图书借阅平台'])

    def test_skill_boundaries_and_evidence(self):
        parsed = parse_resume(SAMPLE)
        self.assertIn('Python', parsed['skills'])
        self.assertIn('图书借阅平台', parsed['projects'][0]['title'])
        self.assertIn(parsed['projects'][0]['evidence'], SAMPLE.strip())
        self.assertNotIn('Java', parse_resume('使用 JavaScript 完成课程页面，并整理了界面测试用例和项目文档。')['skills'])
        self.assertIn(retrieve(SAMPLE, '借阅 Flask', 1)[0], SAMPLE)

    def test_contact_redaction(self):
        value = redact_contacts('手机13812345678，邮箱student@example.com，证件110101200001010019')
        self.assertNotIn('13812345678', value)
        self.assertNotIn('student@example.com', value)
        self.assertNotIn('110101200001010019', value)


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.studio = Studio(Path(self.tmp.name))
        self.owner = identifier()
        self.resume = self.studio.import_resume(self.owner, {'text': SAMPLE, 'title': '测试简历'})

    def tearDown(self):
        self.tmp.cleanup()

    def new(self):
        return self.studio.new_session(self.owner, {'resume_id': self.resume['id'], 'role': '后端实习', 'count': 6})

    def action(self, session, action, answer='', **extra):
        q = session['questions'][session['current_index']]
        return self.studio.mutate_session(self.owner, session['id'], action,
                                         {'question_id': q['id'], 'answer': answer, 'request_id': identifier(), **extra})

    def test_complete_six_question_workflow_and_export(self):
        session = self.new()
        original = [(q['id'], q['text']) for q in session['questions']]
        for _ in range(6):
            session = self.action(session, 'answer', ANSWER)
            q = session['questions'][session['current_index']]
            self.assertEqual(q['stage'], 'followup')
            self.assertTrue(q['followup'])
            session = self.action(session, 'answer', '我比较了先查询再写入和数据库唯一约束，最终用并发测试验证唯一约束能阻止重复记录。')
            q = session['questions'][session['current_index']]
            self.assertEqual(q['stage'], 'evaluated')
            self.assertEqual(q['result']['total'], sum(d['score'] for d in q['result']['dimensions']))
            session = self.action(session, 'next')
        self.assertEqual(session['status'], 'completed')
        self.assertEqual(original, [(q['id'], q['text']) for q in session['questions']])
        self.assertIn('STAR 整理', report_markdown(session))
        restarted = Studio(Path(self.tmp.name))
        self.assertEqual(restarted.store.get('sessions', session['id'], self.owner)['status'], 'completed')

    def test_duplicate_submission_and_stale_question(self):
        s = self.new()
        payload = {'question_id': s['questions'][0]['id'], 'answer': ANSWER, 'request_id': 'same-request'}
        first = self.studio.mutate_session(self.owner, s['id'], 'answer', payload)
        second = self.studio.mutate_session(self.owner, s['id'], 'answer', payload)
        self.assertEqual(first, second)
        self.assertEqual(len(second['questions'][0]['answers']), 1)
        with self.assertRaises(ValueError):
            self.studio.mutate_session(self.owner, s['id'], 'next', {'question_id': 'stale'})

    def test_skip_excluded_retry_preserved(self):
        s = self.new()
        s = self.action(s, 'answer', ANSWER)
        s = self.action(s, 'answer', evaluate_now=True)
        old = s['questions'][0]['result']['total']
        s = self.action(s, 'retry')
        self.assertEqual(s['questions'][0]['attempts'][0]['result']['total'], old)
        s = self.action(s, 'answer', ANSWER, evaluate_now=True)
        s = self.action(s, 'next')
        for _ in range(5):
            s = self.action(s, 'skip')
        self.assertEqual(s['status'], 'completed')
        stats = self.studio.bootstrap(self.owner)['sessions'][0]
        self.assertEqual(stats['answered'], 1)
        self.assertEqual(stats['skipped'], 5)
        self.assertEqual(stats['average'], old)

    def test_snapshot_and_browser_isolation(self):
        s = self.new()
        self.resume['text'] = SAMPLE + '\n新的简历内容与技能'
        self.studio.store.put('resumes', self.resume, self.owner)
        self.assertNotIn('新的简历内容', self.studio.store.get('sessions', s['id'], self.owner)['resume_snapshot']['text'])
        with self.assertRaises(KeyError):
            self.studio.store.get('sessions', s['id'], identifier())
        self.assertEqual(self.studio.bootstrap(identifier())['resumes'], [])

    def test_memory_used_in_next_session(self):
        s = self.new()
        s = self.action(s, 'answer', '我做了一个课程小工具，感觉效果还不错。', evaluate_now=True)
        following = self.new()
        self.assertTrue(following['memory_used'])
        self.assertIn('这次请特别注意', following['questions'][5]['text'])

    def test_concurrent_mutation_refused(self):
        s = self.new()
        lock = self.studio.item_lock(s['id'])
        lock.acquire()
        try:
            with self.assertRaises(BlockingIOError):
                self.action(s, 'answer', ANSWER)
        finally:
            lock.release()

    def test_deletion_removes_cached_answers(self):
        s = self.new()
        self.studio.mutate_session(self.owner, s['id'], 'answer',
                                  {'question_id': s['questions'][0]['id'], 'answer': ANSWER, 'request_id': 'cached'})
        self.studio.store.delete('sessions', s['id'], self.owner)
        self.assertIsNone(self.studio.store.cached(self.owner, s['id'] + ':cached'))


class ReliabilityTests(unittest.TestCase):
    def test_local_scores_sum_and_range(self):
        for answer in ['', '短回答', ANSWER, ANSWER * 20, '没有数字但通过验收文档和复现步骤验证了结果。']:
            result = local_evaluate({}, answer)
            self.assertEqual(result['total'], sum(d['score'] for d in result['dimensions']))
            self.assertTrue(all(0 <= d['score'] <= 25 for d in result['dimensions']))

    def test_star_rejects_invented_numbers_and_experiences(self):
        answer = '我负责整理课程实验的测试用例，通过对比日志检查功能。'
        star, missing = safe_star(answer, {'s': ['我在某公司管理团队'], 'r': ['性能提升99%，服务30万人'], 'a': ['通过对比日志检查功能']})
        self.assertNotIn('99%', star)
        self.assertNotIn('某公司', star)
        self.assertIn('【待补充', star)
        self.assertTrue(missing)

    def test_bad_online_output_falls_back_without_losing_answer(self):
        resume = {'text': SAMPLE, 'parsed': parse_resume(SAMPLE)}
        question = {'text': '请介绍项目', 'answers': [{'text': ANSWER}], 'followup': '如何验证？'}
        with patch('studio.interview.call_json', return_value={'dimensions': [{'key': ['bad']}]*4}):
            result = evaluate(resume, question, {'mode': 'online'})
        self.assertEqual(result['engine'], 'local_fallback')
        self.assertEqual(question['answers'][0]['text'], ANSWER)

    def test_online_score_boundaries_and_evidence_checked(self):
        resume = {'text': SAMPLE, 'parsed': parse_resume(SAMPLE)}
        question = {'text': '请介绍项目', 'answers': [{'text': ANSWER}], 'followup': '如何验证？'}
        dims = [{'key': key, 'score': 20, 'evidence': '不在用户回答中的证据', 'feedback': '请说明验证过程'}
                for key in ('structure','depth','expression','evidence')]
        with patch('studio.interview.call_json', return_value={'dimensions': dims, 'star': {'r': ['提升90%']}}):
            result = evaluate(resume, question, {'mode': 'online'})
        self.assertEqual(result['total'], 80)
        self.assertTrue(all(not d['evidence'] for d in result['dimensions']))
        self.assertNotIn('90%', result['optimized'])
        dims[0]['score'] = 30
        with patch('studio.interview.call_json', return_value={'dimensions': dims}):
            self.assertEqual(evaluate(resume, question, {'mode':'online'})['engine'], 'local_fallback')

    def test_bad_question_count_falls_back(self):
        resume = {'text': SAMPLE, 'parsed': parse_resume(SAMPLE)}
        with patch('studio.interview.call_json', return_value={'questions': [{'text':'标题'}]}):
            questions, engine, warning = generate_questions(resume, '后端', '', 6, '标准', [], {'mode':'online'})
        self.assertEqual(len(questions), 6)
        self.assertEqual(engine, 'local_fallback')
        self.assertTrue(warning)

    def test_key_encryption_and_redacted_settings(self):
        value = 'synthetic-test-key-not-real'
        encrypted = protect(value)
        self.assertNotIn(value, encrypted)
        self.assertEqual(protect(encrypted, decrypt=True), value)
        with tempfile.TemporaryDirectory() as root:
            settings = ModelSettings(Path(root))
            settings.update({'mode':'online', 'base_url':'https://example.com/v1', 'model':'test', 'api_key':value})
            self.assertNotIn(value, json.dumps(settings.public()))
            self.assertNotIn(value, settings.path.read_text())
            self.assertEqual(settings.snapshot()['api_key'], value)
            with self.assertRaises(ValueError):
                settings.update({'base_url':'http://remote.example.com'})


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root/'web').mkdir()
        (root/'web'/'index.html').write_text('<html>test</html>')
        cls.studio = Studio(root)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_factory(cls.studio))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def request(self, method, path, payload=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        body = json.dumps(payload).encode() if payload is not None else None
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        conn.close()
        return result

    def test_cookie_csrf_and_private_file_protection(self):
        status, headers, _ = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        cookie = headers['Set-Cookie'].split(';')[0]
        normal = {'Cookie': cookie, 'Content-Type':'application/json', 'X-Studio-Request':'1'}
        status, _, data = self.request('POST', '/api/resumes', {'text':SAMPLE}, normal)
        self.assertEqual(status, 200)
        item = json.loads(data)
        self.assertEqual(self.request('POST', '/api/resumes', {'text':SAMPLE}, {'Cookie':cookie,'Content-Type':'application/json'})[0], 403)
        self.assertEqual(self.request('POST', '/api/resumes', {'text':SAMPLE}, normal|{'Origin':'https://attacker.example'})[0], 403)
        self.assertEqual(self.request('GET', '/.env', headers={'Cookie':cookie})[0], 404)
        self.assertEqual(self.request('GET', '/api/resumes/'+item['id'], headers={'Cookie':cookie})[0], 200)
        self.assertEqual(self.request('GET', '/api/resumes/'+item['id'], headers={'Cookie':'studio_owner='+identifier()})[0], 404)


if __name__ == '__main__':
    unittest.main()
