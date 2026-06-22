#!/usr/bin/env python3
"""
Job Bot — собирает вакансии бизнес-аналитика с hh.ru, getmatch, habr.career,
superjob и linkedin, отправляет новые в Telegram.

Запуск:
    python main.py              # запуск с планировщиком
    python main.py --once       # однократная проверка и выход
    python main.py --stats      # показать статистику БД
"""

import argparse
import logging
import sys
import time

import schedule

from bot import send_job_sync, send_text_sync
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


def check_jobs():
    logger.info("Запуск проверки вакансий (ключевые слова: %s)", SEARCH_KEYWORDS)
    new_count = 0

    for ScraperClass in ALL_SCRAPERS:
        scraper = ScraperClass()
        logger.info("Источник: %s", scraper.SOURCE_NAME)
        try:
            jobs = scraper.fetch(SEARCH_KEYWORDS)
            logger.info("  Найдено: %d вакансий", len(jobs))
            for job in jobs:
                if not is_seen(job.id):
                    mark_seen(job.id, job.source, job.title, job.company, job.url)
                    send_job_sync(job)
                    new_count += 1
                    logger.info("  + Новая: [%s] %s @ %s", job.source, job.title, job.company)
                    time.sleep(0.5)  # пауза между сообщениями
        except Exception as e:
            logger.error("Ошибка скрапера %s: %s", scraper.SOURCE_NAME, e)

    logger.info("Проверка завершена. Новых вакансий: %d", new_count)
    if new_count == 0:
        logger.info("Новых вакансий нет.")


def show_stats():
    stats = get_stats()
    lines = [f"📊 <b>Статистика бота</b>", f"Всего вакансий в БД: {stats['total']}"]
    for source, cnt in stats["by_source"].items():
        lines.append(f"  • {source}: {cnt}")
    print("\n".join(lines).replace("<b>", "").replace("</b>", ""))


def validate_config():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан в .env")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID не задан в .env")
        sys.exit(1)
    if not SEARCH_KEYWORDS:
        logger.error("SEARCH_KEYWORDS пуст")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Job Bot — поиск вакансий BA")
    parser.add_argument("--once", action="store_true", help="Однократная проверка")
    parser.add_argument("--stats", action="store_true", help="Показать статистику")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    validate_config()
    init_db()

    if args.once:
        check_jobs()
        return

    logger.info(
        "Бот запущен. Интервал проверки: %d мин. Ключевые слова: %s",
        CHECK_INTERVAL_MINUTES,
        SEARCH_KEYWORDS,
    )
    send_text_sync(
        f"🤖 <b>Job Bot запущен</b>\n"
        f"Ищу вакансии: {', '.join(SEARCH_KEYWORDS)}\n"
        f"Интервал: каждые {CHECK_INTERVAL_MINUTES} мин."
    )

    # первая проверка сразу при старте
    check_jobs()

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_jobs)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
