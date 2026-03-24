"""
Точка входа для парсера позиций Ozon.

Использование:
    python main.py --query "нож туристический" --sku 123456789
    python main.py --query "рюкзак 60л" --sku 987654321 --no-headless
    python main.py --batch  # Запуск тестовых данных из README
"""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

from src.parser import (
    RESULTS_DIR,
    create_driver,
    save_result,
    search_product_position,
    setup_logger,
)

# ============================================================
# Тестовые данные (Часть 1 ТЗ)
# Выбраны популярные категории с конкурентными запросами
# ============================================================
TEST_CASES = [
    {
        "query": "нож туристический",
        "sku": "1308088830",  # Нож Mora Companion
        "description": "Популярный туристический нож — высокая конкуренция в выдаче",
    },
    {
        "query": "рюкзак туристический 60 литров",
        "sku": "1211985039",  # Рюкзак Osprey
        "description": "Туристический рюкзак — средняя конкуренция",
    },
    {
        "query": "термос для чая 1 литр",
        "sku": "726045611",   # Термос Stanley
        "description": "Термос — стабильный спрос, предсказуемая выдача",
    },
]


def run_single_search(query: str, sku: str, headless: bool = True) -> dict:
    """Выполняет один поисковый запрос и возвращает результат."""
    import os
    os.environ["HEADLESS"] = str(headless).lower()
    
    result = search_product_position(query=query, sku=sku)
    output = result.to_output_dict()
    
    # Красивый вывод в консоль
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТ ПОИСКА")
    print("=" * 60)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("=" * 60 + "\n")
    
    # Сохраняем файл
    save_result(result)
    
    return output


def run_batch_test(headless: bool = True) -> None:
    """Запускает все тестовые случаи последовательно."""
    logger.info(f"🚀 Запуск batch-теста: {len(TEST_CASES)} запросов")
    
    results = []
    
    # Создаём один driver для всех запросов (экономия ресурсов)
    import os
    os.environ["HEADLESS"] = str(headless).lower()
    
    driver = create_driver()
    
    try:
        for i, test_case in enumerate(TEST_CASES, 1):
            logger.info(
                f"\n{'='*50}\n"
                f"Тест {i}/{len(TEST_CASES)}: {test_case['description']}\n"
                f"{'='*50}"
            )
            
            result = search_product_position(
                query=test_case["query"],
                sku=test_case["sku"],
                driver=driver,
            )
            
            output = result.to_output_dict()
            results.append(output)
            save_result(result)
            
            # Пауза между запросами
            if i < len(TEST_CASES):
                from src.anti_bot import human_sleep
                human_sleep(5.0, 10.0)
    
    finally:
        driver.quit()
    
    # Итоговый отчёт
    print("\n" + "=" * 60)
    print("📋 ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 60)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    
    # Сохраняем общий отчёт
    RESULTS_DIR.mkdir(exist_ok=True)
    from datetime import datetime
    report_file = RESULTS_DIR / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.success(f"✅ Batch-тест завершён. Отчёт: {report_file}")


def main():
    setup_logger()
    
    parser = argparse.ArgumentParser(
        description="Ozon Position Tracker — парсер позиций товаров",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py --query "нож туристический" --sku 1308088830
  python main.py --query "рюкзак" --sku 1211985039 --no-headless
  python main.py --batch
  python main.py --batch --no-headless
        """,
    )
    
    parser.add_argument(
        "--query",
        type=str,
        help="Поисковый запрос",
    )
    parser.add_argument(
        "--sku",
        type=str,
        help="Артикул товара на Ozon",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Запустить все тестовые случаи",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Показать браузер (не headless режим)",
    )
    
    args = parser.parse_args()
    
    headless = not args.no_headless
    
    if args.batch:
        run_batch_test(headless=headless)
    elif args.query and args.sku:
        run_single_search(args.query, args.sku, headless=headless)
    else:
        parser.print_help()
        print("\n⚠️  Укажите --query и --sku или используйте --batch")
        sys.exit(1)


if __name__ == "__main__":
    main()