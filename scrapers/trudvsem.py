import logging
import requests
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class TrudvsemScraper(BaseScraper):
    SOURCE_NAME = "trudvsem.ru"

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
                logger.error("trudvsem error for '%s': %s", keyword, e)
        return jobs

    def _fetch_keyword(self, keyword: str) -> list[Job]:
        resp = requests.get(
            "https://trudvsem.ru/vacancy/search",
            params={"text": keyword, "limit": 20},
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for item in data.get("results", {}).get("vacancies", []):
            v = item.get("vacancy", {})
            job_id = "tv_" + str(v.get("id", ""))
            title = v.get("job-name", "")
            if not title:
                continue
            company = v.get("company", {}).get("name", "Не указана")
            sal = v.get("salary", {})
            s_from = sal.get("salary_from")
            s_to = sal.get("salary_to")
            salary = None
            if s_from or s_to:
                salary = f"{s_from or ''}–{s_to or ''} руб."
            addresses = v.get("addresses", {}).get("address", [])
            location = addresses[0].get("location") if addresses else None
            vac_url = v.get("vac_url", "")
            if not vac_url:
                continue
            jobs.append(Job(
                id=job_id,
                source=self.SOURCE_NAME,
                title=title,
                company=company,
                url=vac_url,
                salary=salary,
                location=location,
            ))
        return jobs
