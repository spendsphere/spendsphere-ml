import os
from src.core.config import OLLAMA_API_URL
from src.services.ocr import query_ollama

if __name__ == "__main__":
    prompt = "Extract text from this sample receipt."
    response = query_ollama(prompt)
    print(response)
