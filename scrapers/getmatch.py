import logging
import hashlib
import requests
from bs4 import BeautifulSoup
from config import HEADERS
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)

BASE_URL = "https://getmatch.ru"


class GetMatchScraper(BaseScraper):
    SOURCE_NAME = "getmatch.ru"

    def fetch(self, keywords: list[str]) -> list[Job]:
        jobs: list[Job] = []
        seen_ids = set()
        for keyword in keywords:
            try:
                fetched = self._fetch_keyword(keyword)
                for j in fetched:
                    if j.id not in seen_ids:
                        seen_ids.add(j.id)
                        jobs.append(j)
            except Exception as e:
                logger.error("getmatch error for '%s': %s", keyword, e)
        return jobs

    def _fetch_keyword(self, keyword: str) -> list[Job]:
        url = f"{BASE_URL}/vacancies"
        params = {"q": keyword}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []

        # getmatch uses data-driven cards
        cards = soup.select("a[href*='/vacancies/']")
        seen_hrefs = set()
        for card in cards:
            href = card.get("href", "")
            if not href or href in seen_hrefs or "/vacancies/" not in href:
                continue
            if href.startswith("/vacancies/") and len(href.split("/")) < 3:
                continue
            seen_hrefs.add(href)

            full_url = BASE_URL + href if href.startswith("/") else href
            job_id = "gm_" + hashlib.md5(href.encode()).hexdigest()[:12]

            title_el = card.select_one("h2, h3, [class*='title'], [class*='name']")
            title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:80]
            if not title:
                continue

            company_el = card.select_one("[class*='company'], [class*='employer']")
            company = company_el.get_text(strip=True) if company_el else "Не указана"

            salary_el = card.select_one("[class*='salary'], [class*='compensation']")
            salary = salary_el.get_text(strip=True) if salary_el else None

            jobs.append(
                Job(
                    id=job_id,
                    source=self.SOURCE_NAME,
                    title=title,
                    company=company,
                    url=full_url,
                    salary=salary,
                )
            )

        return jobs
