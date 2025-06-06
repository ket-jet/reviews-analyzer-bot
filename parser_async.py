import re
import os
import asyncio
import logging
import random
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="parser.log",
    filemode="a",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

class WildberriesParser:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    async def _init_browser(self):
        """Инициализация браузера с расширенными настройками для обхода защиты"""
        playwright = await async_playwright().start()
        
        # Расширенные аргументы для запуска браузера
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-web-security",
            "--disable-setuid-sandbox",
            "--no-sandbox",
            "--ignore-certificate-errors",
            "--window-size=1920,1080",
            f"--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        ]
        
        self.browser = await playwright.chromium.launch(
            headless=True,  # Для отладки можно установить False
            args=browser_args
        )
        
        # Создаем контекст с расширенными настройками
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            color_scheme="light",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive",
                "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        # Настройка перехвата запросов для блокировки ненужных ресурсов
        await self.context.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda route: route.abort())
        await self.context.route("**/analytics.js", lambda route: route.abort())
        
        # Создаем страницу
        self.page = await self.context.new_page()
        
        # Эмуляция пользовательского поведения
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en'],
            });
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        """)
        
        logger.info("Браузер инициализирован с расширенными настройками для обхода защиты")

    async def _get_article_from_url(self, url):
        """Извлечение артикула из URL"""
        match = re.search(r"catalog/(\d+)/", url)
        if match:
            return match.group(1)
        return url if url.isdigit() else None

    async def _get_product_url(self, article):
        """Формирование URL товара по артикулу"""
        if "wildberries.ru" in article:
            return article
        return f"https://www.wildberries.ru/catalog/{article}/detail.aspx"

    async def _get_product_info(self, article_id):
        """Получение информации о товаре (название и средняя оценка)"""
        try:
            # Ищем название товара
            product_name_element = await self.page.query_selector(".product-page__header h1")
            if not product_name_element:
                # Альтернативный селектор для названия товара
                product_name_element = await self.page.query_selector(".product-line__name")
            
            if not product_name_element:
                # Еще один альтернативный селектор для мобильной версии
                product_name_element = await self.page.query_selector("h1.same-part-kt__header")
            
            product_name = "Неизвестный товар"
            if product_name_element:
                product_name = await product_name_element.text_content()
                # Если название содержит бренд и слеш, берем только часть после слеша
                if "/" in product_name:
                    product_name = product_name.split("/", 1)[1].strip()
            
            # Ищем среднюю оценку
            rating_element = await self.page.query_selector(".address-rate-mini")
            if not rating_element:
                # Альтернативный селектор для оценки
                rating_element = await self.page.query_selector(".product-review__rating")
            
            avg_rating = "0.0"
            if rating_element:
                avg_rating = await rating_element.text_content()
                # Заменяем запятую на точку для корректного преобразования в float
                avg_rating = avg_rating.replace(",", ".")
            
            logger.info(f"Получена информация о товаре: {product_name}, рейтинг: {avg_rating}")
            return {
                "product_name": product_name,
                "avg_rating": float(avg_rating)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о товаре: {e}")
            return {
                "product_name": "Неизвестный товар",
                "avg_rating": 0.0
            }

    async def _emulate_human_behavior(self):
        """Эмуляция человеческого поведения для обхода защиты"""
        try:
            # Случайные движения мыши
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Случайные прокрутки
            for _ in range(2):
                await self.page.mouse.wheel(0, random.randint(100, 300))
                await asyncio.sleep(random.uniform(0.2, 0.5))
            
            logger.info("Выполнена эмуляция человеческого поведения")
        except Exception as e:
            logger.error(f"Ошибка при эмуляции человеческого поведения: {e}")

    async def _find_reviews_button(self):
        """Поиск кнопки 'Смотреть все отзывы' с учетом различных версий сайта"""
        try:
            # Прокручиваем страницу вниз несколько раз, чтобы найти кнопку отзывов
            for i in range(10):  # Увеличиваем количество попыток прокрутки
                logger.info(f"Попытка {i+1} найти кнопку отзывов")
                
                # Прокручиваем страницу
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
                
                # Проверяем различные селекторы для кнопки отзывов
                selectors = [
                    ".comments__btn-all",  # Стандартный селектор
                    "a[data-link*='feedbacks']",  # Альтернативный селектор по атрибуту
                    "a[href*='feedbacks']",  # Еще один вариант по href
                    ".product-review__all-reviews",  # Мобильная версия
                    "button.btn-base:has-text('отзывы')",  # Поиск по тексту
                    "a:has-text('отзывы')"  # Еще один вариант по тексту
                ]
                
                for selector in selectors:
                    button = await self.page.query_selector(selector)
                    if button:
                        logger.info(f"Найдена кнопка отзывов с селектором: {selector}")
                        return button
                
                # Если кнопка не найдена, пробуем искать по тексту на странице
                try:
                    button = await self.page.query_selector("text=Смотреть все отзывы")
                    if button:
                        logger.info("Найдена кнопка отзывов по тексту")
                        return button
                except:
                    pass
            
            # Если кнопка не найдена, пробуем перейти на страницу отзывов напрямую
            current_url = self.page.url
            article_id = await self._get_article_from_url(current_url)
            if article_id:
                logger.info(f"Кнопка отзывов не найдена, пробуем перейти на страницу отзывов напрямую")
                feedbacks_url = f"https://www.wildberries.ru/catalog/{article_id}/feedbacks"
                await self.page.goto(feedbacks_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                return True  # Возвращаем True, чтобы показать, что мы перешли на страницу отзывов
            
            logger.error("Кнопка 'Смотреть все отзывы' не найдена")
            return None
        except Exception as e:
            logger.error(f"Ошибка при поиске кнопки отзывов: {e}")
            return None

    async def _click_this_variant_button(self):
        """Нажатие на кнопку 'Этот вариант товара'"""
        try:
            # Ждем появления кнопки с увеличенным таймаутом
            try:
                await self.page.wait_for_selector("text='Этот вариант товара'", timeout=15000)
            except TimeoutError:
                logger.warning("Кнопка 'Этот вариант товара' не найдена за 15 секунд")
                return False

            # Ищем и кликаем по кнопке
            button = await self.page.query_selector("text='Этот вариант товара'")
            if button:
                # Прокручиваем к кнопке
                await self.page.evaluate("(el) => el.scrollIntoView({block: 'center'})", button)
                await asyncio.sleep(0.5)

                # Нажимаем
                await button.click()
                logger.info("Нажата кнопка 'Этот вариант товара'")
                await asyncio.sleep(2)  # Ждём загрузки отзывов
                return True

            logger.info("Кнопка 'Этот вариант товара' не найдена")
            return False

        except Exception as e:
            logger.error(f"Ошибка при нажатии на кнопку 'Этот вариант товара': {e}")
            return False

    async def _parse_reviews(self):
        """Парсинг отзывов с текущей страницы"""
        try:
            # Ждем загрузки отзывов с увеличенным таймаутом
            try:
                await self.page.wait_for_function("""
                    () => {
                        const reviews = document.querySelectorAll('.feedback__content, .comment__content, .product-feedbacks__block');
                        return reviews.length > 0;
                    }
                """, timeout=15000)
            except TimeoutError:
                logger.warning("Таймаут при ожидании загрузки отзывов, пробуем продолжить")
            
            # Прокручиваем страницу для загрузки всех отзывов (до 50)
            for _ in range(15):  # Увеличиваем количество прокруток
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            
            # Получаем HTML-содержимое страницы
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Находим все блоки с отзывами, проверяя различные селекторы
            review_blocks = soup.select('.feedback__content, .comment__content, .product-feedbacks__block')
            
            if not review_blocks:
                logger.warning("Не найдены блоки с отзывами, пробуем альтернативные селекторы")
                # Пробуем альтернативные селекторы
                review_blocks = soup.select('.comments__item, .feedback, .feedbacks__item')
            
            logger.info(f"Найдено {len(review_blocks)} блоков с отзывами")
            
            advantages = []
            disadvantages = []
            comments = []
            
            for block in review_blocks[:50]:  # Ограничиваем до 50 отзывов
                # Ищем блоки с достоинствами, недостатками и комментариями
                # Проверяем различные варианты структуры отзывов
                
                # Вариант 1: Стандартная структура с выделенными блоками
                text_items = block.select('.feedback__text--item, .comment__text--item')
                
                if text_items:
                    for item in text_items:
                        bold_text = item.select_one('.feedback__text--item-bold, .comment__text--item-bold')
                        if not bold_text:
                            # Если нет выделенного заголовка, это просто комментарий
                            comments.append(item.get_text().strip())
                            continue
                        
                        category = bold_text.get_text().strip()
                        # Удаляем заголовок из текста
                        text = item.get_text().replace(category, '', 1).strip()
                        
                        if "Достоинства" in category:
                            advantages.append(text)
                        elif "Недостатки" in category:
                            disadvantages.append(text)
                        elif "Комментарий" in category:
                            comments.append(text)
                else:
                    # Вариант 2: Простая структура без выделенных блоков
                    review_text = block.select_one('.feedback__text, .comment__text')
                    if review_text:
                        text = review_text.get_text().strip()
                        if text:
                            comments.append(text)
            
            logger.info(f"Собрано отзывов: достоинства - {len(advantages)}, недостатки - {len(disadvantages)}, комментарии - {len(comments)}")
            return {
                "advantages": advantages,
                "disadvantages": disadvantages,
                "comments": comments
            }
        except TimeoutError:
            logger.error("Таймаут при ожидании загрузки отзывов")
            return {"advantages": [], "disadvantages": [], "comments": []}
        except Exception as e:
            logger.error(f"Ошибка при парсинге отзывов: {e}")
            return {"advantages": [], "disadvantages": [], "comments": []}

    async def _combine_reviews(self, reviews_data):
        """Объединение отзывов по категориям"""
        result = {}
        
        # Объединяем достоинства
        advantages = reviews_data.get("advantages", [])
        if advantages:
            combined_advantages = ""
            for adv in advantages:
                if adv.strip():
                    # Добавляем точку и пробел, если нет знака пунктуации в конце
                    if not adv[-1] in ['.', '!', '?']:
                        combined_advantages += adv + ". "
                    else:
                        combined_advantages += adv + " "
            result["advantages"] = combined_advantages.strip()
        
        # Объединяем недостатки
        disadvantages = reviews_data.get("disadvantages", [])
        if disadvantages:
            combined_disadvantages = ""
            for dis in disadvantages:
                if dis.strip():
                    if not dis[-1] in ['.', '!', '?']:
                        combined_disadvantages += dis + ". "
                    else:
                        combined_disadvantages += dis + " "
            result["disadvantages"] = combined_disadvantages.strip()
        
        # Объединяем комментарии
        comments = reviews_data.get("comments", [])
        if comments:
            combined_comments = ""
            for com in comments:
                if com.strip():
                    if not com[-1] in ['.', '!', '?']:
                        combined_comments += com + ". "
                    else:
                        combined_comments += com + " "
            result["comments"] = combined_comments.strip()
        
        return result

    async def _clean_emoji(self, text):
        """Очистка текста от эмодзи"""
        if not text:
            return ""
        
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # эмодзи: смайлики
            "\U0001F300-\U0001F5FF"  # эмодзи: разные символы и пиктограммы
            "\U0001F680-\U0001F6FF"  # эмодзи: транспорт и символы
            "\U0001F700-\U0001F77F"  # эмодзи: алхимические символы
            "\U0001F780-\U0001F7FF"  # эмодзи: геометрические фигуры
            "\U0001F800-\U0001F8FF"  # эмодзи: дополнительные стрелки
            "\U0001F900-\U0001F9FF"  # эмодзи: дополнительные символы
            "\U0001FA00-\U0001FA6F"  # эмодзи: расширенные символы
            "\U0001FA70-\U0001FAFF"  # эмодзи: символы
            "\U00002702-\U000027B0"  # эмодзи: разные символы
            "\U000024C2-\U0001F251"  # эмодзи: заключенные символы
            "]+", flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)

    async def parse(self, article_or_url):
        """Основной метод парсинга отзывов"""
        try:
            # Инициализация браузера
            await self._init_browser()
            
            # Получаем артикул и URL товара
            article = await self._get_article_from_url(article_or_url)
            if not article:
                logger.error(f"Не удалось извлечь артикул из: {article_or_url}")
                return None
            
            product_url = await self._get_product_url(article)
            
            # Открываем страницу товара
            logger.info(f"Открываем страницу товара: {product_url}")
            await self.page.goto(product_url, wait_until="domcontentloaded")
            await asyncio.sleep(5)  # Увеличиваем время ожидания загрузки
            
            # Эмулируем человеческое поведение для обхода защиты
            await self._emulate_human_behavior()
            
            # Получаем информацию о товаре
            product_info = await self._get_product_info(article)
            
            # Ищем и нажимаем на кнопку "Смотреть все отзывы"
            reviews_button = await self._find_reviews_button()
            
            if not reviews_button:
                logger.error("Не удалось найти или перейти на страницу отзывов")
                return None
            
            # Если reviews_button не является True (т.е. мы не перешли напрямую на страницу отзывов)
            if reviews_button is not True:
                # Нажимаем на кнопку отзывов
                logger.info("Нажимаем на кнопку 'Смотреть все отзывы'")
                await reviews_button.click()
                await asyncio.sleep(5)  # Увеличиваем время ожидания загрузки
            
            # Нажимаем на кнопку "Этот вариант товара", если она есть
            await self._click_this_variant_button()
            
            # Парсим отзывы
            reviews_data = await self._parse_reviews()
            
            # Объединяем отзывы по категориям
            combined_reviews = await self._combine_reviews(reviews_data)
            
            # Очищаем от эмодзи
            for key in combined_reviews:
                combined_reviews[key] = await self._clean_emoji(combined_reviews[key])
            
            # Формируем результат
            result = {
                "article_id": article,
                "product_name": product_info["product_name"],
                "avg_rating": product_info["avg_rating"],
                "advantages": combined_reviews.get("advantages", ""),
                "disadvantages": combined_reviews.get("disadvantages", ""),
                "comments": combined_reviews.get("comments", "")
            }
            
            logger.info(f"Парсинг завершен успешно для артикула {article}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге: {e}")
            return None
        finally:
            # Закрываем браузер
            if self.browser:
                await self.browser.close()
                logger.info("Браузер закрыт")

# Для тестирования
async def main():
    parser = WildberriesParser()
    article = "12345678"  # Замените на реальный артикул
    result = await parser.parse(article)
    print(result)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        article = sys.argv[1]
        asyncio.run(WildberriesParser().parse(article))
    else:
        print("Укажите артикул или ссылку на товар")
