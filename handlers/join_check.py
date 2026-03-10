import asyncio
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

    # ── Delete the old menu message cleanly ───────────────────────────────────
    await _delete_query_message(query)

    # ── Loading Bar Animation ─────────────────────────────────────────────────
    loading_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="🔄 *Verifying* ⏳",
        parse_mode=ParseMode.MARKDOWN,
    )
    
    await asyncio.sleep(0.5)
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=loading_msg.message_id,
            text="🔄 *Verifying* ⌛",
            parse_mode=ParseMode.MARKDOWN,
        )
        await asyncio.sleep(0.5)
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=loading_msg.message_id,
            text="🔄 *Verifying* ⏳",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError:
        pass

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

    # Delete the loading message
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=loading_msg.message_id)
    except TelegramError:
        pass

    if not_joined:
        # ── Show failures with the single Join Link ───────────────────────────
        join_link = db.get_setting("join_channel_link") or "https://t.me"
        text = (
            "❌ *You haven't joined yet!*\n\n"
            "Please join our channel below and then tap *Try Again*:"
        )
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=join_link)],
            [InlineKeyboardButton("🔄 Try Again", callback_data="check_join")]
        ]
        
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
                "Tap below to open them:\n\n"
                "_(This message and the videos will self-delete in 5 minutes)_"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data["menu_msg_id"] = msg.message_id
        
        # Schedule auto-delete for the main success message
        context.application.create_task(
            _delayed_delete(context.bot, chat_id, msg.message_id, 300)
        )

        # ── Send Videos ───────────────────────────────────────────────────────
        videos = db.get_videos()
        if videos:
            for vid in videos:
                try:
                    # We use send_document or send_video based on what is stored,
                    # but since we don't know the exact type, try video first, then fallback to document
                    try:
                        v_msg = await context.bot.send_video(chat_id=chat_id, video=vid["file_id"])
                    except TelegramError:
                        v_msg = await context.bot.send_document(chat_id=chat_id, document=vid["file_id"])

                    # Schedule auto-delete for the video message too
                    context.application.create_task(
                        _delayed_delete(context.bot, chat_id, v_msg.message_id, 300)
                    )
                except TelegramError as e:
                    print(f"Error sending video {vid['id']}: {e}")

async def _delayed_delete(bot, chat_id: int, message_id: int, delay_seconds: int):
    """Wait for delay_seconds then delete the message."""
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError:
        pass


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
