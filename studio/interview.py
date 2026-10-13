"""Stable question sets, grounded follow-ups and transparent evaluation."""
import re
from .models import ModelError, call_json
from .resumes import redact_contacts, retrieve
from .storage import identifier, now
from .knowledge import EvidenceIndex
from .agent import run_coach
from . import runtime

DIMENSIONS = [('structure', '回答完整性'), ('depth', '内容深度'),
              ('expression', '表达组织'), ('evidence', '事实与证据')]


def model_context(config, resume, **extra):
    query=' '.join(str(extra.get(k,'')) for k in ('role','job_description','question','answer'))[:4000]
    records=EvidenceIndex(resume['text'],config.get('_index_path')).search(query or '项目 技能 个人贡献',3)
    runtime.emit('stage',label='已检索简历证据')
    summary={k:resume['parsed'].get(k) for k in ('education','skills','projects')}
    summary['projects']=[{'title':p['title']} for p in resume['parsed'].get('projects',[])]
    if config.get('redact_contacts', True):
        extra = {k: redact_contacts(v) if isinstance(v, str) else v for k, v in extra.items()}
        records=[r | {'text':redact_contacts(r['text'])} for r in records]
    return {'resume_summary':summary,'resume_evidence':records,**extra,
            '_coach_context':{'resume':resume,'memory':extra.get('previous_weak_points',config.get('_memory',[]))}}


def request_json(config,task,payload,max_tokens=2200):
    context=payload.pop('_coach_context',None)
    if config.get('agent_enabled') and context:
        return run_coach(config,task,payload,context,max_tokens)
    return call_json(config,task,payload,max_tokens)


def notice(config, error=None):
    if config['mode'] == 'local':
        return '离线规则辅助：评分用于组织回答，不代表专业录用评价。'
    return f'在线模型暂不可用（{error}），本次使用离线规则辅助。' if error else ''


def local_questions(resume, role, jd, count, memory):
    parsed = resume['parsed']
    projects = parsed['projects']
    first = projects[0]['title'] if projects else '简历中你最熟悉的一段项目或实践经历'
    second = projects[1]['title'] if len(projects) > 1 else first
    skills = parsed['skills']
    skill = '、'.join(skills[:2]) if skills else '你在这段经历中使用的主要方法或工具'
    items = [
        ('项目深挖', f'请介绍「{first}」。当时要解决什么问题，你个人负责什么，最后如何验证结果？',
         '背景、个人贡献、验证结果', projects[0]['evidence'] if projects else resume['text'][:500]),
        ('方法与原理', f'你使用过{skill}，请结合一个实际任务解释：为什么选择它，关键原理是什么，有哪些局限？',
         '选型依据、原理、局限', '\n'.join(retrieve(resume['text'], skill, 1))),
        ('问题解决', f'在「{second}」中，你遇到过什么具体困难？如何定位原因、比较方案并验证改进？',
         '定位过程、方案取舍、验证方法', projects[1]['evidence'] if len(projects) > 1 else resume['text'][:500]),
        ('岗位匹配', f'面向「{role}」，你最有说服力的一项能力是什么？请用一段真实经历说明。' +
         ('请联系岗位要求中的关键职责。' if jd else ''), '能力与岗位要求的证据对应', '\n'.join(retrieve(resume['text'], role + jd, 1))),
        ('协作与反思', '请讲一次与他人协作或意见不同的经历。你如何沟通、推动行动，复盘时会改进什么？',
         '沟通行动、责任边界、反思', '\n'.join(retrieve(resume['text'], '协作 团队 沟通 实习', 1))),
        ('成果验证', '从简历中选择一个成果：它的原始基线、评估方法和结果是什么？没有统计数据时，你如何提供可核对的证据？',
         '真实基线、衡量方法、证据', '\n'.join(retrieve(resume['text'], '结果 提升 测试 用户', 1))),
        ('知识迁移', f'如果「{first}」的使用规模或任务难度提高，你会先检查什么，如何设计小规模验证？',
         '约束识别、迁移能力、验证设计', projects[0]['evidence'] if projects else resume['text'][:500]),
        ('学习能力', f'学习{skills[0] if skills else "一个新领域"}时，你如何验证自己真正理解了它？请给出一个学习后实际应用的例子。',
         '学习路径、应用验证', '\n'.join(retrieve(resume['text'], '学习 技能 课程 竞赛', 1))),
        ('动机与规划', f'你为什么选择「{role}」？目前有哪些能力差距，接下来四周会如何安排学习和实践？',
         '动机、差距、可执行计划', '\n'.join(retrieve(resume['text'], role, 1))),
        ('总结表达', '请用一分钟总结：你能带来什么价值，有什么真实证据，还有什么需要进一步学习？',
         '简洁总结、事实支撑、自我认知', resume['text'][:500]),
    ]
    if memory:
        category, text, objective, source = items[5]
        items[5] = (category, text + '这次请特别注意：' + memory[0]['label'] + '。', objective, source)
    if '保研' in role or '科研' in role:
        items[3] = ('研究潜力', '请结合一项课程、竞赛或研究实践，提出一个值得进一步研究的问题，并说明如何验证你的假设。',
                    '问题意识、假设、实验设计', '\n'.join(retrieve(resume['text'], '研究 课程 竞赛', 1)))
    return [{'id': identifier(), 'category': c, 'text': t, 'objective': o, 'source': s,
             'stage': 'initial', 'answers': [], 'followup': '', 'result': None, 'attempts': []}
            for c, t, o, s in items[:count]]


def generate_questions(resume, role, jd, count, difficulty, memory, config):
    fallback = local_questions(resume, role, jd, count, memory)
    if difficulty == '入门引导':
        fallback[0]['text'] += '可以按「背景—任务—行动—结果」逐步回答，每部分先说一句话。'
    elif difficulty == '深入挑战':
        fallback[0]['text'] += '请同时说明方案的约束、备选方案与仍未解决的局限。'
    if config['mode'] == 'local':
        return fallback, 'local', notice(config)
    task = ('根据简历与目标岗位生成指定数量的个性化中文面试题，覆盖项目、原理、行为、岗位匹配和成果验证。'
            '题目必须能由提供的经历支撑，不假设没有的经验。schema：'
            '{"questions":[{"category":"项目深挖","text":"一个具体问题",'
            '"objective":"考察要点","source":"简历中的逐字摘录"}]}。'
            'source 必须是简历的连续原文。不要生成报告标题，不要给出答案。')
    try:
        response = request_json(config, task, model_context(config, resume, role=role, job_description=jd,
                              count=count, difficulty=difficulty, previous_weak_points=memory), max_tokens=3200)
        items = response.get('questions')
        if not isinstance(items, list) or len(items) != count:
            raise ModelError('题目数量不符合要求')
        result = []
        for i, q in enumerate(items):
            if not isinstance(q, dict) or not isinstance(q.get('text'), str) or not 12 <= len(q['text']) <= 650:
                raise ModelError('题目格式不符合要求')
            source = str(q.get('source', ''))[:750]
            # Never invent a source quotation, including after contact redaction.
            if not source or source not in resume['text']:
                source = retrieve(resume['text'], q['text'], 1)[0]
            result.append(fallback[i] | {'category': str(q.get('category', '综合'))[:20],
                          'text': q['text'], 'objective': str(q.get('objective', ''))[:250], 'source': source,
                          'evidence':EvidenceIndex(resume['text'],config.get('_index_path')).search(q['text'],2),
                          'coach':response.get('_coach',{})})
        return result, 'online', ''
    except ModelError as e:
        return fallback, 'local_fallback', notice(config, e)


def followup(resume, question, answer, config):
    if config['mode'] == 'online':
        try:
            result = request_json(config, '针对学生当前回答，只提出一道最有价值的追问。'
                               '不要替学生回答，不要虚构。返回 {"followup":"追问", "focus":"追问关注点"}。',
                               model_context(config, resume, question=question['text'], answer=answer,
                                             evidence='\n'.join(retrieve(resume['text'], answer + question['text']))), 600)
            fq = result.get('followup', '')
            if not isinstance(fq, str) or not 8 <= len(fq) <= 900:
                raise ModelError('追问格式不符合要求')
            question['followup_coach']=result.get('_coach',{})
            return fq, 'online', ''
        except ModelError as e:
            warning = notice(config, e)
    else:
        warning = notice(config)
    if not re.search(r'我(?:负责|完成|设计|实现|提出|分析|组织)|我的(?:贡献|职责|任务)', answer):
        q = '你个人具体负责哪一部分？请选择一个你亲手完成的步骤，说明做法和判断依据。'
    elif not re.search(r'\d+(?:\.\d+)?\s*(?:%|ms|秒|分钟|小时|人|次|个|万|倍)|测试|验证|对比|反馈|验收|复现', answer, re.I):
        q = '你如何确认这个结果有效？有真实的测试、对比、反馈或可展示的产出吗？没有统计数字也可以说明验证方法。'
    else:
        q = '当时有没有比较过其他方案？你做出这个选择的关键约束是什么，方案在哪些情况下会失效？'
    return q, 'local' if config['mode'] == 'local' else 'local_fallback', warning


def sentences(answer):
    return [s.strip() for s in re.split(r'[。！？\n]+', answer) if s.strip()]


def safe_star(answer, proposed=None):
    """Only rearrange exact answer excerpts; missing facts stay as placeholders."""
    labels = [('s', 'S · 背景', '真实场景、对象及当时的问题'),
              ('t', 'T · 任务', '你个人的职责和目标'),
              ('a', 'A · 行动', '关键步骤、选择依据及验证过程'),
              ('r', 'R · 结果', '实际结果和可核对的证据；没有数据请说明事实')]
    parts = sentences(answer)
    patterns = {'s': r'背景|当时|项目中|期间|场景|遇到|问题是',
                't': r'我负责|我的任务|目标|职责|需要',
                'a': r'首先|然后|通过|采用|实现|使用|编写|分析|设计|对比|因为|测试',
                'r': r'最终|结果|反馈|提升|降低|减少|成功|验证|完成|达到'}
    chosen, used = {}, set()
    if isinstance(proposed, dict):
        for key, _, _ in labels:
            raw = proposed.get(key, [])
            if isinstance(raw, str):
                raw = [raw]
            if isinstance(raw, list):
                accepted = [x.strip() for x in raw if isinstance(x, str) and len(x.strip()) >= 4
                            and x.strip() in answer and len(x) <= 1600]
                if accepted:
                    chosen[key] = '；'.join(accepted[:3])
                    used.update(accepted)
    for key, _, _ in labels:
        if key not in chosen:
            matching = [s for s in parts if s not in used and re.search(patterns[key], s)]
            if matching:
                chosen[key] = '；'.join(matching[:2])
                used.update(matching[:2])
    if 'a' not in chosen and parts:
        chosen['a'] = '；'.join([s for s in parts if s not in used][:3] or parts[:2])
    missing = [hint for key, _, hint in labels if key not in chosen]
    text = '\n\n'.join(label + '\n' + chosen.get(key, f'【待补充：{hint}】') for key, label, hint in labels)
    return text, missing


def local_evaluate(question, answer):
    parts = sentences(answer)
    has_background = bool(re.search(r'背景|当时|项目|场景|期间|问题', answer))
    has_ownership = bool(re.search(r'我负责|我完成|我设计|我实现|我的任务|我提出|我分析|我组织', answer))
    has_result = bool(re.search(r'结果|最终|完成|反馈|提升|降低|减少|验证|产出', answer))
    reasoning = len(re.findall(r'因为|所以|原因|原理|对比|选择|约束|权衡|代价|局限|测试|验证|复现', answer))
    structured = len(re.findall(r'首先|其次|然后|最后|第一|第二|背景|任务|行动|结果', answer))
    metric = re.search(r'\d+(?:\.\d+)?\s*(?:%|ms|秒|分钟|小时|人|次|个|万|倍|QPS)', answer, re.I)
    verified = bool(re.search(r'测试|验证|对比|反馈|验收|复现|报告|日志|截图|文档', answer))
    if not answer.strip():
        scores = [0, 0, 0, 0]
    else:
        scores = [min(25, 4 + 5*has_background + 5*has_ownership + 5*has_result + (4 if len(answer) >= 120 else 0)),
                  min(25, 4 + min(reasoning, 5)*3 + (4 if len(answer) >= 160 else 0)),
                  min(25, 5 + min(structured, 4)*3 + (4 if 2 <= len(parts) <= 12 else 0) + (3 if 70 <= len(answer) <= 1200 else 0)),
                  min(25, 3 + 7*bool(metric) + 7*verified + 4*has_result + (4 if metric and verified else 0))]
    hints = ['交代场景、个人职责、行动和结果。', '解释为什么这么做，以及如何验证；必要时比较备选方案。',
             '先给结论，再按两到三个步骤展开，避免只说“效果还行”。', '提供真实数据或可核对的测试、反馈、文档；不要补造数字。']
    dimensions = []
    for (key, label), score, hint in zip(DIMENSIONS, scores, hints):
        patterns = {'structure': r'我负责|背景|结果|任务', 'depth': r'因为|原理|对比|选择|验证|测试',
                    'expression': r'首先|然后|最后|第一|结果', 'evidence': r'\d|验证|测试|反馈|日志'}
        evidence = next((p for p in parts if re.search(patterns[key], p)), '')
        dimensions.append({'key': key, 'label': label, 'score': score, 'max': 25,
                           'evidence': evidence[:600], 'feedback': hint})
    optimized, missing = safe_star(answer)
    return {'dimensions': dimensions, 'total': sum(scores), 'engine': 'local',
            'suggestions': [d['feedback'] for d in dimensions if d['score'] < 17] or ['保留真实证据，练习在两分钟内讲清重点。'],
            'optimized': optimized, 'missing_facts': missing, 'evaluated_at': now(),
            'notice': '离线规则评分基于回答结构与证据线索，不能判断所有技术结论是否正确。'}


def evaluate(resume, question, config):
    answer = '\n'.join(a['text'] for a in question['answers'])
    fallback = local_evaluate(question, answer)
    if config['mode'] != 'online':
        return fallback
    task = ('评估学生对当前问题的回答及追问补充。四项各 0-25 整数分，依据事实、岗位和内容质量评分，'
            '不得仅因字数或没有数字就判差。证据必须逐字摘自回答。'
            'schema: {"dimensions":[{"key":"structure|depth|expression|evidence",'
            '"score":0,"evidence":"回答原文摘录或空字符串","feedback":"具体建议"}],'
            '"suggestions":["建议"],"star":{"s":["回答原文摘录"],"t":[],"a":[],"r":[]}}。'
            '四个 key 每项出现一次。star 只允许重新组织回答的连续原文摘录，缺少信息用空数组，禁止写新事实。')
    try:
        output = request_json(config, task, model_context(config, resume, question=question['text'],
                           followup=question['followup'], answer=answer,
                           relevant_resume_evidence='\n'.join(retrieve(resume['text'], question['text'] + answer))), 2600)
        dims = output.get('dimensions')
        if (not isinstance(dims, list) or len(dims) != 4 or
            not all(isinstance(d, dict) and isinstance(d.get('key'), str) for d in dims) or
            {d.get('key') for d in dims} != {k for k, _ in DIMENSIONS}):
            raise ModelError('评分维度不完整')
        by_key = {d['key']: d for d in dims}
        dimensions = []
        for key, label in DIMENSIONS:
            d = by_key[key]
            score = d.get('score')
            if type(score) is not int or not 0 <= score <= 25:
                raise ModelError('分项分数超出范围')
            evidence = str(d.get('evidence', ''))[:1000]
            if evidence and evidence not in answer:
                evidence = ''
            dimensions.append({'key': key, 'label': label, 'score': score, 'max': 25,
                               'evidence': evidence, 'feedback': str(d.get('feedback', '请补充真实事实。'))[:800]})
        optimized, missing = safe_star(answer, output.get('star'))
        suggestions = output.get('suggestions', [])
        if not isinstance(suggestions, list):
            suggestions = []
        return {'dimensions': dimensions, 'total': sum(d['score'] for d in dimensions), 'engine': 'online',
                'suggestions': [str(s)[:700] for s in suggestions[:5]], 'optimized': optimized,
                'missing_facts': missing, 'evaluated_at': now(),
                'coach':output.get('_coach',{}),'metrics':runtime.metrics(),
                'notice': 'AI 辅助评价，供练习参考。STAR 整理仅使用你的回答原文，缺失事实保留待补充标记。'}
    except ModelError as e:
        fallback.update(engine='local_fallback', notice=notice(config, e) + ' ' + fallback['notice'])
        return fallback


def report_markdown(session):
    results = [q['result'] for q in session['questions'] if q.get('result')]
    average = round(sum(r['total'] for r in results)/len(results), 1) if results else None
    lines = ['# 面试工坊 · 练习报告', '', f'目标岗位：{session["role"]}',
             f'简历：{session["resume_name"]}', f'创建时间：{session["created_at"]}',
             f'已评分：{len(results)}/{len(session["questions"])}',
             f'平均分：{average if average is not None else "暂无"}/100', '',
             '> 分数为辅助练习评价，不代表录用结论；不同模型或模式的分数不可直接等同。', '']
    for i, q in enumerate(session['questions'], 1):
        lines.extend([f'## 第 {i} 题 · {q["category"]}', '', q['text'], '', '### 回答', ''])
        lines.extend([a['text'] + '\n' for a in q['answers']] or ['尚未作答'])
        if q['followup']:
            lines.extend(['### 追问', '', q['followup'], ''])
        if q.get('result'):
            r = q['result']
            lines.extend([f'### 评分：{r["total"]}/100', '', f'评价引擎：{r["engine"]}', ''])
            for d in r['dimensions']:
                lines.extend([f'- {d["label"]}：{d["score"]}/25。{d["feedback"]}',
                              f'  回答证据：{d["evidence"] or "未找到可引用的直接证据"}'])
            lines.extend(['', '### STAR 整理', '', r['optimized'], '', '### 下一步改进', ''])
            lines.extend('- ' + s for s in r['suggestions'])
            lines.extend(['', r['notice'], ''])
    lines.extend(['## 下次练习计划', '', '1. 补齐待确认事实和真实证据。',
                  '2. 对得分较低的维度重新作答，并核对教师或同行的反馈。', '3. 在相近岗位、相同模型和评分模式下比较进步。', ''])
    return '\n'.join(lines)
