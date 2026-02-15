import asyncio
import yt_dlp
from collections import deque
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped

api_id = 123456
api_hash = "API_HASH"

app = Client("myacc", api_id=api_id, api_hash=api_hash)
vc = PyTgCalls(app)

queue = deque()
playing = False
paused = False
volume = 100


async def is_admin(client, chat_id, user_id):
    m = await client.get_chat_member(chat_id, user_id)
    return m.status in ("administrator", "creator")


def search_and_download(query, name):
    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": f"{name}.%(ext)s",
        "quiet": True,
        "default_search": "ytsearch1"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([query])
    return f"{name}.webm"


controls = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⏯", callback_data="pause"),
        InlineKeyboardButton("⏭", callback_data="skip"),
        InlineKeyboardButton("⏹", callback_data="stop")
    ],
    [
        InlineKeyboardButton("🔊+", callback_data="volup"),
        InlineKeyboardButton("🔉-", callback_data="voldown")
    ]
])


async def play_next(chat_id):
    global playing
    if not queue:
        playing = False
        await vc.leave_group_call(chat_id)
        return

    file = queue.popleft()
    await vc.change_stream(chat_id, AudioPiped(file))
    playing = True


# --- PLAY ПО НАЗВАНИЮ ---

@app.on_message(filters.command("play") & filters.me)
async def play(_, m):
    global playing

    if not await is_admin(app, m.chat.id, m.from_user.id):
        return await m.reply("Только админы")

    if len(m.command) < 2:
        return await m.reply("Название трека")

    query = " ".join(m.command[1:])
    name = f"track_{len(queue)}"

    msg = await m.reply("🔎 Ищу...")
    file = search_and_download(query, name)
    queue.append(file)

    if not playing:
        await vc.join_group_call(m.chat.id, AudioPiped(file))
        playing = True
        await msg.edit("▶️ Играет", reply_markup=controls)
    else:
        await msg.edit("➕ В очереди", reply_markup=controls)


# --- PLAY ФАЙЛОМ ---

@app.on_message(filters.audio & filters.me)
async def play_file(_, m):
    global playing

    if not await is_admin(app, m.chat.id, m.from_user.id):
        return

    msg = await m.reply("⬇️ Качаю файл...")
    path = await m.download()
    queue.append(path)

    if not playing:
        await vc.join_group_call(m.chat.id, AudioPiped(path))
        playing = True
        await msg.edit("▶️ Играет файл", reply_markup=controls)
    else:
        await msg.edit("➕ Файл в очереди", reply_markup=controls)


# --- КНОПКИ ---

@app.on_callback_query()
async def buttons(_, cq):
    global paused, volume
    chat_id = cq.message.chat.id

    if cq.data == "pause":
        if paused:
            await vc.resume_stream(chat_id)
            paused = False
        else:
            await vc.pause_stream(chat_id)
            paused = True

    elif cq.data == "skip":
        await play_next(chat_id)

    elif cq.data == "stop":
        queue.clear()
        await vc.leave_group_call(chat_id)

    elif cq.data == "volup":
        volume = min(200, volume + 10)
        await vc.set_my_volume(chat_id, volume)

    elif cq.data == "voldown":
        volume = max(10, volume - 10)
        await vc.set_my_volume(chat_id, volume)

    await cq.answer("OK")


# --- КОМАНДЫ ---

@app.on_message(filters.command("queue") & filters.me)
async def show_q(_, m):
    if not queue:
        return await m.reply("Очередь пустая")
    await m.reply("\n".join(queue))


@app.on_message(filters.command("stop") & filters.me)
async def stop(_, m):
    queue.clear()
    await vc.leave_group_call(m.chat.id)
    await m.reply("⏹ Стоп")


async def main():
    await app.start()
    await vc.start()
    print("ULTRA MUSIC BOT RUNNING")
    from pyrogram import idle
    await idle()

asyncio.run(main())
