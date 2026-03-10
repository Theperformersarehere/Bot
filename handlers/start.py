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

    # Format menu text with user details
    import re
    user = update.effective_user
    
    # We escape HTML characters in the user's name
    first_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;") if user else "User"
    mention = f'<a href="tg://user?id={user.id}">{first_name}</a>' if user else first_name
    username   = f"@{user.username}" if user and user.username else ""
    
    # Use formatted string or fallback to exact requested text if not set in DB
    default_text = f"<b>Hey {mention} {username}</b>\n\n<b>Please Join All My Update Channels To Use Me!</b>"
    menu_text = db.get_setting("menu_text")
    
    if menu_text:
        # Convert legacy markdown *bold* into HTML <b>bold</b> so users can still use stars in the admin panel
        menu_text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', menu_text)
        
        # Replace variables
        menu_text = menu_text.replace("{first_name}", mention).replace("{username}", username)
    else:
        menu_text = default_text

    menu_photo_file_id = db.get_setting("menu_photo_file_id")

    # Build inline keyboard
    keyboard = _build_main_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)

    if menu_photo_file_id:
        sent = await context.bot.send_photo(
            chat_id=chat_id,
            photo=menu_photo_file_id,
            caption=menu_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    else:
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=menu_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )

    context.user_data["menu_msg_id"] = sent.message_id


def _build_main_keyboard() -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []

    join_link = db.get_setting("join_channel_link") or "https://t.me"
    rows.append([InlineKeyboardButton(text="Join Channel 1", url=join_link)])

    if db.get_channels():
        rows.append([
            InlineKeyboardButton("♻️ Try Again", callback_data="check_join")
        ])

    return rows
