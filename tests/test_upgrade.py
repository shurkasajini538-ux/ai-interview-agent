import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from app import Studio
from studio.agent import run_coach
from studio.jobs import Jobs
from studio.knowledge import EvidenceIndex,chunks
from studio.models import ModelSettings,ModelError,preview_text
from studio.runtime import Operation,operation_context,commit,Cancelled
from studio.resumes import parse_resume

TEXT='姓名：模拟同学\n项目经历：校园活动报名平台\n我负责 Python 和 MySQL 接口，通过唯一约束防止重复报名。\n'+('课程经历：学习数据库与计算机网络，完成课程复盘。\n'*20)+'项目经历：数据分析工具\n使用 Excel 和 Python 分析活动统计。'


class KnowledgeTests(unittest.TestCase):
    def test_source_offsets_and_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'index.sqlite3'
            first=EvidenceIndex(TEXT,path)
            second=EvidenceIndex(TEXT,path)
            self.assertEqual(first.search('MySQL 唯一约束'),second.search('MySQL 唯一约束'))
            for r in first.records:
                self.assertEqual(TEXT[r['start']:r['end']],r['text'])
                self.assertEqual(first.resolve(r['id']),r)
            self.assertIn('唯一约束',first.search('MySQL 重复报名',1)[0]['text'])

    def test_limits_and_no_overlap_claim_when_unmatched(self):
        index=EvidenceIndex(TEXT)
        self.assertLessEqual(len(index.search('无关xyz',99)),5)
        self.assertTrue(all(not r['matched'] for r in index.search('zzzzunrelated')))
        self.assertTrue(all(r['text'] for r in chunks(TEXT)))


class ConfigTests(unittest.TestCase):
    def test_environment_precedence_and_no_key_saved(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            (path/'.env').write_text('LLM_API_KEY=file-synthetic\nLLM_MODEL=file-model\nLLM_MODE=online',encoding='utf-8')
            with patch.dict(os.environ,{'LLM_MODEL':'process-model','LLM_API_KEY':'process-synthetic'}):
                settings=ModelSettings(path)
                self.assertEqual(settings.snapshot()['model'],'process-model')
                self.assertEqual(settings.snapshot()['api_key'],'process-synthetic')
                self.assertNotIn('process-synthetic',json.dumps(settings.public()))
                self.assertFalse(settings.path.exists())
                with self.assertRaises(ValueError):
                    settings.update({'model':'changed'})

    def test_stream_preview_handles_partial_json_and_escape(self):
        self.assertEqual(preview_text('{"followup":"你如何验证'), '你如何验证')
        self.assertEqual(preview_text('{"feedback":"第一行\\n第二行'), '第一行\n第二行')


class AgentTests(unittest.TestCase):
    def test_real_tool_dispatch_grounded_output_and_trace(self):
        message={'content':None,'tool_calls':[
            {'id':'a','function':{'name':'search_resume','arguments':'{"query":"MySQL唯一约束","limit":2}'}},
            {'id':'b','function':{'name':'read_weak_points','arguments':'{}'}},
            {'id':'c','function':{'name':'record_fact_gap','arguments':'{"fact":"实际并发规模","reason":"回答未提供"}'}}]}
        with patch('studio.agent.call_chat',side_effect=[message,{'content':'{"ready":true}'}]),patch('studio.agent.call_json',return_value={'followup':'请说明真实验证步骤。'}) as final:
            result=run_coach({'mode':'online'},'追问',{'answer':'使用唯一约束'},
                             {'resume':{'text':TEXT,'parsed':parse_resume(TEXT)},'memory':[{'label':'技术依据'}]})
        self.assertEqual(result['_coach']['tool_calls'],3)
        self.assertEqual(len(result['_coach']['fact_gaps']),1)
        payload=final.call_args.args[2]
        self.assertEqual(len(payload['tool_results']),3)
        self.assertNotIn('课程经历：学习数据库与计算机网络，完成课程复盘。\n'*10,json.dumps(payload,ensure_ascii=False))

    def test_unauthorized_tool_never_executes(self):
        bad={'tool_calls':[{'id':'x','function':{'name':'shell','arguments':'{"cmd":"something"}'}}]}
        with patch('studio.agent.call_chat',return_value=bad),patch('studio.agent.call_json',return_value={'ok':True}):
            result=run_coach({'mode':'online'},'评估',{}, {'resume':{'text':TEXT,'parsed':parse_resume(TEXT)}})
        self.assertEqual(result['_coach']['tool_calls'],0)
        self.assertEqual(result['_coach']['trace'][0]['tool'],'fallback')


class JobTests(unittest.TestCase):
    def wait(self,jobs,job_id,owner):
        for _ in range(100):
            result=jobs.public(jobs.get(job_id,owner))
            if result['state'] in ('done','failed','cancelled'):
                return result
            time.sleep(.01)
        self.fail('job timeout')

    def test_idempotency_and_owner_isolation(self):
        jobs=Jobs()
        job=jobs.create('owner','once',{'kind':'test'},lambda:commit(lambda:{'ok':True}))
        again=jobs.create('owner','once',{'kind':'test'},lambda:self.fail('must not run twice'))
        self.assertEqual(job['id'],again['id'])
        self.assertEqual(self.wait(jobs,job['id'],'owner')['state'],'done')
        with self.assertRaises(KeyError):jobs.get(job['id'],'other')
        with self.assertRaises(ValueError):jobs.create('owner','once',{'kind':'different'},lambda:None)

    def test_cancel_prevents_commit_and_keeps_saved_answers(self):
        jobs=Jobs();started=threading.Event();release=threading.Event();writes=[]
        def task():
            started.set();release.wait(2)
            return commit(lambda:writes.append('saved'))
        job=jobs.create('owner','cancel',{},task);started.wait(1)
        self.assertTrue(jobs.cancel(job['id'],'owner')['cancel_accepted'])
        release.set()
        self.assertEqual(self.wait(jobs,job['id'],'owner')['state'],'cancelled')
        self.assertEqual(writes,[])

    def test_commit_is_atomic_against_cancel(self):
        op=Operation()
        with operation_context(op):
            self.assertEqual(commit(lambda:42),42)
            op.cancelled.set()
            op.check()
        self.assertTrue(op.committed)


if __name__=='__main__':unittest.main()
