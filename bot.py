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

WEEK_DAYS = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cooking_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                cooked_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipe_ratings (
                user_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                rated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, recipe_id)
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


NOTIFICATION_DEFAULT_TIMES = {
    "breakfast": "09:00",
    "lunch": "14:00",
    "dinner": "19:00",
}

MEAL_TITLES = {
    "breakfast": "☀️ Завтрак",
    "lunch": "🍲 Обед",
    "dinner": "🌙 Ужин",
}

MEAL_HOME_TEXTS = {
    "breakfast": "☀️ <b>Доброе утро!</b>\n\nЧем позавтракаем?",
    "lunch": "🍲 <b>Пора подумать об обеде.</b>",
    "dinner": "🌙 <b>Что приготовим на ужин?</b>",
}

MEAL_TIME_OPTIONS = {
    "breakfast": ["07:00", "08:00", "09:00", "10:00"],
    "lunch": ["12:00", "13:00", "14:00", "15:00"],
    "dinner": ["18:00", "19:00", "20:00", "21:00"],
}


def get_notification_time(user_id: int, meal: str) -> str:
    return get_user_flag(user_id, f"notify_time_{meal}") or NOTIFICATION_DEFAULT_TIMES[meal]


def notifications_enabled(user_id: int) -> bool:
    return get_user_flag(user_id, "notifications_enabled") == "1"


def set_notifications_enabled(user_id: int, enabled: bool) -> None:
    set_user_flag(user_id, "notifications_enabled", "1" if enabled else "0")


def get_notification_users() -> list[int]:
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT user_id FROM user_flags WHERE key = 'notifications_enabled' AND value = '1'"
        ).fetchall()
    return [int(row["user_id"]) for row in rows]


def notification_settings_text(user_id: int) -> str:
    status = "включены ✅" if notifications_enabled(user_id) else "выключены ❌"
    return (
        "🔔 <b>Уведомления</b>\n\n"
        f"Статус: <b>{status}</b>\n\n"
        f"☀️ Завтрак: <b>{get_notification_time(user_id, 'breakfast')}</b>\n"
        f"🍲 Обед: <b>{get_notification_time(user_id, 'lunch')}</b>\n"
        f"🌙 Ужин: <b>{get_notification_time(user_id, 'dinner')}</b>\n\n"
        "Бот будет присылать главный экран в выбранное время."
    )


def notification_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    toggle_text = "🔕 Выключить уведомления" if notifications_enabled(user_id) else "🔔 Включить уведомления"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data="notify:toggle")],
            [InlineKeyboardButton(text=f"☀️ Завтрак — {get_notification_time(user_id, 'breakfast')}", callback_data="notify:time:breakfast")],
            [InlineKeyboardButton(text=f"🍲 Обед — {get_notification_time(user_id, 'lunch')}", callback_data="notify:time:lunch")],
            [InlineKeyboardButton(text=f"🌙 Ужин — {get_notification_time(user_id, 'dinner')}", callback_data="notify:time:dinner")],
            [InlineKeyboardButton(text="⬅️ К настройкам", callback_data="settings:menu")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")],
        ]
    )


def notification_time_keyboard(meal: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=time, callback_data=f"notify:set:{meal}:{time.replace(':', '')}")]
        for time in MEAL_TIME_OPTIONS.get(meal, [])
    ]
    rows.append([InlineKeyboardButton(text="⬅️ К уведомлениям", callback_data="settings:notifications")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def notification_time_text(user_id: int, meal: str) -> str:
    return (
        f"⏰ <b>{MEAL_TITLES.get(meal, 'Время')}</b>\n\n"
        f"Сейчас выбрано: <b>{get_notification_time(user_id, meal)}</b>\n\n"
        "Выбери новое время."
    )


def home_text_for_category(category: str) -> str:
    return MEAL_HOME_TEXTS.get(category, format_home_text())


def home_keyboard_for_category(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Подобрать блюдо", callback_data="recommend:now")],
            [InlineKeyboardButton(text=CATEGORY_TITLES.get(category, "🍽 Блюда"), callback_data=f"cat:{category}:0")],
        ]
    )


async def notification_loop(bot: Bot) -> None:
    await asyncio.sleep(5)
    while True:
        try:
            tz = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Moscow"))
            now = datetime.now(tz)
            current_time = now.strftime("%H:%M")
            today = now.date().isoformat()

            for user_id in get_notification_users():
                for meal in ("breakfast", "lunch", "dinner"):
                    if get_notification_time(user_id, meal) != current_time:
                        continue
                    last_key = f"notify_last_{meal}"
                    if get_user_flag(user_id, last_key) == today:
                        continue
                    await bot.send_message(
                        user_id,
                        home_text_for_category(meal),
                        reply_markup=home_keyboard_for_category(meal),
                        parse_mode="HTML",
                    )
                    set_user_flag(user_id, last_key, today)
        except Exception:
            logger.exception("Notification loop failed")
        await asyncio.sleep(30)


def add_cooked_recipe(user_id: int, recipe_id: int) -> int:
    cooked_at = datetime.now(ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Moscow"))).isoformat(timespec="seconds")
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO cooking_history (user_id, recipe_id, cooked_at) VALUES (?, ?, ?)",
            (user_id, recipe_id, cooked_at),
        )
        conn.commit()
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM cooking_history WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return int(row["count"] or 0)


def get_cooked_count(user_id: int) -> int:
    with db_connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM cooking_history WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return int(row["count"] or 0) if row else 0



def get_cooking_history(user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT recipe_id, cooked_at
            FROM cooking_history
            WHERE user_id = ?
            ORDER BY cooked_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    history = []
    for row in rows:
        recipe = RECIPES_BY_ID.get(int(row["recipe_id"]))
        if recipe:
            history.append({"recipe": recipe, "cooked_at": str(row["cooked_at"])})
    return history


def clear_cooking_history(user_id: int) -> None:
    with db_connect() as conn:
        conn.execute("DELETE FROM cooking_history WHERE user_id = ?", (user_id,))
        conn.commit()


def format_history_date(cooked_at: str) -> str:
    tz = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Moscow"))
    try:
        dt = datetime.fromisoformat(cooked_at).astimezone(tz)
    except ValueError:
        return "Без даты"

    today = datetime.now(tz).date()
    cooked_date = dt.date()
    if cooked_date == today:
        return "Сегодня"
    if (today - cooked_date).days == 1:
        return "Вчера"
    return dt.strftime("%d.%m.%Y")


def format_history(user_id: int) -> str:
    items = get_cooking_history(user_id, 30)
    if not items:
        return (
            "📖 <b>История приготовлений</b>\n\n"
            "Пока здесь пусто.\n\n"
            "Когда нажмёшь <b>✅ Приготовили</b> в карточке рецепта, блюдо появится здесь."
        )

    lines = ["📖 <b>История приготовлений</b>", ""]
    current_group = None
    for item in items:
        group = format_history_date(item["cooked_at"])
        recipe = item["recipe"]
        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f"<b>{group}</b>")
            current_group = group
        lines.append(f"• {recipe['name']}")
    return "\n".join(lines)


def history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="history:clear")],
            [InlineKeyboardButton(text="⬅️ К настройкам", callback_data="settings:menu")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")],
        ]
    )


def confirm_clear_history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да, очистить", callback_data="history:clear_confirm")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:history")],
        ]
    )

def get_top_cooked_recipe(user_id: int) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT recipe_id, COUNT(*) AS count
            FROM cooking_history
            WHERE user_id = ?
            GROUP BY recipe_id
            ORDER BY count DESC, MAX(cooked_at) DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return RECIPES_BY_ID.get(int(row["recipe_id"]))


def set_recipe_rating(user_id: int, recipe_id: int, rating: int) -> None:
    rated_at = datetime.now(ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Moscow"))).isoformat(timespec="seconds")
    with db_connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO recipe_ratings (user_id, recipe_id, rating, rated_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, recipe_id, rating, rated_at),
        )
        conn.commit()


def get_user_recipe_rating(user_id: int, recipe_id: int) -> int | None:
    with db_connect() as conn:
        row = conn.execute(
            "SELECT rating FROM recipe_ratings WHERE user_id = ? AND recipe_id = ?",
            (user_id, recipe_id),
        ).fetchone()
    return int(row["rating"]) if row else None


def get_top_rated_recipe(user_id: int) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT recipe_id, rating
            FROM recipe_ratings
            WHERE user_id = ?
            ORDER BY rating DESC, rated_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return RECIPES_BY_ID.get(int(row["recipe_id"]))


def get_recent_cooked_recipe_ids(user_id: int, limit: int = 5) -> set[int]:
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT recipe_id
            FROM cooking_history
            WHERE user_id = ?
            ORDER BY cooked_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return {int(row["recipe_id"]) for row in rows}


def get_user_ratings(user_id: int) -> dict[int, int]:
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT recipe_id, rating FROM recipe_ratings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    return {int(row["recipe_id"]): int(row["rating"]) for row in rows}


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
            [KeyboardButton(text="📅 Меню недели"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="❤️ Избранное")],
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
            InlineKeyboardButton(text="✅ Приготовили", callback_data=f"cooked:{recipe_id}"),
            InlineKeyboardButton(text="⭐ Оценить", callback_data=f"rate:{recipe_id}"),
        ],
        [
            InlineKeyboardButton(text="❤️ В избранное", callback_data=f"fav:{recipe_id}"),
            InlineKeyboardButton(text="🛒 В список", callback_data=f"shop:{recipe_id}"),
        ],
        [InlineKeyboardButton(text="👥 Порции для нас", callback_data=f"portions:{recipe_id}")],
    ]
    if category:
        rows.append([InlineKeyboardButton(text="⬅️ К списку", callback_data=f"cat:{category}:{page}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rating_keyboard(recipe_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐", callback_data=f"rateval:{recipe_id}:1"),
                InlineKeyboardButton(text="⭐⭐", callback_data=f"rateval:{recipe_id}:2"),
                InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"rateval:{recipe_id}:3"),
            ],
            [
                InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"rateval:{recipe_id}:4"),
                InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"rateval:{recipe_id}:5"),
            ],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")],
        ]
    )


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


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:notifications")],
            [InlineKeyboardButton(text="👥 Профили", callback_data="settings:profiles")],
            [InlineKeyboardButton(text="📖 История приготовлений", callback_data="settings:history")],
            [InlineKeyboardButton(text="🗑 Очистить историю", callback_data="history:clear")],
            [InlineKeyboardButton(text="ℹ️ О боте", callback_data="settings:about")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")],
        ]
    )


def settings_text() -> str:
    return "⚙️ <b>Настройки</b>\n\nЗдесь настройки самого бота."


def about_text(user_id: int) -> str:
    cooked_count = get_cooked_count(user_id)
    favorite_recipe = get_top_cooked_recipe(user_id) or get_top_rated_recipe(user_id)
    favorite_name = favorite_recipe["name"] if favorite_recipe else "пока не выбрано"
    return (
        "🍽 <b>Что готовим?</b>\n\n"
        "Версия <b>1.5</b>\n\n"
        "Домашний помощник для выбора блюд.\n\n"
        "Разработано с ❤️\n"
        "для Серафима и Тани.\n\n"
        f"📖 Рецептов: <b>{len(RECIPES)}</b>\n"
        f"🍳 Приготовлено: <b>{cooked_count}</b>\n"
        f"❤️ Любимое: <b>{favorite_name}</b>"
    )

def about_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")],
        ]
    )


def back_to_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К настройкам", callback_data="settings:menu")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")],
        ]
    )


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



def score_recipe_for_week(recipe: dict[str, Any], user_id: int, used_ids: set[int]) -> int:
    """Простая оценка для меню недели: холодильник, избранное, оценки, история и разнообразие."""
    recipe_id = int(recipe.get("id", 0) or 0)
    score = 0

    if recipe_id in used_ids:
        score -= 100

    selected = set(get_fridge_items(user_id))
    required = detected_product_codes(recipe)
    if required:
        matched = required & selected
        missing = required - selected
        if not missing:
            score += 8
        elif len(missing) <= 2:
            score += 4
        score += min(len(matched), 3)

    if recipe_id in set(get_favorites(user_id)):
        score += 3

    rating = get_user_recipe_rating(user_id, recipe_id)
    if rating:
        score += rating

    if recipe_id in get_recent_cooked_recipe_ids(user_id, limit=10):
        score -= 5

    time = int(recipe.get("time", 0) or 0)
    if time and time <= 30:
        score += 1

    return score


def pick_week_recipe(category: str, user_id: int, used_ids: set[int]) -> dict[str, Any] | None:
    candidates = recipes_for_category(category)
    if not candidates:
        return None
    scored = [(score_recipe_for_week(r, user_id, used_ids), random.random(), r) for r in candidates]
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    recipe = scored[0][2]
    used_ids.add(int(recipe["id"]))
    return recipe


def generate_weekly_menu(user_id: int) -> dict[str, list[dict[str, Any]]]:
    used_ids: set[int] = set()
    menu: dict[str, list[dict[str, Any]]] = {}
    for day in WEEK_DAYS:
        day_items: list[dict[str, Any]] = []
        for category in ["breakfast", "lunch", "dinner"]:
            recipe = pick_week_recipe(category, user_id, used_ids)
            if recipe:
                day_items.append(recipe)
        menu[day] = day_items
    set_user_flag(
        user_id,
        "weekly_menu_ids",
        json.dumps({day: [int(r["id"]) for r in items] for day, items in menu.items()}, ensure_ascii=False),
    )
    return menu


def get_saved_weekly_menu(user_id: int) -> dict[str, list[dict[str, Any]]]:
    raw = get_user_flag(user_id, "weekly_menu_ids")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    menu: dict[str, list[dict[str, Any]]] = {}
    for day, ids in data.items():
        items = []
        for recipe_id in ids:
            recipe = RECIPES_BY_ID.get(int(recipe_id))
            if recipe:
                items.append(recipe)
        if items:
            menu[day] = items
    return menu


def clear_weekly_menu(user_id: int) -> None:
    set_user_flag(user_id, "weekly_menu_ids", "")


def save_weekly_menu(user_id: int, menu: dict[str, list[dict[str, Any]]]) -> None:
    set_user_flag(
        user_id,
        "weekly_menu_ids",
        json.dumps({day: [int(r["id"]) for r in items] for day, items in menu.items()}, ensure_ascii=False),
    )


def replace_weekly_menu_item(user_id: int, day_index: int, slot_index: int) -> dict[str, Any] | None:
    menu = get_saved_weekly_menu(user_id)
    if not menu or day_index < 0 or day_index >= len(WEEK_DAYS):
        return None

    day = WEEK_DAYS[day_index]
    items = menu.get(day, [])
    if slot_index < 0 or slot_index >= len(items):
        return None

    category = str(items[slot_index].get("category") or ["breakfast", "lunch", "dinner"][min(slot_index, 2)])
    current_id = int(items[slot_index].get("id", 0) or 0)

    # Сначала стараемся заменить на блюдо той же категории, которого ещё нет в меню недели.
    used_ids: set[int] = set()
    for day_items in menu.values():
        for recipe in day_items:
            recipe_id = int(recipe.get("id", 0) or 0)
            if recipe_id:
                used_ids.add(recipe_id)

    candidates = [
        recipe for recipe in recipes_for_category(category)
        if int(recipe.get("id", 0) or 0) not in used_ids
    ]

    # Если все блюда этой категории уже встречаются в меню, разрешаем повторы,
    # но всё равно не возвращаем то же самое блюдо.
    if not candidates:
        candidates = [
            recipe for recipe in recipes_for_category(category)
            if int(recipe.get("id", 0) or 0) != current_id
        ]

    if not candidates:
        return None

    scored = [
        (score_recipe_for_week(recipe, user_id, used_ids), random.random(), recipe)
        for recipe in candidates
    ]
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    new_recipe = scored[0][2]

    items[slot_index] = new_recipe
    menu[day] = items
    save_weekly_menu(user_id, menu)
    return new_recipe


def format_weekly_menu(menu: dict[str, list[dict[str, Any]]]) -> str:
    if not menu:
        return (
            "📅 <b>Меню недели</b>\n\n"
            "Пока меню не составлено. Нажми кнопку ниже, и я подберу блюда на неделю."
        )
    lines = ["📅 <b>Меню недели</b>", ""]
    for day in WEEK_DAYS:
        items = menu.get(day, [])
        if not items:
            continue
        lines.append(f"<b>{day}</b>")
        for recipe in items:
            icon = CATEGORY_TITLES.get(recipe.get("category"), "🍽").split()[0]
            lines.append(f"{icon} {recipe['name']}")
        lines.append("")
    lines.append("🛒 Можно одной кнопкой добавить продукты в список покупок.")
    return "\n".join(lines).strip()


def weekly_menu_keyboard(has_menu: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if has_menu:
        rows.append([InlineKeyboardButton(text="🛒 Добавить продукты в покупки", callback_data="week:shopping")])
        rows.append([InlineKeyboardButton(text="🔄 Заменить одно блюдо", callback_data="week:replace_menu")])
        rows.append([InlineKeyboardButton(text="🔄 Составить заново", callback_data="week:generate")])
        rows.append([InlineKeyboardButton(text="🧹 Очистить меню", callback_data="week:clear")])
    else:
        rows.append([InlineKeyboardButton(text="📅 Составить меню на неделю", callback_data="week:generate")])
    rows.append([InlineKeyboardButton(text="⬅️ К настройкам", callback_data="settings:menu")])
    rows.append([InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def week_replace_menu_keyboard(menu: dict[str, list[dict[str, Any]]]) -> InlineKeyboardMarkup:
    rows = []
    day_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    meal_icons = ["🍳", "🍲", "🍽"]
    meal_names = ["завтрак", "обед", "ужин"]

    for day_index, day in enumerate(WEEK_DAYS):
        items = menu.get(day, [])
        for slot_index, recipe in enumerate(items):
            icon = meal_icons[slot_index] if slot_index < len(meal_icons) else "🍽"
            meal = meal_names[slot_index] if slot_index < len(meal_names) else "блюдо"
            rows.append([
                InlineKeyboardButton(
                    text=f"{day_short[day_index]} {icon} {meal}: {recipe['name'][:28]}",
                    callback_data=f"week:replace:{day_index}:{slot_index}",
                )
            ])

    rows.append([InlineKeyboardButton(text="⬅️ К меню недели", callback_data="settings:weekly")])
    rows.append([InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def normalize_product_name(name: str) -> str:
    """Приводит название продукта к аккуратному виду для списка покупок."""
    cleaned = " ".join(str(name).strip().split())
    if not cleaned:
        return cleaned
    return cleaned[:1].upper() + cleaned[1:]


def is_taste_item(text: str) -> bool:
    """Определяет продукты без точного количества: «по вкусу»."""
    return "по вкусу" in str(text).lower()


def parse_ingredient_line(line: str) -> tuple[str, float, str] | None:
    """Пробует разобрать строку ингредиента вида «Молоко — 400 мл».

    Возвращает: (название, количество, единица).
    Объединяем только безопасные случаи: число + одинаковая единица.
    Сложные строки вроде «по вкусу» не объединяем.
    """
    text = str(line).strip()
    if not text or is_taste_item(text):
        return None

    if "—" in text:
        name, amount_part = text.split("—", 1)
    elif "-" in text:
        name, amount_part = text.split("-", 1)
    else:
        return None

    name = normalize_product_name(name)
    amount_part = amount_part.strip()
    if not name or not amount_part:
        return None

    pieces = amount_part.split()
    if not pieces:
        return None

    raw_amount = pieces[0].replace(",", ".")
    try:
        amount = float(raw_amount)
    except ValueError:
        return None

    unit = " ".join(pieces[1:]).strip().lower()
    if not unit:
        unit = "шт."

    return name, amount, unit


def format_amount(amount: float) -> str:
    if amount.is_integer():
        return str(int(amount))
    return str(round(amount, 2)).replace(".", ",")


def normalize_shopping_text(item: str) -> str:
    """Нормализует строку покупки без изменения смысла."""
    text = " ".join(str(item).strip().split())
    if "—" in text:
        name, rest = text.split("—", 1)
        return f"{normalize_product_name(name)} — {rest.strip()}"
    if "-" in text:
        name, rest = text.split("-", 1)
        return f"{normalize_product_name(name)} — {rest.strip()}"
    return normalize_product_name(text)


def split_taste_items(items: list[str]) -> tuple[list[str], list[str]]:
    regular: list[str] = []
    taste: list[str] = []
    for item in items:
        normalized = normalize_shopping_text(item)
        if is_taste_item(normalized):
            taste.append(normalized)
        else:
            regular.append(normalized)
    return regular, taste


def build_weekly_shopping_items(menu: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Собирает продукты из меню недели и аккуратно объединяет одинаковые.

    Работает с текущим форматом recipes.json, где ингредиенты — обычные строки.
    Объединяет только одинаковые продукты с одинаковой единицей измерения.
    Остальное добавляет как есть, но без точных дублей и с аккуратным регистром.
    """
    totals: dict[tuple[str, str], dict[str, Any]] = {}
    raw_items: list[str] = []

    for items in menu.values():
        for recipe in items:
            for ingredient in recipe.get("ingredients", []):
                text = str(ingredient).strip()
                if not text:
                    continue

                parsed = parse_ingredient_line(text)
                if not parsed:
                    raw_items.append(normalize_shopping_text(text))
                    continue

                name, amount, unit = parsed
                key = (name.lower(), unit.lower())
                if key not in totals:
                    totals[key] = {"name": name, "amount": 0.0, "unit": unit}
                totals[key]["amount"] += amount

    result = [
        f"{item['name']} — {format_amount(item['amount'])} {item['unit']}"
        for item in totals.values()
    ]

    seen = {item.lower() for item in result}
    for item in raw_items:
        key = item.lower()
        if key not in seen:
            result.append(item)
            seen.add(key)

    regular, taste = split_taste_items(result)
    return sorted(regular, key=str.lower) + sorted(taste, key=str.lower)


def add_weekly_menu_to_shopping(user_id: int) -> int:
    """Добавляет объединённые ингредиенты из текущего меню недели в покупки."""
    menu = get_saved_weekly_menu(user_id)
    shopping_items = build_weekly_shopping_items(menu)
    added = 0

    for item in shopping_items:
        if add_shopping_item_db(user_id, item):
            added += 1

    return added


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


def _has_word(text: str, words: list[str]) -> bool:
    text_low = text.lower()
    return any(word.lower() in text_low for word in words)


def _ingredient_names(recipe: dict[str, Any]) -> str:
    return " ".join(recipe.get("ingredients", [])).lower()


def detailed_steps_for_recipe(recipe: dict[str, Any]) -> list[str]:
    """Возвращает шаги из базы рецептов.

    Если в recipes.json уже есть нормальные подробные шаги, бот больше не
    заменяет их универсальным шаблоном. Шаблоны ниже используются только как
    запасной вариант для совсем коротких старых рецептов.
    """
    name = recipe.get("name", "Блюдо")
    name_low = name.lower()
    ingredients_text = _ingredient_names(recipe)
    base_steps = [str(step).strip().rstrip(".") for step in recipe.get("steps", []) if str(step).strip()]

    # Если рецепт уже подробно расписан в recipes.json — показываем именно его.
    # Это убирает одинаковые шаблонные инструкции у омлетов, яичниц и похожих блюд.
    if len(base_steps) >= 4 or any(len(step) >= 70 for step in base_steps):
        return [step + "." if not step.endswith((".", "!", "?")) else step for step in base_steps]

    # Запасные сценарии для старых коротких рецептов.
    if _has_word(name_low, ["паста", "спагетти", "макароны"]):
        steps = [
            "Поставьте кастрюлю с водой на сильный огонь, посолите и доведите до кипения.",
            "Отварите пасту до состояния al dente по инструкции на упаковке. Перед сливом оставьте немного воды от варки.",
        ]
        if _has_word(ingredients_text, ["лук"]):
            steps.append("Пока варится паста, мелко нарежьте лук.")
        if _has_word(ingredients_text, ["фарш"]):
            steps.append("Разогрейте сковороду, добавьте немного масла и обжарьте лук 3–4 минуты до мягкости.")
            steps.append("Добавьте фарш и готовьте 7–10 минут, разбивая комочки лопаткой.")
        elif _has_word(ingredients_text, ["куриц"]):
            steps.append("Нарежьте курицу небольшими кусочками и обжарьте на сковороде до готовности.")
        if _has_word(ingredients_text, ["томат", "соус"]):
            steps.append("Добавьте томатный соус, перемешайте и тушите 7–10 минут на среднем огне.")
        if _has_word(ingredients_text, ["сливк"]):
            steps.append("Влейте сливки, прогрейте соус 3–5 минут и не доводите до сильного кипения.")
        steps.append("Соедините пасту с соусом, перемешайте. Если соус густой, добавьте немного воды от пасты.")
        steps.append("Подавайте горячей. По желанию добавьте зелень или тёртый сыр.")
        return steps

    if _has_word(name_low, ["омлет", "яичница"]):
        steps = [
            "Подготовьте все ингредиенты: яйца разбейте в миску, овощи или начинку нарежьте небольшими кусочками.",
            "Взбейте яйца вилкой или венчиком до однородности. При желании добавьте немного молока, соль и специи.",
        ]
        if _has_word(ingredients_text, ["овощ", "помидор", "перец", "лук", "гриб"]):
            steps.append("Разогрейте сковороду и слегка обжарьте овощи 3–5 минут, чтобы они стали мягче.")
        steps.append("Влейте яичную смесь на сковороду и готовьте на слабом или среднем огне под крышкой.")
        steps.append("Когда верх схватится, снимите блюдо с огня и дайте постоять 1–2 минуты.")
        steps.append("Подавайте сразу, пока омлет нежный и горячий.")
        return steps

    if _has_word(name_low, ["суп", "борщ", "щи"]):
        steps = [
            "Подготовьте ингредиенты: овощи вымойте и нарежьте, мясо или курицу при необходимости разделите на кусочки.",
            "В кастрюле доведите воду или бульон до кипения.",
            "Добавьте продукты, которым нужно больше времени: мясо, картофель, крупу или капусту.",
            "Пока основа варится, сделайте зажарку: обжарьте лук и морковь на небольшом количестве масла.",
            "Добавьте зажарку в кастрюлю, перемешайте и варите до мягкости всех ингредиентов.",
            "Посолите и приправьте по вкусу. Дайте супу настояться 10 минут под крышкой.",
            "Подавайте горячим. По желанию добавьте зелень или сметану.",
        ]
        return steps

    if _has_word(name_low, ["салат"]):
        steps = [
            "Вымойте и обсушите овощи и зелень.",
        ]
        if _has_word(ingredients_text, ["куриц"]):
            steps.append("Курицу отварите, запеките или обжарьте до готовности, затем немного остудите и нарежьте.")
        if _has_word(ingredients_text, ["яйц"]):
            steps.append("Яйца отварите вкрутую, остудите и нарежьте.")
        steps.extend([
            "Нарежьте остальные ингредиенты удобными кусочками.",
            "Сложите всё в большую миску, добавьте заправку и аккуратно перемешайте.",
            "Попробуйте на соль и специи. При необходимости добавьте немного масла, лимонного сока или соуса.",
            "Подавайте сразу после приготовления, чтобы овощи оставались свежими.",
        ])
        return steps

    if _has_word(name_low, ["каша", "овсян", "гречнев", "рисов"]):
        steps = [
            "Промойте крупу, если это нужно для выбранного вида крупы.",
            "В кастрюле соедините крупу с водой или молоком, добавьте щепотку соли.",
            "Доведите до кипения, затем уменьшите огонь и варите до мягкости, периодически помешивая.",
            "Когда каша загустеет, снимите её с огня и дайте постоять 3–5 минут под крышкой.",
            "Добавьте масло, мёд, фрукты или другие добавки по вкусу.",
            "Подавайте тёплой.",
        ]
        return steps

    if _has_word(name_low, ["сырники", "запеканка"]):
        steps = [
            "Разомните творог вилкой или пробейте блендером, если хотите более нежную текстуру.",
            "Добавьте яйца, сахар и муку или манку. Перемешайте до однородности.",
            "Оставьте массу на 5–10 минут, чтобы она стала плотнее.",
        ]
        if _has_word(name_low, ["сырники"]):
            steps.append("Сформируйте сырники влажными руками и слегка обваляйте в муке.")
            steps.append("Обжарьте на среднем огне по 3–4 минуты с каждой стороны до румяной корочки.")
        else:
            steps.append("Переложите массу в форму для запекания и разровняйте.")
            steps.append("Запекайте до румяности и готовности внутри.")
        steps.append("Подавайте со сметаной, ягодами, мёдом или фруктами.")
        return steps

    # Универсальное расширение коротких шагов из базы.
    steps = ["Подготовьте ингредиенты: вымойте, очистите и нарежьте всё, что нужно по рецепту."]
    for step in base_steps:
        steps.append(step + ".")
    steps.append("В конце попробуйте блюдо и при необходимости добавьте соль, специи или зелень.")
    steps.append("Дайте блюду немного постоять перед подачей, чтобы вкус стал более цельным.")
    return steps


def recipe_tips(recipe: dict[str, Any]) -> list[str]:
    name_low = recipe.get("name", "").lower()
    ingredients_text = _ingredient_names(recipe)
    tips: list[str] = []

    if _has_word(name_low, ["паста", "макароны", "спагетти"]):
        tips.append("Пасту лучше слегка недоварить: она дойдёт до готовности в соусе.")
        tips.append("Немного воды от пасты помогает сделать соус более гладким.")
    elif _has_word(name_low, ["суп", "борщ", "щи"]):
        tips.append("Суп станет вкуснее, если дать ему настояться 10–15 минут после приготовления.")
    elif _has_word(name_low, ["салат"]):
        tips.append("Заправляйте салат перед подачей, чтобы овощи не дали лишний сок.")
    elif _has_word(name_low, ["омлет", "яичница"]):
        tips.append("Готовьте яйца на умеренном огне: так блюдо получится нежнее.")
    elif _has_word(name_low, ["каша", "овсян"]):
        tips.append("Если каша получилась густой, добавьте немного молока или воды и прогрейте ещё минуту.")
    else:
        tips.append("Не спешите увеличивать огонь: большинство домашних блюд вкуснее при спокойном приготовлении.")

    if _has_word(ingredients_text, ["куриц", "фарш", "рыб", "мяс"]):
        tips.append("Мясо, рыбу или курицу лучше не пересушивать: снимайте с огня сразу после готовности.")
    return tips[:3]


def recipe_storage(recipe: dict[str, Any]) -> list[str]:
    name_low = recipe.get("name", "").lower()
    if _has_word(name_low, ["салат"]):
        return [
            "Лучше есть свежим.",
            "Если нужно хранить — держите без заправки до 1 суток в холодильнике.",
        ]
    if _has_word(name_low, ["суп", "борщ", "щи"]):
        return [
            "В холодильнике хранится до 3 суток.",
            "Разогревать лучше порционно, не кипятя весь объём каждый раз.",
        ]
    return [
        "В холодильнике хранится до 2–3 суток.",
        "Разогревать лучше на сковороде или в микроволновке небольшими порциями.",
    ]


def recipe_replacements(recipe: dict[str, Any]) -> list[str]:
    ingredients_text = _ingredient_names(recipe)
    replacements: list[str] = []
    if _has_word(ingredients_text, ["куриц"]):
        replacements.append("Курицу можно заменить индейкой.")
    if _has_word(ingredients_text, ["фарш"]):
        replacements.append("Фарш можно взять говяжий, куриный или смешанный.")
    if _has_word(ingredients_text, ["молоко"]):
        replacements.append("Молоко можно заменить водой или растительным напитком, если это подходит блюду.")
    if _has_word(ingredients_text, ["сметана"]):
        replacements.append("Сметану можно заменить натуральным йогуртом.")
    if _has_word(ingredients_text, ["рис"]):
        replacements.append("Рис можно заменить гречкой, булгуром или кускусом.")
    if _has_word(ingredients_text, ["паста", "макароны"]):
        replacements.append("Пасту можно заменить макаронами из твёрдых сортов пшеницы.")
    if not replacements:
        replacements.append("Часть ингредиентов можно заменить похожими по вкусу и текстуре продуктами.")
    return replacements[:3]


def recipe_serving(recipe: dict[str, Any]) -> list[str]:
    name_low = recipe.get("name", "").lower()
    if _has_word(name_low, ["паста", "макароны", "мяс", "куриц", "рыб", "котлет"]):
        return ["Овощной салат", "Свежая зелень", "Лёгкий соус по вкусу"]
    if _has_word(name_low, ["суп", "борщ", "щи"]):
        return ["Зелень", "Сметана", "Хлеб или сухарики"]
    if _has_word(name_low, ["каша", "сырники", "запеканка"]):
        return ["Фрукты или ягоды", "Мёд", "Йогурт или сметана"]
    if _has_word(name_low, ["салат"]):
        return ["Хлебцы", "Запечённая курица или рыба", "Лимонный сок"]
    return ["Свежие овощи", "Зелень", "Любимый соус"]


def format_recipe(r: dict[str, Any]) -> str:
    ingredients = "\n".join(f"• {item}" for item in r.get("ingredients", [])) or "• Ингредиенты не указаны"
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(detailed_steps_for_recipe(r), 1))
    tips = "\n".join(f"• {tip}" for tip in recipe_tips(r))
    storage = "\n".join(f"• {item}" for item in recipe_storage(r))
    replacements = "\n".join(f"• {item}" for item in recipe_replacements(r))
    serving = "\n".join(f"• {item}" for item in recipe_serving(r))
    tags = ", ".join(r.get("tags", []))

    text = (
        f"🍽 <b>{r['name']}</b>\n\n"
        f"⏱ <b>Время:</b> {r.get('time', '—')} мин\n"
        f"🔥 <b>Калорийность на двоих:</b> ~{r.get('calories', '—')} ккал\n"
        f"💰 <b>Примерно:</b> ~{r.get('price', '—')} ₽\n"
        f"🍳 <b>Сложность:</b> {r.get('difficulty', 'Легко')}\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"🛒 <b>Ингредиенты</b>\n{ingredients}\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"👨‍🍳 <b>Приготовление</b>\n{steps}\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"💡 <b>Советы</b>\n{tips}\n\n"
        f"📦 <b>Хранение</b>\n{storage}\n\n"
        f"🔄 <b>Чем заменить</b>\n{replacements}\n\n"
        f"🍽 <b>Подача</b>\n{serving}"
    )
    if tags:
        text += f"\n\n🏷 {tags}"
    return text


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


def recommend_recipe(user_id: int, exclude_recipe_id: int | None = None) -> tuple[dict[str, Any], list[str]]:
    target_category = current_meal_category()
    selected = set(get_fridge_items(user_id))
    favorites = set(get_favorites(user_id))
    recent = get_recent_cooked_recipe_ids(user_id, limit=5)
    ratings = get_user_ratings(user_id)
    candidates = recipes_for_category(target_category) or RECIPES

    scored = []
    for recipe in candidates:
        recipe_id = int(recipe.get("id", 0))
        score = 0
        reasons = []

        if exclude_recipe_id and recipe_id == exclude_recipe_id and len(candidates) > 1:
            score -= 1000

        required = detected_product_codes(recipe)
        matched = required & selected
        missing = required - selected

        if selected and required:
            if not missing:
                score += 50
                reasons.append("✅ Все продукты есть в холодильнике.")
            elif matched and len(missing) <= 2:
                score += 25 - len(missing) * 5
                missing_titles = ", ".join(FRIDGE_BY_CODE[c]["title"] for c in missing if c in FRIDGE_BY_CODE)
                if missing_titles:
                    reasons.append(f"🛒 Не хватает только: {missing_titles}.")
            elif matched:
                score += 10

        if recipe_id in favorites:
            score += 20
            reasons.append("❤️ Есть в избранном.")

        rating = ratings.get(recipe_id)
        if rating:
            score += rating * 4
            if rating >= 4:
                reasons.append(f"⭐ Вы оценили это блюдо на {rating}/5.")

        if recipe_id in recent:
            score -= 25
        elif get_cooked_count(user_id) > 0:
            score += 8
            reasons.append("📖 Давно не появлялось в истории.")

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
    set_user_flag(user_id, "last_recommendation_id", str(recipe["id"]))
    return recipe, reasons[:4]


def format_recommendation(recipe: dict[str, Any], reasons: list[str]) -> str:
    lines = [
        f"🍽 <b>Сегодня предлагаю «{recipe['name']}»</b>",
        "",
        "<b>Почему именно это блюдо?</b>",
    ]
    if reasons:
        lines.extend(reasons)
    else:
        lines.append("🍽 Подходит под текущее время дня.")
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


@dp.callback_query(F.data == "home:main")
async def home_from_callback(callback: CallbackQuery):
    await callback.message.answer(
        format_home_text(),
        reply_markup=home_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


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
    action = callback.data.split(":", 1)[1] if ":" in callback.data else "now"
    exclude_recipe_id = None
    if action == "again":
        last_id = get_user_flag(callback.from_user.id, "last_recommendation_id")
        if last_id and last_id.isdigit():
            exclude_recipe_id = int(last_id)

    recipe, reasons = recommend_recipe(callback.from_user.id, exclude_recipe_id=exclude_recipe_id)
    await callback.message.edit_text(
        format_recommendation(recipe, reasons),
        reply_markup=recommendation_keyboard(recipe),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(F.text == "📅 Меню недели")
async def weekly_menu_message(message: Message):
    menu = get_saved_weekly_menu(message.from_user.id)
    await message.answer(
        format_weekly_menu(menu),
        reply_markup=weekly_menu_keyboard(bool(menu)),
        parse_mode="HTML",
    )


@dp.message(F.text == "🔍 Поиск")
async def search_message(message: Message):
    SEARCH_WAITING.add(message.from_user.id)
    await message.answer(
        "🔍 <b>Поиск блюда</b>\n\n"
        "Введите название блюда или ингредиент.\n\n"
        "Например: <b>курица</b>, <b>рис</b>, <b>сыр</b>, <b>суп</b>, <b>творог</b>.\n\n"
        "Или выберите фильтр 👇",
        reply_markup=filter_menu_keyboard(),
        parse_mode="HTML",
    )



@dp.message(F.text.in_(["⚙️ Настройки", "⚙️ Фильтры"]))
async def settings_message(message: Message):
    await message.answer(
        settings_text(),
        reply_markup=settings_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "settings:menu")
async def settings_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        settings_text(),
        reply_markup=settings_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "settings:notifications")
async def settings_notifications_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        notification_settings_text(callback.from_user.id),
        reply_markup=notification_settings_keyboard(callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "notify:toggle")
async def notifications_toggle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    set_notifications_enabled(user_id, not notifications_enabled(user_id))
    await callback.message.edit_text(
        notification_settings_text(user_id),
        reply_markup=notification_settings_keyboard(user_id),
        parse_mode="HTML",
    )
    await callback.answer("Настройки уведомлений обновлены")


@dp.callback_query(F.data.startswith("notify:time:"))
async def notifications_time_callback(callback: CallbackQuery):
    meal = callback.data.split(":", 2)[2]
    if meal not in NOTIFICATION_DEFAULT_TIMES:
        await callback.answer("Неизвестный приём пищи", show_alert=True)
        return
    await callback.message.edit_text(
        notification_time_text(callback.from_user.id, meal),
        reply_markup=notification_time_keyboard(meal),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("notify:set:"))
async def notifications_set_time_callback(callback: CallbackQuery):
    _, _, meal, raw_time = callback.data.split(":")
    if meal not in NOTIFICATION_DEFAULT_TIMES or len(raw_time) != 4 or not raw_time.isdigit():
        await callback.answer("Некорректное время", show_alert=True)
        return
    time_value = f"{raw_time[:2]}:{raw_time[2:]}"
    set_user_flag(callback.from_user.id, f"notify_time_{meal}", time_value)
    await callback.message.edit_text(
        notification_settings_text(callback.from_user.id),
        reply_markup=notification_settings_keyboard(callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer(f"Время сохранено: {time_value}")


@dp.callback_query(F.data == "settings:history")
async def settings_history_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        format_history(callback.from_user.id),
        reply_markup=history_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "settings:weekly")
async def settings_weekly_callback(callback: CallbackQuery):
    menu = get_saved_weekly_menu(callback.from_user.id)
    await callback.message.edit_text(
        format_weekly_menu(menu),
        reply_markup=weekly_menu_keyboard(bool(menu)),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "week:generate")
async def week_generate_callback(callback: CallbackQuery):
    menu = generate_weekly_menu(callback.from_user.id)
    await callback.message.edit_text(
        format_weekly_menu(menu),
        reply_markup=weekly_menu_keyboard(True),
        parse_mode="HTML",
    )
    await callback.answer("Меню составлено")


@dp.callback_query(F.data == "week:shopping")
async def week_shopping_callback(callback: CallbackQuery):
    added = add_weekly_menu_to_shopping(callback.from_user.id)
    await callback.answer(f"Добавлено продуктов: {added} 🛒")
    await callback.message.answer(
        f"🛒 Добавлено в список покупок: <b>{added}</b>\n\n"
        "Одинаковые продукты объединены, где это безопасно.",
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "week:replace_menu")
async def week_replace_menu_callback(callback: CallbackQuery):
    menu = get_saved_weekly_menu(callback.from_user.id)
    if not menu:
        await callback.answer("Сначала составь меню недели", show_alert=True)
        return
    await callback.message.edit_text(
        "🔄 <b>Заменить блюдо</b>\n\nВыбери конкретный приём пищи, который нужно заменить.",
        reply_markup=week_replace_menu_keyboard(menu),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("week:replace:"))
async def week_replace_item_callback(callback: CallbackQuery):
    try:
        _, _, day_raw, slot_raw = str(callback.data).split(":")
        day_index = int(day_raw)
        slot_index = int(slot_raw)
    except (ValueError, AttributeError):
        await callback.answer("Не получилось заменить блюдо", show_alert=True)
        return

    new_recipe = replace_weekly_menu_item(callback.from_user.id, day_index, slot_index)
    if not new_recipe:
        await callback.answer("Не нашёл замену", show_alert=True)
        return

    menu = get_saved_weekly_menu(callback.from_user.id)
    await callback.message.edit_text(
        format_weekly_menu(menu),
        reply_markup=weekly_menu_keyboard(True),
        parse_mode="HTML",
    )
    await callback.answer(f"Заменил на: {new_recipe['name']}")


@dp.callback_query(F.data == "week:clear")
async def week_clear_callback(callback: CallbackQuery):
    clear_weekly_menu(callback.from_user.id)
    await callback.message.edit_text(
        format_weekly_menu({}),
        reply_markup=weekly_menu_keyboard(False),
        parse_mode="HTML",
    )
    await callback.answer("Меню очищено")


@dp.callback_query(F.data == "history:clear")
async def history_clear_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧹 <b>Очистить историю?</b>\n\nЭто удалит список приготовленных блюд. Оценки рецептов останутся.",
        reply_markup=confirm_clear_history_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "history:clear_confirm")
async def history_clear_confirm_callback(callback: CallbackQuery):
    clear_cooking_history(callback.from_user.id)
    await callback.message.edit_text(
        "📖 <b>История приготовлений</b>\n\nИстория очищена.",
        reply_markup=history_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer("История очищена")


@dp.callback_query(F.data == "settings:profiles")
async def settings_profiles_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        format_profile_summary(callback.from_user.id),
        reply_markup=back_to_settings_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "settings:about")
async def settings_about_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        about_text(callback.from_user.id),
        reply_markup=about_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "filters:menu")
async def filters_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔍 <b>Фильтры поиска</b>\n\nВыбери, какие блюда показать:",
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

    regular, taste = split_taste_items(items)

    lines = ["🛒 <b>Список продуктов</b>", ""]
    for item in sorted(regular, key=str.lower):
        lines.append(f"☐ {item}")

    if taste:
        if regular:
            lines.append("")
        lines.append("<b>По вкусу:</b>")
        for item in sorted(taste, key=str.lower):
            lines.append(f"☐ {item}")

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


@dp.callback_query(F.data.startswith("cooked:"))
async def mark_cooked(callback: CallbackQuery):
    recipe_id = int(callback.data.split(":")[1])
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    total = add_cooked_recipe(callback.from_user.id, recipe_id)
    await callback.answer("Отметил как приготовленное ✅")
    await callback.message.answer(
        f"✅ <b>Приготовили: {recipe['name']}</b>\n\n"
        f"🍳 Всего приготовлено блюд: <b>{total}</b>\n\n"
        "Можно сразу оценить блюдо:",
        reply_markup=rating_keyboard(recipe_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("rate:"))
async def rate_recipe(callback: CallbackQuery):
    recipe_id = int(callback.data.split(":")[1])
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    current = get_user_recipe_rating(callback.from_user.id, recipe_id)
    suffix = f"\n\nТекущая оценка: <b>{current}⭐</b>" if current else ""
    await callback.message.answer(
        f"⭐ <b>Оценить блюдо</b>\n\n{recipe['name']}{suffix}\n\nВыбери оценку:",
        reply_markup=rating_keyboard(recipe_id),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("rateval:"))
async def save_recipe_rating(callback: CallbackQuery):
    _, recipe_id_s, rating_s = callback.data.split(":")
    recipe_id = int(recipe_id_s)
    rating = int(rating_s)
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    set_recipe_rating(callback.from_user.id, recipe_id, rating)
    await callback.answer(f"Оценка сохранена: {rating}⭐")
    await callback.message.edit_text(
        f"⭐ <b>Оценка сохранена</b>\n\n{recipe['name']} — <b>{rating}⭐</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главная", callback_data="home:main")]]),
        parse_mode="HTML",
    )


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
    asyncio.create_task(notification_loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
