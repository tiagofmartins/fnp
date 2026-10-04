#!/usr/bin/env python3
"""Telegram bot with inline keyboard button interactions.

Requires:  pip install python-telegram-bot

The bot token goes in secrets/telegram-token.txt, and the chat id to
notify on startup goes in secrets/telegram-chat-id.txt (each a single
line). Both are git-ignored — never commit them.
"""

import asyncio
import io
import time
import traceback
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument, InputMediaPhoto, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

import camera_photo
import system_control
import system_stats

script_dir = Path(__file__).parent
TOKEN_FILE = script_dir / "secrets" / "telegram-token.txt"
CHAT_ID_FILE = script_dir / "secrets" / "telegram-chat-id.txt"
LOG_DIR = script_dir / "log"
ACTIONS_DIR = script_dir / "actions"
CONTENTS_DIR = script_dir / "contents"


def _queue_action(name, expires_in_seconds=None):
    """Create an action file for action_watcher.py to act on, replacing
    an existing file for the exact same action.
    A conflicting action file of a different name (e.g.
    "brightness_max" while "brightness_auto" is pending) is left for
    action_watcher.py to resolve, since it always keeps only the most
    recently created action per prefix group."""
    ACTIONS_DIR.mkdir(exist_ok=True)
    existing = ACTIONS_DIR / name
    if existing.exists():
        existing.unlink()
    filename = name
    if expires_in_seconds:
        filename += " " + str(round(time.time() + expires_in_seconds))
    (ACTIONS_DIR / filename).touch()


def _main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Content AUTO", callback_data="content_auto"),
            InlineKeyboardButton("Content MANUAL", callback_data="content_manual"),
        ], [
            InlineKeyboardButton("Content RANDOM", callback_data="content_random"),
            InlineKeyboardButton("Content OFF", callback_data="content_off"),
        ], [
            InlineKeyboardButton("Display AUTO", callback_data="display_auto"),
            InlineKeyboardButton("Display ALL", callback_data="display_all"),
        ], [
            InlineKeyboardButton("Display WALL", callback_data="display_wall"),
            InlineKeyboardButton("Display STANDBY", callback_data="display_standby"),
        ], [
            InlineKeyboardButton("Brightness AUTO", callback_data="brightness_auto"),
            InlineKeyboardButton("Brightness MAX", callback_data="brightness_max"),
        ], [
            InlineKeyboardButton("System stats", callback_data="system_stats"),
            InlineKeyboardButton("Log files", callback_data="log_files"),
        ], [
            InlineKeyboardButton("Screenshot", callback_data="screenshot"),
            InlineKeyboardButton("Photo", callback_data="photo"),
        ], [
            InlineKeyboardButton("Hide cursor", callback_data="hide_cursor")
        ]
    ])


def _contents_keyboard():
    """Buttons for every folder in CONTENTS_DIR, two per row, plus a
    final row with a button to go back to the main keyboard."""
    content_names = sorted(p.name for p in CONTENTS_DIR.iterdir() if p.is_dir())
    buttons = [InlineKeyboardButton(name, callback_data=f"content_manual {name}") for name in content_names]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)


async def options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Options:", reply_markup=_main_keyboard(), disable_notification=True)


async def button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "content_manual":
        await query.edit_message_text(text="Choose a content:", reply_markup=_contents_keyboard())
        return

    if query.data == "back_to_main":
        await query.edit_message_text(text="Options:", reply_markup=_main_keyboard())
        return
    
    if query.data.split("_")[0] in ["content", "display", "brightness"]:
        action_is_auto = query.data.endswith("_auto") and " " not in query.data
        expiry = (12 * 60 * 60) if not action_is_auto else None
        _queue_action(query.data, expires_in_seconds=expiry)
        await query.edit_message_text(
            text=f"Queued action: <b>{query.data}</b>. This may take a few seconds to take effect.", parse_mode="HTML")
        return
    
    if query.data == "system_stats":
        await query.edit_message_text(text="Collecting stats…")
        stats = await asyncio.to_thread(system_stats.stats_str)
        await query.edit_message_text(f"System stats:\n<pre>{stats}</pre>", parse_mode="HTML")
        return

    if query.data == "log_files":
        log_files = sorted(LOG_DIR.glob("*.log")) if LOG_DIR.is_dir() else []
        if not log_files:
            await query.edit_message_text(text="No log files found.")
            return
        if len(log_files) == 1:
            await query.message.reply_document(document=log_files[0].open("rb"), disable_notification=True)
        else:
            media = [InputMediaDocument(media=path.open("rb")) for path in log_files]
            await query.message.reply_media_group(media=media, disable_notification=True)
        await query.edit_message_text(text="Log files")
        return

    if query.data == "screenshot":
        await query.edit_message_text(text="Taking screenshot…")
        image = await asyncio.to_thread(system_control.screenshot_all_displays)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        buffer.name = f"{datetime.now():%Y-%m-%d %H.%M.%S}.png"
        await query.message.reply_document(document=buffer, disable_notification=True)
        await query.edit_message_text(text="Screenshot")
        return

    if query.data == "photo":
        await query.edit_message_text(text="Taking photo…")
        photos = await asyncio.to_thread(camera_photo.capture_photos)
        timestamp = f"{datetime.now():%Y-%m-%d %H.%M.%S}"
        media = []
        for camera_name, image in photos.items():
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            buffer.seek(0)
            buffer.name = f"{timestamp} {camera_name}.jpg"
            media.append(InputMediaPhoto(media=buffer, caption=camera_name))

        if not media:
            await query.edit_message_text(text="No cameras available or all failed.")
            return

        await query.message.reply_media_group(media=media, disable_notification=True)
        await query.edit_message_text(text="Photos taken from available cameras")
        return

    if query.data == "hide_cursor":
        await asyncio.to_thread(system_control.hide_cursor)
        await query.edit_message_text(text="Cursor hidden.")
        return


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    trace = "".join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))
    response = f"Oops! Something went wrong.\n<pre>{trace}</pre>"
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode="HTML", disable_notification=False)


async def notify_startup(app):
    chat_id = CHAT_ID_FILE.read_text().strip()
    await app.bot.send_message(chat_id=chat_id, text="FnP chat bot started.", disable_notification=True)


def main():
    token = TOKEN_FILE.read_text().strip()
    app = Application.builder().token(token).post_init(notify_startup).build()
    app.add_handler(CommandHandler("options", options))
    app.add_handler(CallbackQueryHandler(button_pressed))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_error_handler(error_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
