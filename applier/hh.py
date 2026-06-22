import logging
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from .base import BaseApplier, ApplyResult

logger = logging.getLogger(__name__)


class HHApplier(BaseApplier):
    SOURCE = "hh.ru"

    def apply(self, vacancy_url: str, vacancy_title: str) -> ApplyResult:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = ctx.new_page()
            try:
                # Логин
                page.goto("https://hh.ru/account/login", timeout=30000)
                page.wait_for_selector("input[name='login']", timeout=10000)
                page.fill("input[name='login']", self.email)
                page.click("button[data-qa='expand-login-by-password']")
                page.wait_for_selector("input[name='password']", timeout=5000)
                page.fill("input[name='password']", self.password)
                page.click("button[data-qa='account-login-submit']")
                page.wait_for_url("**//**", timeout=15000)
                time.sleep(2)

                if "account/login" in page.url:
                    return ApplyResult(False, "Неверный логин или пароль на hh.ru")

                # Переход на вакансию
                page.goto(vacancy_url, timeout=30000)
                page.wait_for_selector("[data-qa='vacancy-response-link-top']", timeout=10000)
                page.click("[data-qa='vacancy-response-link-top']")
                time.sleep(2)

                # Выбор резюме (если появился диалог)
                try:
                    page.wait_for_selector("[data-qa='resume-title']", timeout=5000)
                    # Выбираем первое резюме
                    page.click("[data-qa='resume-title']")
                    time.sleep(1)
                    submit = page.query_selector("[data-qa='vacancy-response-submit-popup']")
                    if submit:
                        submit.click()
                        time.sleep(2)
                except PWTimeout:
                    pass  # диалог не появился — отклик уже отправлен

                # Проверяем результат
                try:
                    page.wait_for_selector(
                        "[data-qa='vacancy-response-letter-open'], "
                        "[data-qa='response-status']",
                        timeout=5000,
                    )
                    return ApplyResult(True, f"Отклик на hh.ru отправлен: {vacancy_title}")
                except PWTimeout:
                    return ApplyResult(True, f"Отклик, вероятно, отправлен: {vacancy_title}")

            except Exception as e:
                logger.error("HH apply error: %s", e)
                return ApplyResult(False, f"Ошибка при отклике на hh.ru: {e}")
            finally:
                browser.close()
