import json
import logging
import os
import sqlite3
from datetime import datetime, date, time
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN", "VSTAV_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
PAYMENT_INFO = os.getenv(
    "PAYMENT_INFO",
    "Якщо хочеш підтримати проєкт - буду вдячна за будь-яку суму: посилання буде тут",
)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://iressiya.github.io/uranus-bot/webapp/index.html")
DAILY_SEND_TIME = time(hour=9, minute=0)

TRANSIT_START = date(2026, 9, 6)

DB_DIR = os.getenv("DB_DIR", str(Path(__file__).parent))
DB_PATH = Path(DB_DIR) / "subscribers.db"
TIPS_PATH = Path(__file__).parent / "tips.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Прогноз дня")],
        [KeyboardButton(text="Підписатись")],
        [KeyboardButton(text="Підказка 💜", web_app=WebAppInfo(url=WEBAPP_URL))],
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
            status TEXT DEFAULT 'active',
            joined_at TEXT,
            tip_index INTEGER DEFAULT 0
        )
    """)
    try:
        conn.execute("ALTER TABLE subscribers ADD COLUMN full_name TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def add_active_subscriber(user_id, username, full_name):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO subscribers (user_id, username, full_name, status, joined_at) "
        "VALUES (?, ?, ?, 'active', ?) "
        "ON CONFLICT(user_id) DO UPDATE SET status='active', username=excluded.username, "
        "full_name=excluded.full_name",
        (user_id, username, full_name, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_active_subscribers():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT user_id FROM subscribers WHERE status='active'").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_all_subscribers():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT user_id, username, full_name, joined_at FROM subscribers "
        "WHERE status='active' ORDER BY joined_at DESC"
    ).fetchall()
    conn.close()
    return rows


def load_tips():
    with open(TIPS_PATH, encoding="utf-8") as f:
        return json.load(f)


TIPS = load_tips()


def get_today_forecast():
    day_index = (date.today() - TRANSIT_START).days
    day_index = max(0, min(day_index, len(TIPS) - 1))
    return TIPS[day_index], day_index + 1


def format_user_label(username, full_name, user_id):
    label = full_name or "Без імені"
    if username:
        label += " (@" + username + ")"
    label += " - id " + str(user_id)
    return label


async def activate_subscription(user_id, username, full_name):
    add_active_subscriber(user_id, username, full_name)
    text = (
        "Підписку активовано! Щоденний прогноз надходитиме о 9:00.\n\n"
        + PAYMENT_INFO
    )
    await bot.send_message(user_id, text)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "Привіт! Я Уранічний бот. Ретроградний Уран стартував 6 вересня 2026 "
        "і триватиме до лютого 2027. Я надсилатиму тобі короткий прогноз дня, "
        "прив'язаний саме до поточного етапу транзиту.\n\n"
        "Обирай кнопку знизу або команди:\n"
        "/subscribe - підписатись (безкоштовно)\n"
        "/tip - прогноз на сьогодні"
    )
    await message.answer(text, reply_markup=MAIN_MENU)


@dp.message(Command("tip"))
@dp.message(F.text == "Прогноз дня")
async def cmd_tip_today(message: Message):
    forecast, day_number = get_today_forecast()
    await message.answer(forecast)


@dp.message(Command("subscribe"))
@dp.message(F.text == "Підписатись")
async def cmd_subscribe(message: Message):
    await activate_subscription(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
    )


@dp.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    data = message.web_app_data.data
    if data == "subscribe":
        await activate_subscription(
            message.from_user.id,
            message.from_user.username or "",
            message.from_user.full_name or "",
        )


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    rows = get_all_subscribers()
    if not rows:
        await message.answer("Поки що немає підписників.")
        return
    lines = ["Активні підписники (" + str(len(rows)) + "):"]
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
    for user_id in get_active_subscribers():
        try:
            await bot.send_message(user_id, text)
        except Exception as e:
            logging.warning("Не вдалось надіслати " + str(user_id) + ": " + str(e))
    await message.answer("Розіслано.")


async def send_daily_tips():
    forecast, day_number = get_today_forecast()
    text = "День " + str(day_number) + " ретроградного циклу:\n\n" + forecast
    for user_id in get_active_subscribers():
        try:
            await bot.send_message(user_id, text)
        except Exception as e:
            logging.warning("Не вдалось надіслати " + str(user_id) + ": " + str(e))


async def main():
    init_db()
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(send_daily_tips, "cron", hour=DAILY_SEND_TIME.hour, minute=DAILY_SEND_TIME.minute)
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
