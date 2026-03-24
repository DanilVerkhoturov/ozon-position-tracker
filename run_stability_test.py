"""
Тест устойчивости (Часть 2 ТЗ).

Запускает один и тот же поисковый запрос 3 раза подряд
с интервалом 30 секунд между запусками.

Фиксирует:
- Успешность каждого запуска
- Время выполнения
- Найденную позицию
- Итоговую статистику
"""

import json
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.parser import RESULTS_DIR, save_result, search_product_position, setup_logger

# Параметры теста устойчивости
STABILITY_TEST_QUERY = "нож туристический"
STABILITY_TEST_SKU = "1308088830"
RUNS_COUNT = 3
INTERVAL_SECONDS = 30


def run_stability_test() -> None:
    """
    Выполняет тест устойчивости: 3 запуска с интервалом 30 секунд.
    """
    setup_logger()
    
    logger.info("=" * 60)
    logger.info("🔬 ТЕСТ УСТОЙЧИВОСТИ (Часть 2)")
    logger.info(f"Запрос: '{STABILITY_TEST_QUERY}'")
    logger.info(f"SKU: {STABILITY_TEST_SKU}")
    logger.info(f"Количество запусков: {RUNS_COUNT}")
    logger.info(f"Интервал: {INTERVAL_SECONDS}с")
    logger.info("=" * 60)
    
    results = []
    successful_runs = 0
    
    for run_num in range(1, RUNS_COUNT + 1):
        logger.info(f"\n🏃 Запуск {run_num}/{RUNS_COUNT}")
        
        start_time = time.time()
        run_start = datetime.now().isoformat(timespec='seconds')
        
        try:
            result = search_product_position(
                query=STABILITY_TEST_QUERY,
                sku=STABILITY_TEST_SKU,
            )
            
            elapsed = time.time() - start_time
            output = result.to_output_dict()
            
            run_report = {
                "run": run_num,
                "started_at": run_start,
                "elapsed_seconds": round(elapsed, 2),
                "success": result.status in ("success", "not_found"),
                "result": output,
            }
            
            results.append(run_report)
            
            if result.status in ("success", "not_found"):
                successful_runs += 1
                status_icon = "✅"
            else:
                status_icon = "❌"
            
            logger.info(
                f"{status_icon} Запуск {run_num}: "
                f"статус={result.status}, "
                f"позиция={output.get('position')}, "
                f"время={elapsed:.1f}с"
            )
            
            save_result(result)
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Запуск {run_num} завершился ошибкой: {e}")
            
            results.append({
                "run": run_num,
                "started_at": run_start,
                "elapsed_seconds": round(elapsed, 2),
                "success": False,
                "error": str(e),
            })
        
        # Пауза между запусками (кроме последнего)
        if run_num < RUNS_COUNT:
            logger.info(f"⏳ Ожидание {INTERVAL_SECONDS}с перед следующим запуском...")
            
            # Отображаем обратный отсчёт каждые 10 секунд
            remaining = INTERVAL_SECONDS
            while remaining > 0:
                sleep_chunk = min(10, remaining)
                time.sleep(sleep_chunk)
                remaining -= sleep_chunk
                if remaining > 0:
                    logger.info(f"   Осталось {remaining}с...")
    
    # Итоговый отчёт
    success_rate = (successful_runs / RUNS_COUNT) * 100
    
    final_report = {
        "test_summary": {
            "query": STABILITY_TEST_QUERY,
            "sku": STABILITY_TEST_SKU,
            "total_runs": RUNS_COUNT,
            "successful_runs": successful_runs,
            "success_rate_percent": success_rate,
            "interval_seconds": INTERVAL_SECONDS,
            "completed_at": datetime.now().isoformat(timespec='seconds'),
        },
        "runs": results,
    }
    
    # Сохраняем отчёт
    RESULTS_DIR.mkdir(exist_ok=True)
    report_file = RESULTS_DIR / f"stability_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    # Финальный вывод
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТА УСТОЙЧИВОСТИ")
    print("=" * 60)
    print(f"Успешных запусков: {successful_runs}/{RUNS_COUNT} ({success_rate:.0f}%)")
    print(f"Отчёт сохранён: {report_file}")
    print("=" * 60)
    print(json.dumps(final_report["test_summary"], ensure_ascii=False, indent=2))
    
    if successful_runs == RUNS_COUNT:
        logger.success("🎉 Все запуски успешны! Тест устойчивости пройден.")
    else:
        logger.warning(
            f"⚠️  {RUNS_COUNT - successful_runs} запуска(ов) завершились неудачей."
        )


if __name__ == "__main__":
    run_stability_test()