import requests

from src.core.config import OLLAMA_API_URL


def query_ollama(prompt: str, model: str = "llava-mini") -> dict:
    url = f"{OLLAMA_API_URL}/prompt"
    payload = {"model": model, "prompt": prompt}
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()
