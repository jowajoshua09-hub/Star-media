import os, requests, threading, tempfile, glob, shutil, time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
DL_BASE = "https://blacknodezw.zone.id"

def keep_port():
    port=int(os.environ.get("PORT",10000))
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/":
                self.send_response(200);self.send_header("Content-type","text/html");self.end_headers()
                self.wfile.write(b"<h1>STAR MEDIA V11 - LIVE</h1>");return
            return SimpleHTTPRequestHandler.do_GET(self)
        def log_message(self,*a): pass
    try:
        os.chdir("/opt/render/project/src" if os.path.exists("/opt/render/project/src") else ".")
        HTTPServer(("0.0.0.0",port),H).serve_forever()
    except: pass
threading.Thread(target=keep_port,daemon=True).start()

def has_ffmpeg(): return shutil.which("ffmpeg") is not None

def yt_search(query, limit=5):
    try:
        opts={
            'quiet':True,'extract_flat':True,'skip_download':True,'no_warnings':True,
            'nocheckcertificate':True,
            'extractor_args': {'youtube': {'player_client': ['android']}},
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info=ydl.extract_info(f"ytsearch{limit}:{query}",download=False)
            out=[]
            for e in info.get('entries',[]):
                if not e: continue
                vid=e.get('id')
                out.append({
                    "videoId":vid,
                    "title":e.get('title'),
                    "channel":e.get('uploader') or e.get('channel') or "YouTube",
                    "thumbnail":f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "url":f"https://www.youtube.com/watch?v={vid}"
                })
            print(f"SEARCH FOUND {len(out)}")
            return out
    except Exception as ex:
        print(f"search fail {ex}"); return []

async def send_card(dest,item,ctx,is_edit=False):
    ctx.user_data["current"]=item
    cap=f"🎬 *{item['title']}*\n👤 {item['artist']}"
    mk=InlineKeyboardMarkup([[InlineKeyboardButton("🎵 MP3",callback_data="ask_mp3"),InlineKeyboardButton("🎬 MP4",callback_data="ask_mp4")]])
    try:
        if is_edit: await dest.edit_message_caption(caption=cap,reply_markup=mk,parse_mode="Markdown")
        else: await dest.reply_photo(photo=item['thumb'],caption=cap,reply_markup=mk,parse_mode="Markdown")
    except:
        if is_edit: await dest.edit_message_text(cap,reply_markup=mk,parse_mode="Markdown")
        else: await dest.reply_text(cap,reply_markup=mk,parse_mode="Markdown")

async def start(u,c):
    await u.message.reply_text("🌟 STAR MEDIA Ready\nSend any song name like `Missing Piece Official Lyric Video`",parse_mode="Markdown")

async def handle_text(update:Update,context:ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip()
    if "youtu" in txt or "youtu.be" in txt:
        if "youtu.be" in txt: vid=txt.split("/")[-1].split("?")[0][:11]
        else: vid=txt.split("v=")[-1].split("&")[0][:11]
        item={"title":"YouTube Link","artist":"YouTube","thumb":f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg","url":f"https://www.youtube.com/watch?v={vid}","vid":vid}
        return await send_card(update.message,item,context)
    st=await update.message.reply_text(f"🔍 Searching: {txt}")
    items=yt_search(txt,5)
    if not items:
        return await st.edit_text(f"❌ No results for '{txt}'")
    await st.delete()
    f=items[0]
    first={"title":f["title"],"artist":f["channel"],"thumb":f["thumbnail"],"url":f["url"],"vid":f["videoId"]}
    context.user_data["items"]=items
    await send_card(update.message,first,context)

async def handle_button(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer();d=q.data
    cur=context.user_data.get("current")
    if not cur: return await q.edit_message_text("Session expired, search again")
    if d=="ask_mp3":
        kb=[[InlineKeyboardButton("128k",callback_data="q_mp3|128"),InlineKeyboardButton("320k",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if d=="ask_mp4":
        kb=[[InlineKeyboardButton("360p",callback_data="q_mp4|360"),InlineKeyboardButton("720p",callback_data="q_mp4|720")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if d=="back": return await send_card(q,cur,context,True)
    if d.startswith("q_"):
        qual=d.split("|")[1];context.user_data["chosen"]=d
        kb=[[InlineKeyboardButton("📄 Document",callback_data=f"do|doc|{d}"),InlineKeyboardButton("▶️ Stream",callback_data=f"do|stream|{d}")]]
        try: await q.edit_message_caption(caption=f"Quality: {qual}\nHow to send?",reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")
        except: await q.edit_message_text(f"Quality: {qual}",reply_markup=InlineKeyboardMarkup(kb))
        return
    if d.startswith("do|"):
        _,typ,qf=d.split("|",2);fmt=qf.split("|")[0].replace("q_","");qual=qf.split("|")[1]
        url=cur["url"]; vid=cur.get("vid") or url.split("v=")[-1][:11]
        try: await q.edit_message_caption(caption=f"⏳ Downloading {fmt.upper()} {qual}... 20-40s")
        except: pass
        # 1. Try BlackNode fast (has its own cookies, often works for mp3)
        dl_url=None
        try:
            r=requests.get(f"{DL_BASE}/api/youtube/{fmt}",params={"url":url,"quality":qual},timeout=30)
            j=r.json(); dl_url=j.get("url") or j.get("download_url") or j.get("result")
            print(f"BN {dl_url}")
            if dl_url and dl_url.startswith("http"):
                if typ=="doc": await q.message.reply_document(document=dl_url,caption=f"🎵 {cur['title']}")
                else:
                    if fmt=="mp3": await q.message.reply_audio(audio=dl_url,title=cur['title'][:60],performer=cur['artist'])
                    else: await q.message.reply_video(video=dl_url,caption=f"🎬 {cur['title']}",supports_streaming=True)
                return
        except Exception as e: print(f"BN fail {e}")

        # 2. yt-dlp with Android client bypass (fixes Sign in to confirm you're not a bot)
        try:
            tmpdir=tempfile.mkdtemp()
            common={'quiet':True,'nocheckcertificate':True,'extractor_args':{'youtube':{'player_client':['android','ios','web_embedded']} },'http_headers':{'User-Agent':'Mozilla/5.0 (Linux; Android 12)'}}
            if fmt=="mp3":
                if has_ffmpeg():
                    opts={**common,'format':'bestaudio/best','outtmpl':f'{tmpdir}/%(title)s.%(ext)s','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':qual}]}
                else:
                    opts={**common,'format':'bestaudio/best','outtmpl':f'{tmpdir}/%(title)s.%(ext)s'}
            else:
                h=qual.replace("p","")
                opts={**common,'format':f'best[height<={h}][ext=mp4]/best[height<={h}]/best','outtmpl':f'{tmpdir}/%(title)s.%(ext)s'}
            with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
            files=glob.glob(f"{tmpdir}/*")
            if not files: raise Exception("no file")
            fpath=files[0]; print(f"YTDL OK {fpath}")
            if typ=="doc": await q.message.reply_document(document=open(fpath,'rb'),filename=os.path.basename(fpath),caption=cur["title"])
            else:
                if fmt=="mp3": await q.message.reply_audio(audio=open(fpath,'rb'),title=cur["title"][:60])
                else: await q.message.reply_video(video=open(fpath,'rb'),caption=cur["title"],supports_streaming=True)
            return
        except Exception as e:
            print(f"yt-dlp android fail {e}")
            # 3. Piped fallback - uses Piped's cookies
            try:
                pr=requests.get(f"https://pipedapi.kavin.rocks/streams/{vid}",timeout=20).json()
                stream_url=None
                if fmt=="mp3":
                    aud=pr.get("audioStreams",[])
                    if aud: stream_url=aud[0].get("url")
                else:
                    vids=pr.get("videoStreams",[])
                    if vids:
                        # prefer requested quality
                        for s in vids:
                            if str(qual) in str(s.get("quality","")): stream_url=s.get("url");break
                        if not stream_url: stream_url=vids[0].get("url")
                if stream_url:
                    if typ=="doc": await q.message.reply_document(document=stream_url,caption=cur["title"])
                    else:
                        if fmt=="mp3": await q.message.reply_audio(audio=stream_url,title=cur["title"][:60])
                        else: await q.message.reply_video(video=stream_url,caption=cur["title"])
                    return
            except Exception as pe: print(f"piped fail {pe}")
            await q.message.reply_text(f"❌ Still blocked by YouTube.\nTry MP3 128k again or 360p.\nID: {vid}")

def main():
    # kill old webhooks to fix Conflict error
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true",timeout=10); time.sleep(2)
    except: pass
    app=Application.builder().token(BOT_TOKEN).defaults(Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_text))
    print("STAR MEDIA V11 LIVE")
    import asyncio
    try: asyncio.get_event_loop().run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    except: pass
    app.run_polling(drop_pending_updates=True,allowed_updates=Update.ALL_TYPES)

if __name__=="__main__": main()
