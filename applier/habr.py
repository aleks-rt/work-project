import logging
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from .base import BaseApplier, ApplyResult

logger = logging.getLogger(__name__)


class HabrApplier(BaseApplier):
    SOURCE = "habr.career"

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
                page.goto("https://career.habr.com/users/sign_in", timeout=30000)
                page.wait_for_selector("input[name='user[email]']", timeout=10000)
                page.fill("input[name='user[email]']", self.email)
                page.fill("input[name='user[password]']", self.password)
                page.click("input[type='submit']")
                time.sleep(3)

                if "sign_in" in page.url:
                    return ApplyResult(False, "Неверный логин или пароль на Habr Career")

                # Переход на вакансию
                page.goto(vacancy_url, timeout=30000)
                time.sleep(2)

                # Нажать кнопку отклика
                try:
                    page.wait_for_selector(
                        "a.button--blue[href*='respond'], button.button--blue",
                        timeout=8000,
                    )
                    page.click("a.button--blue[href*='respond'], button.button--blue")
                    time.sleep(2)
                except PWTimeout:
                    return ApplyResult(False, "Не найдена кнопка отклика на Habr Career")

                # Если открылась форма с сопроводительным письмом
                try:
                    submit = page.query_selector("input[type='submit'], button[type='submit']")
                    if submit:
                        submit.click()
                        time.sleep(2)
                except Exception:
                    pass

                return ApplyResult(True, f"Отклик на Habr Career отправлен: {vacancy_title}")

            except Exception as e:
                logger.error("Habr apply error: %s", e)
                return ApplyResult(False, f"Ошибка при отклике на Habr Career: {e}")
            finally:
                browser.close()
