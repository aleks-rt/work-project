import logging
import hashlib
import requests
from bs4 import BeautifulSoup
from config import HEADERS
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)

BASE_URL = "https://rabota.ru"


class RabotaScraper(BaseScraper):
    SOURCE_NAME = "rabota.ru"

    def fetch(self, keywords: list[str]) -> list[Job]:
        jobs: list[Job] = []
        seen_ids: set[str] = set()
        for keyword in keywords:
            try:
                for j in self._fetch_keyword(keyword):
                    if j.id not in seen_ids:
                        seen_ids.add(j.id)
                        jobs.append(j)
            except Exception as e:
                logger.error("rabota.ru error for '%s': %s", keyword, e)
        return jobs

    def _fetch_keyword(self, keyword: str) -> list[Job]:
        url = f"{BASE_URL}/vacancy/list/"
        params = {"query": keyword, "sort": "date"}
        headers = {
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []

        cards = soup.select("a[href*='/vacancy/']") or soup.select("[data-test='vacancy-title']")
        seen_hrefs: set[str] = set()
        for el in cards:
            href = el.get("href", "")
            if not href or href in seen_hrefs or "/vacancy/" not in href:
                continue
            seen_hrefs.add(href)

            full_url = BASE_URL + href if href.startswith("/") else href
            job_id = "rb_" + hashlib.md5(href.encode()).hexdigest()[:12]

            title = el.get_text(strip=True)[:120]
            if not title or len(title) < 5:
                continue

            container = el.find_parent("article") or el.find_parent("div")
            company, salary = "Не указана", None
            if container:
                company_el = container.select_one("[data-test='company-name'], [class*='company']")
                if company_el:
                    company = company_el.get_text(strip=True)
                salary_el = container.select_one("[data-test='salary'], [class*='salary']")
                if salary_el:
                    salary = salary_el.get_text(strip=True)

            jobs.append(Job(
                id=job_id,
                source=self.SOURCE_NAME,
                title=title,
                company=company,
                url=full_url,
                salary=salary,
            ))

        return jobs
