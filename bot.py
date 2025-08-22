import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загружаем токен из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище в памяти
playlists = {}  # {playlist_name: [file_id, file_id]}
current_playlist = {}  # {user_id: "playlist_name" или "WAITING_NAME"}


@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать плейлист", callback_data="create")],
        [InlineKeyboardButton(text="Мои плейлисты", callback_data="list")]
    ])
    await message.answer("Привет 👋 Я бот для создания музыкальных плейлистов.\n"
                         "Выбери действие:", reply_markup=kb)


@dp.callback_query(lambda c: c.data == "create")
async def create_playlist(callback: types.CallbackQuery):
    await callback.message.answer("Введи название нового плейлиста:")
    await callback.answer()
    current_playlist[callback.from_user.id] = "WAITING_NAME"


@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    # ждём название плейлиста
    if current_playlist.get(user_id) == "WAITING_NAME":
        pl_name = message.text.strip()
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
        if not pl_name:
            await message.answer("Сначала создай или выбери плейлист!")
            return
        file_id = message.audio.file_id if message.audio else message.document.file_id
        playlists[pl_name].append(file_id)
        await message.answer(f"Добавлено в '{pl_name}' ✅")
        return

    await message.answer("Я понимаю только команды, музыку или название плейлиста 😉")


@dp.callback_query(lambda c: c.data == "list")
async def list_playlists(callback: types.CallbackQuery):
    if not playlists:
        await callback.message.answer("У тебя пока нет плейлистов 😢")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=pl, callback_data=f"open:{pl}")]
                         for pl in playlists.keys()]
    )
    await callback.message.answer("Твои плейлисты:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("open:"))
async def open_playlist(callback: types.CallbackQuery):
    pl_name = callback.data.split(":")[1]
    current_playlist[callback.from_user.id] = pl_name
    if not playlists[pl_name]:
        await callback.message.answer(f"Плейлист '{pl_name}' пуст 🕳️")
    else:
        await callback.message.answer(f"🎵 Песни из '{pl_name}':")
        for file_id in playlists[pl_name]:
            await bot.send_audio(callback.from_user.id, file_id)
    await callback.answer()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())