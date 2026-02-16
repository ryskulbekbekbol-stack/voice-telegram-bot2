import os
import asyncio
import yt_dlp
import subprocess

from pyrogram import Client, filters
from tgcaller import TgCaller

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# ===== проверка ffmpeg =====
try:
    subprocess.run(["ffmpeg", "-version"], capture_output=True)
    print("✅ ffmpeg ok")
except:
    print("❌ ffmpeg не найден")

app = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

vc = TgCaller(app)
started = False


async def ensure_started():
    global started
    if not started:
        await vc.start()
        started = True
        print("✅ TgCaller запущен")


# ===== загрузка =====
async def download(query):
    loop = asyncio.get_event_loop()
    name = f"song_{os.urandom(4).hex()}.mp3"

    opts = {
        "format": "bestaudio",
        "outtmpl": name,
        "noplaylist": True,
        "quiet": True
    }

    def _dl():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"ytsearch1:{query}"])

    await loop.run_in_executor(None, _dl)

    if not os.path.exists(name):
        raise Exception("download failed")

    return name


# ===== play =====
@app.on_message(filters.command("play") & filters.group)
async def play(_, msg):
    if len(msg.command) < 2:
        await msg.reply("Используй: /play название")
        return

    q = " ".join(msg.command[1:])
    m = await msg.reply("🔄 качаю...")

    try:
        file = await download(q)
    except Exception as e:
        await m.edit(f"❌ ошибка загрузки: {e}")
        return

    await ensure_started()

    chat = msg.chat.id

    try:
        if not vc.is_connected(chat):
            await vc.join_call(chat)
    except Exception as e:
        await m.edit(f"❌ войс ошибка: {e}")
        return

    try:
        await vc.play(chat, file)
        await m.edit(f"🎵 играет: {q}")
    except Exception as e:
        await m.edit(f"❌ play ошибка: {e}")


# ===== stop =====
@app.on_message(filters.command("stop") & filters.group)
async def stop(_, msg):
    chat = msg.chat.id

    if vc.is_connected(chat):
        await vc.stop_playback(chat)
        await vc.leave_call(chat)
        await msg.reply("⏹ остановлено")
    else:
        await msg.reply("не в войсе")


print("🚀 старт")
app.run()
