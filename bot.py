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
USER_DATA_FILE = Path("user_data.json")

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


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_recipes() -> List[Dict[str, Any]]:
    return load_json_file(DATA_FILE, [])


RECIPES = load_recipes()
RECIPES_BY_ID = {r["id"]: r for r in RECIPES}


def get_user_record(user_id: int) -> Dict[str, Any]:
    data = load_json_file(USER_DATA_FILE, {})
    key = str(user_id)
    if key not in data:
        data[key] = {"favorites": [], "shopping": []}
        save_json_file(USER_DATA_FILE, data)
    data[key].setdefault("favorites", [])
    data[key].setdefault("shopping", [])
    return data[key]


def update_user_record(user_id: int, record: Dict[str, Any]) -> None:
    data = load_json_file(USER_DATA_FILE, {})
    data[str(user_id)] = record
    save_json_file(USER_DATA_FILE, data)


def normalize_item(item: str) -> str:
    return " ".join(item.strip().split())


def add_shopping_item(record: Dict[str, Any], item: str) -> bool:
    item = normalize_item(item)
    if not item:
        return False
    shopping = record.setdefault("shopping", [])
    existing = {normalize_item(x).casefold() for x in shopping}
    if item.casefold() not in existing:
        shopping.append(item)
        return True
    return False


def shopping_keyboard(items: List[str]) -> InlineKeyboardMarkup:
    rows = []
    if items:
        rows.append([InlineKeyboardButton(text="➖ Удалить продукт", callback_data="shopping_delete_menu")])
        rows.append([InlineKeyboardButton(text="🧹 Очистить список", callback_data="clear_shopping")])
    rows.append([InlineKeyboardButton(text="➕ Добавить вручную", callback_data="shopping_add_manual")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shopping_delete_keyboard(items: List[str]) -> InlineKeyboardMarkup:
    rows = []
    for index, item in enumerate(items[:40]):
        rows.append([InlineKeyboardButton(text=f"❌ {item}", callback_data=f"shopping_delete:{index}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="shopping_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipes_by_category(category: str) -> List[Dict[str, Any]]:
    return [r for r in RECIPES if r.get("category") == category]


def recipe_card(recipe: Dict[str, Any]) -> str:
    ingredients = "\n".join(f"• {item}" for item in recipe["ingredients"])
    steps = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(recipe["steps"]))
    portions = recipe.get("portions", "👨 Серафим — порция побольше.\n👩 Таня — порция чуть легче.")
    protein = recipe.get("protein", "—")
    fats = recipe.get("fats", "—")
    carbs = recipe.get("carbs", "—")
    note = recipe.get("note", "")
    note_block = f"\n\n💬 <b>Заметка</b>\n{note}" if note else ""
    return (
        f"{recipe['emoji']} <b>{recipe['title']}</b>\n\n"
        f"⏱ <b>Время:</b> {recipe['time']}\n"
        f"🔥 <b>Калорийность:</b> {recipe['calories']}\n"
        f"💰 <b>Стоимость:</b> {recipe.get('price', 'примерно')}\n"
        f"🥩 <b>БЖУ:</b> Б {protein} / Ж {fats} / У {carbs}\n"
        f"━━━━━━━━━━━━━━\n"
        f"👫 <b>Порции</b>\n{portions}\n\n"
        f"🛒 <b>Ингредиенты на двоих</b>\n{ingredients}\n\n"
        f"👨‍🍳 <b>Приготовление</b>\n{steps}"
        f"{note_block}"
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
    record = get_user_record(message.from_user.id)
    favs = record.get("favorites", [])
    if not favs:
        await message.answer("❤️ В избранном пока пусто. Открой блюдо и нажми «В избранное».")
        return

    rows = []
    lines = ["❤️ <b>Избранное</b>", "", "Нажми на блюдо, чтобы открыть карточку:", ""]
    for recipe_id in favs:
        recipe = RECIPES_BY_ID.get(recipe_id)
        if recipe:
            lines.append(f"• {recipe['emoji']} {recipe['title']}")
            rows.append([InlineKeyboardButton(text=f"{recipe['emoji']} {recipe['title']}", callback_data=f"recipe:{recipe_id}")])
    rows.append([InlineKeyboardButton(text="🧹 Очистить избранное", callback_data="clear_favorites")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@dp.message(F.text == "🛒 Список продуктов")
async def shopping_list(message: Message):
    record = get_user_record(message.from_user.id)
    items = record.get("shopping", [])
    if not items:
        await message.answer("🛒 Список продуктов пока пуст. Открой блюдо и нажми «В список продуктов».")
        return

    unique_items = []
    for item in items:
        if item not in unique_items:
            unique_items.append(item)
    text = "🛒 <b>Список продуктов</b>\n\n" + "\n".join(f"• {item}" for item in unique_items)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧹 Очистить список", callback_data="clear_shopping")]])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


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
    record = get_user_record(callback.from_user.id)
    favorites_list = record.setdefault("favorites", [])
    if recipe_id in favorites_list:
        await callback.answer("Уже есть в избранном ❤️")
        return
    favorites_list.append(recipe_id)
    update_user_record(callback.from_user.id, record)
    await callback.answer("Добавлено в избранное ❤️")


@dp.callback_query(F.data == "clear_favorites")
async def clear_favorites(callback: CallbackQuery):
    record = get_user_record(callback.from_user.id)
    record["favorites"] = []
    update_user_record(callback.from_user.id, record)
    await callback.message.answer("❤️ Избранное очищено.")
    await callback.answer()


@dp.callback_query(F.data.startswith("shop:"))
async def add_shopping(callback: CallbackQuery):
    recipe_id = callback.data.split(":", 1)[1]
    recipe = RECIPES_BY_ID.get(recipe_id)
    if not recipe:
        await callback.answer("Рецепт не найден")
        return
    record = get_user_record(callback.from_user.id)
    added_count = 0
    for item in recipe["ingredients"]:
        if add_shopping_item(record, item):
            added_count += 1
    update_user_record(callback.from_user.id, record)
    await callback.answer(f"Добавлено продуктов: {added_count} 🛒")


@dp.callback_query(F.data == "shopping_add_manual")
async def shopping_add_manual(callback: CallbackQuery):
    record = get_user_record(callback.from_user.id)
    record["awaiting_shopping_item"] = True
    update_user_record(callback.from_user.id, record)
    await callback.message.answer("➕ Напиши продукт, который добавить в список. Например: <b>молоко 1 л</b>", parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "shopping_delete_menu")
async def shopping_delete_menu(callback: CallbackQuery):
    record = get_user_record(callback.from_user.id)
    items = record.get("shopping", [])
    if not items:
        await callback.message.answer("🛒 Список уже пуст.")
        await callback.answer()
        return
    await callback.message.answer(
        "Нажми на продукт, который нужно удалить:",
        reply_markup=shopping_delete_keyboard(items),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("shopping_delete:"))
async def shopping_delete_item(callback: CallbackQuery):
    index_text = callback.data.split(":", 1)[1]
    record = get_user_record(callback.from_user.id)
    items = record.get("shopping", [])
    try:
        index = int(index_text)
        removed = items.pop(index)
    except Exception:
        await callback.answer("Не получилось удалить")
        return
    record["shopping"] = items
    update_user_record(callback.from_user.id, record)
    await callback.message.answer(f"❌ Удалил: <b>{removed}</b>", parse_mode="HTML")
    if items:
        text = "🛒 <b>Список продуктов</b>

" + "
".join(f"• {item}" for item in items)
        await callback.message.answer(text, reply_markup=shopping_keyboard(items), parse_mode="HTML")
    else:
        await callback.message.answer("🛒 Список продуктов теперь пуст.", reply_markup=shopping_keyboard(items))
    await callback.answer()


@dp.callback_query(F.data == "shopping_back")
async def shopping_back(callback: CallbackQuery):
    record = get_user_record(callback.from_user.id)
    items = record.get("shopping", [])
    if items:
        text = "🛒 <b>Список продуктов</b>

" + "
".join(f"• {item}" for item in items)
    else:
        text = "🛒 <b>Список продуктов</b>

Пока пусто."
    await callback.message.answer(text, reply_markup=shopping_keyboard(items), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "clear_shopping")
async def clear_shopping(callback: CallbackQuery):
    record = get_user_record(callback.from_user.id)
    record["shopping"] = []
    record["awaiting_shopping_item"] = False
    update_user_record(callback.from_user.id, record)
    await callback.message.answer("🛒 Список продуктов очищен.", reply_markup=shopping_keyboard([]))
    await callback.answer()


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
