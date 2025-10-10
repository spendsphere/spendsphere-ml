import os  # noqa: F401

from src.core.config import OLLAMA_API_URL  # noqa: F401
from src.services.ocr import query_ollama

if __name__ == "__main__":
    prompt = "Extract text from this sample receipt."
    response = query_ollama(prompt)
    print(response)
