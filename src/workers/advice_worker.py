import json
import os
import pika
import tempfile
from pathlib import Path
from src.core.logging import logger
from src.services.advice.llm_utils import generate_advice  # предполагаемая функция

BASE_DIR = Path(__file__).resolve().parent.parent.parent

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "rmuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "rmpassword")

ADVICE_MODEL = os.getenv("ADVICE_MODEL", "qwen3:0.6b")

ADVICE_SCHEMA = BASE_DIR / "src/services/advice/schemas/advice_schema.json"
ADVICE_PROMPT = BASE_DIR / "src/services/advice/prompts/advice_prompt.txt"

ADVICE_QUEUE = "advice_tasks"
ADVICE_RESULTS_QUEUE = "advice_results"


def start_advice_worker():
    logger.info(f"--- Запуск Advice Worker. RabbitMQ: {RABBITMQ_HOST} ---")

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=5673,
                credentials=credentials,
                heartbeat=60000
            )
        )
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Не удалось подключиться к RabbitMQ: {e}")
        return

    channel = connection.channel()
    channel.queue_declare(queue=ADVICE_QUEUE, durable=True)
    channel.queue_declare(queue=ADVICE_RESULTS_QUEUE, durable=True)

    def process_task(ch, method, properties, body):
        logger.info("RAW advice message received")

        task_id = "N/A"

        try:
            task = json.loads(body.decode("utf-8"))
            task_id = task.get("task_id", "N/A")

            goal = task.get("goal")
            monthly_stats = task.get("monthly_stats")

            if not goal or not monthly_stats:
                raise ValueError("Отсутствует goal или monthly_stats")

            # --- Generate advice ---
            advice_result = generate_advice(
                goal=goal,
                monthly_stats=monthly_stats,
                model=ADVICE_MODEL,
                schema_path=str(ADVICE_SCHEMA),
                prompt_path=str(ADVICE_PROMPT)
            )

            logger.info(
                f"[{task_id}] Advice result: {json.dumps(advice_result, ensure_ascii=False)}"
            )

            final_result = {
                "task_id": task_id,
                "status": "SUCCESS",
                "goal": goal,
                "advice": advice_result["advice"]
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

        channel.basic_publish(
            exchange="",
            routing_key=ADVICE_RESULTS_QUEUE,
            body=json.dumps(final_result, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        ch.basic_ack(method.delivery_tag)
        logger.info(f"[{task_id}] Advice task обработана и отправлена")

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=ADVICE_QUEUE, on_message_callback=process_task)

    logger.info("Advice Worker запущен. Ожидание задач...")
    channel.start_consuming()


if __name__ == "__main__":
    start_advice_worker()
