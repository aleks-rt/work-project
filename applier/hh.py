import logging
import re
from hh_auth import get_valid_token, get_my_resumes, apply_to_vacancy
from .base import BaseApplier, ApplyResult

logger = logging.getLogger(__name__)


def _extract_vacancy_id(url: str) -> str | None:
    m = re.search(r"/vacancy/(\d+)", url)
    return m.group(1) if m else None


class HHApplier(BaseApplier):
    SOURCE = "hh.ru"

    def apply(self, vacancy_url: str, vacancy_title: str) -> ApplyResult:
        token = get_valid_token()
        if not token:
            return ApplyResult(
                False,
                "Не авторизован в hh.ru. Запустите:\n<code>python3 hh_auth.py</code>"
            )

        vacancy_id = _extract_vacancy_id(vacancy_url)
        if not vacancy_id:
            return ApplyResult(False, f"Не удалось извлечь ID вакансии из URL: {vacancy_url}")

        try:
            resumes = get_my_resumes(token)
        except Exception as e:
            return ApplyResult(False, f"Ошибка получения резюме с hh.ru: {e}")

        if not resumes:
            return ApplyResult(False, "На hh.ru нет ни одного резюме. Создайте резюме на сайте.")

        # Берём первое резюме
        resume = resumes[0]
        resume_id = resume["id"]
        resume_title = resume.get("title", "резюме")

        try:
            result = apply_to_vacancy(token, vacancy_id, resume_id)
        except Exception as e:
            return ApplyResult(False, f"Ошибка отклика на hh.ru: {e}")

        if result["status"] in (200, 201):
            return ApplyResult(True, f"Отклик отправлен! Резюме: «{resume_title}»\n{vacancy_title}")
        elif result["status"] == 403:
            return ApplyResult(False, "Уже откликались на эту вакансию или она закрыта.")
        elif result["status"] == 400:
            return ApplyResult(False, f"Ошибка hh.ru: {result['body'][:200]}")
        else:
            return ApplyResult(False, f"hh.ru вернул статус {result['status']}: {result['body'][:200]}")
