import os, requests, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Defaults

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = "https://blacknodezw.zone.id"

def keep_port():
    port = int(os.environ.get("PORT", 10000))
    class H(BaseHTTPRequestHandler):
        def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"STAR MEDIA Running")
        def log_message(self,*a): pass
    try: HTTPServer(("0.0.0.0",port),H).serve_forever()
    except: pass
threading.Thread(target=keep_port,daemon=True).start()

# --- HELPERS ---
def get_search(q):
    r = requests.get(f"{BASE}/api/tiktok/search", params={"q": q}, timeout=20).json()
    if isinstance(r, dict):
        data = r.get("data") or r.get("results") or r.get("result") or []
    else: data = r
    if not isinstance(data, list): data = [data]
    return data[0] if data else None

async def show_result(msg_or_update, item, context, is_edit=False):
    # Parse your API fields - adjust keys if different
    title = item.get("title","Unknown Title")
    artist = item.get("artist") or item.get("author") or item.get("channel") or "Unknown Artist"
    thumb = item.get("thumbnail") or item.get("thumb") or item.get("cover") or item.get("image")
    duration = item.get("duration") or item.get("length") or ""
    release = item.get("release_date") or item.get("published") or item.get("date") or ""
    size_est = item.get("size") or ""
    vid_url = item.get("url") or item.get("link") or item.get("id") or ""

    # Save for next steps
    context.user_data["current_url"] = vid_url
    context.user_data["current_title"] = title
    context.user_data["current_thumb"] = thumb
    context.user_data["current_artist"] = artist

    caption = f"🎵 **{title}**\n👤 {artist}\n⏱ {duration} 📅 {release}\n📦 {size_est}\n\nChoose download type:"

    buttons = [
        [InlineKeyboardButton("⬇️ Download as", callback_data="noop")],
        [InlineKeyboardButton("🎵 MP3 (Audio)", callback_data="ask_mp3"),
         InlineKeyboardButton("🎬 MP4 (Video)", callback_data="ask_mp4")]
    ]
    markup = InlineKeyboardMarkup(buttons)

    if thumb and thumb.startswith("http"):
        if is_edit:
            await msg_or_update.edit_message_caption(caption, reply_markup=markup, parse_mode="Markdown")
        else:
            await msg_or_update.reply_photo(photo=thumb, caption=caption, reply_markup=markup, parse_mode="Markdown")
    else:
        if is_edit:
            await msg_or_update.edit_message_text(caption, reply_markup=markup, parse_mode="Markdown")
        else:
            await msg_or_update.reply_text(caption, reply_markup=markup, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌟 STAR MEDIA\n\nSend song name: e.g. John Michael Howell missing piece")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if "http" in text:
        item = {"title": "Direct Link", "artist": "YouTube", "url": text, "thumbnail": None}
        return await show_result(update.message, item, context)

    msg = await update.message.reply_text(f"🔍 Searching: {text}")
    try:
        item = get_search(text)
        if not item: return await msg.edit_text("No results.")
        await msg.delete()
        await show_result(update.message, item, context)
    except Exception as e:
        await msg.edit_text(f"Error: {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    url = context.user_data.get("current_url","")
    title = context.user_data.get("current_title","file")

    # STEP 1: Choose MP3 / MP4
    if data == "ask_mp3":
        buttons = [
            [InlineKeyboardButton("64kbps", callback_data="q_mp3|64"), InlineKeyboardButton("128kbps", callback_data="q_mp3|128"), InlineKeyboardButton("320kbps", callback_data="q_mp3|320")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(buttons))

    if data == "ask_mp4":
        buttons = [
            [InlineKeyboardButton("144p", callback_data="q_mp4|144"), InlineKeyboardButton("360p", callback_data="q_mp4|360")],
            [InlineKeyboardButton("720p", callback_data="q_mp4|720"), InlineKeyboardButton("1080p", callback_data="q_mp4|1080")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ]
        return await q.edit_message_reply_markup(InlineKeyboardMarkup(buttons))

    # STEP 2: Choose quality -> ask Document or Stream
    if data.startswith("q_mp3|") or data.startswith("q_mp4|"):
        fmt_quality = data # e.g. q_mp3|320
        context.user_data["chosen_quality"] = fmt_quality
        buttons = [
            [InlineKeyboardButton("📄 Document", callback_data=f"send|doc|{fmt_quality}"),
             InlineKeyboardButton("▶️ Streamable", callback_data=f"send|stream|{fmt_quality}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_quality")]
        ]
        qual = fmt_quality.split("|")[1]
        return await q.edit_message_caption(f"🎧 {title}\nQuality: {qual}\n\nHow to send?", reply_markup=InlineKeyboardMarkup(buttons))

    # STEP 3: Final Send
    if data.startswith("send|"):
        _, send_type, fmt_quality = data.split("|", 2) # doc/stream, q_mp3|320
        _, fmt, quality = fmt_quality.split("|") # q, mp3, 320 -> actually q_mp3|320
        # fix split
        real_fmt = fmt_quality.split("|")[0].replace("q_","") # mp3
        real_qual = fmt_quality.split("|")[1]

        await q.edit_message_caption(f"⏳ Fetching {real_fmt.upper()} {real_qual} as {send_type}...")

        try:
            endpoint = f"{BASE}/api/youtube/{real_fmt}"
            # pass quality if your API supports it
            params = {"url": url, "quality": real_qual, "q": real_qual}
            res = requests.get(endpoint, params=params, timeout=60).json()
            dl_url = res.get("url") or res.get("download_url") or res.get("result") or res.get("link")
            if not dl_url and isinstance(res, str): dl_url = res
            if not dl_url: return await q.message.reply_text(f"API error: {str(res)[:400]}")

            thumb = context.user_data.get("current_thumb")
            artist = context.user_data.get("current_artist")

            if send_type == "doc":
                if real_fmt == "mp3":
                    await q.message.reply_document(document=dl_url, caption=f"🎵 {title} - {artist}", thumbnail=thumb if thumb else None)
                else:
                    await q.message.reply_document(document=dl_url, caption=f"🎬 {title}", thumbnail=thumb if thumb else None)
            else: # streamable
                if real_fmt == "mp3":
                    await q.message.reply_audio(audio=dl_url, title=title, performer=artist, thumbnail=thumb if thumb else None, caption=f"🎵 {title}")
                else:
                    await q.message.reply_video(video=dl_url, caption=f"🎬 {title}", thumbnail=thumb if thumb else None, supports_streaming=True)

            await q.edit_message_caption(f"✅ Done: {title} [{real_fmt.upper()} {real_qual}]")
        except Exception as e:
            await q.message.reply_text(f"Download failed: {e}\nLink was: {dl_url if 'dl_url' in locals() else 'none'}")

    if data == "back_main":
        item = {"title": context.user_data.get("current_title"), "artist": context.user_data.get("current_artist"), "thumbnail": context.user_data.get("current_thumb"), "url": url}
        await show_result(q, item, context, is_edit=True)

    if data == "back_quality":
        # go back to quality selection
        last_fmt = context.user_data.get("chosen_quality","q_mp3|128")
        if "mp3" in last_fmt: await q.edit_message_reply_markup(InlineKeyboardMarkup([[InlineKeyboardButton("64kbps",callback_data="q_mp3|64"),InlineKeyboardButton("128kbps",callback_data="q_mp3|128"),InlineKeyboardButton("320kbps",callback_data="q_mp3|320")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]))
        else: await q.edit_message_reply_markup(InlineKeyboardMarkup([[InlineKeyboardButton("144p",callback_data="q_mp4|144"),InlineKeyboardButton("360p",callback_data="q_mp4|360")],[InlineKeyboardButton("720p",callback_data="q_mp4|720"),InlineKeyboardButton("1080p",callback_data="q_mp4|1080")],[InlineKeyboardButton("⬅️ Back",callback_data="back_main")]]))

def main():
    defaults = Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app = Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("STAR MEDIA Pro Live")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
