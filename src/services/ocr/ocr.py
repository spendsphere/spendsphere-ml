import base64
import json
import requests
from pathlib import Path

OLLAMA_API_URL = "http://localhost:11434"


def load_json(path: str) -> dict:
    """Load JSON file from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_prompt(path: str) -> str:
    """Load prompt text from disk."""
    return Path(path).read_text(encoding="utf-8").strip()


def extract_text_from_image(
    image_path: str, model: str, schema_path: str, prompt_path: str
) -> dict:
    """
    Extract structured text (Name, Price, Description) from an image using Ollama multimodal model.
    Returns a Python dict.
    """
    url = f"{OLLAMA_API_URL}/api/chat"

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    schema = load_json(schema_path)
    prompt = load_prompt(prompt_path)

    messages = [{"role": "user", "content": prompt, "images": [image_b64]}]

    payload = {"model": model, "messages": messages, "stream": False, "format": schema}

    resp = requests.post(url, json=payload)
    resp.raise_for_status()

    content_str = resp.json()["message"]["content"]
    return json.loads(content_str)


def categorize_items(
    ocr_result: dict,
    categories: list[str],
    model: str,
    schema_path: str,
    prompt_path: str,
) -> dict:
    """
    Assign a category from the provided list to each OCR item using Ollama.
    Returns a Python dict with 'Category' field added.
    """
    url = f"{OLLAMA_API_URL}/api/chat"

    schema = load_json(schema_path)

    # Inject allowed categories into enum
    if "items" in schema["properties"]:
        item_props = schema["properties"]["items"]["items"]["properties"]
        if "Category" in item_props:
            item_props["Category"]["enum"] = categories

    prompt = load_prompt(prompt_path)

    messages = [
        {"role": "system", "content": "You are a categorization assistant."},
        {
            "role": "user",
            "content": f"{prompt}\n\nAvailable categories: "
            f"{categories}\n\n"
            f"Items:\n{json.dumps(ocr_result, indent=2, ensure_ascii=False)}",
        },
    ]

    payload = {"model": model, "messages": messages, "stream": False, "format": schema}

    resp = requests.post(url, json=payload)
    resp.raise_for_status()

    content_str = resp.json()["message"]["content"]
    return json.loads(content_str)
