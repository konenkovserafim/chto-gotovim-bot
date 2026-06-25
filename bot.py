import asyncio
import json
import logging
import os
import random
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway Variables.")

RECIPES_PATH = Path("recipes.json")
DATA_PATH = Path("user_data.json")
PAGE_SIZE = 8

CATEGORY_TITLES = {
    "breakfast": "🍳 Завтрак",
    "lunch": "🍲 Обед",
    "dinner": "🍽 Ужин",
    "snack": "🥗 Перекус",
}
TEXT_TO_CATEGORY = {v: k for k, v in CATEGORY_TITLES.items()}

FRIDGE_PRODUCTS = [
    {"code": "chicken", "title": "🐔 Курица", "aliases": ["куриц", "филе", "голень", "бедро"]},
    {"code": "eggs", "title": "🥚 Яйца", "aliases": ["яйц", "омлет"]},
    {"code": "cheese", "title": "🧀 Сыр", "aliases": ["сыр"]},
    {"code": "cottage", "title": "🍚 Творог", "aliases": ["творог", "творож"]},
    {"code": "milk", "title": "🥛 Молоко", "aliases": ["молоко"]},
    {"code": "potato", "title": "🥔 Картофель", "aliases": ["картоф", "пюре"]},
    {"code": "rice", "title": "🍚 Рис", "aliases": ["рис"]},
    {"code": "buckwheat", "title": "🌾 Гречка", "aliases": ["греч"]},
    {"code": "pasta", "title": "🍝 Макароны", "aliases": ["макарон", "паста", "спагетти"]},
    {"code": "tomato", "title": "🍅 Помидоры", "aliases": ["помид", "томат"]},
    {"code": "cucumber", "title": "🥒 Огурцы", "aliases": ["огур"]},
    {"code": "onion", "title": "🧅 Лук", "aliases": ["лук"]},
    {"code": "carrot", "title": "🥕 Морковь", "aliases": ["морков"]},
    {"code": "fish", "title": "🐟 Рыба", "aliases": ["рыб", "минтай", "лосос", "треск"]},
    {"code": "mince", "title": "🥩 Фарш", "aliases": ["фарш"]},
    {"code": "bread", "title": "🍞 Хлеб", "aliases": ["хлеб", "тост", "лаваш"]},
    {"code": "sourcream", "title": "🥣 Сметана", "aliases": ["сметан"]},
]
FRIDGE_BY_CODE = {item["code"]: item for item in FRIDGE_PRODUCTS}


def load_recipes() -> list[dict[str, Any]]:
    with RECIPES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


RECIPES = load_recipes()
RECIPES_BY_ID = {int(r["id"]): r for r in RECIPES}


def load_data() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {}
    try:
        with DATA_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Failed to load user_data.json")
        return {}


def save_data(data: dict[str, Any]) -> None:
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data: dict[str, Any], user_id: int) -> dict[str, Any]:
    key = str(user_id)
    if key not in data:
        data[key] = {"favorites": [], "shopping": [], "fridge": []}
    data[key].setdefault("favorites", [])
    data[key].setdefault("shopping", [])
    data[key].setdefault("fridge", [])
    return data[key]


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍳 Завтрак"), KeyboardButton(text="🍲 Обед")],
            [KeyboardButton(text="🍽 Ужин"), KeyboardButton(text="🥗 Перекус")],
            [KeyboardButton(text="🎲 Что приготовить?")],
            [KeyboardButton(text="❤️ Избранное"), KeyboardButton(text="🛒 Список продуктов")],
            [KeyboardButton(text="🥶 Холодильник")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери раздел",
    )


def recipes_for_category(category: str) -> list[dict[str, Any]]:
    return [r for r in RECIPES if r.get("category") == category]


def recipe_list_keyboard(category: str, page: int = 0) -> InlineKeyboardMarkup:
    items = recipes_for_category(category)
    start = page * PAGE_SIZE
    chunk = items[start:start + PAGE_SIZE]
    rows = [
        [InlineKeyboardButton(text=f"{r['name']}", callback_data=f"recipe:{r['id']}:{category}:{page}")]
        for r in chunk
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{category}:{page-1}"))
    if start + PAGE_SIZE < len(items):
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"cat:{category}:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🎲 Случайное из раздела", callback_data=f"randomcat:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipe_actions_keyboard(recipe_id: int, category: str | None = None, page: int = 0) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="❤️ В избранное", callback_data=f"fav:{recipe_id}"),
            InlineKeyboardButton(text="🛒 В список", callback_data=f"shop:{recipe_id}"),
        ]
    ]
    if category:
        rows.append([InlineKeyboardButton(text="⬅️ К списку", callback_data=f"cat:{category}:{page}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def favorites_keyboard(fav_ids: list[int]) -> InlineKeyboardMarkup:
    rows = []
    for recipe_id in fav_ids:
        recipe = RECIPES_BY_ID.get(recipe_id)
        if recipe:
            rows.append([InlineKeyboardButton(text=recipe["name"], callback_data=f"favrecipe:{recipe_id}")])
    rows.append([InlineKeyboardButton(text="🧹 Очистить избранное", callback_data="clear:favorites")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clear_keyboard(kind: str) -> InlineKeyboardMarkup:
    if kind == "favorites":
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧹 Очистить избранное", callback_data="clear:favorites")]])
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧹 Очистить список", callback_data="clear:shopping")]])




def fridge_keyboard(selected_codes: list[str]) -> InlineKeyboardMarkup:
    selected = set(selected_codes)
    rows = []
    row = []
    for product in FRIDGE_PRODUCTS:
        mark = "✅ " if product["code"] in selected else ""
        row.append(InlineKeyboardButton(text=f"{mark}{product['title']}", callback_data=f"fridge:toggle:{product['code']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔎 Найти блюда", callback_data="fridge:find")])
    rows.append([InlineKeyboardButton(text="🧹 Очистить холодильник", callback_data="fridge:clear")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_fridge(selected_codes: list[str]) -> str:
    if not selected_codes:
        selected_text = "пока ничего не выбрано"
    else:
        selected_text = ", ".join(FRIDGE_BY_CODE[code]["title"] for code in selected_codes if code in FRIDGE_BY_CODE)
    return (
        "🥶 <b>Холодильник</b>\n\n"
        "Отметь продукты, которые есть дома. Потом нажми <b>Найти блюда</b>.\n\n"
        f"Сейчас выбрано: {selected_text}"
    )


def recipe_text_for_match(recipe: dict[str, Any]) -> str:
    parts = [recipe.get("name", ""), " ".join(recipe.get("ingredients", [])), " ".join(recipe.get("tags", []))]
    return " ".join(parts).lower()


def find_recipes_by_fridge(selected_codes: list[str]) -> list[tuple[dict[str, Any], int]]:
    if not selected_codes:
        return []
    selected_products = [FRIDGE_BY_CODE[code] for code in selected_codes if code in FRIDGE_BY_CODE]
    results = []
    for recipe in RECIPES:
        text = recipe_text_for_match(recipe)
        score = 0
        for product in selected_products:
            if any(alias in text for alias in product["aliases"]):
                score += 1
        if score > 0:
            results.append((recipe, score))
    results.sort(key=lambda pair: (pair[1], -int(pair[0].get("time", 999))), reverse=True)
    return results


def fridge_results_keyboard(results: list[tuple[dict[str, Any], int]], selected_codes: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for recipe, score in results[:12]:
        rows.append([InlineKeyboardButton(text=f"{recipe['name']} · совпадений: {score}", callback_data=f"recipe:{recipe['id']}:{recipe.get('category', 'lunch')}:0")])
    rows.append([InlineKeyboardButton(text="⬅️ К холодильнику", callback_data="fridge:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_recipe(r: dict[str, Any]) -> str:
    ingredients = "\n".join(f"• {item}" for item in r.get("ingredients", []))
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(r.get("steps", []), 1))
    tags = ", ".join(r.get("tags", []))

    return (
        f"🍽 <b>{r['name']}</b>\n\n"
        f"⏱ Время: {r.get('time', '—')} мин\n"
        f"🔥 Калорийность на двоих: ~{r.get('calories', '—')} ккал\n"
        f"💰 Примерно: ~{r.get('price', '—')} ₽\n"
        f"🍳 Сложность: {r.get('difficulty', 'Легко')}\n\n"
        f"🛒 <b>Ингредиенты</b>\n{ingredients}\n\n"
        f"👨‍🍳 <b>Приготовление</b>\n{steps}\n\n"
        f"🏷 {tags}"
    )


def format_category(category: str, page: int = 0) -> str:
    total = len(recipes_for_category(category))
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return f"{CATEGORY_TITLES[category]}\n\nВыбери блюдо.\nСтраница {page + 1}/{pages}. Всего рецептов: {total}."


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🍽 <b>Привет! Я бот «Что готовим?»</b>\n\n"
        "Помогу выбрать завтрак, обед, ужин или перекус для вас с Таней.\n\n"
        f"Сейчас в базе: <b>{len(RECIPES)} рецептов</b>.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text.in_(list(TEXT_TO_CATEGORY.keys())))
async def category_from_keyboard(message: Message):
    category = TEXT_TO_CATEGORY[message.text]
    await message.answer(format_category(category, 0), reply_markup=recipe_list_keyboard(category, 0))


@dp.message(F.text == "🎲 Что приготовить?")
async def random_recipe_message(message: Message):
    recipe = random.choice(RECIPES)
    await message.answer(format_recipe(recipe), reply_markup=recipe_actions_keyboard(recipe["id"], recipe.get("category")), parse_mode="HTML")


@dp.message(F.text == "❤️ Избранное")
async def favorites_message(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    fav_ids = [int(x) for x in user.get("favorites", []) if int(x) in RECIPES_BY_ID]
    if not fav_ids:
        await message.answer("❤️ В избранном пока пусто.")
        return
    await message.answer(
        "❤️ <b>Избранное</b>\n\nВыбери блюдо, чтобы открыть полную карточку.",
        reply_markup=favorites_keyboard(fav_ids),
        parse_mode="HTML",
    )


@dp.message(F.text == "🛒 Список продуктов")
async def shopping_message(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    items = user.get("shopping", [])
    if not items:
        await message.answer("🛒 Список продуктов пока пуст.")
        return
    lines = ["🛒 <b>Список продуктов</b>", ""]
    for item in items:
        lines.append(f"• {item}")
    await message.answer("\n".join(lines), reply_markup=clear_keyboard("shopping"), parse_mode="HTML")




@dp.message(F.text == "🥶 Холодильник")
async def fridge_message(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    selected = user.get("fridge", [])
    await message.answer(format_fridge(selected), reply_markup=fridge_keyboard(selected), parse_mode="HTML")




@dp.callback_query(F.data.startswith("fridge:"))
async def fridge_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    data = load_data()
    user = get_user(data, callback.from_user.id)
    selected = user.get("fridge", [])

    if action == "toggle":
        code = parts[2]
        if code in selected:
            selected.remove(code)
        else:
            selected.append(code)
        user["fridge"] = selected
        save_data(data)
        await callback.message.edit_text(format_fridge(selected), reply_markup=fridge_keyboard(selected), parse_mode="HTML")
        await callback.answer()
        return

    if action == "clear":
        user["fridge"] = []
        save_data(data)
        await callback.message.edit_text(format_fridge([]), reply_markup=fridge_keyboard([]), parse_mode="HTML")
        await callback.answer("Холодильник очищен")
        return

    if action == "back":
        await callback.message.edit_text(format_fridge(selected), reply_markup=fridge_keyboard(selected), parse_mode="HTML")
        await callback.answer()
        return

    if action == "find":
        results = find_recipes_by_fridge(selected)
        if not selected:
            await callback.answer("Сначала выбери продукты", show_alert=True)
            return
        if not results:
            await callback.message.edit_text(
                "🥶 <b>Холодильник</b>\n\nПо выбранным продуктам ничего не нашёл. Попробуй выбрать больше продуктов.",
                reply_markup=fridge_keyboard(selected),
                parse_mode="HTML",
            )
            await callback.answer()
            return
        selected_text = ", ".join(FRIDGE_BY_CODE[code]["title"] for code in selected if code in FRIDGE_BY_CODE)
        text = (
            "🥶 <b>Что можно приготовить?</b>\n\n"
            f"Выбрано: {selected_text}\n\n"
            f"Нашёл вариантов: <b>{len(results)}</b>. Показываю самые подходящие:"
        )
        await callback.message.edit_text(text, reply_markup=fridge_results_keyboard(results, selected), parse_mode="HTML")
        await callback.answer()
        return


@dp.callback_query(F.data.startswith("favrecipe:"))
async def favorite_recipe_callback(callback: CallbackQuery):
    recipe_id = int(callback.data.split(":")[1])
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_recipe(recipe),
        reply_markup=recipe_actions_keyboard(recipe_id, recipe.get("category"), 0),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def category_callback(callback: CallbackQuery):
    _, category, page_s = callback.data.split(":")
    page = int(page_s)
    await callback.message.edit_text(format_category(category, page), reply_markup=recipe_list_keyboard(category, page))
    await callback.answer()


@dp.callback_query(F.data.startswith("recipe:"))
async def recipe_callback(callback: CallbackQuery):
    _, recipe_id_s, category, page_s = callback.data.split(":")
    recipe_id = int(recipe_id_s)
    page = int(page_s)
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_recipe(recipe),
        reply_markup=recipe_actions_keyboard(recipe_id, category, page),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("randomcat:"))
async def random_category_callback(callback: CallbackQuery):
    category = callback.data.split(":")[1]
    recipe = random.choice(recipes_for_category(category))
    await callback.message.edit_text(
        format_recipe(recipe),
        reply_markup=recipe_actions_keyboard(recipe["id"], category, 0),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("fav:"))
async def add_favorite(callback: CallbackQuery):
    recipe_id = int(callback.data.split(":")[1])
    data = load_data()
    user = get_user(data, callback.from_user.id)
    if recipe_id not in user["favorites"]:
        user["favorites"].append(recipe_id)
        save_data(data)
        await callback.answer("Добавлено в избранное ❤️")
    else:
        await callback.answer("Уже есть в избранном ❤️")


@dp.callback_query(F.data.startswith("shop:"))
async def add_shopping(callback: CallbackQuery):
    recipe_id = int(callback.data.split(":")[1])
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    data = load_data()
    user = get_user(data, callback.from_user.id)
    added = 0
    for item in recipe.get("ingredients", []):
        if item not in user["shopping"]:
            user["shopping"].append(item)
            added += 1
    save_data(data)
    await callback.answer(f"Добавлено продуктов: {added} 🛒")


@dp.callback_query(F.data.startswith("clear:"))
async def clear_callback(callback: CallbackQuery):
    kind = callback.data.split(":")[1]
    data = load_data()
    user = get_user(data, callback.from_user.id)
    if kind == "favorites":
        user["favorites"] = []
        save_data(data)
        await callback.message.edit_text("❤️ Избранное очищено.")
    elif kind == "shopping":
        user["shopping"] = []
        save_data(data)
        await callback.message.edit_text("🛒 Список продуктов очищен.")
    await callback.answer()


@dp.message()
async def fallback(message: Message):
    await message.answer("Выбери раздел на клавиатуре 👇", reply_markup=main_keyboard())


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    logger.info("Bot started. Recipes loaded: %s", len(RECIPES))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
