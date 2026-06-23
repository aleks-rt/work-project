import logging
import os
import threading
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.base import Job
from storage import get_job, get_user_data, save_user_data

logger = logging.getLogger(__name__)
_app = None
RESUME_PATH = "resume_saved"


def _http_send(payload: dict):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json=payload)
        if not r.json().get("ok"):
            logger.error("Telegram error: %s", r.json().get("description"))


def _generate_and_send_letter(job: dict):
    resume_path = get_user_data("resume_local_path")
    if not resume_path or not os.path.exists(resume_path):
        return
    try:
        from ai_helper import generate_cover_letter, extract_resume_text, fetch_vacancy_description
        resume_text = extract_resume_text(resume_path)
        vacancy_desc = fetch_vacancy_description(job["url"])
        letter = generate_cover_letter(job["title"], job["company"], vacancy_desc, resume_text)
        _http_send({"chat_id": TELEGRAM_CHAT_ID, "text": letter})
    except Exception as e:
        logger.error("Ошибка генерации письма: %s", e)


def send_job_sync(job: Job):
    keyboard = [[
        {"text": "🔗 Открыть", "url": job.url},
        {"text": "📊 Анализ резюме", "callback_data": f"analyze:{job.id}"},
    ]]
    _http_send({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": job.format_message(),
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": keyboard},
    })
    job_dict = {"title": job.title, "company": job.company, "url": job.url}
    threading.Thread(target=_generate_and_send_letter, args=(job_dict,), daemon=True).start()


def send_text_sync(text: str):
    _http_send({"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"})


def build_app():
    global _app
    if _app is None:
        _app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        _app.add_handler(CommandHandler("start", cmd_start))
        _app.add_handler(CommandHandler("resume", cmd_resume))
        _app.add_handler(CommandHandler("stats", cmd_stats))
        _app.add_handler(MessageHandler(filters.Document.ALL, handle_resume_upload))
        _app.add_handler(CallbackQueryHandler(handle_analyze, pattern=r"^analyze:"))
    return _app


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я слежу за вакансиями бизнес-аналитика.\n\n"
        "Загрузи резюме: /resume\n"
        "Статистика: /stats\n\n"
        "Под каждой вакансией 2 кнопки:\n"
        "🔗 Открыть — перейти на сайт\n"
        "📊 Анализ резюме — ИИ сравнит резюме с вакансией\n\n"
        "Письмо для отклика генерируется автоматически под каждую вакансию."
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пришли файл резюме (PDF или Word) — я его сохраню.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from storage import get_stats
    stats = get_stats()
    lines = ["Вакансий в базе: " + str(stats["total"])]
    for source, cnt in stats["by_source"].items():
        lines.append(f"  {source}: {cnt}")
    await update.message.reply_text("\n".join(lines))


async def handle_resume_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    save_user_data("resume_file_id", doc.file_id)
    save_user_data("resume_name", doc.file_name or "resume")
    file = await context.bot.get_file(doc.file_id)
    ext = os.path.splitext(doc.file_name or "resume.pdf")[1]
    local_path = RESUME_PATH + ext
    await file.download_to_drive(local_path)
    save_user_data("resume_local_path", local_path)
    await update.message.reply_text(f"Резюме «{doc.file_name}» сохранено!")


async def handle_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    job_id = query.data.replace("analyze:", "")
    job = get_job(job_id)
    if not job:
        await query.message.reply_text("Вакансия не найдена.")
        return
    resume_path = get_user_data("resume_local_path")
    if not resume_path or not os.path.exists(resume_path):
        await query.message.reply_text("Сначала загрузи резюме через /resume")
        return
    await query.message.reply_text("Анализирую резюме под вакансию...")
    chat_id = query.message.chat_id

    def do_analyze():
        try:
            from ai_helper import analyze_resume, extract_resume_text, fetch_vacancy_description
            resume_text = extract_resume_text(resume_path)
            vacancy_desc = fetch_vacancy_description(job["url"])
            analysis = analyze_resume(job["title"], job["company"], vacancy_desc, resume_text)
            _http_send({"chat_id": chat_id, "text": f"📊 <b>Анализ резюме</b>\n\n{analysis}", "parse_mode": "HTML"})
        except Exception as e:
            _http_send({"chat_id": chat_id, "text": f"Ошибка анализа: {e}"})

    threading.Thread(target=do_analyze, daemon=True).start()


def make_keyboard(job: Job) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Открыть", url=job.url),
        InlineKeyboardButton("📊 Анализ резюме", callback_data=f"analyze:{job.id}"),
    ]])


def run_bot():
    app = build_app()
    app.run_polling(drop_pending_updates=True)
