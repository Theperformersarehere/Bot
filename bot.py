"""
bot.py — Single entry point.
Run with: python bot.py
"""
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

import database as db
from config import BOT_TOKEN
from handlers.start import start_handler
from handlers.join_check import join_check_callback, main_menu_callback
from handlers.admin_panel import build_admin_conv_handler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    db.init_db()
    logger.info("✅ Database ready.")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ── Admin panel (ConversationHandler — must be first) ─────────────────────
    app.add_handler(build_admin_conv_handler())

    # ── Public handlers ───────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(join_check_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(main_menu_callback,  pattern="^main_menu$"))

    logger.info("🤖 Bot is polling…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
