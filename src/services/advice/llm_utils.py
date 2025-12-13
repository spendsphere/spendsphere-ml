import json
from pathlib import Path
import requests

OLLAMA_API_URL = "http://ollama:11434"


def load_json(path: str) -> dict:
    """Load JSON file from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_prompt(path: str) -> str:
    """Load prompt text from disk."""
    return Path(path).read_text(encoding="utf-8").strip()


def generate_advice(
        goal: dict,
        monthly_stats: dict,
        model: str,
        schema_path: str,
        prompt_path: str
) -> dict:
    """
    Generate 3-6 actionable financial advice items for the given goal and monthly statistics.
    Returns a dict matching the advice schema.
    """
    url = f"{OLLAMA_API_URL}/api/chat"

    # Загружаем схему и промпт
    schema = load_json(schema_path)
    prompt = load_prompt(prompt_path)

    # Контекст для модели
    input_context = {
        "goal": goal,
        "monthly_stats": monthly_stats
    }

    messages = [
        {"role": "system", "content": "Вы финансовый помощник."},
        {
            "role": "user",
            "content": f"{prompt}\n\nКонтекст:\n{json.dumps(input_context, ensure_ascii=False, indent=2)}"
        }
    ]

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": schema
    }

    resp = requests.post(url, json=payload)
    resp.raise_for_status()

    content_str = resp.json()["message"]["content"]
    advice_result = json.loads(content_str)

    # Проверка, что есть ключ 'advice'
    if "advice" not in advice_result:
        raise ValueError("LLM не вернула поле 'advice'")

    return advice_result
