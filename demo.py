"""一键Demo：满足命题7个硬指标，直接运行录屏就能交。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.agent import InterviewAgent

RESUME = Path(__file__).resolve().parent / "config" / "resume_sample.md"
# 模拟一个“典型的没准备好的学生回答”，故意留毛病，方便展示追问+打分+优化
STUDENT_ANSWER = "我那个监测小工具就是写了个脚本采集CPU内存，发现卡了就重启，效果还行。"

def main():
    agent = InterviewAgent(str(RESUME))
    r = agent.run(STUDENT_ANSWER)
    print("="*60)
    print("【1.简历片段输入】见 config/resume_sample.md")
    print(r["parsed"]["项目经历"][:300] + "...\n")
    print("【2.生成至少5个面试问题】")
    print(r["questions"] + "\n")
    print("【3.追问过程】")
    print("学生答：" + STUDENT_ANSWER)
    print("追问：" + r["followup"] + "\n")
    print("【4.评分结果】")
    print(r["score"] + "\n")
    print("【5.优化后的回答】")
    print(r["optimized"] + "\n")
    print("【6.工作流图】见 docs/workflow.mmd，节点：" + "→".join(r["nodes"]))
    print("【7.引擎】" + r["engine"])
    print(f"【Memory】薄弱点：{r['memory']}")
    # 落盘，方便贴进PPT
    out = Path(__file__).resolve().parent / "output" / "demo_result.txt"
    out.write_text(
        f"问题:\n{r['questions']}\n\n追问:\n{r['followup']}\n\n评分:\n{r['score']}\n\n优化:\n{r['optimized']}\n\nMemory:{r['memory']}\n",
        encoding="utf-8")
    print(f"\n已保存到 {out}")

if __name__ == "__main__":
    main()
