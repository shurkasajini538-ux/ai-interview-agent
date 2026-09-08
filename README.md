# AI面试陪练 Agent（基于 openJiuwen）

## 一句话
读取简历 → 自动出题 → 追问 → 打分 → 给优化版，帮本科生准备求职/保研面试。

## 快速跑
```bash
pip install -r requirements.txt
python demo.py
streamlit run app.py
```

## 对应命题要求
- Knowledge：`src/knowledge.py` 存简历+项目材料，Studio里再配RAG知识库
- Workflow：`src/workflow.py` 六步：简历解析→问题生成→学生回答→追问→打分→优化回答，工作流图见 `docs/workflow.mmd`
- Memory：`src/memory.py` 记薄弱点（缺少量化结果/技术细节不清），存在 `output/memory.json`
- 7个硬指标：跑 `python demo.py` 一次全展示，结果存 `output/demo_result.txt`

## 普通大模型 vs openJiuwen Agent
| | 普通大模型 | openJiuwen Agent |
|---|---|---|
| 记忆 | 单轮，问完就忘 | Knowledge+RAG记住简历，Memory记住薄弱点 |
| 流程 | 你问一句答一句 | Workflow强制走6步，可追问、可打断恢复 |
| 提问 | 通用八股 | 基于个人项目持续深挖 |
| 输出 | 只给建议 | 打分+STAR优化版，直接能背 |
| 可观测 | 黑盒 | Studio全链路日志 rostlin |
