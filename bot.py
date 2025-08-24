import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
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
last_messages = {}  # {user_id: [message_id, message_id...]}


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎶 Новый плейлист", callback_data="create")],
        [InlineKeyboardButton(text="📂 Список", callback_data="list")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ])


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет 👋 Я бот для создания музыкальных плейлистов.\n"
                         "Выбери действие:", reply_markup=main_menu())


# ---------- СОЗДАНИЕ ПЛЕЙЛИСТА ----------
@dp.callback_query(F.data == "create")
async def create_playlist(callback: types.CallbackQuery):
    await callback.message.answer("Введи название нового плейлиста:")
    await callback.answer()
    current_playlist[callback.from_user.id] = "WAITING_NAME"


# ---------- ПОЛУЧЕНИЕ НАЗВАНИЯ ----------
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
        if not pl_name or pl_name == "WAITING_NAME":
            await message.answer("Сначала создай или выбери плейлист!")
            return
        file_id = message.audio.file_id if message.audio else message.document.file_id
        playlists[pl_name].append(file_id)
        await message.answer(f"Добавлено в '{pl_name}' ✅")
        return

    await message.answer("Я понимаю только команды, музыку или название плейлиста 😉")


# ---------- СПИСОК ПЛЕЙЛИСТОВ ----------
@dp.callback_query(F.data == "list")
async def list_playlists(callback: types.CallbackQuery):
    if not playlists:
        await callback.message.answer("У тебя пока нет плейлистов 😢")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=pl, callback_data=f"open:{pl}")]
                         for pl in playlists.keys()]
    )
    await callback.message.answer("📂 Твои плейлисты:", reply_markup=kb)
    await callback.answer()


# ---------- ОТКРЫТИЕ ПЛЕЙЛИСТА ----------
@dp.callback_query(F.data.startswith("open:"))
async def open_playlist(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    pl_name = callback.data.split(":")[1]

    # удаляем прошлые сообщения с музыкой
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
        msg = await callback.message.answer(f"Плейлист '{pl_name}' пуст 🕳️")
        sent_ids.append(msg.message_id)
    else:
        msg = await callback.message.answer(f"🎵 Песни из '{pl_name}':")
        sent_ids.append(msg.message_id)
        for file_id in playlists[pl_name]:
            audio_msg = await bot.send_audio(user_id, file_id)
            sent_ids.append(audio_msg.message_id)

    last_messages[user_id] = sent_ids
    await callback.answer()


# ---------- НАСТРОЙКИ ----------
@dp.callback_query(F.data == "settings")
async def settings_menu(callback: types.CallbackQuery):
    if not playlists:
        await callback.message.answer("Нет плейлистов для настройки 😢")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=pl, callback_data=f"settings:{pl}")]
                         for pl in playlists.keys()]
    )
    await callback.message.answer("⚙️ Выбери плейлист для настроек:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("settings:"))
async def playlist_settings(callback: types.CallbackQuery):
    pl_name = callback.data.split(":")[1]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить плейлист", callback_data=f"delete:{pl_name}")],
        [InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename:{pl_name}")],
        [InlineKeyboardButton(text="➖ Удалить трек", callback_data=f"remove_track:{pl_name}")]
    ])
    await callback.message.answer(f"⚙️ Настройки плейлиста '{pl_name}':", reply_markup=kb)
    await callback.answer()


# ---------- УДАЛЕНИЕ ПЛЕЙЛИСТА ----------
@dp.callback_query(F.data.startswith("delete:"))
async def delete_playlist(callback: types.CallbackQuery):
    pl_name = callback.data.split(":")[1]
    playlists.pop(pl_name, None)
    await callback.message.answer(f"🗑 Плейлист '{pl_name}' удалён!")
    await callback.answer()


# ---------- ПЕРЕИМЕНОВАНИЕ ----------
@dp.callback_query(F.data.startswith("rename:"))
async def rename_playlist(callback: types.CallbackQuery):
    pl_name = callback.data.split(":")[1]
    current_playlist[callback.from_user.id] = f"RENAME:{pl_name}"
    await callback.message.answer(f"Введи новое имя для плейлиста '{pl_name}':")
    await callback.answer()


# обработка ввода нового имени
@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    state = current_playlist.get(user_id)

    if state and state.startswith("RENAME:"):
        old_name = state.split(":")[1]
        new_name = message.text.strip()
        if new_name in playlists:
            await message.answer("Такой плейлист уже существует ❌")
        else:
            playlists[new_name] = playlists.pop(old_name)
            current_playlist[user_id] = new_name
            await message.answer(f"✏️ Плейлист '{old_name}' переименован в '{new_name}' ✅")
        return


# ---------- УДАЛЕНИЕ ТРЕКА ----------
@dp.callback_query(F.data.startswith("remove_track:"))
async def remove_track(callback: types.CallbackQuery):
    pl_name = callback.data.split(":")[1]
    if not playlists[pl_name]:
        await callback.message.answer("Плейлист пуст 🕳️")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Трек {i+1}", callback_data=f"rm:{pl_name}:{i}")]
            for i in range(len(playlists[pl_name]))
        ]
    )
    await callback.message.answer("Выбери трек для удаления:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("rm:"))
async def rm_track(callback: types.CallbackQuery):
    _, pl_name, idx = callback.data.split(":")
    idx = int(idx)
    if 0 <= idx < len(playlists[pl_name]):
        playlists[pl_name].pop(idx)
        await callback.message.answer(f"➖ Трек {idx+1} удалён из '{pl_name}' ✅")
    else:
        await callback.message.answer("Ошибка: трек не найден ❌")
    await callback.answer()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())