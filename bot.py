import os
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = "https://blacknodezw.zone.id"

# --- FIX for Render Web Service "No open ports" ---
def keep_port():
    port = int(os.environ.get("PORT", 10000))
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"STAR MEDIA Bot Running")
        def log_message(self, *a):
            pass
    try:
        HTTPServer(("0.0.0.0", port), H).serve_forever()
    except:
        pass

threading.Thread(target=keep_port, daemon=True).start()
# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 STAR MEDIA\n\nSend song name OR YouTube link\nExample: John Michael Howell missing piece"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "youtube.com" in text or "youtu.be" in text or "tiktok.com" in text:
        url = text
        context.user_data["url_0"] = url
        buttons = [
            [InlineKeyboardButton("🎵 MP3", callback_data="mp3|0"),
             InlineKeyboardButton("🎬 MP4", callback_data="mp4|0")]
        ]
        return await update.message.reply_text(
            f"Link detected:\n{url}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    msg = await update.message.reply_text(f"🔍 Searching: {text}")
    try:
        r = requests.get(f"{BASE}/api/tiktok/search", params={"q": text}, timeout=20).json()

        if isinstance(r, dict):
            raw_list = r.get("data") or r.get("results") or r.get("result") or []
        else:
            raw_list = r

        if not isinstance(raw_list, list):
            raw_list = [raw_list]

        results = raw_list[:5]

        if not results:
            return await msg.edit_text("No results found.")

        buttons = []
        for i, item in enumerate(results):
            if isinstance(item, str):
                title = item[:35]
                vid_url = item
            else:
                title = str(item.get("title", f"Result {i+1}"))[:35]
                vid_url = item.get("url") or item.get("link") or item.get("id") or str(item)

            context.user_data[f"url_{i}"] = vid_url
            buttons.append([InlineKeyboardButton(f"⬇️ {title}", callback_data=f"choose|{i}")])

        await msg.edit_text(
            f"Found {len(buttons)} results for '{text}':",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await msg.edit_text(f"Search failed: {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("choose|"):
        sid = data.split("|", 1)[1]
        url = context.user_data.get(f"url_{sid}", "")
        if not url:
            return await q.edit_message_text("URL expired. Search again.")

        buttons = [
            [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3|{sid}"),
             InlineKeyboardButton("🎬 MP4", callback_data=f"mp4|{sid}")]
        ]
        return await q.edit_message_text(
            f"Selected:\n{url}\n\nChoose format:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    if data.startswith("mp3|") or data.startswith("mp4|"):
        fmt, sid = data.split("|", 1)
        url = context.user_data.get(f"url_{sid}", sid)

        endpoint = f"{BASE}/api/youtube/{fmt}"
        await q.edit_message_text(f"⏳ Fetching {fmt.upper()}...\n{url}")

        try:
            res = requests.get(endpoint, params={"url": url}, timeout=40).json()
            dl_url = res.get("url") or res.get("download_url") or res.get("downloadUrl") or res.get("result") or res.get("link")

            if not dl_url:
                if isinstance(res, str):
                    dl_url = res
                else:
                    return await q.edit_message_text(f"❌ No link returned:\n{str(res)[:500]}")

            await q.edit_message_text(f"✅ {fmt.upper()} Ready!\n\n{dl_url}")

        except Exception as e:
            await q.edit_message_text(f"❌ {BASE}/api/youtube/{fmt} failed\nError: {e}")

def main():
    # FIX: New way to disable preview - no more deprecation warning
    defaults = Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app = Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button, pattern="^(choose|mp3|mp4)\\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("STAR MEDIA Live")
    app.run_polling()

if __name__ == "__main__":
    main()
