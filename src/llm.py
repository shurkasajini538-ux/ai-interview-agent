"""LLM 适配层：有 Key 就调大模型，没 Key 就用本地模板兜底，保证初赛一定能跑。"""
import os

def get_llm_reply(prompt: str) -> str:
    # 预留：AtomCode / DeepSeek / OpenAI 兼容接口
    # 只要设置了 LLM_API_KEY + LLM_BASE_URL + LLM_MODEL 就会尝试调用，否则走兜底
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        )
        model = os.getenv("LLM_MODEL", "deepseek-chat")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM调用失败，走本地模板兜底: {e}]")
        return ""
