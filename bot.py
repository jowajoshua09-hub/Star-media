import os, requests, threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
DL_BASE = "https://blacknodezw.zone.id"
SEARCH_API = "https://api.hostify.indevs.in/api/search/youtube"

# ===== WEB SERVER (for render site) =====
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
                self.wfile.write(b"<h1>STAR MEDIA Bot Live</h1><p>Bot is running</p>")
                return
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        base = "/opt/render/project/src" if os.path.exists("/opt/render/project/src") else "."
        os.chdir(base)
        HTTPServer(("0.0.0.0", port), H).serve_forever()
    except Exception as e:
        print(f"web err {e}")
threading.Thread(target=keep_port, daemon=True).start()

# ===== HELPERS =====
def extract_item(raw):
    # fix wrapper {video:{}}
    if isinstance(raw, dict) and "video" in raw and isinstance(raw["video"], dict):
        raw = raw["video"]
    title = raw.get("title") or raw.get("desc") or raw.get("caption") or raw.get("name") or "Unknown Title"
    artist = raw.get("author")
    if isinstance(artist, dict): artist = artist.get("nickname") or artist.get("uniqueId") or "TikTok User"
    else: artist = artist or raw.get("channel") or raw.get("username") or "Unknown Artist"
    thumb = raw.get("cover") or raw.get("coverUrl") or raw.get("thumbnail") or raw.get("originCover") or raw.get("avatarThumb")
    if isinstance(thumb, list): thumb = thumb[0]
    vid = str(raw.get("id") or raw.get("videoId") or raw.get("video_id") or "")
    duration = str(raw.get("duration") or raw.get("length") or "")
    url = raw.get("url") or (f"https://www.tiktok.com/@user/video/{vid}" if len(vid) > 10 else f"https://www.youtube.com/watch?v={vid}" if vid else "")
    item = {"title": str(title)[:80], "artist": str(artist)[:40], "thumb": thumb, "duration": duration, "url": url, "vid": vid}
    print(f"EXTRACTED: {item['title'][:30]} | vid={vid} | thumb_exists={bool(thumb)}")
    return item

async def send_card(msg_obj, item, context, is_edit=False):
    context.user_data["current"] = item
    cap = f"🎵 *{item['title']}*\n👤 {item['artist']}\n"
    if item["duration"]: cap += f"⏱ {item['duration']}\n"
    cap += "\nChoose format:"
    mk = InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3", callback_data="ask_mp3"), InlineKeyboardButton("🎬 MP4", callback_data="ask_mp4")]])
    try:
        if item["thumb"] and str(item["thumb"]).startswith("http"):
            if is_edit: await msg_obj.edit_message_caption(cap, reply_markup=mk, parse_mode="Markdown")
            else: await msg_obj.reply_photo(photo=item["thumb"], caption=cap, reply_markup=mk, parse_mode="Markdown")
        else:
            if is_edit: await msg_obj.edit_message_text(cap, reply_markup=mk, parse_mode="Markdown")
            else: await msg_obj.reply_text(cap, reply_markup=mk, parse_mode="Markdown")
    except Exception as e:
        print(f"send_card err {e}")
        if is_edit: await msg_obj.edit_message_text(cap, reply_markup=mk, parse_mode="Markdown")
        else: await msg_obj.reply_text(cap, reply_markup=mk, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌟 *STAR MEDIA*\nSend song name e.g. `John Michael Howell`", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.startswith("http"):
        it = extract_item({"id": txt.split("/")[-1], "title": "Direct Link", "url": txt, "cover": None})
        return await send_card(update.message, it, context)

    st = await update.message.reply_text(f"🔍 Searching: {txt}")
    try:
        videos = []
        # 1. Try blacknode TikTok search - structure from your screenshot: {status:200, data:{videos:[...]}}
        try:
            r = requests.get(f"{DL_BASE}/api/tiktok/search", params={"q": txt, "count": 5}, timeout=20)
            j = r.json()
            print(f"BLACKNODE RAW: {r.text[:1500]}")
            if isinstance(j, dict):
                if "data" in j and isinstance(j["data"], dict) and "videos" in j["data"]:
                    videos = j["data"]["videos"]
                elif "data" in j and isinstance(j["data"], list):
                    videos = j["data"]
                elif "videos" in j:
                    videos = j["videos"]
        except Exception as e:
            print(f"tiktok search err {e}")

        # 2. Fallback to hostify YouTube search if TikTok empty
        if not videos:
            try:
                r = requests.get(SEARCH_API, params={"q": txt}, timeout=15).json()
                print(f"HOSTIFY RAW: {str(r)[:1000]}")
                tmp = r.get("result") or r.get("data") or r.get("results") or []
                if isinstance(tmp, list) and tmp: videos = tmp
            except Exception as e:
                print(f"hostify err {e}")

        if not videos:
            return await st.edit_text(f"❌ No results for '{txt}'\nTry: `John Michael Howell`")

        await st.delete()
        first = extract_item(videos[0])
        context.user_data["all"] = [extract_item(v) for v in videos]
        await send_card(update.message, first, context)

    except Exception as e:
        print(f"SEARCH FATAL {e}")
        await st.edit_text(f"Error: {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    cur = context.user_data.get("current")
    if not cur: return await q.edit_message_text("Session expired, search again")

    if d == "ask_mp3":
        kb = [[InlineKeyboardButton("64kbps", callback_data="q_mp3|64"), InlineKeyboardButton("128kbps", callback_data="q_mp3|128"), InlineKeyboardButton("320kbps", callback_data="q_mp3|320")],
              [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if d == "ask_mp4":
        kb = [[InlineKeyboardButton("144p", callback_data="q_mp4|144"), InlineKeyboardButton("360p", callback_data="q_mp4|360")],
              [InlineKeyboardButton("720p", callback_data="q_mp4|720"), InlineKeyboardButton("1080p", callback_data="q_mp4|1080")],
              [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if d == "back_main":
        return await send_card(q, cur, context, True)

    if d.startswith("q_"):
        qual = d.split("|")[1]
        context.user_data["chosen"] = d
        kb = [[InlineKeyboardButton("📄 Document", callback_data=f"do|doc|{d}"), InlineKeyboardButton("▶️ Stream", callback_data=f"do|stream|{d}")],
              [InlineKeyboardButton("⬅️ Back", callback_data="back_q")]]
        try: await q.edit_message_caption(caption=f"🎧 {cur['title']}\nQuality: {qual}\nHow to send?", reply_markup=InlineKeyboardMarkup(kb))
        except: await q.edit_message_text(f"🎧 {cur['title']}\nQuality: {qual}\nHow to send?", reply_markup=InlineKeyboardMarkup(kb))
        return

    if d == "back_q":
        chosen = context.user_data.get("chosen","q_mp3|128")
        back = "ask_mp3" if "mp3" in chosen else "ask_mp4"
        if back == "ask_mp3":
            kb = [[InlineKeyboardButton("64",callback_data="q_mp3|64"),InlineKeyboardButton("128",callback_data="q_mp3|128"),InlineKeyboardButton("320",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        else:
            kb = [[InlineKeyboardButton("144p",callback_data="q_mp4|144"),InlineKeyboardButton("360p",callback_data="q_mp4|360")],[InlineKeyboardButton("720p",callback_data="q_mp4|720")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))

    if d.startswith("do|"):
        _, send_type, qfull = d.split("|",2)
        fmt = qfull.split("|")[0].replace("q_","")
        qual = qfull.split("|")[1]
        vid = cur.get("vid","")
        is_tiktok = len(vid) > 12 # TikTok IDs are 19 digits
        print(f"DOWNLOAD START fmt={fmt} qual={qual} vid={vid} is_tiktok={is_tiktok}")
        try: await q.edit_message_caption(f"⏳ Fetching {fmt.upper()} {qual}...")
        except:
            try: await q.edit_message_text(f"⏳ Fetching {fmt.upper()} {qual}...")
            except: pass

        dl_url = None
        caption = cur["title"]
        try:
            if is_tiktok:
                # Try multiple tiktok download patterns
                endpoints = [
                    f"{DL_BASE}/api/tiktok/download",
                    f"{DL_BASE}/api/tiktok/dl",
                    "https://api.hostify.indevs.in/api/download/tiktok"
                ]
                for ep in endpoints:
                    try:
                        pr = {"url": f"https://www.tiktok.com/@a/video/{vid}", "id": vid, "video_id": vid}
                        res = requests.get(ep, params=pr, timeout=30).json()
                        print(f"TT DL {ep} -> {str(res)[:800]}")
                        data = res.get("data") if isinstance(res.get("data"), dict) else res
                        if fmt == "mp3":
                            dl_url = data.get("music") or data.get("audio") or data.get("play") or res.get("music")
                        else:
                            dl_url = data.get("hdplay") or data.get("play") or data.get("wmplay") or res.get("url")
                        if dl_url: break
                    except Exception as e:
                        print(f"ep {ep} fail {e}")
                        continue
            else:
                # YouTube download
                res = requests.get(f"{DL_BASE}/api/youtube/{fmt}", params={"url": cur["url"], "quality": qual}, timeout=60).json()
                print(f"YT DL -> {str(res)[:600]}")
                dl_url = res.get("url") or res.get("download_url") or res.get("result")
        except Exception as e:
            print(f"DL ERROR {e}")

        if not dl_url:
            return await q.message.reply_text(f"❌ No download link for {cur['title']}\nvid={vid}\nCheck Render Logs > TT DL line")

        try:
            if send_type == "doc":
                if fmt == "mp3": await q.message.reply_document(document=dl_url, caption=f"🎵 {caption}")
                else: await q.message.reply_document(document=dl_url, caption=f"🎬 {caption}")
            else:
                if fmt == "mp3": await q.message.reply_audio(audio=dl_url, title=caption[:60], performer=cur["artist"])
                else: await q.message.reply_video(video=dl_url, caption=caption, supports_streaming=True)
            try: await q.edit_message_caption(f"✅ Done: {caption}")
            except: pass
        except Exception as e:
            await q.message.reply_text(f"Here is your link (Telegram could not stream directly):\n{dl_url}\n\nError: {e}")

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing! Set in Render Env Vars")
        return
    defaults = Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app = Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("STAR MEDIA v7 - TikTok videos parser FIXED - Live")
    # Fix Conflict error
    import asyncio
    async def clean():
        try: await app.bot.delete_webhook(drop_pending_updates=True)
        except: pass
    try: asyncio.get_event_loop().run_until_complete(clean())
    except: pass
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
