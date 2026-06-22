import os
from dotenv import load_dotenv
from .base import ApplyResult
from .hh import HHApplier
from .habr import HabrApplier

load_dotenv("credentials.env")


def get_applier(source: str, resume_path: str):
    """Возвращает нужный апплаер по названию источника."""
    source = source.lower()

    if "hh" in source:
        email = os.getenv("HH_EMAIL", "")
        password = os.getenv("HH_PASSWORD", "")
        if email and password and "your_email" not in email:
            return HHApplier(email, password, resume_path)

    if "habr" in source:
        email = os.getenv("HABR_EMAIL", "")
        password = os.getenv("HABR_PASSWORD", "")
        if email and password and "your_email" not in email:
            return HabrApplier(email, password, resume_path)

    return None


def auto_apply(source: str, vacancy_url: str, vacancy_title: str, resume_path: str) -> ApplyResult:
    applier = get_applier(source, resume_path)
    if applier is None:
        return ApplyResult(
            False,
            f"Автоотклик для {source} не настроен.\n"
            f"Заполните credentials.env и убедитесь, что файл резюме загружен."
        )
    return applier.apply(vacancy_url, vacancy_title)
