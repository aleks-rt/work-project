import logging
import requests
from bs4 import BeautifulSoup
from config import HEADERS
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)

BASE_URL = "https://career.habr.com"


class HabrCareerScraper(BaseScraper):
    SOURCE_NAME = "habr.career"

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
                logger.error("habr.career error for '%s': %s", keyword, e)
        return jobs

    def _fetch_keyword(self, keyword: str) -> list[Job]:
        url = f"{BASE_URL}/vacancies"
        params = {"q": keyword, "sort": "date", "type": "all"}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []

        cards = soup.select(".vacancy-card")
        for card in cards:
            title_el = card.select_one(".vacancy-card__title a")
            if not title_el:
                continue

            href = title_el.get("href", "")
            full_url = BASE_URL + href if href.startswith("/") else href
            job_id = "habr_" + href.split("/")[-1].split("?")[0]
            title = title_el.get_text(strip=True)

            company_el = card.select_one(".vacancy-card__company-title, .company_name")
            company = company_el.get_text(strip=True) if company_el else "Не указана"

            salary_el = card.select_one(".vacancy-card__salary, .basic-salary")
            salary = salary_el.get_text(strip=True) if salary_el else None

            location_el = card.select_one(".vacancy-card__meta .icon_location")
            location = None
            if location_el and location_el.parent:
                location = location_el.parent.get_text(strip=True)

            tags = [
                t.get_text(strip=True)
                for t in card.select(".vacancy-card__skills .skill")
            ]

            jobs.append(
                Job(
                    id=job_id,
                    source=self.SOURCE_NAME,
                    title=title,
                    company=company,
                    url=full_url,
                    salary=salary,
                    location=location,
                    tags=tags,
                )
            )

        return jobs
