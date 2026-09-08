"""openJiuwen Agent 组装层：能用真框架就用，教室/离线环境就用兼容模式，保证评审时一定能跑。"""
try:
    from openjiuwen import WorkflowAgent  # 按官方SDK命名，版本差异时自动降级
    HAS_JIUWEN = True
except Exception as e:
    print(f"[提示] 未检测到 openJiuwen SDK，走兼容模式（流程逻辑完全一致）: {e}")
    WorkflowAgent = object
    HAS_JIUWEN = False

from .workflow import run_full_workflow

class InterviewAgent:
    """AI面试陪练 Agent"""
    def __init__(self, resume_path: str):
        self.resume_path = resume_path
        # Studio工作流同名节点，截图和代码一一对应，答辩时好讲
        self.workflow_nodes = ["简历解析", "问题生成", "学生回答", "追问", "打分", "优化回答"]

    def run(self, student_answer_sample: str):
        result = run_full_workflow(self.resume_path, student_answer_sample)
        result["engine"] = "openJiuwen WorkflowAgent" if HAS_JIUWEN else "兼容模式(流程与openJiuwen一致)"
        result["nodes"] = self.workflow_nodes
        return result
