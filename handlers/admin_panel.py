"""
handlers/admin_panel.py

Full in-bot admin panel via /admin command.
Uses ConversationHandler with inline keyboard menus.
Only accessible by ADMIN_TELEGRAM_ID.
"""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
import database as db
from config import ADMIN_TELEGRAM_ID

logger = logging.getLogger(__name__)

# ── Conversation States ───────────────────────────────────────────────────────
(
    ADMIN_MENU,
    SETTINGS_MENU,
    AWAIT_MENU_TEXT,
    AWAIT_MENU_PHOTO,
    JOIN_LINK_MENU,
    AWAIT_JOIN_LINK,
    CHANNELS_MENU,
    AWAIT_CH_ID,
    AWAIT_CH_USERNAME,
    AWAIT_CH_LINK,
    VIDEOS_MENU,
    AWAIT_VIDEO,
) = range(13)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_TELEGRAM_ID


async def _safe_delete(bot, chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except TelegramError:
        pass


async def _replace(context: ContextTypes.DEFAULT_TYPE, chat_id: int, new_msg):
    """Delete the previous admin panel message, store the new one."""
    old_id = context.user_data.get("admin_msg_id")
    if old_id:
        await _safe_delete(context.bot, chat_id, old_id)
    context.user_data["admin_msg_id"] = new_msg.message_id


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ADMIN MENU
# ═══════════════════════════════════════════════════════════════════════════════

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point — /admin command."""
    if not _is_admin(update.effective_user.id):
        try:
            await update.message.delete()
        except TelegramError:
            pass
        return ConversationHandler.END

    # Delete the /admin command message
    try:
        await update.message.delete()
    except TelegramError:
        pass

    msg = await _send_admin_home(update.effective_chat.id, context)
    context.user_data["admin_msg_id"] = msg.message_id
    return ADMIN_MENU


async def _send_admin_home(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [
            InlineKeyboardButton("⚙️  Settings",  callback_data="adm:settings"),
            InlineKeyboardButton("🔗  Join Link",   callback_data="adm:joinlink"),
        ],
        [
            InlineKeyboardButton("📢  Channels",  callback_data="adm:channels"),
            InlineKeyboardButton("🎥  Videos",    callback_data="adm:videos"),
        ],
        [InlineKeyboardButton("❌  Close Panel",  callback_data="adm:close")],
    ]
    return await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🛠️ *Admin Panel*\n"
            "──────────────────\n"
            "Manage your bot from here.\n\n"
            "Choose a section:"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def admin_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    data = query.data

    if data == "adm:settings":
        msg = await _send_settings_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return SETTINGS_MENU

    elif data == "adm:joinlink":
        msg = await _send_join_link_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return JOIN_LINK_MENU

    elif data == "adm:channels":
        msg = await _send_channels_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return CHANNELS_MENU

    elif data == "adm:videos":
        msg = await _send_videos_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return VIDEOS_MENU

    elif data == "adm:close":
        old_id = context.user_data.pop("admin_msg_id", None)
        if old_id:
            await _safe_delete(context.bot, chat_id, old_id)
        return ConversationHandler.END

    return ADMIN_MENU


# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_settings_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    current_text = db.get_setting("menu_text") or "Not set"
    has_photo    = bool(db.get_setting("menu_photo_file_id"))
    photo_status = "✅ Set" if has_photo else "❌ Not set"
    preview      = (current_text[:60] + "…") if len(current_text) > 60 else current_text

    kb = [
        [InlineKeyboardButton("✏️  Edit Menu Text",   callback_data="adm:edit_text")],
        [InlineKeyboardButton("🖼️  Edit Menu Photo",  callback_data="adm:edit_photo")],
        [InlineKeyboardButton("🗑️  Remove Photo",     callback_data="adm:remove_photo")],
        [InlineKeyboardButton("◀️  Back",             callback_data="adm:home")],
    ]
    return await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "⚙️ *Settings*\n"
            "──────────────────\n"
            f"📝 *Menu Text:*\n{preview}\n\n"
            f"🖼️ *Menu Photo:* {photo_status}"
        ),
        parse_mode=None, # Disabled Markdown here to prevent errors from unescaped user text
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = update.effective_chat.id

    if data == "adm:home":
        msg = await _send_admin_home(chat_id, context)
        await _replace(context, chat_id, msg)
        return ADMIN_MENU

    elif data == "adm:edit_text":
        kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:settings")]]
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "✏️ *Edit Menu Text*\n"
                "──────────────────\n"
                "Send the new welcome message text.\n\n"
                "_Tip: you can use Telegram Markdown —_\n"
                "_`*bold*`, `_italic_`, etc._"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb),
        )
        await _replace(context, chat_id, msg)
        return AWAIT_MENU_TEXT

    elif data == "adm:edit_photo":
        kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:settings")]]
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🖼️ *Edit Menu Photo*\n"
                "──────────────────\n"
                "Send the new photo for the main menu:"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb),
        )
        await _replace(context, chat_id, msg)
        return AWAIT_MENU_PHOTO

    elif data == "adm:remove_photo":
        db.set_setting("menu_photo_file_id", "")
        msg = await _send_settings_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return SETTINGS_MENU

    # "adm:settings" — refresh settings menu (used by cancel buttons)
    msg = await _send_settings_menu(chat_id, context)
    await _replace(context, chat_id, msg)
    return SETTINGS_MENU


async def receive_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sent new menu text."""
    new_text = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except TelegramError:
        pass

    if new_text:
        db.set_setting("menu_text", new_text)

    msg = await _send_settings_menu(update.effective_chat.id, context)
    await _replace(context, update.effective_chat.id, msg)
    return SETTINGS_MENU


async def receive_menu_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sent a new menu photo."""
    try:
        await update.message.delete()
    except TelegramError:
        pass

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        db.set_setting("menu_photo_file_id", file_id)

    msg = await _send_settings_menu(update.effective_chat.id, context)
    await _replace(context, update.effective_chat.id, msg)
    return SETTINGS_MENU


# ═══════════════════════════════════════════════════════════════════════════════
#  JOIN LINK
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_join_link_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    current_link = db.get_setting("join_channel_link") or "Not set"
    
    kb = [
        [InlineKeyboardButton("✏️  Edit Join Link", callback_data="adm:edit_joinlink")],
        [InlineKeyboardButton("◀️  Back",           callback_data="adm:home")],
    ]

    return await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🔗 Join Channel Link\n"
            "──────────────────\n"
            "This is the main button shown to users on /start.\n\n"
            f"Current Link: {current_link}"
        ),
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def join_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = update.effective_chat.id

    if data == "adm:home":
        msg = await _send_admin_home(chat_id, context)
        await _replace(context, chat_id, msg)
        return ADMIN_MENU

    elif data == "adm:edit_joinlink":
        kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:joinlink")]]
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "✏️ Update Join Link\n"
                "──────────────────\n"
                "Send the new URL for the Join Channel button:"
            ),
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(kb),
        )
        await _replace(context, chat_id, msg)
        return AWAIT_JOIN_LINK

    # "adm:joinlink" — refresh
    msg = await _send_join_link_menu(chat_id, context)
    await _replace(context, chat_id, msg)
    return JOIN_LINK_MENU


async def receive_join_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except TelegramError:
        pass

    db.set_setting("join_channel_link", url)

    msg = await _send_join_link_menu(update.effective_chat.id, context)
    await _replace(context, update.effective_chat.id, msg)
    return JOIN_LINK_MENU


# ═══════════════════════════════════════════════════════════════════════════════
#  CHANNELS
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_channels_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    channels = db.get_channels()
    kb = []

    for ch in channels:
        kb.append([
            InlineKeyboardButton(
                f"🗑️  {ch['channel_username']}",
                callback_data=f"adm:delch:{ch['id']}"
            )
        ])

    kb.append([InlineKeyboardButton("➕  Add Channel",  callback_data="adm:add_ch")])
    kb.append([InlineKeyboardButton("◀️  Back",         callback_data="adm:home")])

    if channels:
        list_text = "\n".join(
            f"  {i+1}\\. *{c['channel_username']}*  `{c['channel_id']}`"
            for i, c in enumerate(channels)
        )
        body = f"{list_text}\n\n_Tap a channel to remove it._"
    else:
        body = "_No channels configured yet._"

    return await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"📢 Force-Join Channels ({len(channels)} total)\n"
            f"──────────────────\n"
            f"{body}"
        ),
        parse_mode=None, # Disabled ParseMode to prevent bad escape chars breaking the bot
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = update.effective_chat.id

    if data == "adm:home":
        msg = await _send_admin_home(chat_id, context)
        await _replace(context, chat_id, msg)
        return ADMIN_MENU

    elif data == "adm:add_ch":
        kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:channels")]]
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "➕ Add Channel — Step 1 / 3\n"
                "──────────────────\n"
                "Send the Channel ID\n"
                "(e.g. -1001234567890)\n\n"
                "💡 Forward a message from the channel to @userinfobot to get its ID."
            ),
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(kb),
        )
        await _replace(context, chat_id, msg)
        return AWAIT_CH_ID

    elif data.startswith("adm:delch:"):
        ch_id = int(data.split(":")[2])
        db.delete_channel(ch_id)
        msg = await _send_channels_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return CHANNELS_MENU

    # "adm:channels" — refresh
    msg = await _send_channels_menu(chat_id, context)
    await _replace(context, chat_id, msg)
    return CHANNELS_MENU


async def receive_ch_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch_id = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except TelegramError:
        pass

    context.user_data["new_ch_id"] = ch_id
    kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:channels")]]
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "➕ Add Channel — Step 2 / 3\n"
            "──────────────────\n"
            f"ID saved: {ch_id}\n\n"
            "Now send the channel username\n"
            "(e.g. @mychannel)"
        ),
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(kb),
    )
    await _replace(context, update.effective_chat.id, msg)
    return AWAIT_CH_USERNAME


async def receive_ch_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except TelegramError:
        pass

    context.user_data["new_ch_username"] = username
    kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:channels")]]
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "➕ Add Channel — Step 3 / 3\n"
            "──────────────────\n"
            f"Username saved: {username}\n\n"
            "Finally, send the invite link\n"
            "(e.g. https://t.me/mychannel or a private invite link)"
        ),
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(kb),
    )
    await _replace(context, update.effective_chat.id, msg)
    return AWAIT_CH_LINK


async def receive_ch_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except TelegramError:
        pass

    ch_id       = context.user_data.pop("new_ch_id", "")
    ch_username = context.user_data.pop("new_ch_username", "")
    db.add_channel(ch_id, ch_username, link)

    msg = await _send_channels_menu(update.effective_chat.id, context)
    await _replace(context, update.effective_chat.id, msg)
    return CHANNELS_MENU


# ═══════════════════════════════════════════════════════════════════════════════
#  VIDEOS
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_videos_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    videos = db.get_videos()
    kb = []

    for vid in videos:
        kb.append([
            InlineKeyboardButton(
                f"🗑️  Delete Video {vid['id']}",
                callback_data=f"adm:delvid:{vid['id']}"
            )
        ])

    kb.append([InlineKeyboardButton("➕  Add Video",  callback_data="adm:add_vid")])
    kb.append([InlineKeyboardButton("◀️  Back",       callback_data="adm:home")])

    if videos:
        body = f"You have {len(videos)} video(s) configured.\n_Tap one to delete it._"
    else:
        body = "_No videos configured yet._"

    return await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🎥 Forwarded Videos\n"
            f"──────────────────\n"
            f"{body}"
        ),
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def videos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = update.effective_chat.id

    if data == "adm:home":
        msg = await _send_admin_home(chat_id, context)
        await _replace(context, chat_id, msg)
        return ADMIN_MENU

    elif data == "adm:add_vid":
        kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:videos")]]
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "➕ Add Video\n"
                "──────────────────\n"
                "Please forward or upload the video you want to save. You can do this multiple times."
            ),
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(kb),
        )
        await _replace(context, chat_id, msg)
        return AWAIT_VIDEO

    elif data.startswith("adm:delvid:"):
        vid_id = int(data.split(":")[2])
        db.delete_video(vid_id)
        msg = await _send_videos_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return VIDEOS_MENU

    # refresh
    msg = await _send_videos_menu(chat_id, context)
    await _replace(context, chat_id, msg)
    return VIDEOS_MENU


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        db.add_video(file_id)
    elif update.message.document and update.message.document.mime_type.startswith('video/'):
        file_id = update.message.document.file_id
        db.add_video(file_id)

    try:
        await update.message.delete()
    except TelegramError:
        pass

    msg = await _send_videos_menu(update.effective_chat.id, context)
    await _replace(context, update.effective_chat.id, msg)
    return VIDEOS_MENU


# ═══════════════════════════════════════════════════════════════════════════════
#  CANCEL / FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    old_id = context.user_data.pop("admin_msg_id", None)
    if old_id:
        await _safe_delete(context.bot, update.effective_chat.id, old_id)
    try:
        await update.message.delete()
    except TelegramError:
        pass
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════════════════
#  BUILD HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

def build_admin_conv_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_MENU: [
                CallbackQueryHandler(admin_home_callback, pattern=r"^adm:"),
            ],
            SETTINGS_MENU: [
                CallbackQueryHandler(settings_callback, pattern=r"^adm:"),
            ],
            AWAIT_MENU_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_menu_text),
                CallbackQueryHandler(settings_callback, pattern=r"^adm:"),
            ],
            AWAIT_MENU_PHOTO: [
                MessageHandler(filters.PHOTO, receive_menu_photo),
                CallbackQueryHandler(settings_callback, pattern=r"^adm:"),
            ],
            JOIN_LINK_MENU: [
                CallbackQueryHandler(join_link_callback, pattern=r"^adm:"),
            ],
            AWAIT_JOIN_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_join_link),
                CallbackQueryHandler(join_link_callback, pattern=r"^adm:"),
            ],
            CHANNELS_MENU: [
                CallbackQueryHandler(channels_callback, pattern=r"^adm:"),
            ],
            AWAIT_CH_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ch_id),
                CallbackQueryHandler(channels_callback, pattern=r"^adm:"),
            ],
            AWAIT_CH_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ch_username),
                CallbackQueryHandler(channels_callback, pattern=r"^adm:"),
            ],
            AWAIT_CH_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ch_link),
                CallbackQueryHandler(channels_callback, pattern=r"^adm:"),
            ],
            VIDEOS_MENU: [
                CallbackQueryHandler(videos_callback, pattern=r"^adm:"),
            ],
            AWAIT_VIDEO: [
                MessageHandler(filters.VIDEO | filters.Document.VIDEO, receive_video),
                CallbackQueryHandler(videos_callback, pattern=r"^adm:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        # Allow re-entering the admin panel even if already in a conversation
        allow_reentry=True,
        per_chat=True,
        per_user=True,
    )
