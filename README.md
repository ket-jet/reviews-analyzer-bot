# reviews-analyzer-bot
Telegram-bot that can analyze and summarize your reviews via link.

# Руководство по запуску парсера отзывов

## Описание проекта
Данный проект представляет собой систему для сбора и анализа отзывов с маркетплейсов. Система включает в себя парсер отзывов, модули сентимент-анализа и суммаризации, а также Telegram-бота для удобного взаимодействия.

## Структура проекта
```
reviews_bot/
├── bot.py                     # Telegram-бот на aiogram 3
├── parser_async.py            # Асинхронный парсер отзывов
├── analyzer_async.py          # Асинхронный анализатор отзывов
├── models/                    # Модуль для работы с языковыми моделями
│   ├── __init__.py
│   ├── sentiment.py           # Сентимент-анализ
│   └── summarization.py       # Суммаризация
├── data/                      # Директория для хранения данных
│   └── reviews_data.csv       # Централизованный файл с отзывами
└── requirements.txt           # Зависимости проекта
```

## Требования
- Python 3.8 или выше
- Установленные зависимости из файла requirements.txt
- Токен Telegram-бота от @BotFather

## Установка

1. Клонируйте репозиторий или распакуйте архив:

2. Установите зависимости:
```
pip install -r requirements.txt
```

3. Установите браузеры для Playwright:
```
python -m playwright install
```

4. Создайте файл `.env` в корневой директории проекта и добавьте в него токен бота:
```
BOT_TOKEN=ваш_токен_от_BotFather
```

## Запуск

Для запуска бота выполните команду:
```
python bot.py
```

## Использование

1. Запустите бота в Telegram
2. Отправьте боту ссылку на товар Wildberries или артикул
3. Бот соберет отзывы, проведет сентимент-анализ и суммаризацию
4. Результаты будут сохранены в:
   - Индивидуальный файл в формате `артикул_дата_время.csv`
   - Централизованный файл `data/reviews_data.csv`

## Особенности

- Логи записываются в файл `bot.log` и в терминал
- CSV-файлы сохраняются в кодировке UTF-8-SIG для корректного отображения в Excel
- Централизованный файл `reviews_data.csv` дополняется новыми данными при каждом анализе
- Сентимент-анализ включает категории: крайне положительная, положительная, нейтральная, негативная, крайне отрицательная
- Суммаризация настроена с параметрами: num_beams=4, min_new_tokens=10, max_new_tokens=45/100

## Устранение неполадок

Если возникают проблемы с загрузкой страниц:
- Проверьте интернет-соединение
- Убедитесь, что установлены все браузеры для Playwright
- Проверьте логи в файле `bot.log` для диагностики проблемы

## Примечания

- Для анализа используются предварительно скачанные модели:
  - cointegrated/rubert-tiny-sentiment-balanced для сентимент-анализа
  - RussianNLP/FRED-T5-Summarizer для суммаризации
