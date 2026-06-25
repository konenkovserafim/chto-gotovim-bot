import asyncio
import json
import logging
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_DIR = Path(__file__).resolve().parent
RECIPES_PATH = BASE_DIR / "recipes.json"
USER_DATA_PATH = BASE_DIR / "user_data.json"

CATEGORY_TITLES = {
    "breakfast": "🔍 Завтрак",
    "lunch": "🍲 Обед",
    "dinner": "🍽 Ужин",
    "snack": "🥗 Перекус",
}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Завтрак"), KeyboardButton(text="🍲 Обед")],
        [KeyboardButton(text="🍽 Ужин"), KeyboardButton(text="🥗 Перекус")],
        [KeyboardButton(text="🎲 Что приготовить?")],
        [KeyboardButton(text="❤️ Избранное"), KeyboardButton(text="🛒 Список продуктов")],
    ],
    resize_keyboard=True,
)


def load_recipes() -> dict:
    with RECIPES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_user_data() -> dict:
    if not USER_DATA_PATH.exists():
        return {"favorites": {}, "shopping": {}}
    try:
        with USER_DATA_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        data.setdefault("favorites", {})
        data.setdefault("shopping", {})
        return data
    except Exception:
        logger.exception("Cannot load user_data.json")
        return {"favorites": {}, "shopping": {}}


def save_user_data(data: dict) -> None:
    try:
        with USER_DATA_PATH.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Cannot save user_data.json")


RECIPES = load_recipes()
USER_DATA = load_user_data()


def all_recipes() -> list[dict]:
    result = []
    for items in RECIPES.values():
        result.extend(items)
    return result


def find_recipe(recipe_id: str) -> dict | None:
    for recipe in all_recipes():
        if recipe.get("id") == recipe_id:
            return recipe
    return None


def format_recipe(recipe: dict) -> str:
    ingredients = "\n".join(f"• {item}" for item in recipe.get("ingredients", []))
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(recipe.get("steps", []), start=1))
    portions = "\n".join(f"• {item}" for item in recipe.get("portions", []))

    return (
        f"{recipe['title']}\n\n"
        f"⏱ Время: {recipe.get('time', '—')}\n"
        f"💰 Стоимость: {recipe.get('price', '—')}\n"
        f"🔥 Калорийность: {recipe.get('calories', '—')}\n\n"
        f"🛒 Ингредиенты:\n{ingredients}\n\n"
        f"👨‍🍳 Приготовление:\n{steps}\n\n"
        f"🍽 Порции:\n{portions}"
    )


def recipe_actions(recipe_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❤️ В избранное", callback_data=f"fav:{recipe_id}")],
            [InlineKeyboardButton(text="🛒 В список продуктов", callback_data=f"shop:{recipe_id}")],
        ]
    )


def recipe_list_keyboard(category: str) -> InlineKeyboardMarkup:
    rows = []
    for recipe in RECIPES.get(category, []):
        rows.append([InlineKeyboardButton(text=recipe["title"], callback_data=f"recipe:{recipe['id']}")])
    rows.append([InlineKeyboardButton(text="🎲 Случайное блюдо", callback_data=f"random:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_by_button(text: str) -> str | None:
    mapping = {
        "🔍 Завтрак": "breakfast",
        "🍲 Обед": "lunch",
        "🍽 Ужин": "dinner",
        "🥗 Перекус": "snack",
    }
    return mapping.get(text)


async def show_main(message: Message) -> None:
    await message.answer(
        "🍽 Привет! Я бот «Что готовим?»\n\n"
        "Помогу выбрать завтрак, обед, ужин или перекус для вас с Таней.",
        reply_markup=MAIN_KEYBOARD,
    )


dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await show_main(message)


@dp.message(F.text.in_(list(CATEGORY_TITLES.values())))
async def category_handler(message: Message) -> None:
    category = category_by_button(message.text)
    if not category:
        await show_main(message)
        return
    await message.answer(
        f"{CATEGORY_TITLES[category]}\n\nВыбери блюдо:",
        reply_markup=recipe_list_keyboard(category),
    )


@dp.message(F.text == "🎲 Что приготовить?")
async def random_handler(message: Message) -> None:
    recipe = random.choice(all_recipes())
    await message.answer(format_recipe(recipe), reply_markup=recipe_actions(recipe["id"]))


@dp.message(F.text == "❤️ Избранное")
async def favorites_handler(message: Message) -> None:
    user_id = str(message.from_user.id)
    favorite_ids = USER_DATA.get("favorites", {}).get(user_id, [])
    if not favorite_ids:
        await message.answer("❤️ В избранном пока пусто.", reply_markup=MAIN_KEYBOARD)
        return
    lines = ["❤️ Избранное:"]
    for recipe_id in favorite_ids:
        recipe = find_recipe(recipe_id)
        if recipe:
            lines.append(f"• {recipe['title']}")
    await message.answer("\n".join(lines), reply_markup=MAIN_KEYBOARD)


@dp.message(F.text == "🛒 Список продуктов")
async def shopping_handler(message: Message) -> None:
    user_id = str(message.from_user.id)
    products = USER_DATA.get("shopping", {}).get(user_id, [])
    if not products:
        await message.answer("🛒 Список продуктов пуст.", reply_markup=MAIN_KEYBOARD)
        return
    unique_products = []
    for item in products:
        if item not in unique_products:
            unique_products.append(item)
    text = "🛒 Список продуктов:\n" + "\n".join(f"• {item}" for item in unique_products)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧹 Очистить список", callback_data="clear_shop")]])
    await message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("recipe:"))
async def recipe_callback(callback: CallbackQuery) -> None:
    recipe_id = callback.data.split(":", 1)[1]
    recipe = find_recipe(recipe_id)
    if not recipe:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    await callback.message.answer(format_recipe(recipe), reply_markup=recipe_actions(recipe_id))
    await callback.answer()


@dp.callback_query(F.data.startswith("random:"))
async def random_category_callback(callback: CallbackQuery) -> None:
    category = callback.data.split(":", 1)[1]
    recipe = random.choice(RECIPES.get(category, all_recipes()))
    await callback.message.answer(format_recipe(recipe), reply_markup=recipe_actions(recipe["id"]))
    await callback.answer()


@dp.callback_query(F.data.startswith("fav:"))
async def add_favorite_callback(callback: CallbackQuery) -> None:
    recipe_id = callback.data.split(":", 1)[1]
    user_id = str(callback.from_user.id)
    USER_DATA.setdefault("favorites", {}).setdefault(user_id, [])
    if recipe_id not in USER_DATA["favorites"][user_id]:
        USER_DATA["favorites"][user_id].append(recipe_id)
        save_user_data(USER_DATA)
    await callback.answer("Добавлено в избранное ❤️")


@dp.callback_query(F.data.startswith("shop:"))
async def add_shopping_callback(callback: CallbackQuery) -> None:
    recipe_id = callback.data.split(":", 1)[1]
    recipe = find_recipe(recipe_id)
    if not recipe:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    user_id = str(callback.from_user.id)
    USER_DATA.setdefault("shopping", {}).setdefault(user_id, [])
    USER_DATA["shopping"][user_id].extend(recipe.get("ingredients", []))
    save_user_data(USER_DATA)
    await callback.answer("Ингредиенты добавлены в список 🛒")


@dp.callback_query(F.data == "clear_shop")
async def clear_shopping_callback(callback: CallbackQuery) -> None:
    user_id = str(callback.from_user.id)
    USER_DATA.setdefault("shopping", {})[user_id] = []
    save_user_data(USER_DATA)
    await callback.message.answer("🛒 Список продуктов очищен.", reply_markup=MAIN_KEYBOARD)
    await callback.answer()


@dp.message()
async def fallback_handler(message: Message) -> None:
    await message.answer("Выбери действие на клавиатуре 👇", reply_markup=MAIN_KEYBOARD)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Add it in Railway Variables.")
    bot = Bot(token=BOT_TOKEN)
    logger.info("Bot started")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
