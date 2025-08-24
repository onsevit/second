import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Загружаем токен из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище
playlists = {}  # {playlist_name: [file_id, file_id]}
current_playlist = {}  # {user_id: "playlist_name" или "WAITING_NAME"}
last_messages = {}  # {user_id: [message_id, message_id...]}

# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎶 Новый плейлист")],
        [KeyboardButton(text="📂 Список")],
        [KeyboardButton(text="⚙️ Настройки")]
    ],
    resize_keyboard=True
)


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет 👋 Я бот для создания музыкальных плейлистов.\nВыбери действие:",
        reply_markup=main_kb
    )


@dp.message(lambda m: m.text == "🎶 Новый плейлист")
async def create_playlist(message: types.Message):
    await message.answer("Введи название нового плейлиста:")
    current_playlist[message.from_user.id] = "WAITING_NAME"


@dp.message(lambda m: m.text == "📂 Список")
async def list_playlists(message: types.Message):
    if not playlists:
        await message.answer("У тебя пока нет плейлистов 😢")
        return

    text = "📂 Твои плейлисты:\n" + "\n".join([f"• {pl}" for pl in playlists.keys()])
    await message.answer(text)


@dp.message(lambda m: m.text == "⚙️ Настройки")
async def settings_menu(message: types.Message):
    if not playlists:
        await message.answer("Нет плейлистов для настройки 😢")
        return

    text = "⚙️ Доступные плейлисты:\n" + "\n".join([f"• {pl}" for pl in playlists.keys()])
    await message.answer(text + "\n\nНапиши команду:\n"
                         "`удалить <название>`\n"
                         "`переименовать <старое> <новое>`\n"
                         "`удалить трек <плейлист> <номер>`", parse_mode="Markdown")


@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # ждём название плейлиста
    if current_playlist.get(user_id) == "WAITING_NAME":
        pl_name = text
        if pl_name in playlists:
            await message.answer("Такой плейлист уже есть ❌")
        else:
            playlists[pl_name] = []
            current_playlist[user_id] = pl_name
            await message.answer(f"✅ Плейлист '{pl_name}' создан!\nКидай музыку для добавления.")
        return

    # добавляем музыку
    if message.audio or message.document:
        pl_name = current_playlist.get(user_id)
        if not pl_name or pl_name == "WAITING_NAME":
            await message.answer("Сначала создай или выбери плейлист!")
            return
        file_id = message.audio.file_id if message.audio else message.document.file_id
        playlists[pl_name].append(file_id)
        await message.answer(f"Добавлено в '{pl_name}' ✅")
        return

    # команды для настроек
    if text.startswith("удалить "):
        pl_name = text.replace("удалить ", "", 1).strip()
        if pl_name in playlists:
            playlists.pop(pl_name)
            await message.answer(f"🗑 Плейлист '{pl_name}' удалён!")
        else:
            await message.answer("Такого плейлиста нет ❌")
        return

    if text.startswith("переименовать "):
        parts = text.split()
        if len(parts) >= 3:
            old_name, new_name = parts[1], parts[2]
            if old_name in playlists:
                if new_name in playlists:
                    await message.answer("Такой плейлист уже есть ❌")
                else:
                    playlists[new_name] = playlists.pop(old_name)
                    current_playlist[user_id] = new_name
                    await message.answer(f"✏️ '{old_name}' переименован в '{new_name}' ✅")
            else:
                await message.answer("Такого плейлиста нет ❌")
        else:
            await message.answer("Используй: переименовать <старое> <новое>")
        return

    if text.startswith("удалить трек "):
        parts = text.split()
        if len(parts) >= 3:
            pl_name, idx = parts[2], None
            try:
                idx = int(parts[3]) - 1
            except:
                pass
            if pl_name in playlists and idx is not None and 0 <= idx < len(playlists[pl_name]):
                playlists[pl_name].pop(idx)
                await message.answer(f"➖ Трек {idx+1} удалён из '{pl_name}' ✅")
            else:
                await message.answer("Ошибка: проверь название и номер трека ❌")
        else:
            await message.answer("Используй: удалить трек <плейлист> <номер>")
        return

    # выбор плейлиста для прослушивания
    if text in playlists:
        pl_name = text
        if user_id in last_messages:
            for msg_id in last_messages[user_id]:
                try:
                    await bot.delete_message(user_id, msg_id)
                except:
                    pass
            last_messages[user_id] = []

        current_playlist[user_id] = pl_name
        sent_ids = []

        if not playlists[pl_name]:
            msg = await message.answer(f"Плейлист '{pl_name}' пуст 🕳️")
            sent_ids.append(msg.message_id)
        else:
            msg = await message.answer(f"🎵 Песни из '{pl_name}':")
            sent_ids.append(msg.message_id)
            for file_id in playlists[pl_name]:
                audio_msg = await bot.send_audio(user_id, file_id)
                sent_ids.append(audio_msg.message_id)

        last_messages[user_id] = sent_ids
        return

    await message.answer("Я понимаю только команды, музыку или название плейлиста 😉")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())