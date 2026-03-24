```markdown
# Лог подхода к решению

## Итерация 1: Первый подход — requests + BeautifulSoup

**Что пробовал:**
Начал с самого простого — requests + BeautifulSoup.

```python
import requests
from bs4 import BeautifulSoup

response = requests.get(
    "https://www.ozon.ru/search/?text=нож+туристический",
    headers={"User-Agent": "Mozilla/5.0..."}
)
soup = BeautifulSoup(response.text, "html.parser")