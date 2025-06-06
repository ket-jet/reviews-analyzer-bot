import asyncio
import logging
import os
import sys
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from parser_async import WildberriesParser
from analyzer_async import Analyzer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="bot.log",
    filemode="a",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

# Убираем ВСЕ обработчики по умолчанию
logger.handlers.clear()

# Добавляем обработчик ТОЛЬКО для файла
file_handler = logging.FileHandler("bot.log", encoding="utf-8", mode="a")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# Создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

# Создание диспетчера
dp = Dispatcher()

# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start
    """
    user_info = f"{message.from_user.full_name} (id: {message.from_user.id})"
    logger.info(f"Пользователь {user_info} запустил бота командой /start")
    
    await message.answer(
        f"👋 Привет, {html.bold(message.from_user.full_name)}!\n\n"
        "Я бот для анализа отзывов с Wildberries.\n\n"
        "Отправь мне ссылку на товар или артикул, и я соберу отзывы, "
        "проведу сентимент-анализ и суммаризацию.\n\n"
        "Для получения справки используй команду /help."
    )
    logger.info(f"Отправлено приветственное сообщение пользователю {user_info}")

# Обработчик команды /help
@dp.message(Command("help"))
async def help_command_handler(message: Message) -> None:
    """
    Обработчик команды /help
    """
    user_info = f"{message.from_user.full_name} (id: {message.from_user.id})"
    logger.info(f"Пользователь {user_info} запросил справку командой /help")
    
    await message.answer(
        "ℹ️ Помощь:\n\n"
        "1. Найди артикул товара на Wildberries\n"
        "2. Отправь мне артикул или ссылку\n"
        "3. Я проанализирую отзывы и покажу результаты\n\n"
        "Примечания:\n"
        "- Сбор и анализ отзывов может занять некоторое время\n"
        "- Я анализирую достоинства, недостатки и комментарии отдельно\n"
        "- Результаты включают тональность отзывов и их суммаризацию"
    )
    logger.info(f"Отправлена справка пользователю {user_info}")

# Обработчик текстовых сообщений
@dp.message()
async def process_message(message: Message) -> None:
    """
    Обработчик текстовых сообщений
    """
    text = message.text
    user_info = f"{message.from_user.full_name} (id: {message.from_user.id})"
    logger.info(f"Получено сообщение от пользователя {user_info}: {text}")

    # Проверка на ссылку или артикул
    if "wildberries.ru" in text or text.isdigit():
        logger.info(f"Начинаем обработку запроса для артикула/ссылки: {text}")

        # Сообщение о начале работы
        status_start = await message.answer('🔍 Начинаю сбор и анализ отзывов. Это может занять некоторое время...')

        try:
            # Создание экземпляров парсера и анализатора
            parser = WildberriesParser()
            analyzer = Analyzer()

            # Запуск парсинга
            logger.info(f"Запускаем парсинг для: {text}")
            # Отправляем сообщение о начале парсинга
            status_parse = await message.answer('💡 Запускаю парсинг отзывов...')
            
            reviews = await parser.parse(text)

            if not reviews:
                logger.warning(f"Отзывы не найдены или произошла ошибка при парсинге для: {text}")
                
                # Удаляем служебные сообщения
                for msg in [status_start, status_parse]:
                    await bot.delete_message(message.chat.id, msg.message_id)
                
                await message.answer('⚠️ Отзывов по товару не найдено или произошла ошибка при парсинге.')
                return

            logger.info(f"Парсинг успешно завершен для: {text}")

            # Отправляем сообщение о начале анализа
            status_analyze = await message.answer('⚖️ Приступаю к анализу отзывов...')

            # Анализ отзывов
            logger.info(f"Начинаем анализ отзывов для: {text}")
            csv_path, analyzed_data = await analyzer.analyze_reviews_data_async(reviews)
            logger.info(f"Анализ отзывов завершен, результаты сохранены в: {csv_path}")

            # Удаляем все служебные сообщения
            for msg in [status_start, status_parse, status_analyze]:
                await bot.delete_message(message.chat.id, msg.message_id)

            # Формируем ответное сообщение
            product_name = reviews.get('product_name', f'Артикул {reviews["article_id"]}')
            overall_sentiment = await _calculate_overall_sentiment(analyzed_data)
            summary = await _format_summary(analyzed_data)
            avg_rating = reviews.get('avg_rating', None)

            # Формируем строку с рейтингом
            if avg_rating is not None:
                rating_str = f"<b>{avg_rating:.1f}</b>"  # Жирный текст для числа рейтинга
            else:
                rating_str = "<i>не указан</i>"  # Курсив для случая "не указан"

                        # Формируем итоговое сообщение
            response_text = (
                "✅✅✅ Обзор на товар готов! ✅✅✅\n\n"
                f"<b>{product_name}</b>\n"
                f"Рейтинг: {rating_str}\n\n"
                f"<b>Общая оценка:</b> {overall_sentiment}\n"
                f"{summary}"
            )

            # Отправляем результаты
            logger.info(f"Отправляем результаты анализа пользователю {user_info}")
            await message.answer(response_text, parse_mode=ParseMode.HTML)
            logger.info(f"Результаты успешно отправлены пользователю {user_info}")

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения от пользователя {user_info}: {e}", exc_info=True)

            # Попытаемся удалить все временные сообщения, если они были
            for msg in [status_start, getattr(status_parse, 'message_id', None), getattr(status_analyze, 'message_id', None)]:
                if msg:
                    try:
                        await bot.delete_message(message.chat.id, msg.message_id if hasattr(msg, 'message_id') else msg)
                    except Exception:
                        pass

            await message.answer(f'⛔ Произошла ошибка: {str(e)}')
            logger.info(f"Отправлено сообщение об ошибке пользователю {user_info}")
    else:
        logger.warning(f"Получен некорректный запрос от пользователя {user_info}: {text}")
        await message.answer(
            '❌ Пожалуйста, отправьте ссылку на товар Wildberries или артикул.\n'
            'Например: https://www.wildberries.ru/catalog/12345678/detail.aspx    или 12345678'
        )
        logger.info(f"Отправлено сообщение о некорректном запросе пользователю {user_info}")

async def _calculate_overall_sentiment(analyzed_data):
    """
    Расчет общей тональности отзывов
    
    Args:
        analyzed_data (list): Список с проанализированными данными
        
    Returns:
        str: Общая тональность
    """
    if not analyzed_data:
        return "нейтральная"
    
    sentiment_counts = {
        "крайне положительная": 0,
        "положительная": 0,
        "нейтральная": 0,
        "негативная": 0,
        "крайне отрицательная": 0
    }
    
    for item in analyzed_data:
        sentiment = item["sentiment"]
        sentiment_counts[sentiment] += 1
    
    # Определяем преобладающую тональность
    return max(sentiment_counts, key=sentiment_counts.get)

async def _format_summary(analyzed_data):
    """
    Форматирование суммаризации отзывов
    
    Args:
        analyzed_data (list): Список с проанализированными данными
        
    Returns:
        str: Отформатированная суммаризация
    """
    result = "\n\n📝📝📝 Суммаризация 📝📝📝\n"
    
    # Словарь соответствия категорий и эмоджи
    category_emojis = {
        "Достоинства": "🔺",
        "Недостатки": "🔻",
        "Комментарий": "💬"
    }

    for item in analyzed_data:
        category = item["category"]
        summary = item["summary"]
        
        if summary and summary not in ["Нет данных.", "Не удалось сформировать описание."]:
            emoji = category_emojis.get(category, "")
            
            # Проверка и удаление дублирования категории в начале текста
            if category == "Достоинства" and summary.startswith("Достоинства:"):
                summary = summary.replace("Достоинства:", "", 1).strip()
            elif category == "Недостатки" and summary.startswith("Недостатки:"):
                summary = summary.replace("Недостатки:", "", 1).strip()
            
            result += f"\n<b>{emoji}{category}:</b> {summary}\n"
    
    return result

async def main() -> None:
    """
    Основная функция запуска бота
    """
    global bot 

    # Проверка наличия токена
    if not TOKEN:
        logger.error("Токен бота не найден. Убедитесь, что файл .env содержит переменную BOT_TOKEN.")
        sys.exit(1)
    
    # Создание директории для данных
    os.makedirs("data", exist_ok=True)
    logger.info("Создана директория для данных")
    
    # Инициализация бота с настройками
    bot = Bot(
        token=TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    logger.info("Бот инициализирован")
    
    # Запуск бота
    try:
        print("\n" + "="*40)
        print("🚀 Бот запущен. Ожидаем запросы...")
        print("="*40 + "\n")
        logger.info("🚀 Бот запущен. Ожидаем запросы...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n" + "="*40)
        print("🛑 Бот остановлен вручную")
        print("="*40 + "\n")
        logger.info("🛑 Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("Сессия бота закрыта")
        await bot.session.close()

if __name__ == "__main__":
    # Запуск бота
    asyncio.run(main())
