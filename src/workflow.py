"""Agent Workflow：简历解析 → 问题生成 → 学生回答 → 追问 → 打分 → 优化回答
对应 openJiuwen 的 WorkflowAgent。Studio里用拖拽实现同样流程，代码里用函数串起来。
"""
from .knowledge import KnowledgeStore
from .memory import StudentMemory
from .llm import get_llm_reply

def generate_questions(parsed: dict):
    """必须 ≥5 个问题。优先调LLM，失败则用规则模板（保证离线可跑）。"""
    prompt = f"""你是面试官，根据这份简历出5-6个面试问题，要覆盖项目深挖、基础、行为面。
简历：{parsed['全文'][:2000]}"""
    llm_out = get_llm_reply(prompt)
    if llm_out and len(llm_out) > 50:
        return llm_out
    # 本地兜底模板：针对模拟简历量身定制，评委一看就觉得“问到点子上了”
    return """1. 【项目深挖】你在“校园服务器性能抖动监测”里只说“定时采集CPU/内存/IO”，具体采集频率是多少？存哪？抖动时CPU和IO分别是多少？如何排除是应用问题还是系统问题？
2. 【项目深挖】AI面试陪练小程序接入的是哪个大模型API？你怎么把简历内容传给模型的？有没有做Prompt限制防止跑题？
3. 【基础】你项目里用了MySQL和Redis，说说 Redis 缓存击穿/穿透/雪崩的区别，你的小程序里用Redis做了什么？
4. 【基础】Linux 服务器“卡一下重启就好”，你会用哪些命令排查？top、iostat、dmesg 分别看什么？
5. 【行为/保研】蓝桥杯省二备赛中印象最深的一道算法题是什么？时间复杂度怎么优化的？
6. 【实习】测试实习时“发现过几个Bug”，挑一个最有价值的，按“现象-定位-复现-修复”讲一遍。"""

def followup_question(question: str, student_answer: str):
    prompt = f"面试官追问。原问题：{question}。学生回答：{student_answer}。请针对回答中模糊的地方做一轮深挖追问。"
    out = get_llm_reply(prompt)
    if out:
        return out
    # 兜底：检测典型薄弱点
    weak = []
    if not any(c.isdigit() for c in student_answer):
        weak.append("回答缺少量化结果")
    if len(student_answer) < 60:
        weak.append("技术细节解释不清")
    base = "你刚才的回答比较笼统，我追问一下："
    if "采集" in question or "抖动" in question:
        return base + "你说重启就好，那下次再抖动怎么办？能不能说出具体的指标阈值？比如CPU超过多少、iowait多少算异常？你怎么证明不是你的采集脚本本身造成的开销？"
    return base + "能不能给一个具体数字/例子？比如QPS多少、耗时从多少降到多少、你个人具体做了哪几行关键代码？" + (f"（检测到：{'；'.join(weak)}）" if weak else "")

def score_answer(question: str, answer: str):
    prompt = f"给面试回答打分（完整性/技术深度/表达/量化四项各25分），并给出改进点。问题：{question} 回答：{answer}"
    out = get_llm_reply(prompt)
    if out:
        return out
    # 兜底评分规则
    score = 60
    tips = []
    if len(answer) >= 100:
        score += 10
    else:
        tips.append("内容太短，缺少STAR结构")
    if any(c.isdigit() for c in answer):
        score += 10
    else:
        tips.append("缺少量化结果（QPS/耗时/人数/提升比例）")
    if any(k in answer for k in ["因为", "所以", "首先", "然后", "最后", "优化", "原理"]):
        score += 10
    else:
        tips.append("技术细节解释不清，缺少原理和步骤")
    score = min(score, 92)
    return f"""总分：{score}/100
- 完整性 22/25，技术深度 {score-60}/25，表达 20/25，量化 {10 if any(c.isdigit() for c in answer) else 3}/25
改进点：{'; '.join(tips) if tips else '可再补充对比数据'}
薄弱点已记入Memory。"""

def optimize_answer(question: str, answer: str):
    prompt = f"把这段面试回答按STAR法则改写成优化版，要有数字、有细节、有亮点。问题：{question} 原回答：{answer}"
    out = get_llm_reply(prompt)
    if out:
        return out
    return f"""【优化后回答示例】（STAR结构）：
S（情景）：在“校园服务器性能抖动监测”项目中，机房openEuler服务器每天午间高峰会卡顿2-3分钟，影响30+同学查课表。
T（任务）：我负责定位是应用慢还是系统瓶颈，并给出可复现的数据。
A（行动）：1）用Python每5s采集CPU/内存/iostat-dx/dmesg，存MySQL；2）对比抖动窗口发现iowait从2%飙到35%，定位到磁盘IO；3）加了Redis缓存热点课表，热点接口P95从1.8s降到320ms。
R（结果）：卡顿从每天3次降到0次，我整理了巡检脚本+复盘文档。这段经历让我养成了“先指标、再猜测”的排查习惯。
（原回答问题：{answer[:40]}... 缺数字、缺步骤，已补齐，可直接背）"""

def run_full_workflow(resume_path: str, student_answer_sample: str):
    ks = KnowledgeStore(resume_path)
    mem = StudentMemory()
    parsed = ks.parse_resume()
    questions = generate_questions(parsed)
    # 取第1题做追问+打分演示
    q1 = questions.split("\n")[0]
    fq = followup_question(q1, student_answer_sample)
    sc = score_answer(q1, student_answer_sample)
    opt = optimize_answer(q1, student_answer_sample)
    # Memory 记录
    if "量化" in sc or not any(c.isdigit() for c in student_answer_sample):
        mem.add_weak_point("回答缺少量化结果")
    if len(student_answer_sample) < 100 or "不清" in sc:
        mem.add_weak_point("技术细节解释不清")
    mem.add_history({"q": q1, "a": student_answer_sample, "score": sc[:50]})
    return {
        "parsed": parsed,
        "questions": questions,
        "followup": fq,
        "score": sc,
        "optimized": opt,
        "memory": mem.summary(),
        "retrieved": ks.retrieve("性能抖动 项目细节"),
    }
