import random

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.main import category_menu, main_menu, recipe_actions
from utils.recipes import CATEGORY_NAMES, format_recipe, get_random_recipes, get_recipe, random_recipe

router = Router()


@router.callback_query(F.data.startswith("category:"))
async def show_category(callback: CallbackQuery):
    category = callback.data.split(":")[1]
    recipes = get_random_recipes(category, limit=5)
    text = f"{CATEGORY_NAMES[category]}\n\nСегодня можно приготовить:" 
    await callback.message.edit_text(text, reply_markup=category_menu(category, recipes))
    await callback.answer()


@router.callback_query(F.data.startswith("recipe:"))
async def show_recipe(callback: CallbackQuery):
    _, category, index = callback.data.split(":")
    recipe = get_recipe(category, int(index))
    await callback.message.edit_text(format_recipe(recipe), reply_markup=recipe_actions(category))
    await callback.answer()


@router.callback_query(F.data == "random:any")
async def show_random_recipe(callback: CallbackQuery):
    category, recipe = random_recipe()
    await callback.message.edit_text(format_recipe(recipe), reply_markup=recipe_actions(category))
    await callback.answer()


@router.callback_query(F.data == "day_menu")
async def day_menu(callback: CallbackQuery):
    breakfast = random.choice(get_random_recipes("breakfast", limit=10))
    lunch = random.choice(get_random_recipes("lunch", limit=10))
    dinner = random.choice(get_random_recipes("dinner", limit=10))
    snack = random.choice(get_random_recipes("snack", limit=10))

    text = (
        "📋 <b>Меню на день</b>\n\n"
        f"🍳 Завтрак: {breakfast['title']}\n"
        f"🍲 Обед: {lunch['title']}\n"
        f"🥗 Перекус: {snack['title']}\n"
        f"🍽 Ужин: {dinner['title']}\n\n"
        "Нажми на нужный раздел в главном меню, чтобы открыть рецепты."
    )
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()
