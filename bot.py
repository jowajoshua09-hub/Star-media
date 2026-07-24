import os, requests, re, json, asyncio, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.getenv("BOT_TOKEN")
MUSIC_API = os.getenv("MUSIC_API", "https://api.omegatech.app/api/ai/Remusicv2")
LYRICS_API = os.getenv("LYRICS_API", "https://api.omegatech.app/api/ai/Gpt-4o-mini")

logging.basicConfig(level=logging.INFO)
TITLE, LYRICS, GENRE, MOOD, VOCAL, TEMPO, CONFIRM = range(7)

def clean_lyrics(raw: str):
    if not raw: return ""
    txt = str(raw).replace("--n--", "\n").replace("\\n", "\n").replace("\\n--", "\n")
    txt = txt.replace("**", "").strip()
    return txt[:1500]

def call_lyrics(message: str):
    try:
        resp = requests.get(LYRICS_API, params={"message": message}, timeout=30)
        data = resp.json()
        # Your API returns {"answer": "..."} as in your screenshot
        raw = data.get("answer") or data.get("data") or data.get("result") or ""
        return clean_lyrics(raw)
    except Exception as e:
        logging.error(f"lyrics error {e}")
        return "[Verse 1]\nThe darkness is calling\n[Chorus]\nTake my soul"

def call_music(payload: dict):
    # IMPORTANT: No GET word in URL, only requests.get()
    resp = requests.get(MUSIC_API, params=payload, timeout=90)
    return resp.json()

def ai_generate_all(theme: str):
    prompt = f'Return ONLY JSON: {{"title":"short title","lyrics":"[Verse 1]... 120 words","genre":"Metal","mood":"Dark","vocal":"Male vocal","tempo":"Slow"}} Theme: {theme}. Genre: Rock,Tock,Lo-Fi,Phonk,Trap,Pop,Metal. Mood: Calm,Dark,Energetic,Sad,Happy. Vocal: Male vocal,Female vocal. Tempo: Slow,Medium,Fast.'
    raw = call_lyrics(prompt)
    try:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m: return json.loads(m.group())
    except: pass
    return {"title": theme[:20].title(), "lyrics": raw, "genre": "Metal", "mood": "Dark", "vocal": "Male vocal", "tempo": "Slow"}

def ai_lyrics_only(title):
    return call_lyrics(f"Write 120 word {title} metal rock lyrics, structure [Verse 1][Chorus][Verse 2][Bridge][Outro], singable, original. No intro, only lyrics.")

def genre_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton(g, callback_data=f"g|{g}") for g in ["Rock","Tock","Metal","Phonk"]],[InlineKeyboardButton(g, callback_data=f"g|{g}") for g in ["Lo-Fi","Trap","Pop"]]])
def mood_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton(m, callback_data=f"m|{m}") for m in ["Calm","Dark","Energetic","Sad"]]])
def vocal_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("Male", callback_data="v|Male vocal"), InlineKeyboardButton("Female", callback_data="v|Female vocal")]])
def tempo_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=f"t|{t}") for t in ["Slow","Medium","Fast"]]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🤖 Generate Everything with AI", callback_data="mode_auto")],[InlineKeyboardButton("✋ Build Manually", callback_data="mode_manual")]]
    await update.message.reply_text("🎵 **Star Music Gen**\nChoose mode:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "mode_auto":
        context.user_data['mode']='auto'
        await q.message.reply_text("🤖 **AUTO MODE**\nSend theme:\n`metal rock about darkness calling`", parse_mode="Markdown")
        return TITLE
    else:
        context.user_data['mode']='manual'
        await q.message.reply_text("**Step 1/6: TITLE**\nSong title?", parse_mode="Markdown")
        return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if context.user_data.get('mode')=='auto':
        w = await update.message.reply_text(f"🤖 Creating for **{text}** ⏳", parse_mode="Markdown")
        data = await asyncio.to_thread(ai_generate_all, text)
        context.user_data.update(data)
        preview = f"✨ **AI Made:**\n**{data['title']}**\n{data['genre']} • {data['mood']}\n\n{data['lyrics'][:700]}"
        await w.edit_text(preview, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎧 GENERATE NOW", callback_data="gen")],[InlineKeyboardButton("🔄 Regenerate", callback_data="mode_auto")]]), parse_mode="Markdown")
        return CONFIRM
    else:
        context.user_data['title']=text
        await update.message.reply_text("**Step 2/6: LYRICS**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 Let AI Write", callback_data="ai_l")],[InlineKeyboardButton("✍️ Type My Own", callback_data="my_l")]]), parse_mode="Markdown")
        return LYRICS

async def lyrics_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if q.data=="ai_l":
        w=await q.message.edit_text(f"🤖 Writing lyrics for **{context.user_data.get('title')}**... ⏳", parse_mode="Markdown")
        lyrics=await asyncio.to_thread(ai_lyrics_only, context.user_data.get('title','Live'))
        context.user_data['lyrics']=lyrics
        await w.edit_text(f"✨ **AI Lyrics:**\n\n{lyrics[:1000]}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Use These", callback_data="use_ai")],[InlineKeyboardButton("🔄 Regenerate", callback_data="ai_l")]]), parse_mode="Markdown")
        return LYRICS
    else:
        await q.message.edit_text("Send your lyrics now:"); return LYRICS

async def use_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("**Step 3/6: GENRE**", reply_markup=genre_kb()); return GENRE

async def get_lyrics_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lyrics']=update.message.text
    await update.message.reply_text("**Step 3/6: GENRE**", reply_markup=genre_kb()); return GENRE

async def get_g(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data['genre']=update.callback_query.data.split("|")[1]; await update.callback_query.answer(); await update.callback_query.message.reply_text(f"**Step 4/6: MOOD**", reply_markup=mood_kb()); return MOOD
async def get_m(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data['mood']=update.callback_query.data.split("|")[1]; await update.callback_query.answer(); await update.callback_query.message.reply_text(f"**Step 5/6: VOCAL**", reply_markup=vocal_kb()); return VOCAL
async def get_v(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data['vocal']=update.callback_query.data.split("|")[1]; await update.callback_query.answer(); await update.callback_query.message.reply_text(f"**Step 6/6: TEMPO**", reply_markup=tempo_kb()); return TEMPO
async def get_t(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tempo']=update.callback_query.data.split("|")[1]; await update.callback_query.answer()
    d=context.user_data; await update.callback_query.message.reply_text(f"✅ **Preview:** {d['title']}\n{d['genre']} • {d['mood']} • {d['vocal']} • {d['tempo']}\n{ d['lyrics'][:100]}...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎧 GENERATE NOW", callback_data="gen")]]), parse_mode="Markdown"); return CONFIRM

async def do_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer(); d=context.user_data
    msg=await update.callback_query.message.reply_text(f"🎧 Generating **{d.get('title')}**... 15-25s", parse_mode="Markdown")
    payload={"action":"generate","prompt":d.get('genre','Metal rock'),"genre":d.get('genre','Tock'),"mood":d.get('mood','Calm'),"vocal":d.get('vocal','Male vocal'),"tempo":d.get('tempo','Slow'),"title":d.get('title','Live'),"lyrics":d.get('lyrics','')}
    try:
        res=await asyncio.to_thread(call_music, payload)
        song=res['data']['songs'][0]; audio, image=song['audio'], song['image']
        await msg.delete()
        await update.callback_query.message.reply_photo(photo=image, caption=f"🎵 **{d['title']}**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬇️ Download MP3", url=audio)],[InlineKeyboardButton("🎵 New Song", callback_data="mode_manual")]]), parse_mode="Markdown")
        await update.callback_query.message.reply_audio(audio=audio, title=d['title'])
        await update.callback_query.message.reply_document(document=audio, filename=f"{d['title']}.mp3")
    except Exception as e: await msg.edit_text(f"❌ Failed: {e}")
    return ConversationHandler.END

def main():
    app=Application.builder().token(TOKEN).build()
    conv=ConversationHandler(entry_points=[CallbackQueryHandler(mode_handler, pattern="^mode_")], states={TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)], LYRICS:[MessageHandler(filters.TEXT & ~filters.COMMAND, get_lyrics_text), CallbackQueryHandler(lyrics_choice, pattern="^(ai_l|my_l)$"), CallbackQueryHandler(use_ai, pattern="^use_ai$")], GENRE:[CallbackQueryHandler(get_g, pattern="^g\\|")], MOOD:[CallbackQueryHandler(get_m, pattern="^m\\|")], VOCAL:[CallbackQueryHandler(get_v, pattern="^v\\|")], TEMPO:[CallbackQueryHandler(get_t, pattern="^t\\|")], CONFIRM:[CallbackQueryHandler(do_gen, pattern="^gen$"), CallbackQueryHandler(mode_handler, pattern="^mode_")]}, fallbacks=[CommandHandler("start", start)])
    app.add_handler(CommandHandler("start", start)); app.add_handler(conv)
    app.run_polling()

if __name__=="__main__":
    # Fake port for Render Web Service
    import threading, os
    from http.server import HTTPServer, BaseHTTPRequestHandler
    def fake_server():
        port = int(os.environ.get("PORT", 10000))
        HTTPServer(("", port), BaseHTTPRequestHandler).serve_forever()
    threading.Thread(target=fake_server, daemon=True).start()
    main()
