import logging
import httpx
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.base import Job

logger = logging.getLogger(__name__)


def get_bot() -> Bot:
    return Bot(token=TELEGRAM_BOT_TOKEN)


def send_job_sync(job: Job):
    _send(job.format_message())


def send_text_sync(text: str):
    _send(text)


def _send(text: str):
    try:
        with httpx.Client() as client:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            resp = client.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            }, timeout=15)
            data = resp.json()
            if not data.get("ok"):
                logger.error("Telegram error: %s", data.get("description"))
    except Exception as e:
        logger.error("Telegram send error: %s", e)
