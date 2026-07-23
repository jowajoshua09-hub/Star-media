import os, requests, threading, json
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = "https://blacknodezw.zone.id"

# ====== WEB SERVER TO SERVE index.html + KEEP RENDER ALIVE ======
def keep_port():
    port = int(os.environ.get("PORT", 10000))
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            # Map / to app/index.html or root index.html
            if self.path == "/":
                for cand in ["app/index.html", "index.html"]:
                    if os.path.exists(cand):
                        self.path = "/" + cand
                        return SimpleHTTPRequestHandler.do_GET(self)
                self.send_response(200); self.send_header("Content-type","text/html"); self.end_headers()
                self.wfile.write(b"<h1>STAR MEDIA Bot Live</h1><p>Add index.html to root or app/ folder</p>")
                return
            if self.path.startswith("/app/") or self.path == "/app":
                return SimpleHTTPRequestHandler.do_GET(self)
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        base_dir = "/opt/render/project/src" if os.path.exists("/opt/render/project/src") else "."
        os.chdir(base_dir)
        print(f"WEB ROOT: {os.getcwd()} app_exists={os.path.exists('app')} files={os.listdir('.')[:10]}")
        if os.path.exists("app"): print(f"app/ files: {os.listdir('app')}")
        HTTPServer(("0.0.0.0", port), H).serve_forever()
    except Exception as e:
        print(f"Web error: {e}")

threading.Thread(target=keep_port, daemon=True).start()

# ====== HELPERS ======
def extract_item(raw):
    print(f"RAW DEBUG keys={list(raw.keys()) if isinstance(raw,dict) else type(raw)} sample={str(raw)[:600]}")
    if isinstance(raw, str):
        return {"title": raw[:50], "artist": "YouTube", "thumb": None, "duration": "", "release": "", "url": raw}
    title = raw.get("title") or raw.get("name") or raw.get("video_title") or raw.get("caption") or raw.get("text") or raw.get("desc") or "Unknown Title"
    artist = raw.get("artist") or raw.get("author") or raw.get("channel") or raw.get("uploader") or raw.get("username") or "Unknown Artist"
    if isinstance(raw.get("owner"), dict): artist = raw["owner"].get("nickname", artist)
    thumb = (raw.get("thumbnail") or raw.get("thumb") or raw.get("cover") or raw.get("image") or raw.get("avatarThumb") or
             (raw.get("thumbnails",[None])[0] if isinstance(raw.get("thumbnails"), list) else None))
    if isinstance(thumb, dict): thumb = thumb.get("url")
    duration = raw.get("duration") or raw.get("length") or raw.get("durationString") or ""
    release = raw.get("release_date") or raw.get("published") or raw.get("date") or raw.get("publishTime") or ""
    url = raw.get("url") or raw.get("link") or raw.get("watch_url") or raw.get("videoId") or raw.get("id") or ""
    if url and not str(url).startswith("http"):
        if len(str(url)) <= 20: url = f"https://www.youtube.com/watch?v={url}"
        else: url = str(url)[:200]
    return {"title": str(title)[:60], "artist": str(artist)[:40], "thumb": thumb, "duration": str(duration), "release": str(release), "url": str(url)}

async def send_card(dest, item, context, is_edit=False):
    context.user_data["current"] = item
    caption = f"🎵 *{item['title']}*\n👤 {item['artist']}\n"
    if item["duration"]: caption += f"⏱ {item['duration']} "
    if item["release"]: caption += f"📅 {item['release']}\n"
    caption += "\nChoose format:"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3", callback_data="ask_mp3"), InlineKeyboardButton("🎬 MP4", callback_data="ask_mp4")]])
    thumb = item["thumb"]
    try:
        if thumb and str(thumb).startswith("http"):
            if is_edit: await dest.edit_message_caption(caption, reply_markup=markup, parse_mode="Markdown")
            else: await dest.reply_photo(photo=str(thumb), caption=caption, reply_markup=markup, parse_mode="Markdown")
        else:
            if is_edit: await dest.edit_message_text(caption, reply_markup=markup, parse_mode="Markdown")
            else: await dest.reply_text(caption, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"send_card error thumb={thumb} err={e}")
        if is_edit: await dest.edit_message_text(caption, reply_markup=markup, parse_mode="Markdown")
        else: await dest.reply_text(caption, reply_markup=markup, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌟 *STAR MEDIA*\n\nSend song name e.g. `John Michael Howell missing piece`", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if "http" in text:
        item = extract_item({"title":"Direct Link","artist":"YouTube","url":text,"thumbnail":None})
        return await send_card(update.message, item, context, False)
    status = await update.message.reply_text(f"🔍 Searching: {text}")
    try:
        r = requests.get(f"{BASE}/api/tiktok/search", params={"q": text}, timeout=20).json()
        items = r.get("data") or r.get("results") or r.get("result") or r
        if not isinstance(items, list): items = [items] if items else []
        if not items:
            try:
                r2 = requests.get(f"{BASE}/api/youtube/search", params={"q": text}, timeout=20).json()
                items = r2.get("data") or r2.get("results") or r2 or []
                if not isinstance(items, list): items = [items]
            except: pass
        if not items: return await status.edit_text("❌ No results found")
        await status.delete()
        first = extract_item(items[0])
        context.user_data["results"] = [extract_item(i) for i in items[:5]]
        await send_card(update.message, first, context, False)
    except Exception as e:
        await status.edit_text(f"Error: {e}"); print(f"SEARCH FAIL {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); d = q.data
    cur = context.user_data.get("current", {})
    if not cur and d!= "back_main": return await q.edit_message_text("Session expired, search again")
    if d == "ask_mp3":
        kb = [[InlineKeyboardButton("64kbps",callback_data="q_mp3|64"),InlineKeyboardButton("128kbps",callback_data="q_mp3|128"),InlineKeyboardButton("320kbps",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d == "ask_mp4":
        kb = [[InlineKeyboardButton("144p",callback_data="q_mp4|144"),InlineKeyboardButton("360p",callback_data="q_mp4|360")],[InlineKeyboardButton("720p",callback_data="q_mp4|720"),InlineKeyboardButton("1080p",callback_data="q_mp4|1080")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d.startswith("q_"):
        context.user_data["chosen"] = d
        qual = d.split("|")[1]
        kb = [[InlineKeyboardButton("📄 Document",callback_data=f"do|doc|{d}"),InlineKeyboardButton("▶️ Streamable",callback_data=f"do|stream|{d}")],[InlineKeyboardButton("⬅️ Back",callback_data="ask_back")]]
        try: await q.edit_message_caption(caption=f"🎧 {cur.get('title')}\nQuality: {qual}\n\nHow should I send?", reply_markup=InlineKeyboardMarkup(kb))
        except: await q.edit_message_text(f"🎧 {cur.get('title')}\nQuality: {qual}\n\nHow should I send?", reply_markup=InlineKeyboardMarkup(kb))
        return
    if d == "ask_back":
        fmt = context.user_data.get("chosen","q_mp3|128")
        if "mp3" in fmt: d="ask_mp3"
        else: d="ask_mp4"
        return await handle_button.__wrapped__ if False else await q.edit_message_reply_markup(InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3",callback_data="ask_mp3"),InlineKeyboardButton("🎬 MP4",callback_data="ask_mp4")]]))
    if d == "back_main":
        return await send_card(q, cur, context, True)
    if d.startswith("do|"):
        _, send_type, qfull = d.split("|",2)
        real_fmt = qfull.split("|")[0].replace("q_",""); real_q = qfull.split("|")[1]
        url = cur.get("url","")
        try:
            await q.edit_message_caption(f"⏳ Fetching {real_fmt.upper()} {real_q}...")
        except:
            try: await q.edit_message_text(f"⏳ Fetching {real_fmt.upper()} {real_q}...")
            except: pass
        try:
            res = requests.get(f"{BASE}/api/youtube/{real_fmt}", params={"url":url,"quality":real_q,"q":real_q}, timeout=90).json()
            dl = res.get("url") or res.get("download_url") or res.get("downloadUrl") or res.get("result") or res.get("link") or (res if isinstance(res,str) else None)
            if not dl: return await q.message.reply_text(f"API returned no link: {str(res)[:500]}")
            if send_type=="doc":
                if real_fmt=="mp3": await q.message.reply_document(document=dl, caption=f"🎵 {cur['title']} - {cur['artist']}")
                else: await q.message.reply_document(document=dl, caption=f"🎬 {cur['title']}")
            else:
                if real_fmt=="mp3": await q.message.reply_audio(audio=dl, title=cur['title'], performer=cur['artist'], caption=f"🎵 {cur['title']}")
                else: await q.message.reply_video(video=dl, caption=f"🎬 {cur['title']}", supports_streaming=True)
            try: await q.edit_message_caption(f"✅ Done: {cur['title']} [{real_fmt.upper()} {real_q}]")
            except: pass
        except Exception as e:
            print(f"DOWNLOAD ERR {e}"); await q.message.reply_text(f"❌ Download failed: {e}")

def main():
    if not BOT_TOKEN: print("ERROR: BOT_TOKEN not set"); return
    defaults = Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app = Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("STAR MEDIA Pro v4 Live - No links shown, thumbnail enabled")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
