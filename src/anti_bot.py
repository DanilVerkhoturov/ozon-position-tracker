"""
Anti-bot механизмы для устойчивой работы парсера.

Стратегии:
1. Случайные задержки между запросами (имитация человека)
2. Ротация User-Agent
3. Случайные движения мыши и скроллинг
4. Имитация человеческого поведения на странице
"""

import random
import time
from typing import Tuple

from fake_useragent import UserAgent
from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver


# Пул реалистичных User-Agent строк (Chrome на разных ОС)
FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


def get_random_user_agent() -> str:
    """
    Получает случайный User-Agent.
    Сначала пробует fake_useragent, при ошибке — fallback список.
    """
    try:
        ua = UserAgent(browsers=['chrome'], os=['windows', 'macos', 'linux'])
        agent = ua.random
        logger.debug(f"User-Agent: {agent[:60]}...")
        return agent
    except Exception as e:
        logger.warning(f"fake_useragent недоступен: {e}. Используем fallback.")
        return random.choice(FALLBACK_USER_AGENTS)


def get_random_delay(min_sec: float = 2.0, max_sec: float = 5.0) -> float:
    """
    Генерирует случайную задержку с нормальным распределением.
    Нормальное распределение более реалистично, чем равномерное.
    """
    # Центр распределения — середина диапазона
    mean = (min_sec + max_sec) / 2
    std = (max_sec - min_sec) / 4
    
    delay = random.gauss(mean, std)
    # Клипуем в допустимый диапазон
    delay = max(min_sec, min(max_sec, delay))
    
    return delay


def human_sleep(min_sec: float = 2.0, max_sec: float = 5.0) -> None:
    """
    Случайная пауза с логированием.
    Имитирует время чтения/обработки страницы человеком.
    """
    delay = get_random_delay(min_sec, max_sec)
    logger.debug(f"Пауза {delay:.2f}с (имитация человека)")
    time.sleep(delay)


def human_scroll(driver: WebDriver) -> None:
    """
    Имитирует человеческий скроллинг страницы.
    
    Человек не скроллит страницу мгновенно — делает несколько
    движений с паузами между ними.
    """
    try:
        # Получаем высоту страницы
        total_height = driver.execute_script(
            "return document.body.scrollHeight"
        )
        
        # Скроллим несколькими шагами
        scroll_steps = random.randint(3, 6)
        step_size = total_height // scroll_steps
        
        current_pos = 0
        for i in range(scroll_steps):
            # Случайный шаг скроллинга
            scroll_amount = step_size + random.randint(-100, 100)
            current_pos += scroll_amount
            
            driver.execute_script(
                f"window.scrollTo({{top: {current_pos}, behavior: 'smooth'}})"
            )
            
            # Пауза между скроллами (0.3-1.2 сек)
            time.sleep(random.uniform(0.3, 1.2))
            
        logger.debug(f"Скроллинг выполнен ({scroll_steps} шагов)")
        
    except Exception as e:
        logger.warning(f"Ошибка при скроллинге: {e}")


def random_mouse_movement(driver: WebDriver) -> None:
    """
    Случайные движения мыши по странице.
    Помогает обойти детекторы, которые проверяют активность курсора.
    """
    try:
        actions = ActionChains(driver)
        
        # 2-4 случайных движения
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            actions.move_by_offset(x, y)
            actions.pause(random.uniform(0.1, 0.5))
        
        actions.perform()
        logger.debug("Случайные движения мыши выполнены")
        
    except Exception as e:
        # Движения мыши — не критичная функция
        logger.debug(f"Движения мыши пропущены: {e}")


def get_viewport_size() -> Tuple[int, int]:
    """
    Возвращает случайный реалистичный размер окна браузера.
    Избегаем стандартных headless размеров (1920x1080 слишком очевидно).
    """
    viewports = [
        (1366, 768),   # Самый популярный размер экрана
        (1440, 900),   # MacBook
        (1536, 864),   # Популярный ноутбук
        (1280, 720),   # HD
        (1600, 900),   # Широкий экран
    ]
    return random.choice(viewports)