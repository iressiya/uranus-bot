import json
import logging
import os
import random
import sqlite3
from datetime import datetime, time
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN", "VSTAV_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
PAYMENT_INFO = os.getenv("PAYMENT_INFO", "Оплата підписки: посилання буде тут")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://iressiya.github.io/uranus-bot/webapp/index.html")
DAILY_SEND_TIME = time(hour=9, minute=0)
DB_PATH = Path(__file__).parent / "subscribers.db"
TIPS_PATH = Path(__file__).parent / "tips.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Підказка")],
        [KeyboardButton(text="Підписка"), KeyboardButton(text="Статус")],
        [KeyboardButton(text="Відкрити застосунок", web_app=WebAppInfo(url=WEBAPP_URL))],
    ],
    resize_keyboard=True,
)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'pending',
            joined_at TEXT,
            tip_index INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def add_pending(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO subscribers (user_id, username, status, joined_at) VALUES (?, ?, 'pending', ?)",
        (user_id, username, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def set_status(user_id, status):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE subscribers SET status=? WHERE user_id=?", (status, user_id))
    conn.commit()
    conn.close()


def get_active_subscribers():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT user_id, tip_index FROM subscribers WHERE status='active'").fetchall()
    conn.close()
    return rows


def bump_tip_index(user_id, new_index):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE subscribers SET tip_index=? WHERE user_id=?", (new_index, user_id))
    conn.commit()
    conn.close()


def load_tips():
    with open(TIPS_PATH, encoding="utf-8") as f:
        return json.load(f)


TIPS = load_tips()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "Привіт! Я Уранічний бот. Ретроградний Уран стартує 6-10 вересня 2026 "
        "і триватиме до лютого 2027. Я надсилатиму тобі коротку щоденну підказку.\n\n"
        "Обирай кнопку знизу або команди:\n"
        "/subscribe - оформити підписку\n"
        "/tip - отримати підказку зараз\n"
        "/status - перевірити статус підписки"
    )
    await message.answer(text, reply_markup=MAIN_MENU)


@dp.message(Command("tip"))
@dp.message(F.text == "Підказка")
async def cmd_tip_demo(message: Message):
    tip = random.choice(TIPS)
    await message.answer(tip)


@dp.message(Command("subscribe"))
@dp.message(F.text == "Підписка")
async def cmd_subscribe(message: Message):
    add_pending(message.from_user.id, message.from_user.username or "")
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Я оплатив", callback_data="paid"))
    await message.answer(PAYMENT_INFO, reply_markup=kb.as_markup())


@dp.callback_query(F.data == "paid")
async def cb_paid(callback: CallbackQuery):
    user = callback.from_user
    await callback.message.answer("Дякую! Заявку передано адміну.")
    await bot.send_message(ADMIN_ID, "Нова заявка на підписку: id " + str(user.id))
    await callback.answer()


@dp.message(Command("status"))
@dp.message(F.text == "Статус")
async def cmd_status(message: Message):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT status FROM subscribers WHERE user_id=?", (message.from_user.id,)).fetchone()
    conn.close()
    if not row:
        await message.answer("Ти ще не оформлював підписку. Тисни Підписка")
    elif row[0] == "pending":
        await message.answer("Оплата в очікуванні підтвердження адміном.")
    elif row[0] == "active":
        await message.answer("Підписка активна. Щоденні підказки надходитимуть о 9:00.")
    else:
        await message.answer("Підписка неактивна. Тисни Підписка щоб відновити.")


@dp.message(Command("approve"))
async def cmd_approve(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат команди: approve і user id")
        return
    user_id = int(parts[1])
    set_status(user_id, "active")
    await message.answer("Активовано підписку для " + str(user_id))
    await bot.send_message(user_id, "Твою підписку активовано! Перша підказка прийде завтра о 9:00.")


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("Формат команди: broadcast і текст")
        return
    for user_id, _ in get_active_subscribers():
        try:
            await bot.send_message(user_id, text)
        except Exception as e:
            logging.warning("Не вдалось надіслати " + str(user_id) + ": " + str(e))
    await message.answer("Розіслано.")


async def send_daily_tips():
    for user_id, tip_index in get_active_subscribers():
        idx = tip_index % len(TIPS)
        tip = TIPS[idx]
        try:
            await bot.send_message(user_id, "Ранкова уранічна підказка: " + tip)
            bump_tip_index(user_id, idx + 1)
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
