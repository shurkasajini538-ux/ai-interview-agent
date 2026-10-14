"""Opt-in end-to-end model smoke test, using synthetic data only."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.models import ModelSettings
from studio.resumes import parse_resume
from studio.interview import generate_questions, followup, evaluate
from studio.storage import now
from studio import runtime

root = Path(__file__).resolve().parents[1]
runtime.CURRENT.set(runtime.Operation())
config = ModelSettings(root).snapshot()
text = '姓名：测试同学\n教育背景：示例大学 计算机科学 本科\n项目经历：图书借阅平台\n我负责 Python、Flask 接口设计和 MySQL 数据表，通过12个测试用例验证借阅流程。'
resume = {'text':text, 'parsed':parse_resume(text)}
result = {'date':now(), 'model':config['model'], 'mode':config['mode']}
print('Testing question generation with synthetic resume...', flush=True)
questions, engine, warning = generate_questions(resume, '后端实习生', '', 6, '标准', [], config)
result.update(question_engine=engine, question_count=len(questions), question_notice=warning)
result['generation_tool_calls']=questions[0].get('coach',{}).get('tool_calls',0)
if engine == 'online':
    answer = '在图书借阅平台中，我负责 Python 接口和 MySQL 表设计。因为重复点击可能产生重复记录，所以使用数据库唯一约束，并通过12个测试用例检查参数校验和重复借阅。'
    print('Testing targeted follow-up...', flush=True)
    q = questions[0]
    fq, fe, fw = followup(resume, q, answer, config)
    q.update(followup=fq, answers=[{'text':answer}])
    print('Testing grounded evaluation...', flush=True)
    evaluation = evaluate(resume, q, config)
    result.update(followup_engine=fe, followup_notice=fw, evaluation_engine=evaluation['engine'],
                  evaluation_notice=evaluation['notice'], total=evaluation['total'],
                  total_is_sum=evaluation['total']==sum(d['score'] for d in evaluation['dimensions']),
                  no_invented_numeric_claims='99%' not in evaluation['optimized'],
                  evidence_valid=all(not d['evidence'] or d['evidence'] in answer for d in evaluation['dimensions']))
    result['passed'] = fe == evaluation['engine'] == 'online' and result['total_is_sum'] and result['evidence_valid']
    result['evaluation_tool_calls']=evaluation.get('coach',{}).get('tool_calls',0)
    result['followup_tool_calls']=q.get('followup_coach',{}).get('tool_calls',0)
    result['metrics']=runtime.metrics()
    result['stream_events']=sum(e['kind']=='generation' for e in runtime.CURRENT.get().events)
else:
    result['passed'] = False
(root/'verification'/'live-model-v2-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False), flush=True)
raise SystemExit(0 if result['passed'] else 1)
