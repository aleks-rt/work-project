import logging
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.base import Job
from storage import get_job_url, get_user_data, save_user_data

logger = logging.getLogger(__name__)

_app: Application | None = None


def build_app() -> Application:
    global _app
    if _app is None:
        _app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        _app.add_handler(CommandHandler("start", cmd_start))
        _app.add_handler(CommandHandler("resume", cmd_resume))
        _app.add_handler(CommandHandler("stats", cmd_stats))
        _app.add_handler(MessageHandler(filters.Document.PDF | filters.Document.MimeType("application/msword") | filters.Document.MimeType("application/vnd.openxmlformats-officedocument.wordprocessingml.document"), handle_resume_upload))
        _app.add_handler(CallbackQueryHandler(handle_apply, pattern=r"^apply:"))
    return _app


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я слежу за вакансиями бизнес-аналитика.\n\n"
        "📎 Загрузи резюме командой /resume — и я смогу напоминать его при отклике.\n"
        "📊 Статистика: /stats"
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📎 Пришли мне файл резюме (PDF или Word) — я его сохраню.\n"
        "При нажатии 'Откликнуться' под вакансией я пришлю резюме обратно тебе вместе со ссылкой."
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from storage import get_stats
    stats = get_stats()
    lines = [f"📊 <b>Статистика</b>", f"Всего вакансий в базе: {stats['total']}"]
    for source, cnt in stats["by_source"].items():
        lines.append(f"  • {source}: {cnt}")
    await update.message.reply_html("\n".join(lines))


async def handle_resume_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_id = doc.file_id
    save_user_data("resume_file_id", file_id)
    save_user_data("resume_name", doc.file_name or "resume")
    await update.message.reply_text(
        f"✅ Резюме «{doc.file_name}» сохранено!\n"
        "Теперь при нажатии 'Откликнуться' я буду присылать его тебе вместе со ссылкой."
    )


async def handle_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    job_id = query.data.replace("apply:", "")
    url = get_job_url(job_id)
    resume_file_id = get_user_data("resume_file_id")
    resume_name = get_user_data("resume_name") or "resume"

    if resume_file_id:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=resume_file_id,
            caption=f"📎 Твоё резюме для отклика.\n🔗 Вакансия: {url}",
        )
    else:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🔗 Ссылка на вакансию:\n{url}\n\n"
                 "💡 Загрузи резюме через /resume — и я буду присылать его сюда при каждом отклике.",
        )


def make_keyboard(job: Job) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton("🔗 Открыть", url=job.url),
        InlineKeyboardButton("📨 Откликнуться", callback_data=f"apply:{job.id}"),
    ]
    return InlineKeyboardMarkup([buttons])


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
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    asyncio.run(_send())


def run_bot():
    """Запустить бота в режиме polling (блокирующий вызов)."""
    app = build_app()
    app.run_polling(drop_pending_updates=True)
