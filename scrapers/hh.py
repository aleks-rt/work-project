import logging
import time
import requests
from config import EXPERIENCE, MIN_SALARY
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)

HH_API = "https://api.hh.ru/vacancies"

# 113 = вся Россия, 1 = Москва, 2 = Санкт-Петербург
HH_AREA = "113"

HEADERS = {
    "User-Agent": "JobBot/1.0 (job search bot; contact: user@example.com)",
    "HH-User-Agent": "JobBot/1.0 (job search bot; contact: user@example.com)",
    "Accept": "application/json",
}


def _salary_str(salary: dict | None) -> str | None:
    if not salary:
        return None
    parts = []
    if salary.get("from"):
        parts.append(f"от {salary['from']:,}")
    if salary.get("to"):
        parts.append(f"до {salary['to']:,}")
    currency = salary.get("currency", "")
    if currency == "RUR":
        currency = "₽"
    return " ".join(parts) + f" {currency}".strip() if parts else None


class HHScraper(BaseScraper):
    SOURCE_NAME = "hh.ru"

    def fetch(self, keywords: list[str]) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for keyword in keywords:
            try:
                for job in self._fetch_keyword(keyword):
                    if job.id not in seen:
                        seen.add(job.id)
                        jobs.append(job)
                time.sleep(0.5)
            except Exception as e:
                logger.error("hh.ru error for '%s': %s", keyword, e)
        return jobs

    def _fetch_keyword(self, keyword: str) -> list[Job]:
        params = {
            "text": keyword,
            "area": HH_AREA,
            "per_page": 50,
            "order_by": "publication_time",
        }
        if MIN_SALARY:
            params["salary"] = MIN_SALARY
            params["only_with_salary"] = "true"
        if EXPERIENCE:
            params["experience"] = EXPERIENCE

        resp = requests.get(HH_API, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for item in data.get("items", []):
            employer = item.get("employer") or {}
            area = item.get("area") or {}
            tags = [r["name"] for r in item.get("professional_roles", [])]

            jobs.append(Job(
                id=f"hh_{item['id']}",
                source=self.SOURCE_NAME,
                title=item.get("name", ""),
                company=employer.get("name", "Не указана"),
                url=item.get("alternate_url", ""),
                salary=_salary_str(item.get("salary")),
                location=area.get("name"),
                tags=tags,
            ))
        return jobs
