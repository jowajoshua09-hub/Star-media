import os, requests, json
from threading import Thread
from http.server import HTTPServer, SimpleHTTPRequestHandler

# --- RENDER WEB SERVER + MINI APP SERVER ---
PORT = int(os.getenv("PORT", 10000))

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Health check for Render
        if self.path == "/" or self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type","text/plain")
            self.end_headers()
            self.wfile.write(b"Star Media OK - Bot Running")
            return
        # Serve Mini App at /app
        if self.path.startswith("/app"):
            # /app -> /app/index.html or /index.html in root
            if self.path == "/app" or self.path == "/app/":
                self.path = "/app/index.html" if os.path.exists("app/index.html") else "/index.html"
            # strip /app prefix if file is in root
            if not os.path.exists("."+self.path) and os.path.exists("./index.html"):
                self.path = "/index.html"
            return SimpleHTTPRequestHandler.do_GET(self)
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        return # silence logs

Thread(target=lambda: HTTPServer(("0.0.0.0", PORT), Handler).serve_forever(), daemon=True).start()
print(f"HTTP server on {PORT}")
# --- END SERVER ---

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

API_MP3 = "https://blacknodezw.zone.id/api/youtube/mp3"
API_MP4 = "https://blacknodezw.zone.id/api/youtube/mp4"
# WEBAPP_URL will be auto-detected from Render URL, fallback to your custom domain
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://blacknodezw.zone.id/app")
# If on Render, use same domain for Mini App
if os.getenv("RENDER_EXTERNAL_URL"):
    WEBAPP_URL = os.getenv("RENDER_EXTERNAL_URL").rstrip("/") + "/app"

def yt_search(query, limit=5):
    try:
        r = requests.get("https://iv.gg/api/v1/search", params={"q": query, "type": "video"}, timeout=10)
        out=[]
        for v in r.json()[:limit]:
            if v.get("type")=="video":
                out.append({
                    "id": v["videoId"],
                    "title": v["title"],
                    "author": v.get("author",""),
                    "thumb": f"https://i.ytimg.com/vi/{v['videoId']}/hqdefault.jpg",
                    "url": f"https://www.youtube.com/watch?v={v['videoId']}"
                })
        return out
    except Exception as e:
        print("Search error", e)
        return []

def dl_blacknode(yt_url, mode="mp3", quality="720"):
    quality_map = {"144":"144p","360":"360p","480":"480p","720":"720p","1080":"1080p","128":"128k","320":"320k"}
    q_param = quality_map.get(str(quality), str(quality))
    api = API_MP3 if "mp3" in mode else API_MP4
    payload = {"url": yt_url, "quality": q_param, "format": q_param}
    try:
        res = requests.post(api, json=payload, timeout=90)
        j = res.json()
        print("BlackNode Response:", j)
        link = j.get("url") or j.get("downloadUrl") or j.get("download_url") or j.get("link") or (j.get("data",{}).get("url") if isinstance(j.get("data"), dict) else None)
        title = j.get("title") or (j.get("data",{}).get("title") if isinstance(j.get("data"), dict) else None) or "gojo"
        return link, title
    except Exception as e:
        print(f"BlackNode {mode} {q_param} error:", e)
        return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("⭐ Open Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton("🔍 Search Songs"), KeyboardButton("🎬 Search Videos")]
    ]
    await update.message.reply_text(
        "⭐ *Star Media - Mini App Ready*\n\n"
        f"🌐 Mini App: {WEBAPP_URL}\n\n"
        "1️⃣ Tap **Open Mini App** for full YouTube inside Telegram\n"
        "2️⃣ Or just send song/video name here\n\n"
        "• Songs → sent as document `gojo.mp3`\n"
        "• Videos → 480p / 720p / 1080p choose",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.strip()
    if not q or q.startswith("/") or q.startswith("⭐") or q.startswith("🔍") or q.startswith("🎬"):
        return
    if "youtube.com" in q or "youtu.be" in q:
        yt_url = q
        kb = [[InlineKeyboardButton("🎵 SONG (MP3)", callback_data=f"type|song|{yt_url}"),
               InlineKeyboardButton("🎬 VIDEO (MP4)", callback_data=f"type|video|{yt_url}")]]
        await update.message.reply_text(f"🔗 *Found:*\n{yt_url}\n\nChoose type:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return
    msg = await update.message.reply_text(f"🔍 *Searching:* {q}", parse_mode="Markdown")
    results = yt_search(q)
    if not results:
        await msg.edit_text("❌ Not found. Try direct YouTube link."); return
    for v in results:
        kb = [[InlineKeyboardButton("🎵 Song", callback_data=f"type|song|{v['url']}"),
               InlineKeyboardButton("🎬 Video", callback_data=f"type|video|{v['url']}")]]
        try:
            await update.message.reply_photo(v['thumb'], caption=f"*{v['title']}*\n_{v['author']}_", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except:
            await update.message.reply_text(f"*{v['title']}*\n{v['url']}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    try: await msg.delete()
    except: pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    if data.startswith("type|"):
        _, ftype, yt_url = data.split("|", 2)
        if ftype == "song":
            kb = [[InlineKeyboardButton("🎧 128k Fast", callback_data=f"dl|mp3|128|{yt_url}"),
                   InlineKeyboardButton("🔊 320k Best", callback_data=f"dl|mp3|320|{yt_url}")],
                  [InlineKeyboardButton("📁 Send as gojo.mp3 (Document)", callback_data=f"dl|mp3_doc|320|{yt_url}")]]
            txt = "\n\n🎵 *Choose audio quality:*"
        else:
            kb = [[InlineKeyboardButton("480p", callback_data=f"dl|mp4|480|{yt_url}"),
                   InlineKeyboardButton("720p HD", callback_data=f"dl|mp4|720|{yt_url}"),
                   InlineKeyboardButton("1080p FHD", callback_data=f"dl|mp4|1080|{yt_url}")],
                  [InlineKeyboardButton("144p", callback_data=f"dl|mp4|144|{yt_url}"),
                   InlineKeyboardButton("360p", callback_data=f"dl|mp4|360|{yt_url}"),
                   InlineKeyboardButton("🎵 Extract gojo.mp3", callback_data=f"dl|mp3_doc|320|{yt_url}")]]
            txt = "\n\n🎬 *Choose video quality:*"
        try:
            await query.edit_message_caption(caption=(query.message.caption or "") + txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except:
            try: await query.edit_message_text((query.message.text or "") + txt, reply_markup=InlineKeyboardMarkup(kb))
            except: pass
        return
    if data.startswith("dl|"):
        _, mode, quality, yt_url = data.split("|", 3)
        is_doc = "doc" in mode
        real_mode = "mp3" if "mp3" in mode else "mp4"
        try:
            await query.edit_message_caption(caption=query.message.caption + f"\n\n⏳ *Downloading {real_mode.upper()} {quality} via BlackNode...*", parse_mode="Markdown")
        except:
            try: await query.edit_message_text(f"⏳ Downloading {real_mode.upper()} {quality}...")
            except: pass
        link, title = dl_blacknode(yt_url, real_mode, quality)
        if not link:
            await query.message.reply_text("❌ BlackNode failed. Please tap Retry.")
            return
        try:
            if real_mode == "mp3" or is_doc:
                await context.bot.send_document(chat_id=query.message.chat_id, document=link, filename="gojo.mp3",
                    caption=f"⭐ *{title}*\n`gojo.mp3` | {quality}\nPowered by Star Media x BlackNode", parse_mode="Markdown")
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=link,
                    caption=f"⭐ *{title}* [{quality}p]\nPowered by Star Media", parse_mode="Markdown", supports_streaming=True)
        except Exception as e:
            print("Send error", e)
            await query.message.reply_text(f"✅ Ready! Direct link:\n{link}\n\n*{title}*", parse_mode="Markdown")

async def webapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_message.web_app_data:
        return
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        dl_url = data.get('dl_url'); ftype = data.get('type','mp3'); quality = data.get('quality','320k'); title = data.get('title','gojo')
        if not dl_url: return
        if ftype == "mp3":
            await context.bot.send_document(chat_id=update.effective_chat.id, document=dl_url, filename="gojo.mp3", caption=f"⭐ {title} | {quality} via Mini App")
        else:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=dl_url, caption=f"⭐ {title} [{quality}] via Mini App", supports_streaming=True)
    except Exception as e:
        print("WebApp error", e)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # WEB_APP_DATA must be BEFORE text handler
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_handler))
    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^(type|dl)\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
    print("⭐ Star Media LIVE")
    app.run_polling()

if __name__ == "__main__":
    main()