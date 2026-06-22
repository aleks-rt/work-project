import logging
import os
import requests
from bs4 import BeautifulSoup
import anthropic
from config import HEADERS

logger = logging.getLogger(__name__)

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY не задан в .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def extract_resume_text(resume_path: str) -> str:
    ext = os.path.splitext(resume_path)[1].lower()
    try:
        if ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(resume_path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif ext in (".docx", ".doc"):
            from docx import Document
            doc = Document(resume_path)
            return "\n".join(p.text for p in doc.paragraphs)
        else:
            with open(resume_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        logger.error("Ошибка чтения резюме: %s", e)
        return ""


def fetch_vacancy_description(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        # hh.ru
        el = soup.select_one("[data-qa='vacancy-description']")
        if el:
            return el.get_text(separator="\n", strip=True)
        # habr.career
        el = soup.select_one(".vacancy-description, .job-description, article")
        if el:
            return el.get_text(separator="\n", strip=True)
        # fallback — весь текст страницы
        return soup.get_text(separator="\n", strip=True)[:3000]
    except Exception as e:
        logger.error("Ошибка загрузки вакансии: %s", e)
        return ""


def generate_cover_letter(
    vacancy_title: str,
    company: str,
    vacancy_description: str,
    resume_text: str,
) -> str:
    prompt = f"""Ты — карьерный консультант. Напиши сопроводительное письмо для отклика на вакансию.

ВАКАНСИЯ: {vacancy_title}
КОМПАНИЯ: {company}

ОПИСАНИЕ ВАКАНСИИ:
{vacancy_description[:2000]}

МОЁ РЕЗЮМЕ:
{resume_text[:2000]}

Требования к письму:
- Длина: 150-200 слов
- Тон: профессиональный, но живой
- Подчеркни соответствие моего опыта требованиям вакансии
- Не начинай с "Уважаемые" — начни с сути
- Не используй шаблонные фразы вроде "рад предложить свою кандидатуру"
- Напиши только текст письма, без заголовков и пояснений"""

    message = get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def analyze_resume(
    vacancy_title: str,
    company: str,
    vacancy_description: str,
    resume_text: str,
) -> str:
    prompt = f"""Ты — карьерный консультант. Сравни резюме с требованиями вакансии и дай конкретные рекомендации.

ВАКАНСИЯ: {vacancy_title}
КОМПАНИЯ: {company}

ОПИСАНИЕ ВАКАНСИИ:
{vacancy_description[:2000]}

МОЁ РЕЗЮМЕ:
{resume_text[:2000]}

Дай ответ в формате:

✅ СОВПАДЕНИЯ (что уже есть в резюме и нужно вакансии):
— ...

❌ ПРОБЕЛЫ (чего не хватает):
— ...

💡 ЧТО ДОБАВИТЬ В РЕЗЮМЕ:
— ...

⭐ ОБЩАЯ ОЦЕНКА СООТВЕТСТВИЯ: X/10
Коротко объясни оценку."""

    message = get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
