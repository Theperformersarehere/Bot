from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import TelegramError
import database as db


# Statuses that count as "member"
_MEMBER_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.OWNER,
}


async def join_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called when user presses the '✅ I've Joined — Verify' button."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    channels = db.get_channels()
    if not channels:
        # No channels configured — just delete the menu and confirm
        await _delete_query_message(query)
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="✅ *You're all set!*\n\nNo channels to verify right now.",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["menu_msg_id"] = msg.message_id
        return

    # ── Check each channel ────────────────────────────────────────────────────
    not_joined: list[dict] = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(
                chat_id=ch["channel_id"], user_id=user_id
            )
            if member.status not in _MEMBER_STATUSES:
                not_joined.append(dict(ch))
        except TelegramError:
            # Bot not in channel or channel private — treat as not joined
            not_joined.append(dict(ch))

    # ── Delete the old menu message cleanly ───────────────────────────────────
    await _delete_query_message(query)

    if not_joined:
        # ── Show which channels they haven't joined ───────────────────────────
        text = (
            "❌ *You haven't joined all required channels yet!*\n\n"
            "Please join the channels below and tap *Verify Again*:"
        )
        keyboard = []
        for ch in not_joined:
            keyboard.append([
                InlineKeyboardButton(
                    f"📢 {ch['channel_username']}",
                    url=ch["invite_link"]
                )
            ])
        keyboard.append([
            InlineKeyboardButton("🔄 Verify Again", callback_data="check_join")
        ])
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data["menu_msg_id"] = msg.message_id

    else:
        # ── All joined — send success + channel link buttons ──────────────────
        all_channels = list(channels)
        keyboard = []
        for ch in all_channels:
            keyboard.append([
                InlineKeyboardButton(
                    f"🚀 Open {ch['channel_username']}",
                    url=ch["invite_link"]
                )
            ])
        keyboard.append([
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ])
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉 *Welcome! You're verified!*\n\n"
                "You've successfully joined all required channels.\n"
                "Tap below to open them:"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data["menu_msg_id"] = msg.message_id


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to main menu when user presses 🏠 Main Menu button."""
    query = update.callback_query
    await query.answer()
    await _delete_query_message(query)

    # Re-trigger the start handler logic
    from handlers.start import start_handler
    await start_handler(update, context)


async def _delete_query_message(query):
    """Silently delete the message that hosted the button press."""
    try:
        await query.message.delete()
    except TelegramError:
        pass
