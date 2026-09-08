"""Memory 模块：对应 openJiuwen agent-memory。
记录学生薄弱点，如“缺少量化结果”“技术细节不清”，跨轮次记住。"""
import json
from pathlib import Path

MEM_PATH = Path(__file__).resolve().parent.parent / "output" / "memory.json"

class StudentMemory:
    def __init__(self):
        self.data = {"weak_points": [], "history": []}
        if MEM_PATH.exists():
            try:
                self.data = json.loads(MEM_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass

    def add_weak_point(self, point: str):
        if point not in self.data["weak_points"]:
            self.data["weak_points"].append(point)
        self.save()

    def add_history(self, record: dict):
        self.data["history"].append(record)
        self.save()

    def save(self):
        MEM_PATH.parent.mkdir(parents=True, exist_ok=True)
        MEM_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def summary(self):
        if not self.data["weak_points"]:
            return "暂无明显薄弱点"
        return "；".join(self.data["weak_points"])
