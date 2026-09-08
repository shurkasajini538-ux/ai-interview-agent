"""Streamlit 演示页：录屏用，左边贴简历，右边模拟面试。运行: streamlit run app.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import streamlit as st
from src.agent import InterviewAgent

st.set_page_config(page_title="AI面试陪练Agent - openJiuwen", layout="wide")
st.title("AI面试陪练 Agent（基于 openJiuwen）")

resume_path = Path(__file__).resolve().parent / "config" / "resume_sample.md"
default_resume = resume_path.read_text(encoding="utf-8")

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. 简历输入（Knowledge）")
    resume_text = st.text_area("粘贴简历", default_resume, height=400)
    if st.button("解析并生成问题"):
        tmp = Path("output/_tmp_resume.md")
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_text(resume_text, encoding="utf-8")
        st.session_state["resume_tmp"] = str(tmp)
        agent = InterviewAgent(str(tmp))
        # 先存解析结果
        from src.workflow import generate_questions
        from src.knowledge import KnowledgeStore
        ks = KnowledgeStore(str(tmp))
        st.session_state["questions"] = generate_questions(ks.parse_resume())
        st.success("已生成面试问题！看右侧")
with col2:
    st.subheader("2. 模拟面试")
    qs = st.session_state.get("questions", "先点左侧按钮生成问题")
    st.text_area("面试官问题（≥5个）", qs, height=250)
    ans = st.text_area("你的回答", "我那个监测小工具就是写了个脚本采集CPU内存，发现卡了就重启，效果还行。", height=100)
    if st.button("追问+打分+优化"):
        rp = st.session_state.get("resume_tmp", str(resume_path))
        agent = InterviewAgent(rp)
        r = agent.run(ans)
        st.markdown("**追问**")
        st.write(r["followup"])
        st.markdown("**评分**")
        st.write(r["score"])
        st.markdown("**优化后回答（直接背）**")
        st.write(r["optimized"])
        st.info(f"Memory记住的薄弱点：{r['memory']} | 引擎：{r['engine']}")
