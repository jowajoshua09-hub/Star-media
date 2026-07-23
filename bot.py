import os, requests, threading, json
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
SEARCH_API = "https://api.hostify.indevs.in/api/search/youtube"
DL_BASE = "https://blacknodezw.zone.id"

def keep_port():
    port = int(os.environ.get("PORT", 10000))
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                for c in ["app/index.html","index.html"]:
                    if os.path.exists(c):
                        self.path = "/"+c
                        return SimpleHTTPRequestHandler.do_GET(self)
                self.send_response(200);self.send_header("Content-type","text/html");self.end_headers()
                self.wfile.write(b"<h1>STAR MEDIA Live</h1>")
                return
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        os.chdir("/opt/render/project/src" if os.path.exists("/opt/render/project/src") else ".")
        HTTPServer(("0.0.0.0", port), H).serve_forever()
    except: pass
threading.Thread(target=keep_port, daemon=True).start()

def deep_find(d, keys):
    """recursively find first matching key in dict/list"""
    if isinstance(d, dict):
        for k in keys:
            if k in d and d[k]: return d[k]
        for v in d.values():
            r = deep_find(v, keys)
            if r: return r
    elif isinstance(d, list):
        for i in d:
            r = deep_find(i, keys)
            if r: return r
    return None

def extract_item(raw):
    # hostify sometimes wraps in {video:{...}}
    if isinstance(raw, dict) and "video" in raw and isinstance(raw["video"], dict):
        raw = raw["video"]
    title = deep_find(raw, ["title","name","video_title"]) or "Unknown Title"
    if isinstance(title, dict): title = title.get("text") or title.get("simpleText") or str(title)
    artist = deep_find(raw, ["channel","author","channelTitle","channelName","owner"]) or "YouTube"
    if isinstance(artist, dict): artist = artist.get("name") or artist.get("text") or str(artist)
    thumb = deep_find(raw, ["thumbnail","thumbnailUrl","hqdefault"])
    if isinstance(thumb, list): thumb = thumb[0].get("url") if isinstance(thumb[0],dict) else thumb[0]
    if isinstance(thumb, dict): thumb = thumb.get("url") or thumb.get("src")
    # Find videoId in any depth
    vid = deep_find(raw, ["videoId","video_id","id"])
    if isinstance(vid, dict): vid = vid.get("videoId") or vid.get("id")
    url = deep_find(raw, ["url","link","watchUrl"])
    if not url and vid and len(str(vid)) < 20:
        url = f"https://www.youtube.com/watch?v={vid}"
    duration = deep_find(raw, ["duration","lengthText","durationText"]) or ""
    if isinstance(duration, dict): duration = duration.get("simpleText") or ""
    item = {"title":str(title)[:70],"artist":str(artist)[:40],"thumb":str(thumb) if thumb else None,"duration":str(duration),"url":str(url) if url else "","vid":str(vid) if vid else ""}
    print(f"EXTRACTED -> {item}")
    return item

async def send_card(dest, item, context, is_edit=False):
    context.user_data["current"] = item
    cap = f"*{item['title']}*\n👤 {item['artist']}\n"
    if item["duration"]: cap+=f"⏱ {item['duration']}\n"
    cap+="\nChoose format:"
    mk = InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3",callback_data="ask_mp3"),InlineKeyboardButton("🎬 MP4",callback_data="ask_mp4")]])
    try:
        if item["thumb"] and item["thumb"].startswith("http"):
            if is_edit: await dest.edit_message_caption(cap, reply_markup=mk, parse_mode="Markdown")
            else: await dest.reply_photo(photo=item["thumb"], caption=cap, reply_markup=mk, parse_mode="Markdown")
        else:
            if is_edit: await dest.edit_message_text(cap, reply_markup=mk, parse_mode="Markdown")
            else: await dest.reply_text(cap, reply_markup=mk, parse_mode="Markdown")
    except:
        if is_edit: await dest.edit_message_text(cap, reply_markup=mk, parse_mode="Markdown")
        else: await dest.reply_text(cap, reply_markup=mk, parse_mode="Markdown")

async def start(update, context): await update.message.reply_text("🌟 STAR MEDIA\nSend song name")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if "http" in txt:
        return await send_card(update.message, {"title":"Direct","artist":"YouTube","thumb":None,"duration":"","url":txt,"vid":""}, context)
    st = await update.message.reply_text(f"🔍 Searching: {txt}")
    try:
        r = requests.get(SEARCH_API, params={"q": txt}, timeout=20)
        j = r.json()
        print(f"HOSTIFY RAW: {r.text[:1500]}")
        items = j.get("data") or j.get("results") or j.get("contents") or j.get("videos") or j
        if isinstance(items, dict): # contents case
            items = items.get("contents") or items.get("data") or [items]
        if not isinstance(items, list): items = [items]
        if not items: return await st.edit_text("No results")
        await st.delete()
        first = extract_item(items[0])
        context.user_data["results"] = [extract_item(x) for x in items[:5]]
        if not first["url"] and first["vid"]:
            first["url"] = f"https://www.youtube.com/watch?v={first['vid']}"
        if not first["url"]:
            return await update.message.reply_text(f"Parser fail. Raw sample:\n{str(items[0])[:1000]}")
        await send_card(update.message, first, context)
    except Exception as e:
        print(f"SEARCH ERR {e}"); await st.edit_text(f"Error {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); d = q.data
    cur = context.user_data.get("current",{})
    if d=="ask_mp3":
        kb=[[InlineKeyboardButton("64",callback_data="q_mp3|64"),InlineKeyboardButton("128",callback_data="q_mp3|128"),InlineKeyboardButton("320",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d=="ask_mp4":
        kb=[[InlineKeyboardButton("144p",callback_data="q_mp4|144"),InlineKeyboardButton("360p",callback_data="q_mp4|360")],[InlineKeyboardButton("720p",callback_data="q_mp4|720"),InlineKeyboardButton("1080p",callback_data="q_mp4|1080")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d=="back_main":
        return await send_card(q, cur, context, True)
    if d.startswith("q_"):
        context.user_data["chosen"]=d
        qual=d.split("|")[1]
        kb=[[InlineKeyboardButton("📄 Document",callback_data=f"do|doc|{d}"),InlineKeyboardButton("▶️ Stream",callback_data=f"do|stream|{d}")]]
        try: await q.edit_message_caption(f"Quality {qual}\nHow to send?", reply_markup=InlineKeyboardMarkup(kb))
        except: await q.edit_message_text(f"Quality {qual}\nHow to send?", reply_markup=InlineKeyboardMarkup(kb))
        return
    if d.startswith("do|"):
        _, typ, qf = d.split("|",2)
        fmt = qf.split("|")[0].replace("q_",""); qual = qf.split("|")[1]
        url = cur.get("url") or f"https://www.youtube.com/watch?v={cur.get('vid')}"
        print(f"DL TRY url={url} fmt={fmt} qual={qual}")
        try: await q.edit_message_caption(f"⏳ Downloading {fmt.upper()} {qual}...")
        except: pass
        dl=None
        try:
            res=requests.get(f"{DL_BASE}/api/youtube/{fmt}", params={"url":url,"quality":qual}, timeout=70).json()
            print(f"BLACKNODE RESP {str(res)[:600]}")
            dl=res.get("url") or res.get("download_url") or res.get("result") or (res if isinstance(res,str) else None)
        except Exception as e: print(f"bn err {e}")
        if not dl:
            try:
                r2=requests.get("https://api.hostify.indevs.in/api/download", params={"url":url}, timeout=60).json()
                print(f"HOSTIFY DL {str(r2)[:600]}")
                dl=r2.get("url") or r2.get("downloadUrl")
            except: pass
        if not dl: return await q.message.reply_text(f"❌ No link for {url}\nCheck logs BLACKNODE RESP")
        try:
            if typ=="doc": await q.message.reply_document(document=dl, caption=cur['title'])
            else:
                if fmt=="mp3": await q.message.reply_audio(audio=dl, title=cur['title'])
                else: await q.message.reply_video(video=dl, caption=cur['title'], supports_streaming=True)
        except Exception as e:
            await q.message.reply_text(f"Direct link (Telegram failed to stream):\n{dl}\n{e}")

def main():
    app=Application.builder().token(BOT_TOKEN).defaults(Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("STAR v6 fixed url parser live")
    app.run_polling()
if __name__=="__main__": main()
