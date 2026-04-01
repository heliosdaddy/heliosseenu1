import asyncio
import os
import main_script
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")

running_task = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running_task

    if running_task and not running_task.done():
        await update.message.reply_text("⚠️ Already running!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage:\n/start username")
        return

    target = context.args[0]
    await update.message.reply_text(f"🚀 Starting bot for @{target}")

    loop = asyncio.get_event_loop()
    running_task = loop.create_task(main_script.start_bot(target))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running_task

    if running_task and not running_task.done():
        running_task.cancel()
        running_task = None
        await update.message.reply_text("🛑 Bot stopped")
    else:
        await update.message.reply_text("❌ No bot running")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if running_task and not running_task.done():
        await update.message.reply_text("✅ Bot is running")
    else:
        await update.message.reply_text("❌ Bot is stopped")
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = ApplicationBuilder().token(BOT_TOKEN).build()

ApplicationBuilder().token(BOT_TOKEN)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("status", status))

print("🤖 Telegram Bot Running...")
import asyncio
import os
from telegram.ext import ApplicationBuilder

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = ApplicationBuilder().token(BOT_TOKEN).build()

async def main():
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)  # 🔥 force clear everything
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
app.run_polling(drop_pending_updates=True, close_loop=False)
