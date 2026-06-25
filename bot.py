import asyncio
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Any, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = Path("recipes.json")

CATEGORY_TITLES = {
    "breakfast": "🍳 Завтрак",
    "lunch": "🍲 Обед",
    "dinner": "🍽 Ужин",
    "snack": "🥗 Перекус",
}

CATEGORY_BY_BUTTON = {v: k for k, v in CATEGORY_TITLES.items()}

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍳 Завтрак"), KeyboardButton(text="🍲 Обед")],
        [KeyboardButton(text="🍽 Ужин"), KeyboardButton(text="🥗 Перекус")],
        [KeyboardButton(text="🎲 Что приготовить?")],
        [KeyboardButton(text="❤️ Избранное"), KeyboardButton(text="🛒 Список продуктов")],
    ],
    resize_keyboard=True,
)

user_favorites: Dict[int, set] = {}
user_shopping: Dict[int, List[str]] = {}

def load_recipes() -> List[Dict[str, Any]]:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

RECIPES = load_recipes()
RECIPES_BY_ID = {r["id"]: r for r in RECIPES}


def recipes_by_category(category: str) -> List[Dict[str, Any]]:
    return [r for r in RECIPES if r.get("category") == category]


def recipe_card(recipe: Dict[str, Any]) -> str:
    ingredients = "\n".join(f"• {item}" for item in recipe["ingredients"])
    steps = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(recipe["steps"]))
    portions = recipe.get("portions", "Серафиму — порция побольше, Тане — чуть легче.")
    return (
        f"{recipe['emoji']} <b>{recipe['title']}</b>\n\n"
        f"⏱ Время: {recipe['time']}\n"
        f"🔥 Примерно: {recipe['calories']}\n"
        f"💰 Стоимость: {recipe.get('price', 'примерно')}\n\n"
        f"👫 <b>Порции</b>\n{portions}\n\n"
        f"🛒 <b>Ингредиенты на двоих</b>\n{ingredients}\n\n"
        f"👨‍🍳 <b>Рецепт</b>\n{steps}"
    )


def category_keyboard(category: str) -> InlineKeyboardMarkup:
    rows = []
    for recipe in recipes_by_category(category):
        rows.append([InlineKeyboardButton(text=f"{recipe['emoji']} {recipe['title']}", callback_data=f"recipe:{recipe['id']}")])
    rows.append([InlineKeyboardButton(text="🎲 Случайное из раздела", callback_data=f"random_category:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipe_actions(recipe_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❤️ В избранное", callback_data=f"fav:{recipe_id}")],
            [InlineKeyboardButton(text="🛒 В список продуктов", callback_data=f"shop:{recipe_id}")],
        ]
    )


def find_random_recipe(category: Optional[str] = None) -> Dict[str, Any]:
    pool = recipes_by_category(category) if category else RECIPES
    return random.choice(pool)


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Привет! Это бот <b>«Что готовим?»</b>\n\n"
        "Выбирай раздел — я покажу блюда и рецепты для вас с Таней.",
        reply_markup=main_keyboard,
        parse_mode="HTML",
    )


@dp.message(F.text.in_(CATEGORY_BY_BUTTON.keys()))
async def show_category(message: Message):
    category = CATEGORY_BY_BUTTON[message.text]
    count = len(recipes_by_category(category))
    await message.answer(
        f"{message.text}\n\nВыбери блюдо. Сейчас в разделе: {count} рецептов.",
        reply_markup=category_keyboard(category),
    )


@dp.message(F.text == "🎲 Что приготовить?")
async def random_any(message: Message):
    recipe = find_random_recipe()
    await message.answer(recipe_card(recipe), reply_markup=recipe_actions(recipe["id"]), parse_mode="HTML")


@dp.message(F.text == "❤️ Избранное")
async def favorites(message: Message):
    favs = user_favorites.get(message.from_user.id, set())
    if not favs:
        await message.answer("❤️ В избранном пока пусто. Открой блюдо и нажми «В избранное».")
        return
    lines = ["❤️ <b>Избранное</b>\n"]
    for recipe_id in favs:
        recipe = RECIPES_BY_ID.get(recipe_id)
        if recipe:
            lines.append(f"• {recipe['emoji']} {recipe['title']}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "🛒 Список продуктов")
async def shopping_list(message: Message):
    items = user_shopping.get(message.from_user.id, [])
    if not items:
        await message.answer("🛒 Список продуктов пока пуст. Открой блюдо и нажми «В список продуктов».")
        return
    unique_items = []
    for item in items:
        if item not in unique_items:
            unique_items.append(item)
    text = "🛒 <b>Список продуктов</b>\n\n" + "\n".join(f"• {item}" for item in unique_items)
    await message.answer(text, parse_mode="HTML")


@dp.callback_query(F.data.startswith("recipe:"))
async def show_recipe(callback: CallbackQuery):
    recipe_id = callback.data.split(":", 1)[1]
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден")
        return
    await callback.message.answer(recipe_card(recipe), reply_markup=recipe_actions(recipe_id), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("random_category:"))
async def random_category(callback: CallbackQuery):
    category = callback.data.split(":", 1)[1]
    recipe = find_random_recipe(category)
    await callback.message.answer(recipe_card(recipe), reply_markup=recipe_actions(recipe["id"]), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("fav:"))
async def add_favorite(callback: CallbackQuery):
    recipe_id = callback.data.split(":", 1)[1]
    user_favorites.setdefault(callback.from_user.id, set()).add(recipe_id)
    await callback.answer("Добавлено в избранное ❤️")


@dp.callback_query(F.data.startswith("shop:"))
async def add_shopping(callback: CallbackQuery):
    recipe_id = callback.data.split(":", 1)[1]
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден")
        return
    user_shopping.setdefault(callback.from_user.id, []).extend(recipe["ingredients"])
    await callback.answer("Добавлено в список продуктов 🛒")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
