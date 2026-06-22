import logging
import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.base import Job

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=TELEGRAM_BOT_TOKEN)
    return _bot


async def send_job(job: Job):
    bot = get_bot()
    text = job.format_message()
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )
    except TelegramError as e:
        logger.error("Telegram send error: %s", e)


async def send_text(text: str):
    bot = get_bot()
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        logger.error("Telegram send error: %s", e)


def send_job_sync(job: Job):
    asyncio.run(send_job(job))


def send_text_sync(text: str):
    asyncio.run(send_text(text))
