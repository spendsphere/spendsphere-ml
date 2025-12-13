import json
import os
import pika
import tempfile
from pathlib import Path
from src.core.logging import logger
from src.services.ocr.ocr import extract_text_from_base64_image, categorize_items

BASE_DIR = Path(__file__).resolve().parent.parent.parent

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

OCR_MODEL = os.getenv("OCR_MODEL", "qwen3-vl:8b")
BUDGET_MODEL = os.getenv("BUDGET_MODEL", "qwen3:14b")

OCR_SCHEMA = BASE_DIR / "src/services/ocr/schemas/ocr_schema.json"
OCR_PROMPT = BASE_DIR / "src/services/ocr/prompts/ocr_prompt.txt"

# ⚠️ схема категоризации — ТОЛЬКО Category
CATEGORIZATION_SCHEMA_TEMPLATE = BASE_DIR / "src/services/ocr/schemas/categorize_schema.json"
CATEGORIZATION_PROMPT = BASE_DIR / "src/services/ocr/prompts/categorize_prompt.txt"

OCR_QUEUE = "ocr_tasks"
OCR_RESULTS_QUEUE = "ocr_results"


def load_schema_with_enum(categories: list[str]) -> dict:
    """
    Загружает схему категоризации и подставляет enum.
    Схема должна содержать ТОЛЬКО поле Category.
    """
    schema_text = CATEGORIZATION_SCHEMA_TEMPLATE.read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    schema["properties"]["items"]["items"]["properties"]["Category"]["enum"] = categories
    return schema


def merge_categories(ocr_result: dict, category_result: dict) -> dict:
    """
    Склеивает OCR items + Category от LLM.
    Гарантирует валидный финальный объект.
    """
    ocr_items = ocr_result.get("items", [])
    cat_items = category_result.get("items", [])

    if len(ocr_items) != len(cat_items):
        raise ValueError("Количество items в OCR и категоризации не совпадает")

    merged_items = []
    for ocr_item, cat_item in zip(ocr_items, cat_items):
        merged_items.append({
            **ocr_item,
            "Category": cat_item.get("Category", "Unknown")
        })

    return {"items": merged_items}


def start_ocr_worker():
    logger.info(f"--- Запуск OCR Worker. Подключение к RabbitMQ на {RABBITMQ_HOST} ---")

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=5672,
                credentials=credentials,
                heartbeat=60000
            )
        )
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Не удалось подключиться к RabbitMQ: {e}")
        return

    channel = connection.channel()
    channel.queue_declare(queue=OCR_QUEUE, durable=True)
    channel.queue_declare(queue=OCR_RESULTS_QUEUE, durable=True)

    def process_task(ch, method, properties, body):
        logger.info("RAW message received")

        task_id = "N/A"
        try:
            task = json.loads(body.decode())
            task_id = task.get("task_id", "N/A")

            # --- Categories ---
            raw_categories = task.get("categories")
            if isinstance(raw_categories, list) and all(isinstance(c, str) for c in raw_categories):
                categories = raw_categories
            else:
                categories = ["Groceries", "Dining", "Transport", "Entertainment", "Other", "Unknown"]

            logger.info(f"[{task_id}] Using categories: {categories}")

            # --- Image ---
            image_b64 = task.get("image_b64")
            if not image_b64:
                raise ValueError("Отсутствует поле image_b64")

            # --- OCR ---
            ocr_result = extract_text_from_base64_image(
                image_b64=image_b64,
                model=OCR_MODEL,
                schema_path=str(OCR_SCHEMA),
                prompt_path=str(OCR_PROMPT)
            )
            logger.info(f"[{task_id}] OCR result: {json.dumps(ocr_result, ensure_ascii=False)}")

            # --- Categorization schema (TEMP FILE) ---
            categorization_schema_json = load_schema_with_enum(categories)
            with tempfile.NamedTemporaryFile(
                "w", delete=False, suffix=".json", encoding="utf-8"
            ) as tmp_file:
                json.dump(categorization_schema_json, tmp_file, ensure_ascii=False, indent=2)
                tmp_schema_path = tmp_file.name

            # --- Categorization (ONLY Category) ---
            category_result = categorize_items(
                ocr_result=ocr_result,
                categories=categories,
                model=BUDGET_MODEL,
                schema_path=tmp_schema_path,
                prompt_path=str(CATEGORIZATION_PROMPT)
            )

            logger.info(
                f"[{task_id}] Category result: {json.dumps(category_result, ensure_ascii=False)}"
            )

            # --- Merge ---
            final_items = merge_categories(ocr_result, category_result)

            final_result = {
                "task_id": task_id,
                "status": "SUCCESS",
                "data": final_items
            }

        except Exception as e:
            logger.error(f"[{task_id}] Ошибка: {e}")
            final_result = {
                "task_id": task_id,
                "status": "FAILED",
                "error": str(e)
            }
            ch.basic_nack(method.delivery_tag)
            return

        # --- Publish ---
        channel.basic_publish(
            exchange="",
            routing_key=OCR_RESULTS_QUEUE,
            body=json.dumps(final_result, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        ch.basic_ack(method.delivery_tag)
        logger.info(f"[{task_id}] Задача обработана и результат отправлен.")

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=OCR_QUEUE, on_message_callback=process_task)

    logger.info("OCR Worker запущен. Ожидание задач...")
    channel.start_consuming()


if __name__ == "__main__":
    start_ocr_worker()
