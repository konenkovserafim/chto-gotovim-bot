import asyncio
import json
import logging
import os
import random
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway Variables.")

BASE_DIR = Path(__file__).parent
RECIPES_FILE = BASE_DIR / "recipes.json"
STATE_FILE = BASE_DIR / "state.json"

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


def load_recipes() -> dict[str, list[dict[str, Any]]]:
    with RECIPES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"favorites": {}, "shopping": {}}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("favorites", {})
        state.setdefault("shopping", {})
        return state
    except Exception:
        logging.exception("Failed to read state.json")
        return {"favorites": {}, "shopping": {}}


def save_state(state: dict[str, Any]) -> None:
    try:
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Failed to save state.json")


RECIPES = load_recipes()


def all_recipes() -> list[dict[str, Any]]:
    result = []
    for category, items in RECIPES.items():
        for item in items:
            item = dict(item)
            item["category"] = category
            result.append(item)
    return result


def find_recipe(recipe_id: str) -> dict[str, Any] | None:
    for recipe in all_recipes():
        if recipe["id"] == recipe_id:
            return recipe
    return None


def user_id(obj: Message | CallbackQuery) -> str:
    if isinstance(obj, CallbackQuery):
        return str(obj.from_user.id)
    return str(obj.from_user.id)


def category_keyboard(category: str) -> InlineKeyboardMarkup:
    rows = []
    for recipe in RECIPES.get(category, []):
        rows.append([InlineKeyboardButton(text=recipe["title"], callback_data=f"recipe:{recipe['id']}")])
    rows.append([InlineKeyboardButton(text="🎲 Случайное из раздела", callback_data=f"randomcat:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipe_keyboard(recipe_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❤️ В избранное", callback_data=f"fav:{recipe_id}")],
            [InlineKeyboardButton(text="🛒 В список продуктов", callback_data=f"shop:{recipe_id}")],
        ]
    )


def shopping_keyboard(items: list[str]) -> InlineKeyboardMarkup | None:
    rows = []
    for idx, item in enumerate(items):
        rows.append([InlineKeyboardButton(text=f"❌ {item}", callback_data=f"delshop:{idx}")])
    if items:
        rows.append([InlineKeyboardButton(text="🧹 Очистить список", callback_data="clearshop")])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def format_recipe(recipe: dict[str, Any]) -> str:
    ingredients = "\n".join(f"• {x}" for x in recipe.get("ingredients", []))
    steps = "\n".join(f"{i}. {x}" for i, x in enumerate(recipe.get("steps", []), start=1))
    return (
        f"{recipe['title']}\n\n"
        f"⏱ Время: {recipe.get('time', '—')}\n"
        f"🔥 Калорийность: {recipe.get('calories', '—')}\n\n"
        f"🛒 Ингредиенты:\n{ingredients}\n\n"
        f"👨‍🍳 Приготовление:\n{steps}"
    )


bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🍽 Привет! Я бот «Что готовим?»\n\n"
        "Помогу выбрать завтрак, обед, ужин или перекус для вас с Таней.",
        reply_markup=main_keyboard,
    )


@dp.message(F.text.in_(list(CATEGORY_BY_BUTTON.keys())))
async def show_category(message: Message):
    category = CATEGORY_BY_BUTTON[message.text]
    await message.answer(
        f"{CATEGORY_TITLES[category]}\n\nВыбери блюдо:",
        reply_markup=category_keyboard(category),
    )


@dp.message(F.text == "🎲 Что приготовить?")
async def random_any(message: Message):
    recipe = random.choice(all_recipes())
    await message.answer(format_recipe(recipe), reply_markup=recipe_keyboard(recipe["id"]))


@dp.message(F.text == "❤️ Избранное")
async def favorites(message: Message):
    state = load_state()
    ids = state["favorites"].get(user_id(message), [])
    if not ids:
        await message.answer("❤️ В избранном пока пусто.")
        return
    recipes = [find_recipe(rid) for rid in ids]
    recipes = [r for r in recipes if r]
    text = "❤️ Избранное:\n\n" + "\n".join(f"• {r['title']}" for r in recipes)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=r["title"], callback_data=f"recipe:{r['id']}")] for r in recipes]
        + [[InlineKeyboardButton(text="🧹 Очистить избранное", callback_data="clearfav")]]
    )
    await message.answer(text, reply_markup=keyboard)


@dp.message(F.text == "🛒 Список продуктов")
async def shopping(message: Message):
    state = load_state()
    items = state["shopping"].get(user_id(message), [])
    if not items:
        await message.answer("🛒 Список продуктов пока пуст.\n\nЧтобы добавить продукты, открой блюдо и нажми «В список продуктов».")
        return
    text = "🛒 Список продуктов:\n\n" + "\n".join(f"• {x}" for x in items)
    await message.answer(text, reply_markup=shopping_keyboard(items))


@dp.callback_query(F.data.startswith("recipe:"))
async def cb_recipe(callback: CallbackQuery):
    recipe_id = callback.data.split(":", 1)[1]
    recipe = find_recipe(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    await callback.message.answer(format_recipe(recipe), reply_markup=recipe_keyboard(recipe_id))
    await callback.answer()


@dp.callback_query(F.data.startswith("randomcat:"))
async def cb_random_category(callback: CallbackQuery):
    category = callback.data.split(":", 1)[1]
    recipe = random.choice(RECIPES.get(category, all_recipes()))
    await callback.message.answer(format_recipe(recipe), reply_markup=recipe_keyboard(recipe["id"]))
    await callback.answer()


@dp.callback_query(F.data.startswith("fav:"))
async def cb_fav(callback: CallbackQuery):
    recipe_id = callback.data.split(":", 1)[1]
    recipe = find_recipe(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    state = load_state()
    uid = user_id(callback)
    favs = state["favorites"].setdefault(uid, [])
    if recipe_id not in favs:
        favs.append(recipe_id)
        save_state(state)
        await callback.answer("Добавлено в избранное ❤️")
    else:
        await callback.answer("Уже есть в избранном ❤️")


@dp.callback_query(F.data == "clearfav")
async def cb_clear_fav(callback: CallbackQuery):
    state = load_state()
    state["favorites"][user_id(callback)] = []
    save_state(state)
    await callback.message.answer("❤️ Избранное очищено.")
    await callback.answer()


@dp.callback_query(F.data.startswith("shop:"))
async def cb_shop(callback: CallbackQuery):
    recipe_id = callback.data.split(":", 1)[1]
    recipe = find_recipe(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    state = load_state()
    uid = user_id(callback)
    shopping = state["shopping"].setdefault(uid, [])
    added = 0
    for item in recipe.get("ingredients", []):
        if item not in shopping:
            shopping.append(item)
            added += 1
    save_state(state)
    await callback.answer(f"Добавлено продуктов: {added} 🛒")


@dp.callback_query(F.data == "clearshop")
async def cb_clear_shop(callback: CallbackQuery):
    state = load_state()
    state["shopping"][user_id(callback)] = []
    save_state(state)
    await callback.message.answer("🛒 Список продуктов очищен.")
    await callback.answer()


@dp.callback_query(F.data.startswith("delshop:"))
async def cb_del_shop(callback: CallbackQuery):
    idx = int(callback.data.split(":", 1)[1])
    state = load_state()
    uid = user_id(callback)
    items = state["shopping"].setdefault(uid, [])
    if 0 <= idx < len(items):
        removed = items.pop(idx)
        save_state(state)
        await callback.message.answer(f"Удалено: {removed}")
    await callback.answer()


@dp.message()
async def fallback(message: Message):
    await message.answer("Выбери раздел кнопками ниже 👇", reply_markup=main_keyboard)


async def main():
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
