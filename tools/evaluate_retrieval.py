"""Reproducible synthetic retrieval benchmark; no student data or API cost."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio.knowledge import EvidenceIndex
from studio.resumes import retrieve

root=Path(__file__).resolve().parents[1]
topics=[
 ('MySQL 重复报名','并发报名唯一约束方案','我负责 MySQL 数据表，使用唯一约束防止重复报名，通过并发测试验证。'),
 ('Redis 缓存过期','热点数据过期策略','我负责 Redis 缓存，设置过期策略并核对缓存失效后的数据一致性。'),
 ('Python 采集日志','故障日志采集流程','我负责 Python 指标采集，将故障日志与时间窗口对照定位采集异常。'),
 ('Flask 参数校验','注册接口校验清单','我负责 Flask 注册接口，校验参数缺失、格式错误并记录失败响应。'),
 ('React 列表渲染','列表键值复用检查','我负责 React 列表渲染，用稳定键值减少错误复用，并检查更新行为。'),
 ('Git 冲突协作','分支冲突沟通记录','我负责 Git 分支协作，先沟通修改意图，再解决冲突并复查测试。'),
]
text='模拟简历评测资料。以下内容为自制测试样本，不代表真实学生经历。\n'
for i,(_,marker,body) in enumerate(topics):
    text+=f'\n项目{i+1}：{marker}\n{body}\n'+('课程补充材料：明确任务、整理文档、参与小组讨论、核对实际结果。\n'*14)
index=EvidenceIndex(text)
cases=[]
for query,marker,_ in topics:
    for suffix in ('',' 请说明个人贡献和验证方法'):
        cases.append({'query':query+suffix,'expected_marker':marker})
rows=[]
for strategy in ('legacy-character','keyword','vector','hybrid'):
    hits1=hits3=0
    started=time.perf_counter()
    details=[]
    for case in cases:
        if strategy=='legacy-character':
            results=retrieve(text,case['query'],3)
        else:
            records=index.search(case['query'],3,strategy)
            assert all(text[r['start']:r['end']]==r['text'] for r in records)
            results=[r['text'] for r in records]
        h1=bool(results and case['expected_marker'] in results[0])
        h3=any(case['expected_marker'] in r for r in results)
        hits1+=h1;hits3+=h3
        details.append(case|{'hit_at_1':h1,'hit_at_3':h3})
    rows.append({'strategy':strategy,'cases':len(cases),'hit_at_1':hits1/len(cases),'hit_at_3':hits3/len(cases),
                 'total_ms':round((time.perf_counter()-started)*1000,2),'details':details})
out={'dataset':'self-authored synthetic resume, 6 project passages / 12 queries',
     'limitations':'Small synthetic retrieval benchmark only. Not a human study or proof of better coaching outcomes. TF-IDF vectors are not neural semantic embeddings.',
     'results':rows}
(root/'verification'/'retrieval-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='details'} for r in rows],ensure_ascii=False))
