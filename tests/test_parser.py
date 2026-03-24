"""
Юнит-тесты для парсера.
Тестируем логику без реальных HTTP запросов.
"""

import pytest
from src.parser import extract_sku_from_url
from src.models import SearchResult


class TestSkuExtraction:
    """Тесты извлечения SKU из URL."""
    
    def test_standard_url(self):
        """Стандартный URL товара Ozon."""
        url = "https://www.ozon.ru/product/nozh-turisticheskiy-mora-1308088830/"
        assert extract_sku_from_url(url) == "1308088830"
    
    def test_url_with_params(self):
        """URL с query параметрами."""
        url = "https://www.ozon.ru/product/ryukzak-60l-1211985039/?at=abc123"
        assert extract_sku_from_url(url) == "1211985039"
    
    def test_url_without_trailing_slash(self):
        """URL без завершающего слеша."""
        url = "https://www.ozon.ru/product/termos-726045611"
        assert extract_sku_from_url(url) == "726045611"
    
    def test_invalid_url(self):
        """Невалидный URL — должен вернуть None."""
        assert extract_sku_from_url("https://www.ozon.ru/category/") is None
    
    def test_empty_string(self):
        """Пустая строка."""
        assert extract_sku_from_url("") is None


class TestSearchResult:
    """Тесты модели результата."""
    
    def test_found_result_format(self):
        """Формат вывода для найденного товара."""
        result = SearchResult(
            query="нож туристический",
            sku="1308088830",
            position=17,
            page=1,
            total_checked=36,
            status="success",
        )
        output = result.to_output_dict()
        
        assert output["query"] == "нож туристический"
        assert output["sku"] == "1308088830"
        assert output["position"] == 17
        assert output["page"] == 1
        assert output["total_checked"] == 36
        assert "timestamp" in output
        assert "status" not in output  # Не показываем success статус
    
    def test_not_found_result_format(self):
        """Формат вывода для ненайденного товара."""
        result = SearchResult(
            query="нож туристический",
            sku="999999999",
            position=None,
            page=None,
            total_checked=100,
            status="not_found",
        )
        output = result.to_output_dict()
        
        assert output["position"] == "not_found"
        assert output["page"] is None
        assert output["status"] == "not_found"
    
    def test_timestamp_format(self):
        """Проверяем формат timestamp."""
        result = SearchResult(
            query="test",
            sku="123",
        )
        # ISO формат: YYYY-MM-DDTHH:MM:SS
        assert "T" in result.timestamp
        assert len(result.timestamp) == 19