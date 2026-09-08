"""Knowledge 模块：对应 openJiuwen 的 Knowledge / RAG。
初赛简化实现：文件存储 + 关键词检索，Studio里再配真正的知识库。"""
import re
from pathlib import Path

class KnowledgeStore:
    def __init__(self, resume_path: str):
        self.resume_path = Path(resume_path)
        self.text = self.resume_path.read_text(encoding="utf-8")
        self.chunks = self._split()

    def _split(self):
        # 按二级标题切块，模拟 RAG 切片
        parts = re.split(r"\n## ", self.text)
        return [p.strip() for p in parts if p.strip()]

    def retrieve(self, query: str, top_k: int = 3):
        """极简检索：按关键词重合度排序，演示用足够了。"""
        scores = []
        for c in self.chunks:
            s = sum(1 for w in set(query) if w in c)
            scores.append((s, c))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scores[:top_k]]

    def parse_resume(self):
        """简历解析：提取教育、项目、技能、成果亮点"""
        text = self.text
        def find(sec):
            m = re.search(sec + r"([\s\S]*?)(?=\n## |\Z)", text)
            return m.group(1).strip() if m else ""
        return {
            "教育背景": find("## 教育背景"),
            "项目经历": find("## 项目经历1") + "\n" + find("## 项目经历2"),
            "竞赛实习": find("## 竞赛经历") + "\n" + find("## 实习经历"),
            "技能点": find("## 技能点"),
            "全文": text,
        }
