#!/usr/bin/env python3
"""Telegram bot with inline keyboard button interactions.

Requires:  pip install python-telegram-bot

The bot token goes in secrets/telegram-token.txt, and the chat id to
notify on startup goes in secrets/telegram-chat-id.txt (each a single
line). Both are git-ignored — never commit them.
"""

import asyncio
import io
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import camera_photo
import display_setup
import system_control
import system_stats

TOKEN_FILE = Path(__file__).parent / "secrets" / "telegram-token.txt"
CHAT_ID_FILE = Path(__file__).parent / "secrets" / "telegram-chat-id.txt"

DISPLAY_SETUPS = {
    "setup_wall": ("Wall", display_setup.WALL_DISPLAYS),
    "setup_internal": ("Internal", display_setup.INTERNAL_DISPLAY),
    "setup_all": ("All", display_setup.ALL_DISPLAYS),
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("System stats", callback_data="system_stats")],
        [InlineKeyboardButton("Screenshot", callback_data="screenshot")],
        [InlineKeyboardButton("Camera photos", callback_data="camera")],
        [InlineKeyboardButton("Hide cursor", callback_data="hide_cursor")],
        [InlineKeyboardButton(label, callback_data=key) for key, (label, _) in DISPLAY_SETUPS.items()],
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard), disable_notification=True)


async def button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "system_stats":
        await query.edit_message_text(text="Collecting stats…")
        stats = await asyncio.to_thread(system_stats.stats)
        await query.edit_message_text(f"Here is the system stats:\n<pre>{json.dumps(stats, indent=2)}</pre>", parse_mode="HTML")
        return

    if query.data == "screenshot":
        await query.edit_message_text(text="Taking screenshot…")
        image = await asyncio.to_thread(system_control.screenshot_all_displays)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        buffer.name = f"{datetime.now():%Y-%m-%d %H.%M.%S}.png"
        await query.message.reply_document(document=buffer, disable_notification=True)
        await query.edit_message_text(text="Here is the screenshot.")
        return

    if query.data == "camera":
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
        await query.edit_message_text(text="Here are the photos from the available cameras.")
        return

    if query.data == "hide_cursor":
        await asyncio.to_thread(system_control.hide_cursor)
        await query.edit_message_text(text="Cursor hidden.")
        return

    if query.data in DISPLAY_SETUPS:
        label, setup = DISPLAY_SETUPS[query.data]
        await query.edit_message_text(text=f"Switching to {label}…")
        await asyncio.to_thread(display_setup.apply_setup, setup)
        await query.edit_message_text(text=f"Switched to {label}.")
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("An error occurred: %s", traceback.format_exc())
    response = f"Oops! Something went wrong.\n<pre>{traceback.format_exc()}</pre>"
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode="HTML", disable_notification=False)


async def notify_startup(app):
    chat_id = CHAT_ID_FILE.read_text().strip()
    await app.bot.send_message(chat_id=chat_id, text="Bot started.", disable_notification=False)


def main():
    token = TOKEN_FILE.read_text().strip()
    app = Application.builder().token(token).post_init(notify_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_pressed))
    app.add_error_handler(error_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
