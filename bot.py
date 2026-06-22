import logging
import asyncio
import os
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.base import Job
from storage import get_job, get_user_data, save_user_data

logger = logging.getLogger(__name__)
_app = None

RESUME_PATH = "resume_saved"


def build_app():
    global _app
    if _app is None:
        _app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        _app.add_handler(CommandHandler("start", cmd_start))
        _app.add_handler(CommandHandler("resume", cmd_resume))
        _app.add_handler(CommandHandler("stats", cmd_stats))
        _app.add_handler(MessageHandler(filters.Document.ALL, handle_resume_upload))
        _app.add_handler(CallbackQueryHandler(handle_apply, pattern=r"^apply:"))
    return _app


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я слежу за вакансиями бизнес-аналитика.\n\n"
        "📎 /resume — загрузить резюме\n"
        "📊 /stats — статистика\n\n"
        "Когда появится новая вакансия, нажми 'Откликнуться' — "
        "я сам зайду на сайт и подам заявку!"
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📎 Пришли файл резюме (PDF или Word).\n"
        "Я сохраню его и буду прикладывать при автоотклике."
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from storage import get_stats
    stats = get_stats()
    lines = [f"📊 <b>Статистика</b>", f"Вакансий в базе: {stats['total']}"]
    for source, cnt in stats["by_source"].items():
        lines.append(f"  • {source}: {cnt}")
    await update.message.reply_html("\n".join(lines))


async def handle_resume_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    # Сохраняем file_id для отправки обратно при ручном отклике
    save_user_data("resume_file_id", doc.file_id)
    save_user_data("resume_name", doc.file_name or "resume")

    # Скачиваем файл локально для автоотклика
    file = await context.bot.get_file(doc.file_id)
    ext = os.path.splitext(doc.file_name or "resume.pdf")[1]
    local_path = RESUME_PATH + ext
    await file.download_to_drive(local_path)
    save_user_data("resume_local_path", local_path)

    await update.message.reply_text(
        f"✅ Резюме «{doc.file_name}» сохранено!\n"
        "Теперь при нажатии 'Откликнуться' бот сам подаст заявку на сайте."
    )


async def handle_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Отправляю отклик...")

    job_id = query.data.replace("apply:", "")
    job = get_job(job_id)

    if not job:
        await query.message.reply_text("❌ Вакансия не найдена в базе.")
        return

    resume_path = get_user_data("resume_local_path")
    if not resume_path or not os.path.exists(resume_path):
        await query.message.reply_text(
            "❌ Резюме не загружено. Сначала пришли файл резюме командой /resume"
        )
        return

    await query.message.reply_text(
        f"⏳ Отправляю отклик на вакансию:\n<b>{job['title']}</b> — {job['company']}\n"
        f"Сайт: {job['source']}",
        parse_mode=ParseMode.HTML,
    )

    # Запускаем автоотклик в отдельном потоке (Playwright блокирующий)
    def do_apply():
        from applier import auto_apply
        result = auto_apply(job["source"], job["url"], job["title"], resume_path)
        asyncio.run(send_apply_result(query.message.chat_id, result, job))

    threading.Thread(target=do_apply, daemon=True).start()


async def send_apply_result(chat_id, result, job):
    app = build_app()
    if result.success:
        text = f"✅ {result.message}"
    else:
        # При ошибке автоотклика — присылаем резюме вручную
        text = f"⚠️ Автоотклик не удался: {result.message}\n\n🔗 Подай заявку вручную: {job['url']}"
        resume_file_id = get_user_data("resume_file_id")
        if resume_file_id:
            await app.bot.send_document(
                chat_id=chat_id,
                document=resume_file_id,
                caption=f"📎 Резюме для вакансии: {job['title']}",
            )
    await app.bot.send_message(chat_id=chat_id, text=text)


def make_keyboard(job: Job) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Открыть", url=job.url),
        InlineKeyboardButton("📨 Откликнуться", callback_data=f"apply:{job.id}"),
    ]])


def send_job_sync(job: Job):
    async def _send():
        app = build_app()
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=job.format_message(),
            parse_mode=ParseMode.HTML,
            reply_markup=make_keyboard(job),
        )
    asyncio.run(_send())


def send_text_sync(text: str):
    async def _send():
        app = build_app()
        await app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=ParseMode.HTML)
    asyncio.run(_send())


def run_bot():
    app = build_app()
    app.run_polling(drop_pending_updates=True)
