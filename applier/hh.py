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
                ),
                locale="ru-RU",
            )
            page = ctx.new_page()
            try:
                page.goto("https://hh.ru/account/login", timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)

                # Выбираем "Я соискатель"
                for sel in [
                    "input[value='APPLICANT']",
                    "label:has-text('Я соискатель')",
                    "input[name='account-type'][value='applicant']",
                ]:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        time.sleep(1)
                        break

                # Нажимаем "Продолжить" или "Войти"
                for sel in [
                    "button[data-qa='account-login-submit']",
                    "button[type='submit']",
                    "button:has-text('Продолжить')",
                    "button:has-text('Войти')",
                ]:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        time.sleep(2)
                        break

                # Вводим email
                for sel in ["input[name='login']", "input[type='email']", "input[placeholder*='mail']"]:
                    el = page.query_selector(sel)
                    if el:
                        el.fill(self.email)
                        break
                else:
                    return ApplyResult(False, "Не найдено поле email на hh.ru")

                # Нажимаем "Войти с паролем"
                for sel in [
                    "button[data-qa='expand-login-by-password']",
                    "button:has-text('Войти с паролем')",
                    "a:has-text('Войти с паролем')",
                ]:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        time.sleep(1)
                        break

                # Нажимаем "Продолжить" если есть
                for sel in ["button[type='submit']", "button:has-text('Продолжить')"]:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        time.sleep(2)
                        break

                # Вводим пароль
                for sel in ["input[name='password']", "input[type='password']"]:
                    el = page.query_selector(sel)
                    if el:
                        el.fill(self.password)
                        break
                else:
                    return ApplyResult(False, "Не найдено поле пароля на hh.ru")

                # Нажимаем войти
                for sel in [
                    "button[data-qa='account-login-submit']",
                    "button[type='submit']",
                ]:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        break

                time.sleep(3)

                if "account/login" in page.url:
                    return ApplyResult(False, "Неверный логин или пароль на hh.ru")

                # Переход на вакансию
                page.goto(vacancy_url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)

                # Кнопка отклика
                for sel in [
                    "[data-qa='vacancy-response-link-top']",
                    "[data-qa='vacancy-response-btn-top']",
                    "button:has-text('Откликнуться')",
                    "a:has-text('Откликнуться')",
                ]:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        time.sleep(2)
                        break
                else:
                    return ApplyResult(False, "Не найдена кнопка отклика на hh.ru")

                # Выбор резюме в диалоге
                try:
                    page.wait_for_selector("[data-qa='resume-title']", timeout=5000)
                    page.click("[data-qa='resume-title']")
                    time.sleep(1)
                    for sel in ["[data-qa='vacancy-response-submit-popup']", "button[type='submit']"]:
                        el = page.query_selector(sel)
                        if el:
                            el.click()
                            time.sleep(2)
                            break
                except PWTimeout:
                    pass

                return ApplyResult(True, f"Отклик на hh.ru отправлен: {vacancy_title}")

            except Exception as e:
                logger.error("HH apply error: %s", e)
                return ApplyResult(False, f"Ошибка при отклике на hh.ru: {e}")
            finally:
                browser.close()
