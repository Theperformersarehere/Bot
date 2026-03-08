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
    BUTTONS_MENU,
    AWAIT_BTN_LABEL,
    AWAIT_BTN_URL,
    CHANNELS_MENU,
    AWAIT_CH_ID,
    AWAIT_CH_USERNAME,
    AWAIT_CH_LINK,
) = range(11)


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
            InlineKeyboardButton("🔘  Buttons",   callback_data="adm:buttons"),
        ],
        [
            InlineKeyboardButton("📢  Channels",  callback_data="adm:channels"),
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

    elif data == "adm:buttons":
        msg = await _send_buttons_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return BUTTONS_MENU

    elif data == "adm:channels":
        msg = await _send_channels_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return CHANNELS_MENU

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
        parse_mode=ParseMode.MARKDOWN,
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
#  BUTTONS
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_buttons_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    buttons = db.get_buttons()
    kb = []

    for btn in buttons:
        label_preview = btn["label"][:20] + "…" if len(btn["label"]) > 20 else btn["label"]
        kb.append([
            InlineKeyboardButton(
                f"🗑️  {label_preview}",
                callback_data=f"adm:delbtn:{btn['id']}"
            )
        ])

    kb.append([InlineKeyboardButton("➕  Add New Button",  callback_data="adm:add_btn")])
    kb.append([InlineKeyboardButton("◀️  Back",            callback_data="adm:home")])

    if buttons:
        list_text = "\n".join(
            f"  {i+1}\\. *{b['label']}*\n      `{b['url']}`"
            for i, b in enumerate(buttons)
        )
        body = f"{list_text}\n\n_Tap a button label above to delete it._"
    else:
        body = "_No buttons yet. Add one below._"

    return await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🔘 *Inline Buttons* ({len(buttons)} total)\n"
            f"──────────────────\n"
            f"{body}"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def buttons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = update.effective_chat.id

    if data == "adm:home":
        msg = await _send_admin_home(chat_id, context)
        await _replace(context, chat_id, msg)
        return ADMIN_MENU

    elif data == "adm:add_btn":
        kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:buttons")]]
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "➕ *Add Button — Step 1 / 2*\n"
                "──────────────────\n"
                "Send the *button label* (text shown on the button):"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb),
        )
        await _replace(context, chat_id, msg)
        return AWAIT_BTN_LABEL

    elif data.startswith("adm:delbtn:"):
        btn_id = int(data.split(":")[2])
        db.delete_button(btn_id)
        msg = await _send_buttons_menu(chat_id, context)
        await _replace(context, chat_id, msg)
        return BUTTONS_MENU

    # "adm:buttons" — refresh
    msg = await _send_buttons_menu(chat_id, context)
    await _replace(context, chat_id, msg)
    return BUTTONS_MENU


async def receive_btn_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except TelegramError:
        pass

    context.user_data["new_btn_label"] = label
    kb = [[InlineKeyboardButton("◀️  Cancel", callback_data="adm:buttons")]]
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"➕ *Add Button — Step 2 / 2*\n"
            f"──────────────────\n"
            f"Label set to: *{label}*\n\n"
            f"Now send the *URL* for this button:"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb),
    )
    await _replace(context, update.effective_chat.id, msg)
    return AWAIT_BTN_URL


async def receive_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except TelegramError:
        pass

    label = context.user_data.pop("new_btn_label", "Button")
    db.add_button(label, url)

    msg = await _send_buttons_menu(update.effective_chat.id, context)
    await _replace(context, update.effective_chat.id, msg)
    return BUTTONS_MENU


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
            f"📢 *Force\\-Join Channels* ({len(channels)} total)\n"
            f"──────────────────\n"
            f"{body}"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
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
                "➕ *Add Channel — Step 1 / 3*\n"
                "──────────────────\n"
                "Send the *Channel ID*\n"
                "_(e.g. `-1001234567890`)_\n\n"
                "💡 Forward a message from the channel to @userinfobot to get its ID."
            ),
            parse_mode=ParseMode.MARKDOWN,
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
            "➕ *Add Channel — Step 2 / 3*\n"
            "──────────────────\n"
            f"ID saved: `{ch_id}`\n\n"
            "Now send the *channel username*\n"
            "_(e.g. `@mychannel`)_"
        ),
        parse_mode=ParseMode.MARKDOWN,
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
            "➕ *Add Channel — Step 3 / 3*\n"
            "──────────────────\n"
            f"Username saved: *{username}*\n\n"
            "Finally, send the *invite link*\n"
            "_(e.g. `https://t.me/mychannel` or a private invite link)_"
        ),
        parse_mode=ParseMode.MARKDOWN,
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
            BUTTONS_MENU: [
                CallbackQueryHandler(buttons_callback, pattern=r"^adm:"),
            ],
            AWAIT_BTN_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_btn_label),
                CallbackQueryHandler(buttons_callback, pattern=r"^adm:"),
            ],
            AWAIT_BTN_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_btn_url),
                CallbackQueryHandler(buttons_callback, pattern=r"^adm:"),
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
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        # Allow re-entering the admin panel even if already in a conversation
        allow_reentry=True,
        per_chat=True,
        per_user=True,
    )
