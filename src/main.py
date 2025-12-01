import os
import json
import argparse
from pathlib import Path

# Импорт из собственных модулей
from src.core.config import OLLAMA_API_URL
from src.core.logging import logger
from src.services.ocr.ocr import extract_text_from_image, categorize_items
from src.services.budget.budget import BudgetAnalysisService, TimePeriod

# Константы для путей к файлам конфигурации
OCR_SCHEMA = "./services/ocr/schemas/ocr_schema.json"
OCR_PROMPT = "./services/ocr/prompts/ocr_prompt.txt"
CATEGORIZATION_SCHEMA = "./services/ocr/schemas/categorize_schema.json"
CATEGORIZATION_PROMPT = "./services/ocr/prompts/categorize_prompt.txt"
BUDGET_ANALYSIS_SCHEMA = "./services/budget/schemas/budget_analysis_schema.json"
BUDGET_ANALYSIS_PROMPT = "./services/budget/prompts/budget_analysis_prompt.txt"
TEST_RECEIPT_IMAGE = "./test_receipt.png"  # Имя файла чека


def demo_main(ocr_model: str = "qwen3-vl:4b", budget_model: str = "qwen3:14b"):
    """Основная функция для демонстрации OCR и анализа бюджета."""
    logger.info("--- Запуск демо-режима Spendsphere ML ---")
    logger.info(f"Ollama API URL: {OLLAMA_API_URL}")

    # Проверка наличия тестового изображения
    if not Path(TEST_RECEIPT_IMAGE).exists():
        logger.error(f"Файл чека '{TEST_RECEIPT_IMAGE}' не найден.")
        logger.error("Пожалуйста, разместите ваш файл чека в корневой папке проекта и назовите его 'test_receipt.png'.")
        return

    # --- 1. Демо OCR (Извлечение текста) ---
    logger.info("\n--- 1. Запуск OCR: Извлечение структурированного текста из чека ---")
    ocr_result = {}
    try:
        # Вызов реальной функции OCR
        ocr_result = extract_text_from_image(
            image_path=TEST_RECEIPT_IMAGE,
            model=ocr_model,
            schema_path=OCR_SCHEMA,
            prompt_path=OCR_PROMPT
        )

        logger.info(f"OCR Result: \n{json.dumps(ocr_result, indent=2, ensure_ascii=False)}")

    except Exception as e:
        logger.error(f"Ошибка при выполнении OCR: {e}.")
        logger.error(f"Убедитесь, что модель '{ocr_model}' загружена в Ollama и доступна.")
        return  # Останавливаем выполнение, если OCR не удался

    # --- 2. Демо Категоризации ---
    logger.info("\n--- 2. Запуск Категоризации: Присвоение категорий элементам чека ---")
    try:
        categories = ["Groceries", "Dining Out", "Transport", "Entertainment", "Other", "Unknown"]

        # Вызов реальной функции категоризации
        categorized_result = categorize_items(
            ocr_result=ocr_result,
            categories=categories,
            model=budget_model,  # Используем более мощную текстовую модель
            schema_path=CATEGORIZATION_SCHEMA,
            prompt_path=CATEGORIZATION_PROMPT
        )
        logger.info(f"Categorized Result: \n{json.dumps(categorized_result, indent=2, ensure_ascii=False)}")

    except Exception as e:
        logger.error(f"Ошибка при выполнении Категоризации: {e}.")
        logger.error(
            f"Убедитесь, что модель '{budget_model}' загружена и доступна, а схема '{CATEGORIZATION_SCHEMA}' корректна.")

    # --- 3. Демо Анализа Бюджета ---
    logger.info("\n--- 3. Запуск Анализа Бюджета ---")
    try:
        budget_service = BudgetAnalysisService(base_url=OLLAMA_API_URL, model=budget_model)

        # Статические тестовые финансовые данные для анализа (входные данные)
        financial_data = {
            "income": {"salary": 5000.00, "side_gig": 500.00},
            "expenses": {
                "housing": 1500.00,
                "utilities": 200.00,
                "food": 800.00,
                "transportation": 300.00,
                "insurance": 100.00,
                "discretionary": 500.00
            },
            "savings": {"investment": 500.00},
            "debts": {"credit_card": 2000.00, "car_loan": 5000.00}
        }

        # Вызов реальной функции анализа бюджета
        analysis_result = budget_service.analyze_budget(
            financial_data=financial_data,
            time_period=TimePeriod.ONE_MONTH,
            user_goals=["Save $10,000 for a down payment in 12 months."]
        )
        logger.info(f"Budget Analysis Result: \n{json.dumps(analysis_result, indent=2, ensure_ascii=False)}")

    except Exception as e:
        logger.error(f"Ошибка при выполнении Анализа Бюджета: {e}.")
        logger.error(
            f"Убедитесь, что модель '{budget_model}' загружена и доступна, а схема '{BUDGET_ANALYSIS_SCHEMA}' корректна.")

    logger.info("\n--- Демонстрация завершена ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spendsphere ML Service.")
    parser.add_argument("--demo", action="store_true", help="Run the service in demonstration mode.")
    parser.add_argument("--ocr-model", type=str, default="qwen3-vl:4b", help="Ollama model for OCR (multimodal).")
    parser.add_argument("--budget-model", type=str, default="qwen3:14b",
                        help="Ollama model for budget analysis (text).")

    args = parser.parse_args()

    if args.demo:
        demo_main(args.ocr_model, args.budget_model)
    else:
        # TODO: Добавить логику для Production режима (например, запуск FastAPI сервера)
        logger.info("Сервис запущен в Production режиме (функционал пока не реализован).")
        logger.info("Используйте 'python src/main.py --demo' для запуска демонстрации.")