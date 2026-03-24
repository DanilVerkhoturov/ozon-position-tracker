"""
Модели данных для результатов парсинга.
Используем Pydantic для валидации и сериализации.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """
    Результат поиска позиции товара.
    
    Attributes:
        query: Поисковый запрос
        sku: Артикул товара на Ozon
        position: Позиция товара (None если не найден)
        page: Страница, на которой найден товар
        total_checked: Сколько товаров проверено
        timestamp: Время выполнения запроса
        status: Статус выполнения (success/not_found/error)
        error_message: Сообщение об ошибке (если есть)
    """
    
    query: str
    sku: str
    position: Optional[int] = Field(
        default=None,
        description="Позиция товара в выдаче (1-100), None если не найден"
    )
    page: Optional[int] = Field(
        default=None,
        description="Страница выдачи"
    )
    total_checked: int = Field(
        default=0,
        description="Количество проверенных позиций"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec='seconds')
    )
    status: str = Field(
        default="success",
        description="success | not_found | error"
    )
    error_message: Optional[str] = None

    def to_output_dict(self) -> dict:
        """
        Формат вывода согласно ТЗ.
        Если товар не найден — position = 'not_found'.
        """
        result = {
            "query": self.query,
            "sku": self.sku,
            "position": self.position if self.position is not None else "not_found",
            "page": self.page,
            "total_checked": self.total_checked,
            "timestamp": self.timestamp,
        }
        
        # Добавляем статус и ошибку только если есть проблема
        if self.status != "success":
            result["status"] = self.status
        if self.error_message:
            result["error_message"] = self.error_message
            
        return result