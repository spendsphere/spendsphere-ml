# OCR and Categorization with Ollama

This module provides functions to:

1. Extract structured text from images (OCR)  
2. Categorize extracted items using a predefined list of categories  

Prompts and JSON schemas are separated into their own files for easy modification.

---

## 🚀 Example Usage

```python
# Path to image
image_path = "/path/to/receipt.jpg"

# List of allowed categories
categories = ["ЖКХ", "Кафе", "Продукты", "Одежда", "Подписки", "Прочее"]

# OCR extraction
ocr_result = extract_text_from_image(
    image_path=image_path,
    model="qwen2.5vl:3b",
    schema_path="schemas/ocr_schema.json",
    prompt_path="prompts/ocr_prompt.txt"
)

# Categorization
categorized_result = categorize_items(
    ocr_result=ocr_result,
    categories=categories,
    model="qwen3:0.6b",
    schema_path="schemas/categorize_schema.json",
    prompt_path="prompts/categorize_prompt.txt"
)

# categorized_result now contains OCR items with assigned categories
print(categorized_result)
```