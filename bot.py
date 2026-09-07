import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN", "VSTAV_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
PAYMENT_INFO = os.getenv(
    "PAYMENT_INFO",
    "Якщо ця інформація відгукнулась - можеш зробити енергообмін: посилання буде тут",
)

DB_DIR = os.getenv("DB_DIR", str(Path(__file__).parent))
DB_PATH = Path(DB_DIR) / "subscribers.db"
MOON_PATH = Path(__file__).parent / "moon_signs.json"
VENUS_PATH = Path(__file__).parent / "venus_signs.json"
MARS_PATH = Path(__file__).parent / "mars_signs.json"
ASPECTS_PATH = Path(__file__).parent / "venus_aspects.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

SIGNS = [
    ("aries", "♈ Овен"),
    ("taurus", "♉ Телець"),
    ("gemini", "♊ Близнюки"),
    ("cancer", "♋ Рак"),
    ("leo", "♌ Лев"),
    ("virgo", "♍ Діва"),
    ("libra", "♎ Терези"),
    ("scorpio", "♏ Скорпіон"),
    ("sagittarius", "♐ Стрілець"),
    ("capricorn", "♑ Козоріг"),
    ("aquarius", "♒ Водолій"),
    ("pisces", "♓ Риби"),
]

PLANETS = [
    ("jupiter", "Юпітер"),
    ("saturn", "Сатурн"),
    ("uranus", "Уран"),
    ("neptune", "Нептун"),
    ("pluto", "Плутон"),
]

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌙 Місяць"), KeyboardButton(text="💗 Венера")],
        [KeyboardButton(text="🔥 Марс"), KeyboardButton(text="⚡ Аспекти Венери")],
        [KeyboardButton(text="💜 Подякувати")],
    ],
    resize_keyboard=True,
)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            status TEXT DEFAULT 'visited',
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def record_visit(user_id, username, full_name):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO subscribers (user_id, username, full_name, status, joined_at) "
        "VALUES (?, ?, ?, 'visited', ?) "
        "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, "
        "full_name=excluded.full_name",
        (user_id, username, full_name, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    logging.info("VISIT user_id=" + str(user_id) + " username=" + str(username) + " name=" + str(full_name))


def get_all_visitors():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT user_id, username, full_name, joined_at FROM subscribers ORDER BY joined_at DESC"
    ).fetchall()
    conn.close()
    return rows


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


MOON_SIGNS = load_json(MOON_PATH)
VENUS_SIGNS = load_json(VENUS_PATH)
MARS_SIGNS = load_json(MARS_PATH)
VENUS_ASPECTS = load_json(ASPECTS_PATH)


def format_user_label(username, full_name, user_id):
    label = full_name or "Без імені"
    if username:
        label += " (@" + username + ")"
    label += " - id " + str(user_id)
    return label


def build_signs_keyboard(prefix):
    kb = InlineKeyboardBuilder()
    for key, label in SIGNS:
        kb.button(text=label, callback_data=prefix + ":" + key)
    kb.adjust(2)
    return kb.as_markup()


def build_planets_keyboard(prefix):
    kb = InlineKeyboardBuilder()
    for key, label in PLANETS:
        kb.button(text=label, callback_data=prefix + ":" + key)
    kb.adjust(2)
    return kb.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    record_visit(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
    )
    text = (
        "Привіт люба! ✨\n\n"
        "Якщо ти тут - значить, настав час познайомитися із собою трохи глибше.\n\n"
        "Цей бот - не про те, якою «правильною» жінкою ти повинна бути, "
        "і не про те, щоб знайти один знак, який пояснить усе твоє життя.\n\n"
        "Ми дивимось на натальну карту як на систему символів для саморефлексії - "
        "щоб зрозуміти не «якою я повинна бути», а «яка я вже є».\n\n"
        "Доступні розділи:\n"
        "🌙 Місяць - твій емоційний світ\n"
        "💗 Венера - як ти любиш, цінуєш себе і гроші\n"
        "🔥 Марс - як ти дієш і проявляєш бажання\n"
        "⚡ Аспекти Венери - звʼязок кохання з вищими планетами\n\n"
        "Якщо не знаєш свої знаки - можна розрахувати натальну карту на будь-якому "
        "безкоштовному сайті (наприклад astro.com) за датою, часом і місцем народження.\n\n"
        "Обирай кнопку знизу, коли будеш готова 💜"
    )
    await message.answer(text, reply_markup=MAIN_MENU)


@dp.message(F.text == "🌙 Місяць")
async def show_moon_menu(message: Message):
    await message.answer("Обери свій знак Місяця:", reply_markup=build_signs_keyboard("moon"))


@dp.message(F.text == "💗 Венера")
async def show_venus_menu(message: Message):
    await message.answer("Обери свій знак Венери:", reply_markup=build_signs_keyboard("venus"))


@dp.message(F.text == "🔥 Марс")
async def show_mars_menu(message: Message):
    await message.answer("Обери свій знак Марса:", reply_markup=build_signs_keyboard("mars"))


@dp.message(F.text == "⚡ Аспекти Венери")
async def show_aspects_menu(message: Message):
    await message.answer(
        "Обери планету, з якою у тебе аспект Венери:",
        reply_markup=build_planets_keyboard("aspect"),
    )


@dp.callback_query(F.data.startswith("moon:"))
async def send_moon_sign(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    text = MOON_SIGNS.get(key)
    if text:
        await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data.startswith("venus:"))
async def send_venus_sign(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    text = VENUS_SIGNS.get(key)
    if text:
        await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data.startswith("mars:"))
async def send_mars_sign(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    text = MARS_SIGNS.get(key)
    if text:
        await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data.startswith("aspect:"))
async def send_aspect(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    text = VENUS_ASPECTS.get(key)
    if text:
        await callback.message.answer(text)
    await callback.answer()


@dp.message(F.text == "💜 Подякувати")
async def cmd_thanks(message: Message):
    await message.answer(PAYMENT_INFO)


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    rows = get_all_visitors()
    if not rows:
        await message.answer("Поки що ніхто не заходив.")
        return
    lines = ["Всього відвідувачів (" + str(len(rows)) + "):"]
    for user_id, username, full_name, joined_at in rows:
        lines.append(format_user_label(username, full_name, user_id))
    await message.answer("\n".join(lines))


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("Формат команди: broadcast і текст")
        return
    rows = get_all_visitors()
    for user_id, _, _, _ in rows:
        try:
            await bot.send_message(user_id, text)
        except Exception as e:
            logging.warning("Не вдалось надіслати " + str(user_id) + ": " + str(e))
    await message.answer("Розіслано.")


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
