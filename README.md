# Job Bot — парсер вакансий бизнес-аналитика

Бот автоматически собирает свежие вакансии по направлению **"бизнес-аналитик" / "business analyst"** с популярных job-сайтов и отправляет новые в Telegram.

## Источники

| Источник | Метод |
|---|---|
| **hh.ru** | Официальный API |
| **Habr Career** | Парсинг HTML |
| **GetMatch** | Парсинг HTML |
| **SuperJob** | Парсинг HTML |
| **LinkedIn** | Парсинг публичных страниц |

## Быстрый старт

### 1. Установить зависимости

```bash
pip install -r requirements.txt
```

### 2. Создать Telegram бота

1. Напишите [@BotFather](https://t.me/BotFather) → `/newbot`
2. Скопируйте токен
3. Узнайте свой Chat ID — напишите [@userinfobot](https://t.me/userinfobot)

### 3. Настроить `.env`

```bash
cp .env.example .env
```

Заполните `.env`:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=123456789
CHECK_INTERVAL_MINUTES=60
SEARCH_KEYWORDS=бизнес-аналитик,business analyst,системный аналитик
HH_AREA=1
```

**Значения `HH_AREA`:** `1` = Москва, `2` = Санкт-Петербург, `0` = вся Россия

### 4. Запустить

```bash
# Режим планировщика (работает непрерывно)
python main.py

# Однократная проверка
python main.py --once

# Статистика собранных вакансий
python main.py --stats
```

## Настройка параметров (`.env`)

| Параметр | Описание | По умолчанию |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота | — |
| `TELEGRAM_CHAT_ID` | ID чата для уведомлений | — |
| `CHECK_INTERVAL_MINUTES` | Интервал проверки (мин) | `60` |
| `SEARCH_KEYWORDS` | Ключевые слова через запятую | `бизнес-аналитик,business analyst` |
| `HH_AREA` | Регион hh.ru | `1` (Москва) |
| `MIN_SALARY` | Минимальная зарплата (0 = любая) | `0` |
| `EXPERIENCE` | Опыт: `noExperience`, `between1And3`, `between3And6`, `moreThan6` | пусто (любой) |
| `DB_PATH` | Путь к файлу БД | `jobs.db` |

## Структура проекта

```
├── main.py          # Точка входа и планировщик
├── bot.py           # Отправка в Telegram
├── storage.py       # SQLite — хранение просмотренных вакансий
├── config.py        # Загрузка конфигурации из .env
├── scrapers/
│   ├── base.py      # Базовый класс и модель Job
│   ├── hh.py        # hh.ru (API)
│   ├── habr.py      # Habr Career
│   ├── getmatch.py  # GetMatch
│   ├── superjob.py  # SuperJob
│   └── linkedin.py  # LinkedIn
├── requirements.txt
└── .env.example
```

## Запуск через systemd (Linux)

Создайте `/etc/systemd/system/job-bot.service`:

```ini
[Unit]
Description=Job Bot BA
After=network.target

[Service]
WorkingDirectory=/path/to/work-project
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable job-bot
systemctl start job-bot
```

## Пример уведомления в Telegram

```
🔔 Business Analyst
🏢 Сбербанк
💰 от 150,000 ₽
📍 Москва
⏳ Опыт от 3 лет
🌐 hh.ru
🔗 Открыть вакансию
```
