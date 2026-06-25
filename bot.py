import asyncio
import json
import logging
import os
import random
import sqlite3
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
DB_PATH = Path("bot_data.db")
PAGE_SIZE = 8

CATEGORY_TITLES = {
    "breakfast": "🍳 Завтрак",
    "lunch": "🍲 Обед",
    "dinner": "🍽 Ужин",
    "snack": "🥗 Перекус",
}
TEXT_TO_CATEGORY = {v: k for k, v in CATEGORY_TITLES.items()}

FRIDGE_CATEGORIES = {
    "meat": {"title": "🥩 Мясо", "products": [
        {"code": "chicken", "title": "🐔 Курица", "aliases": ["куриц", "филе", "голень", "бедро"]},
        {"code": "turkey", "title": "🦃 Индейка", "aliases": ["индейк"]},
        {"code": "beef", "title": "🥩 Говядина", "aliases": ["говядин", "говяж"]},
        {"code": "pork", "title": "🥓 Свинина", "aliases": ["свинин", "свин"]},
        {"code": "mince", "title": "🥩 Фарш", "aliases": ["фарш"]},
        {"code": "sausage", "title": "🌭 Сосиски", "aliases": ["сосиск", "колбас"]},
        {"code": "ham", "title": "🥓 Ветчина", "aliases": ["ветчин"]},
    ]},
    "fish": {"title": "🐟 Рыба и морепродукты", "products": [
        {"code": "fish", "title": "🐟 Рыба", "aliases": ["рыб", "минтай", "треск", "хек"]},
        {"code": "salmon", "title": "🍣 Красная рыба", "aliases": ["лосос", "семг", "форел", "красная рыба"]},
        {"code": "tuna", "title": "🥫 Тунец", "aliases": ["тунец"]},
        {"code": "shrimp", "title": "🦐 Креветки", "aliases": ["кревет"]},
        {"code": "canned_fish", "title": "🥫 Рыбные консервы", "aliases": ["консервы", "сайра", "сардин"]},
    ]},
    "dairy": {"title": "🥚 Молочка и яйца", "products": [
        {"code": "eggs", "title": "🥚 Яйца", "aliases": ["яйц", "омлет", "яичниц"]},
        {"code": "cheese", "title": "🧀 Сыр", "aliases": ["сыр"]},
        {"code": "cottage", "title": "🍚 Творог", "aliases": ["творог", "творож"]},
        {"code": "milk", "title": "🥛 Молоко", "aliases": ["молоко"]},
        {"code": "kefir", "title": "🥛 Кефир", "aliases": ["кефир"]},
        {"code": "yogurt", "title": "🥛 Йогурт", "aliases": ["йогурт"]},
        {"code": "sourcream", "title": "🥣 Сметана", "aliases": ["сметан"]},
        {"code": "cream", "title": "🥛 Сливки", "aliases": ["сливк"]},
        {"code": "butter", "title": "🧈 Сливочное масло", "aliases": ["сливочное масло", "масло слив"]},
    ]},
    "grains": {"title": "🌾 Крупы и гарниры", "products": [
        {"code": "rice", "title": "🍚 Рис", "aliases": ["рис"]},
        {"code": "buckwheat", "title": "🌾 Гречка", "aliases": ["греч"]},
        {"code": "pasta", "title": "🍝 Макароны", "aliases": ["макарон", "паста", "спагетти", "лапша"]},
        {"code": "oatmeal", "title": "🥣 Овсянка", "aliases": ["овсян", "хлопья"]},
        {"code": "millet", "title": "🌾 Пшено", "aliases": ["пшено", "пшенн"]},
        {"code": "semolina", "title": "🥣 Манка", "aliases": ["манк", "манная"]},
        {"code": "bulgur", "title": "🌾 Булгур", "aliases": ["булгур"]},
        {"code": "flour", "title": "🌾 Мука", "aliases": ["мука", "муки"]},
        {"code": "bread", "title": "🍞 Хлеб/лаваш", "aliases": ["хлеб", "тост", "лаваш"]},
    ]},
    "vegetables": {"title": "🥬 Овощи", "products": [
        {"code": "potato", "title": "🥔 Картофель", "aliases": ["картоф", "пюре"]},
        {"code": "tomato", "title": "🍅 Помидоры", "aliases": ["помид", "томат"]},
        {"code": "cucumber", "title": "🥒 Огурцы", "aliases": ["огур"]},
        {"code": "onion", "title": "🧅 Лук", "aliases": ["лук", "луков"]},
        {"code": "carrot", "title": "🥕 Морковь", "aliases": ["морков"]},
        {"code": "cabbage", "title": "🥬 Капуста", "aliases": ["капуст"]},
        {"code": "beet", "title": "🟣 Свёкла", "aliases": ["свек", "свёк"]},
        {"code": "pepper", "title": "🫑 Перец", "aliases": ["перец", "болгар"]},
        {"code": "zucchini", "title": "🥒 Кабачок", "aliases": ["кабач"]},
        {"code": "eggplant", "title": "🍆 Баклажан", "aliases": ["баклаж"]},
        {"code": "mushrooms", "title": "🍄 Грибы", "aliases": ["гриб", "шампин"]},
        {"code": "broccoli", "title": "🥦 Брокколи", "aliases": ["брокк"]},
        {"code": "garlic", "title": "🧄 Чеснок", "aliases": ["чеснок"]},
        {"code": "greens", "title": "🌿 Зелень", "aliases": ["зелень", "укроп", "петруш", "кинз"]},
    ]},
    "fruits": {"title": "🍎 Фрукты и ягоды", "products": [
        {"code": "apple", "title": "🍎 Яблоки", "aliases": ["яблок"]},
        {"code": "banana", "title": "🍌 Бананы", "aliases": ["банан"]},
        {"code": "orange", "title": "🍊 Апельсины", "aliases": ["апельсин"]},
        {"code": "lemon", "title": "🍋 Лимон", "aliases": ["лимон"]},
        {"code": "berries", "title": "🫐 Ягоды", "aliases": ["ягод", "клубник", "черник", "малин"]},
        {"code": "pear", "title": "🍐 Груши", "aliases": ["груш"]},
    ]},
    "other": {"title": "🥫 Прочее", "products": [
        {"code": "beans", "title": "🫘 Фасоль", "aliases": ["фасол"]},
        {"code": "peas", "title": "🟢 Горошек", "aliases": ["горош"]},
        {"code": "corn", "title": "🌽 Кукуруза", "aliases": ["кукуруз"]},
        {"code": "tomato_paste", "title": "🥫 Томатная паста", "aliases": ["томатная паста"]},
        {"code": "honey", "title": "🍯 Мёд", "aliases": ["мёд", "мед"]},
        {"code": "nuts", "title": "🥜 Орехи", "aliases": ["орех"]},
        {"code": "oil", "title": "🛢 Растительное масло", "aliases": ["растительное масло", "масло"]},
        {"code": "soy_sauce", "title": "🥫 Соевый соус", "aliases": ["соевый"]},
        {"code": "mayo", "title": "🥫 Майонез", "aliases": ["майонез"]},
    ]},
}

FRIDGE_PRODUCTS = [product for group in FRIDGE_CATEGORIES.values() for product in group["products"]]
FRIDGE_BY_CODE = {item["code"]: item for item in FRIDGE_PRODUCTS}



def load_recipes_from_json() -> list[dict[str, Any]]:
    with RECIPES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    recipes = load_recipes_from_json()
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                time INTEGER,
                difficulty TEXT,
                price INTEGER,
                calories INTEGER,
                ingredients_json TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                tags_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, recipe_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping_items (
                user_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                PRIMARY KEY (user_id, item)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fridge_items (
                user_id INTEGER NOT NULL,
                product_code TEXT NOT NULL,
                PRIMARY KEY (user_id, product_code)
            )
        """)
        for recipe in recipes:
            conn.execute(
                """
                INSERT OR REPLACE INTO recipes
                (id, category, name, time, difficulty, price, calories, ingredients_json, steps_json, tags_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(recipe["id"]),
                    recipe.get("category", "lunch"),
                    recipe.get("name", "Без названия"),
                    int(recipe.get("time", 0) or 0),
                    recipe.get("difficulty", "Легко"),
                    int(recipe.get("price", 0) or 0),
                    int(recipe.get("calories", 0) or 0),
                    json.dumps(recipe.get("ingredients", []), ensure_ascii=False),
                    json.dumps(recipe.get("steps", []), ensure_ascii=False),
                    json.dumps(recipe.get("tags", []), ensure_ascii=False),
                ),
            )
        conn.commit()


def row_to_recipe(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "category": row["category"],
        "name": row["name"],
        "time": row["time"],
        "difficulty": row["difficulty"],
        "price": row["price"],
        "calories": row["calories"],
        "ingredients": json.loads(row["ingredients_json"]),
        "steps": json.loads(row["steps_json"]),
        "tags": json.loads(row["tags_json"]),
    }


def get_all_recipes() -> list[dict[str, Any]]:
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
    return [row_to_recipe(row) for row in rows]


def get_recipe_by_id(recipe_id: int) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    return row_to_recipe(row) if row else None


def get_favorites(user_id: int) -> list[int]:
    with db_connect() as conn:
        rows = conn.execute("SELECT recipe_id FROM favorites WHERE user_id = ? ORDER BY recipe_id", (user_id,)).fetchall()
    return [int(row["recipe_id"]) for row in rows]


def add_favorite_db(user_id: int, recipe_id: int) -> bool:
    with db_connect() as conn:
        cur = conn.execute("INSERT OR IGNORE INTO favorites (user_id, recipe_id) VALUES (?, ?)", (user_id, recipe_id))
        conn.commit()
        return cur.rowcount > 0


def clear_favorites_db(user_id: int) -> None:
    with db_connect() as conn:
        conn.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
        conn.commit()


def get_shopping_items(user_id: int) -> list[str]:
    with db_connect() as conn:
        rows = conn.execute("SELECT item FROM shopping_items WHERE user_id = ? ORDER BY item", (user_id,)).fetchall()
    return [row["item"] for row in rows]


def add_shopping_item_db(user_id: int, item: str) -> bool:
    with db_connect() as conn:
        cur = conn.execute("INSERT OR IGNORE INTO shopping_items (user_id, item) VALUES (?, ?)", (user_id, item))
        conn.commit()
        return cur.rowcount > 0


def clear_shopping_db(user_id: int) -> None:
    with db_connect() as conn:
        conn.execute("DELETE FROM shopping_items WHERE user_id = ?", (user_id,))
        conn.commit()


def get_fridge_items(user_id: int) -> list[str]:
    with db_connect() as conn:
        rows = conn.execute("SELECT product_code FROM fridge_items WHERE user_id = ? ORDER BY product_code", (user_id,)).fetchall()
    return [row["product_code"] for row in rows]


def toggle_fridge_item_db(user_id: int, product_code: str) -> list[str]:
    selected = set(get_fridge_items(user_id))
    with db_connect() as conn:
        if product_code in selected:
            conn.execute("DELETE FROM fridge_items WHERE user_id = ? AND product_code = ?", (user_id, product_code))
        else:
            conn.execute("INSERT OR IGNORE INTO fridge_items (user_id, product_code) VALUES (?, ?)", (user_id, product_code))
        conn.commit()
    return get_fridge_items(user_id)


def clear_fridge_db(user_id: int) -> None:
    with db_connect() as conn:
        conn.execute("DELETE FROM fridge_items WHERE user_id = ?", (user_id,))
        conn.commit()


init_db()
RECIPES = get_all_recipes()
RECIPES_BY_ID = {int(r["id"]): r for r in RECIPES}

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




def product_category_keyboard(selected_codes: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for key, group in FRIDGE_CATEGORIES.items():
        rows.append([InlineKeyboardButton(text=group["title"], callback_data=f"fridge:category:{key}")])
    rows.append([InlineKeyboardButton(text="🔎 Найти блюда", callback_data="fridge:find")])
    rows.append([InlineKeyboardButton(text="🧹 Очистить холодильник", callback_data="fridge:clear")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fridge_category_keyboard(category_key: str, selected_codes: list[str]) -> InlineKeyboardMarkup:
    selected = set(selected_codes)
    group = FRIDGE_CATEGORIES[category_key]
    rows = []
    row = []
    for product in group["products"]:
        mark = "✅ " if product["code"] in selected else ""
        row.append(InlineKeyboardButton(text=f"{mark}{product['title']}", callback_data=f"fridge:toggle:{product['code']}:{category_key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ К разделам", callback_data="fridge:back")])
    rows.append([InlineKeyboardButton(text="🔎 Найти блюда", callback_data="fridge:find")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_selected_products(selected_codes: list[str]) -> str:
    if not selected_codes:
        return "пока ничего не выбрано"
    titles = [FRIDGE_BY_CODE[code]["title"] for code in selected_codes if code in FRIDGE_BY_CODE]
    return ", ".join(titles)


def format_fridge(selected_codes: list[str]) -> str:
    return (
        "🥶 <b>Холодильник</b>\n\n"
        "Выбирай продукты по разделам. Потом нажми <b>Найти блюда</b>.\n\n"
        f"Сейчас выбрано: {format_selected_products(selected_codes)}"
    )


def format_fridge_category(category_key: str, selected_codes: list[str]) -> str:
    group = FRIDGE_CATEGORIES[category_key]
    return (
        f"🥶 <b>{group['title']}</b>\n\n"
        "Отметь продукты, которые есть дома.\n\n"
        f"Сейчас выбрано: {format_selected_products(selected_codes)}"
    )


def recipe_text_for_match(recipe: dict[str, Any]) -> str:
    parts = [recipe.get("name", ""), " ".join(recipe.get("ingredients", [])), " ".join(recipe.get("tags", []))]
    return " ".join(parts).lower()


def detected_product_codes(recipe: dict[str, Any]) -> set[str]:
    text = recipe_text_for_match(recipe)
    found = set()
    for product in FRIDGE_PRODUCTS:
        if any(alias in text for alias in product["aliases"]):
            found.add(product["code"])
    return found


def find_recipes_by_fridge(selected_codes: list[str]) -> dict[str, list[tuple[dict[str, Any], set[str], set[str]]]]:
    selected = set(selected_codes)
    results = {"full": [], "almost": []}
    if not selected:
        return results

    for recipe in RECIPES:
        required = detected_product_codes(recipe)
        if not required:
            continue
        matched = required & selected
        missing = required - selected

        if not matched:
            continue

        if not missing:
            results["full"].append((recipe, matched, missing))
        elif len(missing) <= 2:
            results["almost"].append((recipe, matched, missing))

    results["full"].sort(key=lambda item: (-len(item[1]), int(item[0].get("time", 999))))
    results["almost"].sort(key=lambda item: (len(item[2]), -len(item[1]), int(item[0].get("time", 999))))
    return results


def fridge_results_keyboard(results: dict[str, list[tuple[dict[str, Any], set[str], set[str]]]]) -> InlineKeyboardMarkup:
    rows = []
    shown = 0
    for recipe, matched, missing in results["full"][:8]:
        rows.append([InlineKeyboardButton(text=f"✅ {recipe['name']}", callback_data=f"recipe:{recipe['id']}:{recipe.get('category', 'lunch')}:0")])
        shown += 1
    for recipe, matched, missing in results["almost"][:8]:
        missing_titles = ", ".join(FRIDGE_BY_CODE[c]["title"] for c in missing if c in FRIDGE_BY_CODE)
        rows.append([InlineKeyboardButton(text=f"🟡 {recipe['name']} · не хватает: {missing_titles}", callback_data=f"recipe:{recipe['id']}:{recipe.get('category', 'lunch')}:0")])
        shown += 1
    rows.append([InlineKeyboardButton(text="⬅️ К холодильнику", callback_data="fridge:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_fridge_results(selected_codes: list[str], results: dict[str, list[tuple[dict[str, Any], set[str], set[str]]]]) -> str:
    full_count = len(results["full"])
    almost_count = len(results["almost"])
    return (
        "🥶 <b>Что можно приготовить?</b>\n\n"
        f"Выбрано: {format_selected_products(selected_codes)}\n\n"
        f"✅ Полностью подходит: <b>{full_count}</b>\n"
        f"🟡 Почти подходит, не хватает 1–2 продукта: <b>{almost_count}</b>\n\n"
        "Ниже — самые подходящие варианты."
    )


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
    fav_ids = [x for x in get_favorites(message.from_user.id) if x in RECIPES_BY_ID]
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
    items = get_shopping_items(message.from_user.id)
    if not items:
        await message.answer("🛒 Список продуктов пока пуст.")
        return
    lines = ["🛒 <b>Список продуктов</b>", ""]
    for item in items:
        lines.append(f"• {item}")
    await message.answer("\n".join(lines), reply_markup=clear_keyboard("shopping"), parse_mode="HTML")




@dp.message(F.text == "🥶 Холодильник")
async def fridge_message(message: Message):
    selected = get_fridge_items(message.from_user.id)
    await message.answer(format_fridge(selected), reply_markup=product_category_keyboard(selected), parse_mode="HTML")




@dp.callback_query(F.data.startswith("fridge:"))
async def fridge_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    selected = get_fridge_items(callback.from_user.id)

    if action == "category":
        category_key = parts[2]
        if category_key not in FRIDGE_CATEGORIES:
            await callback.answer("Раздел не найден", show_alert=True)
            return
        await callback.message.edit_text(
            format_fridge_category(category_key, selected),
            reply_markup=fridge_category_keyboard(category_key, selected),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    if action == "toggle":
        code = parts[2]
        category_key = parts[3] if len(parts) > 3 else "meat"
        selected = toggle_fridge_item_db(callback.from_user.id, code)
        await callback.message.edit_text(
            format_fridge_category(category_key, selected),
            reply_markup=fridge_category_keyboard(category_key, selected),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    if action == "clear":
        clear_fridge_db(callback.from_user.id)
        await callback.message.edit_text(format_fridge([]), reply_markup=product_category_keyboard([]), parse_mode="HTML")
        await callback.answer("Холодильник очищен")
        return

    if action == "back":
        await callback.message.edit_text(format_fridge(selected), reply_markup=product_category_keyboard(selected), parse_mode="HTML")
        await callback.answer()
        return

    if action == "find":
        if not selected:
            await callback.answer("Сначала выбери продукты", show_alert=True)
            return
        results = find_recipes_by_fridge(selected)
        if not results["full"] and not results["almost"]:
            await callback.message.edit_text(
                "🥶 <b>Холодильник</b>\n\nПо выбранным продуктам ничего не нашёл. Попробуй выбрать больше продуктов.",
                reply_markup=product_category_keyboard(selected),
                parse_mode="HTML",
            )
            await callback.answer()
            return
        await callback.message.edit_text(
            format_fridge_results(selected, results),
            reply_markup=fridge_results_keyboard(results),
            parse_mode="HTML",
        )
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
    if add_favorite_db(callback.from_user.id, recipe_id):
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
    added = 0
    for item in recipe.get("ingredients", []):
        if add_shopping_item_db(callback.from_user.id, item):
            added += 1
    await callback.answer(f"Добавлено продуктов: {added} 🛒")


@dp.callback_query(F.data.startswith("clear:"))
async def clear_callback(callback: CallbackQuery):
    kind = callback.data.split(":")[1]
    if kind == "favorites":
        clear_favorites_db(callback.from_user.id)
        await callback.message.edit_text("❤️ Избранное очищено.")
    elif kind == "shopping":
        clear_shopping_db(callback.from_user.id)
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
