import logging
import requests
from bs4 import BeautifulSoup
from config import HEADERS
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)

BASE_URL = "https://www.superjob.ru"


class SuperjobScraper(BaseScraper):
    SOURCE_NAME = "superjob.ru"

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
                logger.error("superjob error for '%s': %s", keyword, e)
        return jobs

    def _fetch_keyword(self, keyword: str) -> list[Job]:
        url = f"{BASE_URL}/vacancy/search/"
        params = {"keywords": keyword, "noGeo": 1}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []

        # superjob vacancy cards
        cards = soup.select("[class*='VacancyCard_']")
        if not cards:
            # fallback: look for vacancy links
            cards = soup.select("a[href*='/vakansii/']")

        seen_hrefs = set()
        for card in cards:
            link = card if card.name == "a" else card.select_one("a[href*='/vakansii/']")
            if not link:
                continue
            href = link.get("href", "")
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            full_url = BASE_URL + href if href.startswith("/") else href
            slug = href.rstrip("/").split("/")[-1]
            job_id = f"sj_{slug}"

            title_el = card.select_one("h3, h2, [class*='title']")
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)[:80]
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
