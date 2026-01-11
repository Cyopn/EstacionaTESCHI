import os
import ollama

MODEL = os.environ.get("LLM_MODEL", "llama3.1:8b")


def generate_llm_reply(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    resp = ollama.chat(
        model=model or MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": 0.3, "num_predict": 220},
    )
    return resp["message"]["content"].strip()
