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
                    if os.path.exists(c):
                        self.path="/"+c
                        return SimpleHTTPRequestHandler.do_GET(self)
                self.send_response(200);self.send_header("Content-type","text/html");self.end_headers()
                self.wfile.write(b"<h1>STAR MEDIA YouTube - LIVE</h1><p>Search: John Michael Howell Missing Piece</p>")
                return
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        os.chdir("/opt/render/project/src" if os.path.exists("/opt/render/project/src") else ".")
        HTTPServer(("0.0.0.0",port),H).serve_forever()
    except Exception as e: print(f"web {e}")
threading.Thread(target=keep_port,daemon=True).start()

def extract_any(raw):
    vid=str(raw.get("videoId") or raw.get("id") or "")
    if isinstance(raw.get("id"),dict): vid=raw.get("id",{}).get("videoId","")
    title=raw.get("title") or "Unknown Title"
    channel=raw.get("channel") or raw.get("author") or raw.get("channelTitle") or "YouTube"
    thumb=raw.get("thumbnail") or raw.get("thumbnailUrl")
    if isinstance(thumb,list):
        try: thumb=thumb[0].get("url") if isinstance(thumb[0],dict) else thumb[0]
        except: thumb=None
    if isinstance(thumb,dict): thumb=thumb.get("url")
    if not thumb and vid: thumb=f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    url=raw.get("url") or f"https://www.youtube.com/watch?v={vid}" if vid else ""
    return {"title":str(title)[:80],"artist":str(channel)[:40],"thumb":thumb,"url":url,"vid":vid}

async def send_card(dest,item,ctx,is_edit=False):
    ctx.user_data["current"]=item
    cap=f"🎬 *{item['title']}*\n👤 {item['artist']}\n\nChoose format:"
    mk=InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3",callback_data="ask_mp3"),InlineKeyboardButton("🎬 MP4",callback_data="ask_mp4")]])
    try:
        if item["thumb"] and str(item["thumb"]).startswith("http"):
            if is_edit: await dest.edit_message_caption(caption=cap,reply_markup=mk,parse_mode="Markdown")
            else: await dest.reply_photo(photo=item["thumb"],caption=cap,reply_markup=mk,parse_mode="Markdown")
        else:
            if is_edit: await dest.edit_message_text(cap,reply_markup=mk,parse_mode="Markdown")
            else: await dest.reply_text(cap,reply_markup=mk,parse_mode="Markdown")
    except Exception as e:
        print(f"send_card err {e}")
        if is_edit: await dest.edit_message_text(cap,reply_markup=mk,parse_mode="Markdown")
        else: await dest.reply_text(cap,reply_markup=mk,parse_mode="Markdown")

async def start(u,c):
    await u.message.reply_text("🌟 *STAR MEDIA - YouTube Downloader*\nSend song name e.g. `John Michael Howell Missing Piece`",parse_mode="Markdown")

async def handle_text(update:Update,context:ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip()
    if "youtu" in txt or "youtu.be" in txt:
        if "youtu.be" in txt: vid=txt.split("/")[-1].split("?")[0][:11]
        else: vid=txt.split("v=")[-1].split("&")[0].split("?")[0][:11]
        item={"title":"YouTube Link","artist":"YouTube","thumb":f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg","url":f"https://www.youtube.com/watch?v={vid}","vid":vid}
        return await send_card(update.message,item,context)

    st=await update.message.reply_text(f"🔍 YouTube searching: {txt}")
    items=[]
    # 1. Try hostify first (your API)
    try:
        r=requests.get(SEARCH_HOSTIFY,params={"q":txt},timeout=10)
        j=r.json()
        print(f"HOSTIFY RAW: {r.text[:1500]}")
        items=j.get("result") or j.get("data") or j.get("results") or []
        if isinstance(items,dict): items=[items]
    except Exception as e: print(f"hostify err {e}")

    # 2. Fallback to Invidious - THIS FIXES Missing Piece official lyric video
    if not items:
        bases=["https://invidious.nerdvpn.de","https://vid.puffyan.us","https://inv.nadeko.net","https://invidious.io.lol"]
        for base in bases:
            try:
                url=f"{base}/api/v1/search"
                print(f"Trying {url} q={txt}")
                r=requests.get(url,params={"q":txt,"type":"video"},timeout=12,headers={"User-Agent":"Mozilla/5.0"})
                data=r.json()
                if isinstance(data,list) and len(data)>0:
                    items=[]
                    for x in data[:5]:
                        if not x.get("videoId"): continue
                        thumb=""
                        if x.get("videoThumbnails"):
                            thumbs=x["videoThumbnails"]
                            # pick hq
                            for t in thumbs:
                                if "hqdefault" in t.get("url",""): thumb=t["url"];break
                            if not thumb: thumb=thumbs[0].get("url")
                        items.append({"videoId":x["videoId"],"title":x["title"],"channel":x.get("author",""),"thumbnail":thumb})
                    if items:
                        print(f"INVIDIOUS SUCCESS from {base} found {len(items)}")
                        break
            except Exception as e:
                print(f"invidious {base} err {e}")
                continue

    if not items:
        return await st.edit_text(f"❌ No YouTube results for '{txt}'\n\nTry pasting YouTube link directly")

    await st.delete()
    first=extract_any(items[0])
    context.user_data["items"]=[extract_any(i) for i in items[:5]]
    if not first["url"]:
        return await update.message.reply_text(f"Parse fail but found: {items[0]}")
    await send_card(update.message,first,context)

async def handle_button(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer();d=q.data
    cur=context.user_data.get("current")
    if not cur: return await q.edit_message_text("Session expired, search again")
    if d=="ask_mp3":
        kb=[[InlineKeyboardButton("64kbps",callback_data="q_mp3|64"),InlineKeyboardButton("128kbps",callback_data="q_mp3|128"),InlineKeyboardButton("320kbps",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if d=="ask_mp4":
        kb=[[InlineKeyboardButton("360p",callback_data="q_mp4|360"),InlineKeyboardButton("720p",callback_data="q_mp4|720"),InlineKeyboardButton("1080p",callback_data="q_mp4|1080")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if d=="back_main": return await send_card(q,cur,context,True)
    if d.startswith("q_"):
        qual=d.split("|")[1];context.user_data["chosen"]=d
        kb=[[InlineKeyboardButton("📄 Document",callback_data=f"do|doc|{d}"),InlineKeyboardButton("▶️ Stream",callback_data=f"do|stream|{d}")],[InlineKeyboardButton("⬅️ Back",callback_data="back_q")]]
        txt=f"🎧 *{cur['title'][:50]}*\nQuality: {qual}\nHow to send?"
        try: await q.edit_message_caption(caption=txt,reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")
        except: await q.edit_message_text(txt,reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")
        return
    if d=="back_q":
        chosen=context.user_data.get("chosen","q_mp3|128")
        is_mp3="mp3" in chosen
        if is_mp3: kb=[[InlineKeyboardButton("64",callback_data="q_mp3|64"),InlineKeyboardButton("128",callback_data="q_mp3|128"),InlineKeyboardButton("320",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        else: kb=[[InlineKeyboardButton("360p",callback_data="q_mp4|360"),InlineKeyboardButton("720p",callback_data="q_mp4|720")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if d.startswith("do|"):
        _,typ,qf=d.split("|",2);fmt=qf.split("|")[0].replace("q_","");qual=qf.split("|")[1]
        url=cur["url"]
        print(f"DL START fmt={fmt} qual={qual} url={url}")
        try: await q.edit_message_caption(caption=f"⏳ Downloading {fmt.upper()} {qual}...\nPlease wait 15s")
        except:
            try: await q.edit_message_text(f"⏳ Downloading {fmt.upper()} {qual}...")
            except: pass
        dl=None
        try:
            # BlackNode only has /youtube/mp3 and /youtube/mp4 - we use those
            endpoint=f"{DL_BASE}/api/youtube/{fmt}"
            res=requests.get(endpoint,params={"url":url,"quality":qual},timeout=70)
            print(f"BN RESP {res.status_code} {res.text[:1500]}")
            j=res.json()
            dl=j.get("url") or j.get("download_url") or j.get("result") or j.get("data",{}).get("url") if isinstance(j.get("data"),dict) else None
        except Exception as e: print(f"bn dl err {e}")
        if not dl:
            return await q.message.reply_text(f"❌ Download failed\nURL: {url}\n\nCheck Render Logs > BN RESP\nIt may be age-restricted. Try another quality.")
        try:
            if typ=="doc":
                await q.message.reply_document(document=dl,caption=f"🎵 {cur['title']}\n@StarMediaBot")
            else:
                if fmt=="mp3": await q.message.reply_audio(audio=dl,title=cur['title'][:60],performer=cur['artist'])
                else: await q.message.reply_video(video=dl,caption=f"🎬 {cur['title']}",supports_streaming=True)
            try: await q.edit_message_caption(caption=f"✅ Done: {cur['title'][:40]}")
            except: pass
        except Exception as e:
            print(f"send file err {e}")
            await q.message.reply_text(f"✅ Ready!\nDirect link (tap to download):\n{dl}")

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing!");return
    defaults=Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app=Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_text))
    print("STAR MEDIA V9 YouTube Fixed - LIVE")
    import asyncio
    async def clean():
        try: await app.bot.delete_webhook(drop_pending_updates=True)
        except: pass
    try: asyncio.get_event_loop().run_until_complete(clean())
    except: pass
    app.run_polling(drop_pending_updates=True,allowed_updates=Update.ALL_TYPES)

if __name__=="__main__": main()
