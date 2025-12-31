# handyhoch-tg-bot

Телеграм-бот для подбора квартир в Берлине. Бот работает на `python-telegram-bot` и умеет задавать вопросы о типе жилья (WG или Wohnung), типе арендодателя (баугезельшафт или приват), бюджете, районах и количестве комнат, после чего подбирает подходящие варианты из локального списка объявлений.

## Возможности
- `/start` — приветствие и краткое описание.
- `/help` — справка по командам.
- `/listings` — быстрый вывод нескольких вариантов без фильтров.
- `/search` — пошаговый подбор по типу жилья (WG/Wohnung), типу арендодателя (баугезельшафт или приват), периоду публикации (по умолчанию последние 5 часов), бюджету, районам и минимальному числу комнат. Можно включить фильтр для исключения подозрительных объявлений.
- `/cancel` — выход из сценария подбора.

## Настройка
1. Создайте бота через [BotFather](https://t.me/BotFather) и получите токен.
2. Скопируйте `.env.example` в `.env` и заполните значение `BOT_TOKEN`:
   ```bash
   cp .env.example .env
   echo "BOT_TOKEN=ваш-токен" >> .env
   ```
3. (Опционально) Замените путь к данным о квартирах:
   ```bash
   echo "LISTINGS_PATH=data/listings.json" >> .env
   ```
По умолчанию используется файл `data/listings.json` с примерами объявлений (включает WG/Wohnung, баугезельшафты: Gewobag, Howoge, Degewo, Stadt und Land, Berlinovo, WGL, а также приватные источники wggesucht, kleinanzeigen, immoscout).

## Установка зависимостей
Рекомендуется использовать виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск
```bash
python -m handyhoch_tg_bot.bot
```
Бот загрузит объявления из `LISTINGS_PATH` и начнет опрос пользователей через Telegram (поллинг).

### Запуск в Docker
1. Подготовьте `.env` с `BOT_TOKEN` и (опционально) `LISTINGS_PATH`.
2. Соберите образ:
   ```bash
   docker build -t handyhochbot .
   ```
3. Запустите контейнер, подключив файл с объявлениями (по умолчанию `data/listings.json`):
   ```bash
   docker run --env-file .env -v $(pwd)/data:/app/data:ro handyhochbot
   ```
   Или через Docker Compose:
   ```bash
   docker compose up -d
   ```
Контейнер использует команду `python -m handyhoch_tg_bot.bot`.

## Тесты
```bash
pytest
```

## Структура данных
Каждое объявление хранится в JSON-формате:
```json
{
  "id": "wg-ber-001",
  "title": "WG-Zimmer у Ostkreuz, меблированная",
  "price_eur": 680,
  "size_sqm": 16,
  "rooms": 1,
  "district": "Friedrichshain",
  "available_from": "2025-02-01",
  "posted_at": "2025-01-10",
  "category": "wg",
  "provider_type": "private",
  "provider_name": "Privat",
  "source": "wggesucht",
  "is_scam": false,
  "url": "https://wggesucht.example.com/rooms/berlin-ostkreuz"
}
```
`LISTINGS_PATH` может указывать на любой похожий JSON-массив. Фильтры учитывают тип жилья (`category` — wg/wohnung), тип арендодателя (`provider_type` — housing_association/private), бюджет (`price_eur`), районы (`district`), минимальное число комнат (`rooms`), период давности (`posted_at` с шагом в часы/дни) и, при включении фильтра, убирают объявления с `is_scam=true`.
