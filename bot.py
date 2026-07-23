import os, requests, threading, tempfile, glob
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
DL_BASE = "https://blacknodezw.zone.id" # only as backup for download

def keep_port():
    port=int(os.environ.get("PORT",10000))
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/":
                self.send_response(200);self.send_header("Content-type","text/html");self.end_headers()
                self.wfile.write(b"<h1>STAR MEDIA V10 - yt-dlp LIVE</h1>");return
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        os.chdir("/opt/render/project/src" if os.path.exists("/opt/render/project/src") else ".")
        HTTPServer(("0.0.0.0",port),H).serve_forever()
    except: pass
threading.Thread(target=keep_port,daemon=True).start()

def yt_search(query, limit=5):
    # This works even when hostify and invidious are down
    try:
        opts = {'quiet':True,'extract_flat':True,'skip_download':True,'no_warnings':True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            results=[]
            for e in info.get('entries',[]):
                if not e: continue
                vid=e.get('id')
                results.append({
                    "videoId":vid,
                    "title":e.get('title'),
                    "channel":e.get('uploader') or e.get('channel') or "YouTube",
                    "thumbnail":f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "url":f"https://www.youtube.com/watch?v={vid}"
                })
            print(f"YT-DLP SEARCH FOUND {len(results)} for {query}")
            return results
    except Exception as ex:
        print(f"yt-dlp search fail {ex}")
        return []

async def send_card(dest,item,ctx,is_edit=False):
    ctx.user_data["current"]=item
    cap=f"🎬 *{item['title']}*\n👤 {item['artist']}\n\nChoose:"
    mk=InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3",callback_data="ask_mp3"),InlineKeyboardButton("🎬 MP4",callback_data="ask_mp4")]])
    try:
        if is_edit: await dest.edit_message_caption(cap,reply_markup=mk,parse_mode="Markdown")
        else: await dest.reply_photo(photo=item['thumb'],caption=cap,reply_markup=mk,parse_mode="Markdown")
    except:
        if is_edit: await dest.edit_message_text(cap,reply_markup=mk,parse_mode="Markdown")
        else: await dest.reply_text(cap,reply_markup=mk,parse_mode="Markdown")

async def start(u,c): await u.message.reply_text("🌟 STAR MEDIA Ready\nSend any song name")

async def handle_text(update:Update,context:ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip()
    if "youtu" in txt or "youtu.be" in txt:
        vid=txt.split("v=")[-1].split("&")[0][:11] if "v=" in txt else txt.split("/")[-1][:11]
        item={"title":"YouTube Link","artist":"YouTube","thumb":f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg","url":f"https://www.youtube.com/watch?v={vid}","vid":vid}
        return await send_card(update.message,item,context)
    st=await update.message.reply_text(f"🔍 Searching YouTube directly: {txt}")
    items=yt_search(txt,5)
    if not items:
        return await st.edit_text(f"❌ No results for '{txt}'\nTry shorter: 'missing piece john michael'")
    await st.delete()
    first={"title":items[0]["title"],"artist":items[0]["channel"],"thumb":items[0]["thumbnail"],"url":items[0]["url"],"vid":items[0]["videoId"]}
    context.user_data["items"]=items
    await send_card(update.message,first,context)

async def handle_button(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer();d=q.data
    cur=context.user_data.get("current")
    if not cur: return await q.edit_message_text("Expired")
    if d=="ask_mp3":
        kb=[[InlineKeyboardButton("64k",callback_data="q_mp3|64"),InlineKeyboardButton("128k",callback_data="q_mp3|128"),InlineKeyboardButton("320k",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d=="ask_mp4":
        kb=[[InlineKeyboardButton("360p",callback_data="q_mp4|360"),InlineKeyboardButton("720p",callback_data="q_mp4|720")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    if d=="back": return await send_card(q,cur,context,True)
    if d.startswith("q_"):
        qual=d.split("|")[1];context.user_data["chosen"]=d
        kb=[[InlineKeyboardButton("📄 Document",callback_data=f"do|doc|{d}"),InlineKeyboardButton("▶️ Stream",callback_data=f"do|stream|{d}")]]
        try: await q.edit_message_caption(f"Quality {qual}\nHow to send?",reply_markup=InlineKeyboardMarkup(kb))
        except: await q.edit_message_text(f"Quality {qual}\nHow?",reply_markup=InlineKeyboardMarkup(kb))
        return
    if d.startswith("do|"):
        _,typ,qf=d.split("|",2);fmt=qf.split("|")[0].replace("q_","");qual=qf.split("|")[1]
        url=cur["url"]
        await q.edit_message_caption(f"⏳ Downloading {fmt.upper()} {qual}...\nThis takes 20s for the first time") if True else None
        # Try BlackNode fast download first
        dl_url=None
        try:
            r=requests.get(f"{DL_BASE}/api/youtube/{fmt}",params={"url":url,"quality":qual},timeout=30).json()
            dl_url=r.get("url") or r.get("download_url")
            print(f"BN fast dl {dl_url}")
        except: pass
        if dl_url and dl_url.startswith("http"):
            try:
                if typ=="doc": await q.message.reply_document(dl_url,caption=cur["title"])
                else:
                    if fmt=="mp3": await q.message.reply_audio(dl_url,title=cur["title"][:60])
                    else: await q.message.reply_video(dl_url,caption=cur["title"])
                return
            except: pass # fall through to yt-dlp download

        # FINAL FALLBACK: yt-dlp downloads file to server then uploads to Telegram (100% works)
        try:
            tmpdir=tempfile.mkdtemp()
            if fmt=="mp3":
                opts={'format':'bestaudio/best','outtmpl':f'{tmpdir}/%(title)s.%(ext)s','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':qual}],'quiet':True}
            else:
                # 720 max, because 1080 often fails as you saw
                height=qual.replace("p","")
                opts={'format':f'best[height<={height}]','outtmpl':f'{tmpdir}/%(title)s.%(ext)s','quiet':True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            files=glob.glob(f"{tmpdir}/*")
            if not files: raise Exception("no file")
            fpath=files[0]
            print(f"YT-DLP DOWNLOADED {fpath}")
            if typ=="doc":
                await q.message.reply_document(document=open(fpath,'rb'),filename=os.path.basename(fpath),caption=cur["title"])
            else:
                if fmt=="mp3": await q.message.reply_audio(audio=open(fpath,'rb'),title=cur["title"][:60])
                else: await q.message.reply_video(video=open(fpath,'rb'),caption=cur["title"],supports_streaming=True)
        except Exception as e:
            print(f"yt-dlp dl err {e}")
            await q.message.reply_text(f"❌ Failed: {e}\nTry 360p for video, 128k for audio")

def main():
    app=Application.builder().token(BOT_TOKEN).defaults(Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_text))
    print("STAR MEDIA V10 yt-dlp READY")
    import asyncio
    try: asyncio.get_event_loop().run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    except: pass
    app.run_polling(drop_pending_updates=True)
if __name__=="__main__": main()
