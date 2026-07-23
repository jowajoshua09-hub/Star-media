import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = "https://blacknodezw.zone.id"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 STAR MEDIA\n\nSend song name OR YouTube link\nExample: John Michael Howell missing piece\n\nI'll search and give you MP3 / MP4 buttons.",
        disable_web_page_preview=True
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # 1. If direct YouTube URL -> show MP3/MP4 buttons immediately
    if "youtube.com" in text or "youtu.be" in text:
        url = text
        buttons = [
            [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3|{url}"),
             InlineKeyboardButton("🎬 MP4", callback_data=f"mp4|{url}")]
        ]
        return await update.message.reply_text(
            f"Link detected:\n{url}",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    # 2. Else it's a SEARCH (e.g. John Michael Howell missing piece)
    msg = await update.message.reply_text(f"🔍 Searching: {text}", disable_web_page_preview=True)
    try:
        # Use your BlackNode search - it returns youtube results too
        r = requests.get(f"{BASE}/api/tiktok/search", params={"q": text}, timeout=15).json()
        # Your API returns list - adapt to your structure
        results = r.get("data", r.get("results", []))[:5]

        if not results:
            return await msg.edit_text("No results. Try different keywords.", disable_web_page_preview=True)

        buttons = []
        for item in results:
            title = item.get("title", "Unknown")[:35]
            vid_url = item.get("url") or item.get("link") or f"https://www.youtube.com/watch?v={item.get('id')}"
            # IMPORTANT: We pass the URL here to downloader
            buttons.append([InlineKeyboardButton(f"⬇️ {title}", callback_data=f"choose|{vid_url}")])

        await msg.edit_text(
            f"Found {len(buttons)} results for '{text}':",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
    except Exception as e:
        await msg.edit_text(f"Search failed: {e}", disable_web_page_preview=True)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("choose|"):
        url = data.split("choose|", 1)[1]
        buttons = [
            [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3|{url}"),
             InlineKeyboardButton("🎬 MP4", callback_data=f"mp4|{url}")]
        ]
        return await q.edit_message_text(
            f"Selected:\n{url}\n\nChoose format:",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    if data.startswith("mp3|") or data.startswith("mp4|"):
        fmt, url = data.split("|", 1)
        endpoint = f"{BASE}/api/youtube/{fmt}"

        await q.edit_message_text(f"⏳ Fetching {fmt.upper()} for:\n{url}", disable_web_page_preview=True)

        try:
            res = requests.get(endpoint, params={"url": url}, timeout=30).json()
            # Your API returns download url in 'url' or 'download_url' or 'result'
            dl_url = res.get("url") or res.get("download_url") or res.get("result") or res.get("link")

            if not dl_url:
                return await q.edit_message_text(f"❌ API returned no link:\n{res}", disable_web_page_preview=True)

            await q.edit_message_text(
                f"✅ {fmt.upper()} Ready!\n\n{dl_url}",
                disable_web_page_preview=True
            )
            # Also send as file if direct
            # await context.bot.send_audio(chat_id=q.message.chat.id, audio=dl_url)

        except Exception as e:
            await q.edit_message_text(f"❌ BlackNode {fmt} failed\n{url}\nError: {e}", disable_web_page_preview=True)

def main():
    defaults = Defaults(disable_web_page_preview=True)
    app = Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button, pattern="^(choose|mp3|mp4)\\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("STAR MEDIA Live")
    app.run_polling()

if __name__ == "__main__":
    main()
