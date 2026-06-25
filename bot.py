import asyncio
import json
import logging
import os
import random
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS household_profiles (
                user_id INTEGER NOT NULL,
                profile_code TEXT NOT NULL,
                name TEXT NOT NULL,
                goal TEXT NOT NULL,
                calories INTEGER NOT NULL,
                portion_factor REAL NOT NULL,
                notes TEXT,
                PRIMARY KEY (user_id, profile_code)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_flags (
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (user_id, key)
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


def get_user_flag(user_id: int, key: str) -> str | None:
    with db_connect() as conn:
        row = conn.execute(
            "SELECT value FROM user_flags WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()
    return str(row["value"]) if row else None


def set_user_flag(user_id: int, key: str, value: str) -> None:
    with db_connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_flags (user_id, key, value) VALUES (?, ?, ?)",
            (user_id, key, value),
        )
        conn.commit()


DEFAULT_PROFILES = [
    {
        "code": "serafim",
        "name": "Серафим",
        "goal": "сытная порция / поддержание",
        "calories": 2600,
        "factor": 0.60,
        "notes": "порция побольше",
    },
    {
        "code": "tanya",
        "name": "Таня",
        "goal": "полегче / похудение",
        "calories": 1700,
        "factor": 0.40,
        "notes": "порция поменьше, без свинины в будущих подборках",
    },
]


def ensure_profiles(user_id: int) -> None:
    with db_connect() as conn:
        for p in DEFAULT_PROFILES:
            conn.execute(
                """
                INSERT OR IGNORE INTO household_profiles
                (user_id, profile_code, name, goal, calories, portion_factor, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, p["code"], p["name"], p["goal"], p["calories"], p["factor"], p["notes"]),
            )
        conn.commit()


def get_profiles(user_id: int) -> list[dict[str, Any]]:
    ensure_profiles(user_id)
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT * FROM household_profiles WHERE user_id = ? ORDER BY CASE profile_code WHEN 'serafim' THEN 1 WHEN 'tanya' THEN 2 ELSE 3 END",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


init_db()
RECIPES = get_all_recipes()
RECIPES_BY_ID = {int(r["id"]): r for r in RECIPES}

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍳 Завтрак"), KeyboardButton(text="🍲 Обед")],
            [KeyboardButton(text="🍽 Ужин"), KeyboardButton(text="🥗 Перекус")],
            [KeyboardButton(text="🎲 Подобрать блюдо"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="⚙️ Фильтры"), KeyboardButton(text="❤️ Избранное")],
            [KeyboardButton(text="🏠 Главная"), KeyboardButton(text="🛒 Список продуктов")],
            [KeyboardButton(text="🥶 Холодильник"), KeyboardButton(text="👥 Профили")],
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
        ],
        [InlineKeyboardButton(text="👥 Порции для нас", callback_data=f"portions:{recipe_id}")],
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



SEARCH_WAITING: set[int] = set()


FILTERS = {
    "time30": {"title": "⏱ До 30 минут", "desc": "Быстрые блюда, которые готовятся до 30 минут."},
    "cheap500": {"title": "💰 До 500 ₽", "desc": "Блюда примерно до 500 ₽ на двоих."},
    "low500": {"title": "🔥 До 500 ккал", "desc": "Более лёгкие блюда до 500 ккал на двоих."},
    "protein": {"title": "🥩 Высокобелковые", "desc": "Блюда с курицей, рыбой, яйцами, творогом, мясом или бобовыми."},
    "nopork": {"title": "🚫 Без свинины", "desc": "Рецепты без свинины, бекона, ветчины и колбасы."},
    "light": {"title": "🥗 Полегче", "desc": "Лёгкие блюда: салаты, творог, рыба, овощи и блюда до 550 ккал."},
}


def filter_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=data["title"], callback_data=f"filter:{key}:0")] for key, data in FILTERS.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipe_text_blob(recipe: dict[str, Any]) -> str:
    parts = [recipe.get("name", "")]
    parts.extend(recipe.get("ingredients", []))
    parts.extend(recipe.get("steps", []))
    parts.extend(recipe.get("tags", []))
    return " ".join(parts).lower()


def get_filtered_recipes(kind: str) -> list[dict[str, Any]]:
    result = []
    for r in RECIPES:
        text = recipe_text_blob(r)
        calories = int(r.get("calories", 0) or 0)
        price = int(r.get("price", 0) or 0)
        time = int(r.get("time", 0) or 0)

        if kind == "time30" and time <= 30:
            result.append(r)
        elif kind == "cheap500" and price <= 500:
            result.append(r)
        elif kind == "low500" and calories <= 500:
            result.append(r)
        elif kind == "protein" and any(word in text for word in ["куриц", "индейк", "рыб", "творог", "яйц", "говядин", "фарш", "фасол", "тунец"]):
            result.append(r)
        elif kind == "nopork" and not any(word in text for word in ["свинин", "бекон", "ветчин", "колбас", "сосиск"]):
            result.append(r)
        elif kind == "light" and (calories <= 550 or any(word in text for word in ["салат", "творог", "рыб", "овощ", "кефир", "йогурт"])):
            result.append(r)
    return result


def filter_results_keyboard(kind: str, page: int = 0) -> InlineKeyboardMarkup:
    results = get_filtered_recipes(kind)
    start = page * PAGE_SIZE
    chunk = results[start:start + PAGE_SIZE]
    rows = [
        [InlineKeyboardButton(text=r["name"], callback_data=f"filterrecipe:{r['id']}:{kind}:{page}")]
        for r in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"filter:{kind}:{page-1}"))
    if start + PAGE_SIZE < len(results):
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"filter:{kind}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⚙️ Все фильтры", callback_data="filters:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_filter_results(kind: str, page: int = 0) -> str:
    if kind not in FILTERS:
        return "⚙️ Фильтр не найден."
    results = get_filtered_recipes(kind)
    pages = max(1, (len(results) + PAGE_SIZE - 1) // PAGE_SIZE)
    data = FILTERS[kind]
    if not results:
        return f"⚙️ <b>{data['title']}</b>\n\nПо этому фильтру пока ничего не нашёл."
    return (
        f"⚙️ <b>{data['title']}</b>\n\n"
        f"{data['desc']}\n\n"
        f"Найдено рецептов: <b>{len(results)}</b>\n"
        f"Страница {page + 1}/{pages}.\n\n"
        "Выбери блюдо."
    )


def normalize_text(value: str) -> str:
    return (value or "").lower().replace("ё", "е").strip()


def recipe_search_text(recipe: dict[str, Any]) -> str:
    parts = [
        recipe.get("name", ""),
        " ".join(recipe.get("ingredients", [])),
        " ".join(recipe.get("steps", [])),
        " ".join(recipe.get("tags", [])),
        recipe.get("category", ""),
    ]
    return normalize_text(" ".join(parts))


def search_recipes(query: str) -> list[dict[str, Any]]:
    q = normalize_text(query)
    if len(q) < 2:
        return []
    words = [w for w in q.split() if len(w) >= 2]
    results = []
    for recipe in RECIPES:
        text = recipe_search_text(recipe)
        name = normalize_text(recipe.get("name", ""))
        tags = normalize_text(" ".join(recipe.get("tags", [])))
        if q in text or all(word in text for word in words):
            score = 0
            if q in name:
                score += 100
            if q in tags:
                score += 50
            score += sum(10 for word in words if word in name)
            score += sum(5 for word in words if word in tags)
            results.append((score, recipe))
    results.sort(key=lambda item: (-item[0], int(item[1].get("time", 999)), item[1].get("name", "")))
    return [recipe for score, recipe in results]


def search_results_keyboard(query: str, page: int = 0) -> InlineKeyboardMarkup:
    results = search_recipes(query)
    start = page * PAGE_SIZE
    chunk = results[start:start + PAGE_SIZE]
    rows = [
        [InlineKeyboardButton(text=recipe["name"], callback_data=f"searchrecipe:{recipe['id']}:{page}")]
        for recipe in chunk
    ]
    nav = []
    safe_query = query[:50]
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"searchpage:{page-1}:{safe_query}"))
    if start + PAGE_SIZE < len(results):
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"searchpage:{page+1}:{safe_query}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_search_results(query: str, page: int = 0) -> str:
    results = search_recipes(query)
    pages = max(1, (len(results) + PAGE_SIZE - 1) // PAGE_SIZE)
    if not results:
        return (
            f"🔍 <b>Поиск</b>\n\n"
            f"По запросу <b>{query}</b> ничего не нашёл.\n\n"
            "Попробуй написать проще: например, <b>курица</b>, <b>рис</b>, <b>сыр</b>, <b>суп</b>."
        )
    return (
        f"🔍 <b>Результаты поиска</b>\n\n"
        f"Запрос: <b>{query}</b>\n"
        f"Найдено рецептов: <b>{len(results)}</b>\n"
        f"Страница {page + 1}/{pages}.\n\n"
        "Выбери блюдо."
    )



def scale_ingredient_text(item: str, factor: float) -> str:
    """Простое масштабирование ингредиента вида 'продукт — 100 г'."""
    if "—" not in item:
        return item
    name, amount = [part.strip() for part in item.split("—", 1)]
    import re
    match = re.search(r"(\d+(?:[,.]\d+)?)", amount)
    if not match:
        return item
    raw_number = match.group(1)
    try:
        number = float(raw_number.replace(",", "."))
    except ValueError:
        return item
    scaled = number * factor
    if scaled >= 10:
        scaled_text = str(int(round(scaled)))
    else:
        scaled_text = (f"{scaled:.1f}".rstrip("0").rstrip("."))
    new_amount = amount[:match.start()] + scaled_text + amount[match.end():]
    return f"{name} — {new_amount}"


def format_profile_summary(user_id: int) -> str:
    profiles = get_profiles(user_id)
    lines = ["👥 <b>Профили</b>", "", "Пока стоят базовые настройки. Потом добавим редактирование прямо в боте.", ""]
    for p in profiles:
        icon = "👨" if p["profile_code"] == "serafim" else "👩"
        percent = int(round(float(p["portion_factor"]) * 100))
        lines.append(f"{icon} <b>{p['name']}</b>")
        lines.append(f"• Цель: {p['goal']}")
        lines.append(f"• Дневная норма: ~{p['calories']} ккал")
        lines.append(f"• Доля порции: ~{percent}%")
        if p.get("notes"):
            lines.append(f"• Заметка: {p['notes']}")
        lines.append("")
    return "\n".join(lines).strip()


def format_portions(recipe: dict[str, Any], user_id: int) -> str:
    profiles = get_profiles(user_id)
    total_cal = int(recipe.get("calories", 0) or 0)
    lines = [f"👥 <b>Порции: {recipe['name']}</b>", "", "Расчёт примерный: рецепт делится между вами по долям.", ""]
    for p in profiles:
        icon = "👨" if p["profile_code"] == "serafim" else "👩"
        factor = float(p["portion_factor"])
        kcal = int(round(total_cal * factor)) if total_cal else 0
        lines.append(f"{icon} <b>{p['name']}</b> — примерно {int(round(factor * 100))}%")
        if kcal:
            lines.append(f"🔥 ~{kcal} ккал")
        for item in recipe.get("ingredients", [])[:12]:
            lines.append(f"• {scale_ingredient_text(item, factor)}")
        lines.append("")
    lines.append("🛒 В список покупок всё равно добавляются общие ингредиенты на двоих.")
    return "\n".join(lines)

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


def current_hour() -> int:
    tz_name = os.getenv("BOT_TIMEZONE", "Europe/Moscow")
    try:
        return datetime.now(ZoneInfo(tz_name)).hour
    except Exception:
        return datetime.now().hour


def current_meal_category() -> str:
    hour = current_hour()
    if 5 <= hour < 11:
        return "breakfast"
    if 11 <= hour < 17:
        return "lunch"
    return "dinner"


def format_home_text() -> str:
    category = current_meal_category()
    if category == "breakfast":
        return "☀️ <b>Доброе утро!</b>\n\nЧем позавтракаем?"
    if category == "lunch":
        return "🍲 <b>Пора подумать об обеде.</b>"
    return "🌙 <b>Что приготовим на ужин?</b>"


def home_keyboard() -> InlineKeyboardMarkup:
    category = current_meal_category()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Подобрать блюдо", callback_data="recommend:now")],
            [InlineKeyboardButton(text=CATEGORY_TITLES[category], callback_data=f"cat:{category}:0")],
        ]
    )


def recommend_recipe(user_id: int) -> tuple[dict[str, Any], list[str]]:
    target_category = current_meal_category()
    selected = set(get_fridge_items(user_id))
    favorites = set(get_favorites(user_id))
    candidates = recipes_for_category(target_category) or RECIPES

    scored = []
    for recipe in candidates:
        score = 0
        reasons = []

        required = detected_product_codes(recipe)
        matched = required & selected
        missing = required - selected

        if selected and required:
            if not missing:
                score += 50
                reasons.append("✅ Все продукты уже есть в холодильнике.")
            elif matched and len(missing) <= 2:
                score += 25 - len(missing) * 5
                missing_titles = ", ".join(FRIDGE_BY_CODE[c]["title"] for c in missing if c in FRIDGE_BY_CODE)
                if missing_titles:
                    reasons.append(f"🛒 Не хватает только: {missing_titles}.")
            elif matched:
                score += 10

        if int(recipe.get("id", 0)) in favorites:
            score += 20
            reasons.append("❤️ Это блюдо есть в избранном.")

        time = int(recipe.get("time", 0) or 0)
        if time and time <= 30:
            score += 10
            reasons.append(f"⏱️ Готовится за {time} минут.")
        elif time:
            reasons.append(f"⏱️ Время приготовления: {time} минут.")

        if not reasons:
            reasons.append("🍽 Подходит под текущее время дня.")

        scored.append((score, random.random(), recipe, reasons))

    scored.sort(key=lambda item: (-item[0], item[1]))
    _, _, recipe, reasons = scored[0]
    return recipe, reasons[:3]


def format_recommendation(recipe: dict[str, Any], reasons: list[str]) -> str:
    lines = [
        f"🍽 <b>Сегодня предлагаю «{recipe['name']}»</b>",
        "",
    ]
    lines.extend(reasons)
    return "\n".join(lines)


def recommendation_keyboard(recipe: dict[str, Any]) -> InlineKeyboardMarkup:
    recipe_id = int(recipe["id"])
    category = recipe.get("category", "lunch")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Посмотреть рецепт", callback_data=f"recipe:{recipe_id}:{category}:0")],
            [InlineKeyboardButton(text="🔄 Предложить другое", callback_data="recommend:again")],
        ]
    )


dp = Dispatcher()


async def send_home_screen(message: Message) -> None:
    await message.answer(
        format_home_text(),
        reply_markup=home_keyboard(),
        parse_mode="HTML",
    )


@dp.message(CommandStart())
async def start(message: Message):
    await send_home_screen(message)

    # Один раз отправляем Reply-клавиатуру, чтобы появилась кнопка «🏠 Главная».
    # Дальше главный экран открывается без лишних сообщений.
    if get_user_flag(message.from_user.id, "reply_keyboard_home_v1") != "1":
        await message.answer("⌨️ Клавиатура обновлена", reply_markup=main_keyboard())
        set_user_flag(message.from_user.id, "reply_keyboard_home_v1", "1")


@dp.message(F.text == "🏠 Главная")
async def home_from_keyboard(message: Message):
    await send_home_screen(message)


@dp.message(F.text.in_(list(TEXT_TO_CATEGORY.keys())))
async def category_from_keyboard(message: Message):
    category = TEXT_TO_CATEGORY[message.text]
    await message.answer(format_category(category, 0), reply_markup=recipe_list_keyboard(category, 0))


@dp.message(F.text.in_(["🎲 Подобрать блюдо", "🎲 Что приготовить?", "✨ Подобрать блюдо"]))
async def random_recipe_message(message: Message):
    recipe, reasons = recommend_recipe(message.from_user.id)
    await message.answer(
        format_recommendation(recipe, reasons),
        reply_markup=recommendation_keyboard(recipe),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("recommend:"))
async def recommend_callback(callback: CallbackQuery):
    recipe, reasons = recommend_recipe(callback.from_user.id)
    await callback.message.edit_text(
        format_recommendation(recipe, reasons),
        reply_markup=recommendation_keyboard(recipe),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(F.text == "🔍 Поиск")
async def search_message(message: Message):
    SEARCH_WAITING.add(message.from_user.id)
    await message.answer(
        "🔍 <b>Поиск блюда</b>\n\n"
        "Напиши, что искать. Например:\n"
        "• курица\n"
        "• рис\n"
        "• сыр\n"
        "• суп\n"
        "• творог",
        parse_mode="HTML",
    )



@dp.message(F.text == "⚙️ Фильтры")
async def filters_message(message: Message):
    await message.answer(
        "⚙️ <b>Фильтры</b>\n\nВыбери, какие блюда показать:",
        reply_markup=filter_menu_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "filters:menu")
async def filters_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ <b>Фильтры</b>\n\nВыбери, какие блюда показать:",
        reply_markup=filter_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("filter:"))
async def filter_callback(callback: CallbackQuery):
    _, kind, page_s = callback.data.split(":")
    page = int(page_s)
    await callback.message.edit_text(
        format_filter_results(kind, page),
        reply_markup=filter_results_keyboard(kind, page),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("filterrecipe:"))
async def filter_recipe_callback(callback: CallbackQuery):
    _, recipe_id_s, kind, page_s = callback.data.split(":")
    recipe_id = int(recipe_id_s)
    page = int(page_s)
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



@dp.message(F.text == "👥 Профили")
async def profiles_message(message: Message):
    await message.answer(format_profile_summary(message.from_user.id), parse_mode="HTML")


@dp.callback_query(F.data.startswith("portions:"))
async def portions_callback(callback: CallbackQuery):
    recipe_id = int(callback.data.split(":")[1])
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    await callback.message.answer(format_portions(recipe, callback.from_user.id), parse_mode="HTML")
    await callback.answer()

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


@dp.callback_query(F.data == "search:new")
async def search_new_callback(callback: CallbackQuery):
    SEARCH_WAITING.add(callback.from_user.id)
    await callback.message.edit_text(
        "🔍 <b>Новый поиск</b>\n\nНапиши, что искать. Например: <b>курица</b> или <b>рис</b>.",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("searchpage:"))
async def search_page_callback(callback: CallbackQuery):
    _, page_s, query = callback.data.split(":", 2)
    page = int(page_s)
    await callback.message.edit_text(
        format_search_results(query, page),
        reply_markup=search_results_keyboard(query, page),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("searchrecipe:"))
async def search_recipe_callback(callback: CallbackQuery):
    _, recipe_id_s, page_s = callback.data.split(":")
    recipe_id = int(recipe_id_s)
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
    if message.from_user.id in SEARCH_WAITING and message.text:
        query = message.text.strip()
        SEARCH_WAITING.discard(message.from_user.id)
        await message.answer(
            format_search_results(query, 0),
            reply_markup=search_results_keyboard(query, 0),
            parse_mode="HTML",
        )
        return


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    logger.info("Bot started. Recipes loaded: %s", len(RECIPES))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
