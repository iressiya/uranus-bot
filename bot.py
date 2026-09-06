# -*- coding: utf-8 -*-
"""
Астро-бот "Жіноча енергія".
Користувачка обирає планету -> знак -> дім, бот видає готову інтерпретацію.
Також є розділ аспектів Венери та кнопка подяки/донату.
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from content import (
    WELCOME_TEXT,
    FORMULA_TEXT,
    DONATE_TEXT,
    SIGNS,
    HOUSES,
    PLANETS_INFO,
    ASPECT_PLANETS,
    ASPECT_TYPES,
    VENUS_ASPECTS,
)

# ==== НАЛАШТУВАННЯ (заповни свої дані тут або через змінні середовища) ====

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВ_СЮДИ_ТОКЕН_ВІД_BOTFATHER")
DONATE_LINK = os.getenv("DONATE_LINK", "https://send.monobank.ua/ТВОЄ_ПОСИЛАННЯ")

# ===========================================================================

logging.basicConfig(level=logging.INFO)
router = Router()

# ---------- Клавіатури ----------


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌙 Місяць", callback_data="planet:moon")
    kb.button(text="💗 Венера", callback_data="planet:venus")
    kb.button(text="🔥 Марс", callback_data="planet:mars")
    kb.button(text="⚡️ Аспекти Венери", callback_data="aspects:start")
    kb.button(text="🗺 Моя формула", callback_data="formula")
    kb.button(text="💜 Подякувати", callback_data="donate")
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ У меню", callback_data="menu")
    return kb.as_markup()


def signs_kb(planet: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for sign in SIGNS:
        kb.button(text=sign, callback_data=f"sign:{planet}:{sign}")
    kb.button(text="⬅️ У меню", callback_data="menu")
    kb.adjust(3)
    return kb.as_markup()


def houses_kb(planet: str, sign: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for house in HOUSES:
        kb.button(text=house, callback_data=f"house:{planet}:{sign}:{house}")
    kb.button(text="⬅️ У меню", callback_data="menu")
    kb.adjust(4)
    return kb.as_markup()


def aspect_planets_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in ASPECT_PLANETS:
        kb.button(text=f"Венера — {p}", callback_data=f"aspplanet:{p}")
    kb.button(text="⬅️ У меню", callback_data="menu")
    kb.adjust(2)
    return kb.as_markup()


def aspect_types_kb(planet: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for a in ASPECT_TYPES:
        kb.button(text=a, callback_data=f"asptype:{planet}:{a}")
    kb.button(text="⬅️ У меню", callback_data="menu")
    kb.adjust(2)
    return kb.as_markup()


MAX_LEN = 4000  # трохи менше ліміту Telegram (4096) про всяк випадок


async def send_long_text(message: Message, text: str, reply_markup=None):
    """Надсилає текст новим повідомленням, розбиваючи на частини, якщо він задовгий."""
    if len(text) <= MAX_LEN:
        await message.answer(text, reply_markup=reply_markup)
        return

    parts = []
    while text:
        if len(text) <= MAX_LEN:
            parts.append(text)
            break
        cut = text.rfind("\n\n", 0, MAX_LEN)
        if cut == -1:
            cut = MAX_LEN
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")

    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        await message.answer(part, reply_markup=reply_markup if is_last else None)


# ---------- Хендлери ----------


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Обери розділ 💜", reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text("Обери розділ 💜", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "formula")
async def cb_formula(callback: CallbackQuery):
    await callback.message.edit_text(FORMULA_TEXT, reply_markup=back_to_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "donate")
async def cb_donate(callback: CallbackQuery):
    text = DONATE_TEXT.format(donate_link=DONATE_LINK)
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("planet:"))
async def cb_planet(callback: CallbackQuery):
    planet = callback.data.split(":")[1]
    title = PLANETS_INFO[planet]["title"]
    await callback.message.edit_text(
        f"{title}\n\nОбери свій знак:", reply_markup=signs_kb(planet)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sign:"))
async def cb_sign(callback: CallbackQuery):
    _, planet, sign = callback.data.split(":")
    info = PLANETS_INFO[planet]
    text = info["signs"][sign]

    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Подивитись за домом", callback_data=f"gotohouse:{planet}:{sign}")
    kb.button(text="🔄 Інший знак", callback_data=f"planet:{planet}")
    kb.button(text="⬅️ У меню", callback_data="menu")
    kb.adjust(1)

    # Telegram обмежує повідомлення 4096 символами — довгі тексти ріжемо на частини
    await send_long_text(callback.message, text, reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("gotohouse:"))
async def cb_gotohouse(callback: CallbackQuery):
    _, planet, sign = callback.data.split(":")
    title = PLANETS_INFO[planet]["title"]
    await callback.message.answer(
        f"{title} у знаку {sign}\n\nТепер обери дім, щоб побачити, де це найпомітніше:",
        reply_markup=houses_kb(planet, sign),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("house:"))
async def cb_house(callback: CallbackQuery):
    _, planet, sign, house = callback.data.split(":")
    info = PLANETS_INFO[planet]
    house_text = info["houses"][house]

    result = f"{info['title']}, {house} дім\n\n{house_text}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Інший дім", callback_data=f"gotohouse:{planet}:{sign}")
    kb.button(text="⬅️ У меню", callback_data="menu")
    kb.adjust(1)
    await send_long_text(callback.message, result, reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "aspects:start")
async def cb_aspects_start(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚡️ АСПЕКТИ ВЕНЕРИ\n\nОбери, з якою планетою у Венери аспект:",
        reply_markup=aspect_planets_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("aspplanet:"))
async def cb_aspect_planet(callback: CallbackQuery):
    planet = callback.data.split(":")[1]
    await callback.message.edit_text(
        f"Венера — {planet}\n\nЯкий це аспект?",
        reply_markup=aspect_types_kb(planet),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("asptype:"))
async def cb_aspect_type(callback: CallbackQuery):
    _, planet, aspect = callback.data.split(":")
    text = VENUS_ASPECTS[planet][aspect]
    result = f"⚡️ Венера {aspect} з {planet}\n\n{text}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Інший аспект", callback_data="aspects:start")
    kb.button(text="⬅️ У меню", callback_data="menu")
    kb.adjust(1)
    await callback.message.edit_text(result, reply_markup=kb.as_markup())
    await callback.answer()


# ---------- Запуск ----------


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("Бот запущено! Натисни Ctrl+C щоб зупинити.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
