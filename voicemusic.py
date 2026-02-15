import os
import asyncio
from collections import deque

import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall

# ---------- НАСТРОЙКИ ----------
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

if not API_ID or not API_HASH or not SESSION_STRING:
    raise ValueError("API_ID, API_HASH и SESSION_STRING должны быть заданы в переменных окружения")

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
app = Client(
    name="userbot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH
)

vc = PyTgCalls(app)

# Очередь треков: каждый элемент — (название, путь_к_файлу)
queue = deque()
playing = False
current_track = None
current_chat_id = None   # ID чата, в котором происходит воспроизведение

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
async def is_admin(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except:
        return False

def download_audio(query, output_name):
    """
    Скачивает аудио с YouTube, конвертирует в mp3.
    Возвращает (путь_к_файлу, название_трека)
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_name}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        filename = filename.rsplit('.', 1)[0] + '.mp3'
        title = info.get('title', 'Unknown')
        return filename, title

async def play_next():
    global playing, current_track, current_chat_id
    if not queue:
        playing = False
        current_track = None
        # можно оставить или покинуть голосовой чат
        return

    track_name, file_path = queue.popleft()
    current_track = track_name
    playing = True

    try:
        # Предполагаем, что мы уже присоединились к голосовому чату
        await vc.play(
            current_chat_id,
            AudioPiped(file_path)
        )
        await app.send_message(
            current_chat_id,
            f"🎵 **Сейчас играет:** {track_name}"
        )
    except NoActiveGroupCall:
        await app.send_message(
            current_chat_id,
            "❌ Нет активного голосового чата. Используйте /join, чтобы присоединиться."
        )
        playing = False
    except Exception as e:
        await app.send_message(current_chat_id, f"❌ Ошибка воспроизведения: {e}")
        playing = False
        # пробуем следующий трек
        await play_next()

# ---------- КОМАНДЫ ----------
@app.on_message(filters.command("join") & filters.group)
async def join_vc(client: Client, message: Message):
    """Присоединяется к голосовому чату текущей группы."""
    global current_chat_id
    chat_id = message.chat.id
    try:
        await vc.join(chat_id)
        current_chat_id = chat_id
        await message.reply("✅ Присоединился к голосовому чату!")
    except Exception as e:
        await message.reply(f"❌ Не удалось присоединиться: {e}")

@app.on_message(filters.command("play") & filters.group)
async def play_command(client: Client, message: Message):
    """Добавляет трек в очередь и начинает воспроизведение."""
    global current_chat_id

    if len(message.command) < 2:
        await message.reply("❓ Использование: /play <название или ссылка>")
        return

    if not current_chat_id:
        await message.reply("❌ Сначала присоединитесь к голосовому чату командой /join")
        return

    query = message.text.split(maxsplit=1)[1]
    status_msg = await message.reply("🔍 Ищу трек...")

    try:
        # Скачиваем аудио
        file_path, title = download_audio(query, f"track_{message.id}")
        queue.append((title, file_path))

        await status_msg.edit(f"✅ **{title}** добавлен в очередь. Позиция: {len(queue)}")

        if not playing:
            await play_next()
    except Exception as e:
        await status_msg.edit(f"❌ Ошибка: {e}")

@app.on_message(filters.command("skip") & filters.group)
async def skip_command(client: Client, message: Message):
    """Пропускает текущий трек."""
    global playing
    if not playing:
        await message.reply("⚠️ Сейчас ничего не играет.")
        return

    try:
        await vc.stop(current_chat_id)
        await message.reply("⏭ Трек пропущен.")
        await play_next()
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@app.on_message(filters.command("pause") & filters.group)
async def pause_command(client: Client, message: Message):
    """Приостанавливает воспроизведение."""
    if not playing:
        await message.reply("⚠️ Сейчас ничего не играет.")
        return
    try:
        await vc.pause(current_chat_id)
        await message.reply("⏸ Воспроизведение приостановлено.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@app.on_message(filters.command("resume") & filters.group)
async def resume_command(client: Client, message: Message):
    """Возобновляет воспроизведение."""
    try:
        await vc.resume(current_chat_id)
        await message.reply("▶ Воспроизведение возобновлено.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@app.on_message(filters.command("stop") & filters.group)
async def stop_command(client: Client, message: Message):
    """Останавливает воспроизведение и очищает очередь."""
    global playing, current_track
    queue.clear()
    if playing:
        try:
            await vc.stop(current_chat_id)
        except:
            pass
        playing = False
        current_track = None
        await message.reply("⏹ Воспроизведение остановлено, очередь очищена.")
    else:
        await message.reply("⚠️ Сейчас ничего не играет.")

@app.on_message(filters.command("queue") & filters.group)
async def queue_command(client: Client, message: Message):
    """Показывает текущую очередь."""
    if not queue:
        await message.reply("📭 Очередь пуста.")
        return
    lines = []
    for i, (title, _) in enumerate(queue, 1):
        lines.append(f"{i}. {title}")
    text = "**Очередь:**\n" + "\n".join(lines)
    await message.reply(text)

@app.on_message(filters.command("leave") & filters.group)
async def leave_vc(client: Client, message: Message):
    """Покидает голосовой чат."""
    global current_chat_id, playing, current_track
    if not current_chat_id:
        await message.reply("❌ Я не в голосовом чате.")
        return
    try:
        await vc.leave(current_chat_id)
        current_chat_id = None
        queue.clear()
        playing = False
        current_track = None
        await message.reply("👋 Покинул голосовой чат.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    app.run()
