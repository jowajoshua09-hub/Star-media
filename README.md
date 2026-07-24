# 🎵 Star Music Gen Bot - Render Deployment

AI Telegram Bot that generates full songs. Powered 100% by **Omegatech API**.
- **AUTO Mode:** `Generate Everything with AI` - One prompt → Title + Lyrics + Music
- **MANUAL Mode:** Step-by-step wizard with AI lyrics option

## ✨ Features
- 🤖 AI Lyrics via `https://api.omegatech.app/api/ai/Gpt-4o-mini`
- 🎧 Music Generation via `https://api.omegatech.app/api/ai/Remusicv2`
- Cleans response from `--n--` and `**` (from your screenshot)
- Returns: Cover Image + Audio Player + MP3 Download Button + Document
- No API URL visible to users (hidden in ENV)

## 📁 Project Structure
star-music-bot/
├── http://bot.py           # Main bot (AUTO + MANUAL)
├── http://requirements.txt # Dependencies
├── http://render.yaml      # Render blueprint
└── http://README.md

## 🚀 Deploy to Render (1-Click)

### Method 1: Blueprint (Recommended)
1. Push this repo to GitHub
2. Go to **https://dashboard.render.com** → **New +** → **Blueprint**
3. Connect your GitHub repo `star-music-bot`
4. Render reads `render.yaml` automatically
5. Add Environment Variable:
   - `BOT_TOKEN` = `123456:ABC...` from [@BotFather](https://t.me/BotFather)
6. Click **Apply** → Done. Bot is live.

### Method 2: Manual
1. Render → New → **Worker**
2. Connect repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python bot.py`
5. Add ENV Vars:
BOT_TOKEN=your_token
   MUSIC_API=https://api.omegatech.app/api/ai/Remusicv2
   LYRICS_API=https://api.omegatech.app/api/ai/Gpt-4o-mini
6. Deploy

## 🔧 Environment Variables
| Key | Required | Default |
|---|---|---|
| `BOT_TOKEN` | Yes | - |
| `MUSIC_API` | No | `https://api.omegatech.app/api/ai/Remusicv2` |
| `LYRICS_API` | No | `https://api.omegatech.app/api/ai/Gpt-4o-mini` |

## 💬 How Bot Works

/start
→ [ 🤖 Generate Everything with AI ] [ ✋ Build Manually ]

AUTO:
User: metal rock about darkness calling my soul
Bot: 🤖 AI writing...
Bot: ✨ Title: Live | Metal • Dark | Male vocal • Slow
     [🎧 GENERATE NOW]

MANUAL:
Step 1: Title → Live
Step 2: Lyrics → [🤖 Let AI Write] or Type Own
        → Uses Gpt-4o-mini → Cleans --n-- → Preview
Step 3: Genre → Rock / Tock / Metal / Phonk / Lo-Fi / Trap / Pop
Step 4: Mood → Calm / Dark / Energetic / Sad
Step 5: Vocal → Male / Female
Step 6: Tempo → Slow / Medium / Fast
→ 🎧 GENERATE NOW
→ Calls Remusicv2?action=generate&genre=...&lyrics=...
→ Returns Photo + Audio + Download Button

## 🛠️ API Fix - Why `GET` Failed

❌ Wrong:
```python
url = "GET https://api.omegatech.app/..."
✅ Correct (used in this bot):
requests.get("https://api.omegatech.app/api/ai/Remusicv2", params={
    "action": "generate",
    "prompt": "Metal rock",
    ...
})
`GET` is the HTTP method (`.get()`), not part of the URL.

## 📦 Local Test
pip install -r requirements.txt
export BOT_TOKEN="your_token"
python bot.py
## 📄 License
MIT - Free for Omegatech users.
