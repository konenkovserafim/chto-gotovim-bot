import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CATEGORY_FILES = {
    "breakfast": "breakfasts.json",
    "lunch": "lunches.json",
    "dinner": "dinners.json",
    "snack": "snacks.json",
}

CATEGORY_NAMES = {
    "breakfast": "🍳 Завтрак",
    "lunch": "🍲 Обед",
    "dinner": "🍽 Ужин",
    "snack": "🥗 Перекус",
}


def load_recipes(category: str) -> list[dict]:
    filename = CATEGORY_FILES[category]
    with open(DATA_DIR / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def get_random_recipes(category: str, limit: int = 5) -> list[dict]:
    recipes = load_recipes(category)
    if len(recipes) <= limit:
        return recipes
    return random.sample(recipes, limit)


def get_recipe(category: str, index: int) -> dict:
    recipes = load_recipes(category)
    return recipes[index]


def random_recipe() -> tuple[str, dict]:
    category = random.choice(list(CATEGORY_FILES.keys()))
    recipe = random.choice(load_recipes(category))
    return category, recipe


def format_recipe(recipe: dict) -> str:
    ingredients = "\n".join([f"• {item}" for item in recipe["ingredients"]])
    steps = "\n".join([f"{i + 1}. {step}" for i, step in enumerate(recipe["steps"])])

    return (
        f"{recipe['emoji']} <b>{recipe['title']}</b>\n\n"
        f"⏱ Время: {recipe['time']}\n"
        f"💰 Стоимость: {recipe['cost']}\n"
        f"🔥 Калорийность примерно:\n"
        f"• Серафим — {recipe['calories_serafim']} ккал\n"
        f"• Таня — {recipe['calories_tanya']} ккал\n\n"
        f"🛒 <b>Ингредиенты на двоих:</b>\n{ingredients}\n\n"
        f"👨‍🍳 <b>Рецепт:</b>\n{steps}\n\n"
        f"🍽 <b>Порции:</b>\n{recipe['portions']}"
    )
