from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the main menu. Always deletes the previous menu message for clean UI."""
    chat_id = update.effective_chat.id

    # Delete previous menu message
    prev_msg_id = context.user_data.get("menu_msg_id")
    if prev_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=prev_msg_id)
        except Exception:
            pass

    # Delete the /start command message itself
    if update.message:
        try:
            await update.message.delete()
        except Exception:
            pass

    menu_text          = db.get_setting("menu_text") or "👋 *Welcome!*"
    menu_photo_file_id = db.get_setting("menu_photo_file_id")

    # Build inline keyboard
    keyboard = _build_main_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)

    if menu_photo_file_id:
        sent = await context.bot.send_photo(
            chat_id=chat_id,
            photo=menu_photo_file_id,
            caption=menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
    else:
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    context.user_data["menu_msg_id"] = sent.message_id


def _build_main_keyboard() -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []

    join_link = db.get_setting("join_channel_link") or "https://t.me"
    rows.append([InlineKeyboardButton(text="📢 Join Channel", url=join_link)])

    if db.get_channels():
        rows.append([
            InlineKeyboardButton("✅ I've Joined — Verify", callback_data="check_join")
        ])

    return rows
