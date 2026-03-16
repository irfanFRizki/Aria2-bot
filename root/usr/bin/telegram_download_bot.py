#!/usr/bin/env python3
import os, asyncio, subprocess
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes

def get_uci_config(option):
    try:
        res = subprocess.check_output(f"uci get aria2bot.main.{option}", shell=True)
        return res.decode().strip()
    except:
        return None

TELEGRAM_BOT_TOKEN = get_uci_config("bot_token")
CHAT_ID = get_uci_config("chat_id")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        return
    keyboard = [[KeyboardButton("📊 Status"), KeyboardButton("📂 Storage")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"🤖 Aria2 Bot Aktif!\nToken: Terdeteksi\nChat ID: {CHAT_ID}", reply_markup=reply_markup)

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("Gagal: Token UCI kosong")
        exit(1)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
