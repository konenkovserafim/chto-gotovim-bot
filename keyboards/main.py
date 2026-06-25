from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Завтрак", callback_data="category:breakfast")],
        [InlineKeyboardButton(text="🍲 Обед", callback_data="category:lunch")],
        [InlineKeyboardButton(text="🍽 Ужин", callback_data="category:dinner")],
        [InlineKeyboardButton(text="🥗 Перекус", callback_data="category:snack")],
        [InlineKeyboardButton(text="🎲 Что приготовить?", callback_data="random:any")],
        [InlineKeyboardButton(text="📋 Меню на день", callback_data="day_menu")],
    ])


def category_menu(category: str, recipes: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for index, recipe in enumerate(recipes):
        rows.append([InlineKeyboardButton(text=f"{index + 1}. {recipe['title']}", callback_data=f"recipe:{category}:{index}")])
    rows.append([
        InlineKeyboardButton(text="🔄 Другие варианты", callback_data=f"category:{category}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipe_actions(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другое блюдо", callback_data=f"category:{category}")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back:main")],
    ])
