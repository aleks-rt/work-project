import logging
import hashlib
import requests
from bs4 import BeautifulSoup
from config import HEADERS
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)

# LinkedIn публичный поиск (без авторизации)
SEARCH_URL = "https://www.linkedin.com/jobs/search/"


class LinkedInScraper(BaseScraper):
    SOURCE_NAME = "linkedin.com"

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
                logger.error("linkedin error for '%s': %s", keyword, e)
        return jobs

    def _fetch_keyword(self, keyword: str) -> list[Job]:
        params = {
            "keywords": keyword,
            "location": "Russia",
            "f_TPR": "r86400",  # за последние 24 часа
            "sortBy": "DD",
        }
        headers = {
            **HEADERS,
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }
        resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []

        cards = soup.select(".base-card, .job-search-card")
        for card in cards:
            link = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
            if not link:
                continue

            href = link.get("href", "").split("?")[0]
            if not href:
                continue

            job_id = "li_" + hashlib.md5(href.encode()).hexdigest()[:12]

            title_el = card.select_one(
                "h3.base-search-card__title, .job-search-card__title"
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            company_el = card.select_one(
                "h4.base-search-card__subtitle, .job-search-card__company-name"
            )
            company = company_el.get_text(strip=True) if company_el else "Не указана"

            location_el = card.select_one(
                ".job-search-card__location, .base-search-card__metadata"
            )
            location = location_el.get_text(strip=True) if location_el else None

            jobs.append(
                Job(
                    id=job_id,
                    source=self.SOURCE_NAME,
                    title=title,
                    company=company,
                    url=href,
                    location=location,
                )
            )

        return jobs
