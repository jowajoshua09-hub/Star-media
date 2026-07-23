import os, requests, threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
SEARCH_API = "https://api.hostify.indevs.in/api/search/youtube"
DL_BASE = "https://blacknodezw.zone.id"

# ===== WEB SERVER FOR index.html =====
def keep_port():
    port = int(os.environ.get("PORT", 10000))
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                for cand in ["app/index.html","index.html"]:
                    if os.path.exists(cand):
                        self.path = "/" + cand
                        return SimpleHTTPRequestHandler.do_GET(self)
                self.send_response(200); self.send_header("Content-type","text/html"); self.end_headers()
                self.wfile.write(b"<h1>STAR MEDIA Bot Live</h1>")
                return
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        base = "/opt/render/project/src" if os.path.exists("/opt/render/project/src") else "."
        os.chdir(base)
        HTTPServer(("0.0.0.0", port), H).serve_forever()
    except: pass
threading.Thread(target=keep_port, daemon=True).start()

# ===== HELPERS =====
def extract_item(raw):
    print(f"RAW: {str(raw)[:700]}")
    if isinstance(raw, str):
        return {"title": raw[:60], "artist":"YouTube","thumb":None,"duration":"","release":"","url":raw,"vid":""}
    title = raw.get("title") or raw.get("name") or "Unknown Title"
    artist = raw.get("channel") or raw.get("channelTitle") or raw.get("author") or raw.get("uploader") or "Unknown Artist"
    thumb = raw.get("thumbnail") or raw.get("thumbnailUrl")
    if isinstance(thumb, list) and thumb: thumb = thumb[0]
    if isinstance(thumb, dict): thumb = thumb.get("url")
    if not thumb and raw.get("thumbnails"):
        th = raw["thumbnails"]
        if isinstance(th, list) and th: thumb = th[0] if isinstance(th[0], str) else th[0].get("url")
    vid = raw.get("videoId") or raw.get("id") or ""
    if isinstance(vid, dict): vid = vid.get("videoId","")
    url = raw.get("url") or raw.get("link") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
    duration = raw.get("duration") or raw.get("durationText") or raw.get("length") or ""
    return {"title":str(title)[:65],"artist":str(artist)[:40],"thumb":thumb,"duration":str(duration),"release":"","url":str(url),"vid":str(vid)}

async def send_card(dest, item, context, is_edit=False):
    context.user_data["current"] = item
    caption = f"*{item['title']}*\n👤 {item['artist']}\n"
    if item["duration"]: caption += f"⏱ {item['duration']}\n"
    caption += "\nChoose format:"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3", callback_data="ask_mp3"), InlineKeyboardButton("🎬 MP4", callback_data="ask_mp4")]])
    try:
        if item["thumb"] and str(item["thumb"]).startswith("http"):
            if is_edit: await dest.edit_message_caption(caption, reply_markup=markup, parse_mode="Markdown")
            else: await dest.reply_photo(photo=item["thumb"], caption=caption, reply_markup=markup, parse_mode="Markdown")
        else:
            if is_edit: await dest.edit_message_text(caption, reply_markup=markup, parse_mode="Markdown")
            else: await dest.reply_text(caption, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"send_card thumb fail {e}")
        if is_edit: await dest.edit_message_text(caption, reply_markup=markup, parse_mode="Markdown")
        else: await dest.reply_text(caption, reply_markup=markup, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌟 *STAR MEDIA*\nSend song name", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("http"):
        item = extract_item({"title":"Direct Link","channel":"YouTube","url":text})
        return await send_card(update.message, item, context, False)
    status = await update.message.reply_text(f"🔍 Searching: {text}")
    try:
        # Use your new hostify API
        r = requests.get(SEARCH_API, params={"q": text}, timeout=20)
        print(f"SEARCH status {r.status_code} body {r.text[:1000]}")
        data = r.json()
        # hostify can return {data:[] } or {results:[]} or []
        items = data.get("data") or data.get("results") or data.get("result") or data
        if isinstance(items, dict) and "videos" in items: items = items["videos"]
        if not isinstance(items, list): items = [items] if items else []
        if not items: return await status.edit_text("❌ No results")
        await status.delete()
        first = extract_item(items[0])
        context.user_data["results"] = [extract_item(i) for i in items[:5]]
        # Ensure url exists
        if not first["url"] and first["vid"]:
            first["url"] = f"https://www.youtube.com/watch?v={first['vid']}"
        print(f"FIRST URL={first['url']} THUMB={first['thumb']}")
        await send_card(update.message, first, context, False)
    except Exception as e:
        print(f"SEARCH ERR {e}")
        await status.edit_text(f"Search error: {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); d = q.data
    cur = context.user_data.get("current",{})
    if not cur: return await q.edit_message_text("Expired, search again")
    if d == "ask_mp3":
        kb = [[InlineKeyboardButton("64kbps",callback_data="q_mp3|64"),InlineKeyboardButton("128kbps",callback_data="q_mp3|128"),InlineKeyboardButton("320kbps",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d == "ask_mp4":
        kb = [[InlineKeyboardButton("144p",callback_data="q_mp4|144"),InlineKeyboardButton("360p",callback_data="q_mp4|360")],[InlineKeyboardButton("720p",callback_data="q_mp4|720"),InlineKeyboardButton("1080p",callback_data="q_mp4|1080")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d == "back_main":
        return await send_card(q, cur, context, True)
    if d.startswith("q_"):
        qual = d.split("|")[1]
        context.user_data["chosen"] = d
        kb = [[InlineKeyboardButton("📄 Document",callback_data=f"do|doc|{d}"),InlineKeyboardButton("▶️ Stream",callback_data=f"do|stream|{d}")],[InlineKeyboardButton("⬅️ Back",callback_data="back_q")]]
        try: await q.edit_message_caption(caption=f"🎧 {cur['title']}\nQuality: {qual}\nHow to send?", reply_markup=InlineKeyboardMarkup(kb))
        except: await q.edit_message_text(f"🎧 {cur['title']}\nQuality: {qual}\nHow to send?", reply_markup=InlineKeyboardMarkup(kb))
        return
    if d == "back_q":
        chosen = context.user_data.get("chosen","q_mp3|128")
        back = "ask_mp3" if "mp3" in chosen else "ask_mp4"
        kb = [[InlineKeyboardButton("64kbps",callback_data="q_mp3|64"),InlineKeyboardButton("128kbps",callback_data="q_mp3|128"),InlineKeyboardButton("320kbps",callback_data="q_mp3|320")]] if back=="ask_mp3" else [[InlineKeyboardButton("144p",callback_data="q_mp4|144"),InlineKeyboardButton("360p",callback_data="q_mp4|360")],[InlineKeyboardButton("720p",callback_data="q_mp4|720"),InlineKeyboardButton("1080p",callback_data="q_mp4|1080")]]
        kb.append([InlineKeyboardButton("⬅️ Back",callback_data="back_main")])
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d.startswith("do|"):
        _, send_type, qfull = d.split("|",2)
        real_fmt = qfull.split("|")[0].replace("q_",""); real_q = qfull.split("|")[1]
        url = cur.get("url") or (f"https://www.youtube.com/watch?v={cur.get('vid')}" if cur.get("vid") else "")
        print(f"DOWNLOAD REQ fmt={real_fmt} q={real_q} url={url}")
        try: await q.edit_message_caption(f"⏳ Fetching {real_fmt.upper()} {real_q}...")
        except: pass
        dl = None
        # 1. Try blacknode
        try:
            res = requests.get(f"{DL_BASE}/api/youtube/{real_fmt}", params={"url": url, "quality": real_q}, timeout=60).json()
            print(f"blacknode resp {str(res)[:500]}")
            dl = res.get("url") or res.get("download_url") or res.get("result") if isinstance(res, dict) else res
        except Exception as e: print(f"blacknode fail {e}")
        # 2. Try hostify download fallback
        if not dl:
            try:
                res2 = requests.get(f"https://api.hostify.indevs.in/api/download", params={"url": url, "format": real_fmt, "quality": real_q}, timeout=60).json()
                print(f"hostify dl resp {str(res2)[:500]}")
                dl = res2.get("url") or res2.get("downloadUrl") or res2.get("link")
            except Exception as e: print(f"hostify dl fail {e}")
        if not dl:
            return await q.message.reply_text(f"❌ No download link. URL used: {url}\nCheck Render Logs for API response.")
        try:
            if send_type == "doc":
                await q.message.reply_document(document=dl, caption=f"{cur['title']}")
            else:
                if real_fmt == "mp3": await q.message.reply_audio(audio=dl, title=cur['title'], performer=cur['artist'])
                else: await q.message.reply_video(video=dl, caption=cur['title'], supports_streaming=True)
            try: await q.edit_message_caption(f"✅ Done {cur['title']}")
            except: pass
        except Exception as e:
            await q.message.reply_text(f"Failed to send file, here is direct link:\n{dl}\nError:{e}")

def main():
    defaults = Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app = Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("STAR MEDIA v5 Hostify Search Live")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
