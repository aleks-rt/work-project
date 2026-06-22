import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))

SEARCH_KEYWORDS = [
    kw.strip()
    for kw in os.getenv(
        "SEARCH_KEYWORDS", "бизнес-аналитик,business analyst"
    ).split(",")
    if kw.strip()
]

HH_AREA = os.getenv("HH_AREA", "1")
MIN_SALARY = int(os.getenv("MIN_SALARY", "0"))
EXPERIENCE = os.getenv("EXPERIENCE", "")
DB_PATH = os.getenv("DB_PATH", "jobs.db")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
