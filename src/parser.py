"""
Парсер позиций товаров Ozon.
Адаптирован для Mac + Chrome 146+
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

from src.anti_bot import (
    get_random_user_agent,
    get_viewport_size,
    human_scroll,
    human_sleep,
    random_mouse_movement,
)
from src.models import SearchResult

load_dotenv()

MIN_DELAY = float(os.getenv("MIN_DELAY", "3"))
MAX_DELAY = float(os.getenv("MAX_DELAY", "7"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "3"))
ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", "36"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "results"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", "logs"))

OZON_SEARCH_URL = "https://www.ozon.ru/search/"
SKU_PATTERN = re.compile(r'/product/[^/]+-(\d+)/?')


def setup_logger() -> None:
    """Настройка логгера."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"parser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger.add(
        log_file,
        rotation="10 MB",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        encoding="utf-8",
    )


def get_chromedriver_path() -> Optional[str]:
    """
    Пытается найти ChromeDriver несколькими способами.
    Chrome 146 — используем selenium встроенный менеджер.
    """

    # Способ 1: selenium встроенный SeleniumManager (работает с Chrome 146)
    try:
        logger.info("Пробуем Selenium Manager (встроенный)...")
        # Selenium 4.6+ имеет встроенный менеджер драйверов
        # Просто не передаём service — selenium сам найдёт драйвер
        return None  # None = использовать SeleniumManager
    except Exception as e:
        logger.warning(f"SeleniumManager недоступен: {e}")

    # Способ 2: webdriver-manager
    try:
        logger.info("Пробуем webdriver-manager...")
        from webdriver_manager.chrome import ChromeDriverManager
        path = ChromeDriverManager().install()
        logger.info(f"ChromeDriver найден: {path}")
        return path
    except Exception as e:
        logger.warning(f"webdriver-manager не сработал: {e}")

    # Способ 3: системный chromedriver
    import shutil
    system_driver = shutil.which("chromedriver")
    if system_driver:
        logger.info(f"Системный ChromeDriver: {system_driver}")
        return system_driver

    return None


def create_driver() -> webdriver.Chrome:
    """
    Создаёт Chrome WebDriver.
    Поддерживает Chrome 146+ на Mac через Selenium Manager.
    """
    width, height = get_viewport_size()
    user_agent = get_random_user_agent()

    options = Options()

    if HEADLESS:
        options.add_argument("--headless=new")

    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-agent={user_agent}")
    options.add_argument("--lang=ru-RU")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--start-maximized")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-gpu")

    # Убираем признаки автоматизации
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    # Пробуем создать драйвер
    driver = None

    # Попытка 1: Selenium Manager (встроен в selenium 4.6+, лучший вариант для Chrome 146)
    try:
        logger.info("🚀 Попытка 1: Selenium Manager...")
        driver = webdriver.Chrome(options=options)
        logger.info("✅ Selenium Manager сработал!")
    except Exception as e:
        logger.warning(f"❌ Selenium Manager не сработал: {e}")

    # Попытка 2: webdriver-manager
    if driver is None:
        try:
            logger.info("🚀 Попытка 2: webdriver-manager...")
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("✅ webdriver-manager сработал!")
        except Exception as e:
            logger.warning(f"❌ webdriver-manager не сработал: {e}")

    # Попытка 3: undetected-chromedriver
    if driver is None:
        try:
            logger.info("🚀 Попытка 3: undetected-chromedriver...")
            import undetected_chromedriver as uc
            uc_options = uc.ChromeOptions()
            if HEADLESS:
                uc_options.add_argument("--headless=new")
            uc_options.add_argument(f"--window-size={width},{height}")
            uc_options.add_argument("--lang=ru-RU")
            uc_options.add_argument(f"--user-agent={user_agent}")
            driver = uc.Chrome(options=uc_options, use_subprocess=True)
            logger.info("✅ undetected-chromedriver сработал!")
        except Exception as e:
            logger.warning(f"❌ undetected-chromedriver не сработал: {e}")

    if driver is None:
        raise RuntimeError(
            "❌ Не удалось создать WebDriver ни одним из способов.\n"
            "Попробуй: pip install --upgrade selenium webdriver-manager"
        )

    # JS патчи антидетект
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ru-RU', 'ru', 'en-US', 'en']
                    });
                    window.chrome = { runtime: {} };
                """
            },
        )
    except Exception as e:
        logger.warning(f"JS патчи не применены: {e}")

    logger.info(f"✅ WebDriver готов (headless={HEADLESS}, {width}x{height})")
    return driver


def extract_sku_from_url(url: str) -> Optional[str]:
    """Извлекает SKU из URL товара Ozon."""
    match = SKU_PATTERN.search(url)
    if match:
        return match.group(1)
    return None


def get_product_links(driver: webdriver.Chrome) -> list[dict]:
    """
    Извлекает ссылки на товары с текущей страницы.
    """
    products = []

    try:
        # Ждём товары
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href*='/product/']")
            )
        )

        time.sleep(2)

        product_links = driver.find_elements(
            By.CSS_SELECTOR, "a[href*='/product/']"
        )

        seen_skus = set()

        for link in product_links:
            try:
                href = link.get_attribute("href")
                if not href:
                    continue
                sku = extract_sku_from_url(href)
                if sku and sku not in seen_skus:
                    seen_skus.add(sku)
                    products.append({"url": href, "sku": sku})
            except Exception:
                continue

        logger.info(f"📦 Найдено {len(products)} товаров на странице")

    except TimeoutException:
        logger.warning("⏰ Таймаут загрузки товаров")
        # Сохраняем скриншот для диагностики
        try:
            LOGS_DIR.mkdir(exist_ok=True)
            path = LOGS_DIR / f"timeout_{datetime.now().strftime('%H%M%S')}.png"
            driver.save_screenshot(str(path))
            logger.info(f"📸 Скриншот: {path}")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"❌ Ошибка извлечения ссылок: {e}")

    return products


def handle_captcha_or_block(driver: webdriver.Chrome) -> bool:
    """Проверяет блокировку или капчу."""
    try:
        current_url = driver.current_url
        page_source = driver.page_source.lower()[:5000]

        indicators = [
            "captcha" in current_url.lower(),
            "captcha" in page_source,
            "подтвердите" in page_source,
            "доступ ограничен" in page_source,
            "robot" in page_source,
        ]

        if any(indicators):
            logger.warning(f"⚠️ Блокировка! URL: {current_url}")
            try:
                path = LOGS_DIR / f"block_{datetime.now().strftime('%H%M%S')}.png"
                driver.save_screenshot(str(path))
                logger.info(f"📸 Скриншот блокировки: {path}")
            except Exception:
                pass
            return True

    except Exception:
        pass

    return False


def search_product_position(
    query: str,
    sku: str,
    driver: Optional[webdriver.Chrome] = None,
) -> SearchResult:
    """
    Основная функция поиска позиции товара в выдаче Ozon.
    """
    own_driver = driver is None

    if own_driver:
        driver = create_driver()

    total_checked = 0
    found_position = None
    found_page = None

    try:
        logger.info(f"🔍 Запрос: '{query}' | SKU: {sku}")

        for page_num in range(1, MAX_PAGES + 1):

            query_encoded = query.replace(' ', '+')
            search_url = f"{OZON_SEARCH_URL}?text={query_encoded}&page={page_num}"

            logger.info(f"📄 Страница {page_num}: {search_url}")

            try:
                driver.get(search_url)
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки страницы: {e}")
                break

            human_sleep(3.0, 6.0)

            if handle_captcha_or_block(driver):
                return SearchResult(
                    query=query,
                    sku=sku,
                    total_checked=total_checked,
                    status="error",
                    error_message="Обнаружена блокировка или капча",
                )

            human_scroll(driver)
            human_sleep(2.0, 4.0)

            page_products = get_product_links(driver)

            if not page_products:
                logger.warning(f"Страница {page_num}: товары не найдены")
                break

            for product in page_products:
                total_checked += 1

                if product["sku"] == str(sku):
                    found_position = total_checked
                    found_page = page_num
                    logger.success(
                        f"✅ Найден! Позиция {found_position} (стр. {found_page})"
                    )
                    break

                if total_checked >= 100:
                    break

            if found_position is not None:
                break

            if total_checked >= 100:
                logger.info("✋ Достигнут лимит 100 товаров")
                break

            if page_num < MAX_PAGES:
                human_sleep(MIN_DELAY, MAX_DELAY)

        if found_position is not None:
            return SearchResult(
                query=query,
                sku=sku,
                position=found_position,
                page=found_page,
                total_checked=total_checked,
                status="success",
            )
        else:
            logger.info(f"❌ SKU {sku} не найден в топ-{total_checked}")
            return SearchResult(
                query=query,
                sku=sku,
                position=None,
                page=None,
                total_checked=total_checked,
                status="not_found",
            )

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return SearchResult(
            query=query,
            sku=sku,
            total_checked=total_checked,
            status="error",
            error_message=str(e),
        )

    finally:
        if own_driver and driver:
            try:
                driver.quit()
                logger.info("🔒 Браузер закрыт")
            except Exception:
                pass


def save_result(result: SearchResult, output_dir: Path = RESULTS_DIR) -> Path:
    """Сохраняет результат в JSON."""
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{result.sku}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result.to_output_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Сохранено: {filename}")
    return filename