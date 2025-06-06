import os
import asyncio
import logging
import csv
import emoji
from models.sentiment import SentimentAnalyzer
from models.summarization import Summarizer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="analyzer.log",
    filemode="a",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

class Analyzer:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.summarizer = Summarizer()
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def analyze_reviews_data_async(self, reviews_data):
        """
        Анализ данных отзывов: сентимент-анализ и суммаризация
        
        Args:
            reviews_data (dict): Данные отзывов
            
        Returns:
            tuple: (путь к CSV-файлу, список проанализированных данных)
        """
        try:
            article_id = reviews_data.get("article_id", "unknown")
            product_name = reviews_data.get("product_name", "Неизвестный товар")
            avg_rating = reviews_data.get("avg_rating", 0.0)
            
            # Создаем или открываем CSV-файл
            csv_path = os.path.join(self.data_dir, f"reviews_data_{article_id}.csv")
            file_exists = os.path.isfile(csv_path)
            
            analyzed_data = []
            
            # Анализируем достоинства
            if "advantages" in reviews_data and reviews_data["advantages"]:
                advantages_data = await self._analyze_category(
                    reviews_data["advantages"], 
                    "Достоинства", 
                    article_id, 
                    avg_rating
                )
                analyzed_data.append(advantages_data)
            
            # Анализируем недостатки
            if "disadvantages" in reviews_data and reviews_data["disadvantages"]:
                disadvantages_data = await self._analyze_category(
                    reviews_data["disadvantages"], 
                    "Недостатки", 
                    article_id, 
                    avg_rating
                )
                analyzed_data.append(disadvantages_data)
            
            # Анализируем комментарии
            if "comments" in reviews_data and reviews_data["comments"]:
                comments_data = await self._analyze_category(
                    reviews_data["comments"], 
                    "Комментарий", 
                    article_id, 
                    avg_rating
                )
                analyzed_data.append(comments_data)
            
            # Записываем данные в CSV
            with open(csv_path, mode='a' if file_exists else 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                
                # Записываем заголовок, если файл новый
                if not file_exists:
                    writer.writerow([
                        "№", "Артикул", "Средняя оценка", "Тип отзыва", 
                        "Исходный отзыв", "Оценка", "Уровень уверенности", 
                        "Автосуммаризация", "Эталон"
                    ])
                
                # Определяем номер строки
                row_num = 1
                if file_exists:
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        row_num = sum(1 for _ in f) - 1  # Вычитаем заголовок
                
                # Записываем данные
                for data in analyzed_data:
                    writer.writerow([
                        row_num,
                        article_id,
                        avg_rating,
                        data["category"],
                        data["text"],
                        data["sentiment"],
                        data["confidence"],
                        data["summary"],
                        ""  # Эталон (пустой)
                    ])
                    row_num += 1
            
            await Summarizer.release_model()

            return csv_path, analyzed_data
            
        except Exception as e:
            logger.error(f"Ошибка при анализе отзывов: {e}")
            return None, []
    
    async def _analyze_category(self, text, category, article_id, avg_rating):
        """
        Анализ категории отзывов
        
        Args:
            text (str): Текст отзывов
            category (str): Категория (Достоинства, Недостатки, Комментарий)
            article_id (str): Артикул товара
            avg_rating (float): Средняя оценка
            
        Returns:
            dict: Результаты анализа
        """
        try:
            # Удаляем эмодзи
            clean_text = emoji.replace_emoji(text, replace='')
            
            # Сентимент-анализ
            sentiment, confidence = await self.sentiment_analyzer.analyze(clean_text)
            
            # Суммаризация
            summary = await self.summarizer.summarize(clean_text, category)
            
            return {
                "category": category,
                "text": clean_text,
                "sentiment": sentiment,
                "confidence": confidence,
                "summary": summary
            }
        except Exception as e:
            logger.error(f"Ошибка при анализе категории {category}: {e}")
            return {
                "category": category,
                "text": text,
                "sentiment": "нейтральная",
                "confidence": 0,
                "summary": "Не удалось сформировать описание."
            }

# Для тестирования
async def main():
    analyzer = Analyzer()
    # Тестовые данные
    reviews_data = {
        "article_id": "12345678",
        "product_name": "Тестовый товар",
        "avg_rating": 4.5,
        "advantages": "Хорошее качество. Удобный. Красивый дизайн.",
        "disadvantages": "Высокая цена. Долгая доставка.",
        "comments": "В целом доволен покупкой, но есть некоторые недочеты."
    }
    
    csv_path, analyzed_data = await analyzer.analyze_reviews_data_async(reviews_data)
    print(f"CSV-файл сохранен: {csv_path}")
    print("Результаты анализа:")
    for data in analyzed_data:
        print(f"{data['category']}: {data['sentiment']} ({data['confidence']}%)")
        print(f"Суммаризация: {data['summary']}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
