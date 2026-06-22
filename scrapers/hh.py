import logging
import hashlib
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class HHScraper(BaseScraper):
    SOURCE_NAME = "hh.ru"

    def fetch(self, keywords: list) -> list:
        jobs = []
        seen = set()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="ru-RU",
            )
            page = ctx.new_page()
            for keyword in keywords:
                try:
                    for job in self._fetch_keyword(page, keyword):
                        if job.id not in seen:
                            seen.add(job.id)
                            jobs.append(job)
                except Exception as e:
                    logger.error("hh.ru error for '%s': %s", keyword, e)
            browser.close()
        return jobs

    def _fetch_keyword(self, page, keyword: str) -> list:
        url = (
            f"https://hh.ru/search/vacancy"
            f"?text={keyword.replace(' ', '+')}"
            f"&area=113&order_by=publication_time&search_period=1"
        )
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("[data-qa='vacancy-serp__vacancy']", timeout=10000)
        except PWTimeout:
            logger.warning("hh.ru: вакансии не найдены для '%s'", keyword)
            return []

        cards = page.query_selector_all("[data-qa='vacancy-serp__vacancy']")
        jobs = []
        for card in cards:
            try:
                title_el = card.query_selector("[data-qa='serp-item__title']")
                if not title_el:
                    continue
                title = title_el.inner_text().strip()
                href = title_el.get_attribute("href") or ""
                job_url = href.split("?")[0]
                job_id = "hh_" + hashlib.md5(job_url.encode()).hexdigest()[:12]

                company_el = card.query_selector("[data-qa='vacancy-serp__vacancy-employer']")
                company = company_el.inner_text().strip() if company_el else "Не указана"

                salary_el = card.query_selector("[data-qa='vacancy-serp__vacancy-compensation']")
                salary = salary_el.inner_text().strip() if salary_el else None

                location_el = card.query_selector("[data-qa='vacancy-serp__vacancy-address']")
                location = location_el.inner_text().strip() if location_el else None

                jobs.append(Job(
                    id=job_id,
                    source=self.SOURCE_NAME,
                    title=title,
                    company=company,
                    url=job_url,
                    salary=salary,
                    location=location,
                ))
            except Exception as e:
                logger.debug("hh.ru card parse error: %s", e)
        return jobs
