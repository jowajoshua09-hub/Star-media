import os, requests, threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
SEARCH_HOSTIFY = "https://api.hostify.indevs.in/api/search/youtube"
DL_BASE = "https://blacknodezw.zone.id"

def keep_port():
    port=int(os.environ.get("PORT",10000))
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/":
                for c in ["app/index.html","index.html"]:
                    if os.path.exists(c): self.path="/"+c; return SimpleHTTPRequestHandler.do_GET(self)
                self.send_response(200);self.send_header("Content-type","text/html");self.end_headers()
                self.wfile.write(b"<h1>STAR MEDIA YouTube FIXED</h1>");return
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        os.chdir("/opt/render/project/src" if os.path.exists("/opt/render/project/src") else ".")
        HTTPServer(("0.0.0.0",port),H).serve_forever()
    except: pass
threading.Thread(target=keep_port,daemon=True).start()

def extract_any(raw):
    vid=raw.get("videoId") or raw.get("id") or raw.get("video_id") or ""
    if isinstance(vid,dict): vid=vid.get("videoId","")
    title=raw.get("title") or raw.get("name") or "Unknown"
    channel=raw.get("channel") or raw.get("author") or raw.get("channelTitle") or "YouTube"
    thumb=raw.get("thumbnail") or raw.get("thumbnailUrl") or raw.get("cover")
    if isinstance(thumb,list): thumb=thumb[0].get("url") if isinstance(thumb[0],dict) else thumb[0]
    if isinstance(thumb,dict): thumb=thumb.get("url")
    url=raw.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid and len(str(vid))<=15 else "")
    return {"title":str(title)[:80],"artist":str(channel)[:40],"thumb":thumb,"url":url,"vid":str(vid)}

async def send_card(dest,item,ctx,is_edit=False):
    ctx.user_data["current"]=item
    cap=f"🎬 *{item['title']}*\n👤 {item['artist']}\n\nChoose format:"
    mk=InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3",callback_data="ask_mp3"),InlineKeyboardButton("🎬 MP4",callback_data="ask_mp4")]])
    try:
        if item["thumb"] and str(item["thumb"]).startswith("http"):
            if is_edit: await dest.edit_message_caption(cap,reply_markup=mk,parse_mode="Markdown")
            else: await dest.reply_photo(photo=item["thumb"],caption=cap,reply_markup=mk,parse_mode="Markdown")
        else:
            if is_edit: await dest.edit_message_text(cap,reply_markup=mk,parse_mode="Markdown")
            else: await dest.reply_text(cap,reply_markup=mk,parse_mode="Markdown")
    except:
        if is_edit: await dest.edit_message_text(cap,reply_markup=mk,parse_mode="Markdown")
        else: await dest.reply_text(cap,reply_markup=mk,parse_mode="Markdown")

async def start(u,c): await u.message.reply_text("🌟 STAR MEDIA - YouTube\nSend song name")

async def handle_text(update:Update,context:ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip()
    if "youtu" in txt or "youtube.com" in txt:
        vid=txt.split("v=")[-1].split("&")[0][:11]
        item={"title":"YouTube Link","artist":"YouTube","thumb":None,"url":f"https://www.youtube.com/watch?v={vid}","vid":vid}
        return await send_card(update.message,item,context)
    st=await update.message.reply_text(f"🔍 YouTube searching: {txt}")
    items=[]
    # 1. Try hostify
    try:
        r=requests.get(SEARCH_HOSTIFY,params={"q":txt},timeout=15)
        j=r.json()
        print(f"HOSTIFY RAW {r.text[:2000]}")
        items=j.get("result") or j.get("data") or j.get("results") or []
    except Exception as e: print(f"hostify err {e}")
    # 2. If hostify empty -> BlackNode YouTube search (this WILL find John Michael Howell)
    if not items:
        try:
            r2=requests.get(f"{DL_BASE}/api/youtube/search",params={"q":txt},timeout=15)
            print(f"BLACKNODE YT SEARCH STATUS {r2.status_code} BODY {r2.text[:2000]}")
            j2=r2.json()
            items=j2.get("data") or j2.get("result") or j2.get("results") or j2
            if isinstance(items,dict): items=[items]
        except Exception as e: print(f"bn yt search err {e}")
    # 3. Last fallback - YT search via invidious
    if not items:
        try:
            r3=requests.get(f"https://invidious.nerdvpn.de/api/v1/search",params={"q":txt,"type":"video"},timeout=15).json()
            print(f"INVIDIOUS {str(r3)[:1000]}")
            items=[{"videoId":x.get("videoId"),"title":x.get("title"),"channel":x.get("author"),"thumbnail":x.get("videoThumbnails",[{}])[0].get("url")} for x in r3[:5]]
        except Exception as e: print(f"invidious err {e}")

    if not items:
        return await st.edit_text(f"❌ No YouTube results for '{txt}'")
    await st.delete()
    first=extract_any(items[0])
    context.user_data["items"]=[extract_any(i) for i in items[:5]]
    if not first["url"]:
        return await update.message.reply_text(f"Parse fail: {str(items[0])[:800]}")
    await send_card(update.message,first,context)

async def handle_button(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer();d=q.data
    cur=context.user_data.get("current")
    if not cur: return await q.edit_message_text("Expired")
    if d=="ask_mp3":
        kb=[[InlineKeyboardButton("64kbps",callback_data="q_mp3|64"),InlineKeyboardButton("128kbps",callback_data="q_mp3|128"),InlineKeyboardButton("320kbps",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d=="ask_mp4":
        kb=[[InlineKeyboardButton("360p",callback_data="q_mp4|360"),InlineKeyboardButton("720p",callback_data="q_mp4|720"),InlineKeyboardButton("1080p",callback_data="q_mp4|1080")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d=="back_main": return await send_card(q,cur,context,True)
    if d.startswith("q_"):
        qual=d.split("|")[1];context.user_data["chosen"]=d
        kb=[[InlineKeyboardButton("📄 Document",callback_data=f"do|doc|{d}"),InlineKeyboardButton("▶️ Stream",callback_data=f"do|stream|{d}")]]
        try: await q.edit_message_caption(f"Quality {qual}\nHow to send?",reply_markup=InlineKeyboardMarkup(kb))
        except: await q.edit_message_text(f"Quality {qual}\nHow to send?",reply_markup=InlineKeyboardMarkup(kb))
        return
    if d.startswith("do|"):
        _,typ,qf=d.split("|",2);fmt=qf.split("|")[0].replace("q_","");qual=qf.split("|")[1]
        url=cur["url"]
        print(f"YT DL url={url} fmt={fmt} qual={qual}")
        try: await q.edit_message_caption(f"⏳ Downloading YouTube {fmt.upper()} {qual}...")
        except: pass
        dl=None
        # Try BlackNode download (works for your video)
        try:
            res=requests.get(f"{DL_BASE}/api/youtube/{fmt}",params={"url":url,"quality":qual},timeout=60).json()
            print(f"BN DL {str(res)[:1000]}")
            dl=res.get("url") or res.get("download_url") or res.get("result")
        except Exception as e: print(f"bn dl err {e}")
        if not dl:
            return await q.message.reply_text(f"❌ No download link\nURL tried: {url}\nLog: BN DL failed - try another song or send /start")
        try:
            if typ=="doc": await q.message.reply_document(document=dl,caption=cur["title"])
            else:
                if fmt=="mp3": await q.message.reply_audio(audio=dl,title=cur["title"][:60])
                else: await q.message.reply_video(video=dl,caption=cur["title"],supports_streaming=True)
        except Exception as e:
            await q.message.reply_text(f"Direct link (Telegram could not send file):\n{dl}\n{e}")

def main():
    defaults=Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app=Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_text))
    print("STAR MEDIA YOUTUBE FIXED V8 LIVE")
    import asyncio
    try: asyncio.get_event_loop().run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    except: pass
    app.run_polling(drop_pending_updates=True)
if __name__=="__main__": main()
