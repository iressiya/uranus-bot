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
    con
