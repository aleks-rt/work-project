#!/usr/bin/env python3
"""
Job Bot — собирает вакансии бизнес-аналитика и отправляет в Telegram.

Запуск:
    python main.py          # основной режим (бот + планировщик)
    python main.py --once   # однократная проверка вакансий
    python main.py --stats  # статистика БД
"""

import argparse
import logging
import sys
import threading
import time

import schedule

from bot import send_job_sync, send_text_sync, run_bot
from config import CHECK_INTERVAL_MINUTES, SEARCH_KEYWORDS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers import ALL_SCRAPERS
from storage import init_db, is_seen, mark_seen, get_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

BA_KEYWORDS = [
    "бизнес-аналитик", "бизнес аналитик", "business analyst", "бизнес-анализ",
]


def is_ba_job(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in BA_KEYWORDS)


def check_jobs():
    logger.info("Запуск проверки вакансий")
    new_count = 0

    for ScraperClass in ALL_SCRAPERS:
        scraper = ScraperClass()
        logger.info("Источник: %s", scraper.SOURCE_NAME)
        try:
            jobs = scraper.fetch(SEARCH_KEYWORDS)
            jobs = [j for j in jobs if is_ba_job(j.title)]
            logger.info("  Найдено: %d вакансий BA", len(jobs))
            for job in jobs:
                if not is_seen(job.id):
                    mark_seen(job.id, job.source, job.title, job.company, job.url)
                    send_job_sync(job)
                    new_count += 1
                    logger.info("  + Новая: [%s] %s @ %s", job.source, job.title, job.company)
                    time.sleep(0.5)
        except Exception as e:
            logger.error("Ошибка скрапера %s: %s", scraper.SOURCE_NAME, e)

    logger.info("Проверка завершена. Новых вакансий: %d", new_count)


def show_stats():
    stats = get_stats()
    print(f"Всего вакансий в БД: {stats['total']}")
    for source, cnt in stats["by_source"].items():
        print(f"  {source}: {cnt}")


def validate_config():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан в .env")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID не задан в .env")
        sys.exit(1)


def scheduler_thread():
    check_jobs()
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_jobs)
    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Однократная проверка")
    parser.add_argument("--stats", action="store_true", help="Статистика")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    validate_config()
    init_db()

    if args.once:
        check_jobs()
        return

    logger.info("Бот запущен. Интервал: %d мин.", CHECK_INTERVAL_MINUTES)

    # планировщик вакансий в отдельном потоке
    t = threading.Thread(target=scheduler_thread, daemon=True)
    t.start()

    # основной поток — polling Telegram (обработка кнопок и команд)
    run_bot()


if __name__ == "__main__":
    main()
