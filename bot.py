import asyncio
import logging
import os
import random
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway Variables.")

@dataclass
class Recipe:
    category: str
    name: str
    emoji: str
    time: str
    price: str
    kcal_serafim: str
    kcal_tanya: str
    ingredients: list[str]
    steps: list[str]
    portions: str

RECIPES: dict[str, list[Recipe]] = {
    "🍳 Завтрак": [
        Recipe("🍳 Завтрак", "Омлет с помидорами", "🍳", "10–15 минут", "~160 ₽", "450 ккал", "300 ккал",
               ["4 яйца", "1 помидор", "немного молока", "зелень", "соль"],
               ["Взбей яйца с молоком и солью.", "Нарежь помидор.", "Слегка обжарь помидор.", "Залей яйцами и готовь под крышкой 5–7 минут."],
               "Серафиму — 2–3 яйца. Тане — 1–2 яйца + больше овощей."),
        Recipe("🍳 Завтрак", "Творог с мёдом и молоком", "🥣", "3 минуты", "~220 ₽", "500 ккал", "300 ккал",
               ["творог 400–500 г", "мёд 1–2 ч. л.", "молоко по желанию"],
               ["Разложи творог по тарелкам.", "Добавь немного мёда.", "Молоко можно пить отдельно или добавить чуть-чуть в творог."],
               "Серафиму — 250–300 г творога. Тане — 150–200 г."),
        Recipe("🍳 Завтрак", "Овсянка с бананом", "🍌", "10 минут", "~120 ₽", "450 ккал", "300 ккал",
               ["овсянка", "молоко или вода", "1 банан", "щепотка соли"],
               ["Свари овсянку на молоке или воде.", "Нарежь банан.", "Добавь банан сверху и перемешай."],
               "Серафиму — порция побольше. Тане — меньше каши, больше фрукта."),
    ],
    "🍲 Обед": [
        Recipe("🍲 Обед", "Курица с гречкой и салатом", "🍲", "30 минут", "~350 ₽", "750 ккал", "500 ккал",
               ["куриное филе 350–450 г", "гречка", "огурец", "помидор", "зелень", "немного масла"],
               ["Отвари гречку.", "Курицу посоли и обжарь или потуши.", "Нарежь салат.", "Добавь зелень и немного масла."],
               "Серафиму — больше курицы и гречки. Тане — больше салата, меньше крупы."),
        Recipe("🍲 Обед", "Паста с курицей", "🍝", "25–30 минут", "~430 ₽", "850 ккал", "550 ккал",
               ["макароны 180–220 г сухих", "курица 300–400 г", "молоко/сливки", "сыр по желанию", "соль, специи"],
               ["Отвари макароны.", "Обжарь курицу кусочками.", "Добавь немного молока или сливок.", "Смешай с макаронами."],
               "Серафиму — больше пасты. Тане — меньше пасты + овощи."),
        Recipe("🍲 Обед", "Картошка с курицей и овощами", "🥔", "35 минут", "~380 ₽", "800 ккал", "520 ккал",
               ["курица", "картошка", "морковь/лук по желанию", "огурец или помидор", "специи"],
               ["Нарежь картошку и курицу.", "Обжарь или потуши вместе.", "Добавь специи.", "Подавай с овощами."],
               "Серафиму — больше картошки. Тане — больше курицы и овощей."),
    ],
    "🍽 Ужин": [
        Recipe("🍽 Ужин", "Рыба с картошкой и салатом", "🐟", "30–40 минут", "~450 ₽", "700 ккал", "450 ккал",
               ["рыба 350–450 г", "картошка 4–5 шт.", "огурец/помидор", "зелень", "немного масла"],
               ["Картошку отвари или запеки.", "Рыбу посоли и приготовь на сковороде или в духовке.", "Сделай салат."],
               "Серафиму — больше картошки. Тане — больше рыбы и салата, меньше картошки."),
        Recipe("🍽 Ужин", "Омлет с овощами", "🥚", "15 минут", "~180 ₽", "450 ккал", "300 ккал",
               ["4 яйца", "помидор", "зелень", "немного молока", "соль"],
               ["Нарежь овощи.", "Слегка обжарь.", "Залей яйцами с молоком.", "Готовь под крышкой."],
               "Хороший лёгкий ужин. Серафиму — побольше, Тане — поменьше + овощи."),
        Recipe("🍽 Ужин", "Творожная запеканка", "🧀", "40 минут", "~300 ₽", "650 ккал", "420 ккал",
               ["творог 500 г", "2 яйца", "манка/мука 2–3 ст. л.", "немного сахара или мёда", "сметана по желанию"],
               ["Смешай творог, яйца и манку.", "Добавь чуть сахара или мёда.", "Выложи в форму.", "Запекай 30–35 минут."],
               "Серафиму — кусок побольше. Тане — меньше, без лишней сметаны."),
    ],
    "🥗 Перекус": [
        Recipe("🥗 Перекус", "Кефир и фрукт", "🍎", "2 минуты", "~120 ₽", "250 ккал", "180 ккал",
               ["кефир", "яблоко или банан"],
               ["Налей кефир.", "Добавь фрукт отдельно."],
               "Простой перекус, чтобы не превращать его во второй ужин."),
        Recipe("🥗 Перекус", "Бутерброд с курицей", "🥪", "5 минут", "~180 ₽", "400 ккал", "250 ккал",
               ["хлеб", "готовая курица", "огурец/помидор", "зелень"],
               ["Положи курицу на хлеб.", "Добавь овощи и зелень.", "Можно слегка подогреть."],
               "Серафиму — 2 бутерброда. Тане — 1 бутерброд + овощи."),
    ],
}

last_recipe: dict[int, Recipe] = {}
favorites: dict[int, list[str]] = {}
shopping: dict[int, list[str]] = {}

def keyboard(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=x) for x in row] for row in rows], resize_keyboard=True)

main_menu = keyboard([
    ["🍳 Завтрак", "🍲 Обед"],
    ["🍽 Ужин", "🥗 Перекус"],
    ["🎲 Что приготовить?"],
    ["❤️ Избранное", "🛒 Список продуктов"],
])

def category_menu(category: str) -> ReplyKeyboardMarkup:
    rows = [[f"{r.emoji} {r.name}"] for r in RECIPES[category]]
    rows.append(["🔄 Другие варианты", "⬅ Назад"])
    return keyboard(rows)

action_menu = keyboard([
    ["❤️ В избранное", "🛒 В список продуктов"],
    ["🔄 Другой вариант", "⬅ Назад"],
])

def recipe_text(r: Recipe) -> str:
    ingredients = "\n".join(f"• {i}" for i in r.ingredients)
    steps = "\n".join(f"{n}. {s}" for n, s in enumerate(r.steps, 1))
    return (
        f"{r.emoji} <b>{r.name}</b>\n\n"
        f"⏱ <b>Время:</b> {r.time}\n"
        f"💰 <b>Стоимость:</b> {r.price} на двоих\n\n"
        f"🔥 <b>Калорийность примерно:</b>\n"
        f"👨 Серафим — {r.kcal_serafim}\n"
        f"👩 Таня — {r.kcal_tanya}\n\n"
        f"🛒 <b>Ингредиенты:</b>\n{ingredients}\n\n"
        f"👨‍🍳 <b>Рецепт:</b>\n{steps}\n\n"
        f"🍽 <b>Порции:</b>\n{r.portions}"
    )

def find_recipe_by_button(text: str) -> Recipe | None:
    for items in RECIPES.values():
        for r in items:
            if text == f"{r.emoji} {r.name}":
                return r
    return None

async def show_recipe(message: Message, r: Recipe):
    last_recipe[message.from_user.id] = r
    await message.answer(recipe_text(r), reply_markup=action_menu, parse_mode="HTML")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer(
            "🍽 <b>Привет! Я бот «Что готовим?»</b>\n\n"
            "Помогу выбрать завтрак, обед, ужин или перекус для вас с Таней.",
            reply_markup=main_menu,
            parse_mode="HTML",
        )

    @dp.message(F.text.in_(RECIPES.keys()))
    async def show_category(message: Message):
        await message.answer(
            f"{message.text}\n\nСегодня можно приготовить:",
            reply_markup=category_menu(message.text),
        )

    @dp.message(F.text == "⬅ Назад")
    async def back(message: Message):
        await message.answer("Главное меню 👇", reply_markup=main_menu)

    @dp.message(F.text == "🎲 Что приготовить?")
    async def random_any(message: Message):
        category = random.choice(list(RECIPES.keys()))
        await show_recipe(message, random.choice(RECIPES[category]))

    @dp.message(F.text == "🔄 Другие варианты")
    async def other_options(message: Message):
        await message.answer("Выбери раздел 👇", reply_markup=main_menu)

    @dp.message(F.text == "🔄 Другой вариант")
    async def another_recipe(message: Message):
        old = last_recipe.get(message.from_user.id)
        category = old.category if old else random.choice(list(RECIPES.keys()))
        choices = [r for r in RECIPES[category] if r != old] or RECIPES[category]
        await show_recipe(message, random.choice(choices))

    @dp.message(F.text == "❤️ В избранное")
    async def add_favorite(message: Message):
        r = last_recipe.get(message.from_user.id)
        if not r:
            await message.answer("Сначала выбери блюдо.", reply_markup=main_menu)
            return
        favorites.setdefault(message.from_user.id, [])
        if r.name not in favorites[message.from_user.id]:
            favorites[message.from_user.id].append(r.name)
        await message.answer(f"❤️ Добавил в избранное: {r.name}", reply_markup=action_menu)

    @dp.message(F.text == "❤️ Избранное")
    async def show_favorites(message: Message):
        items = favorites.get(message.from_user.id, [])
        if not items:
            await message.answer("Пока избранное пустое.", reply_markup=main_menu)
        else:
            await message.answer("❤️ Избранное:\n" + "\n".join(f"• {x}" for x in items), reply_markup=main_menu)

    @dp.message(F.text == "🛒 В список продуктов")
    async def add_shopping(message: Message):
        r = last_recipe.get(message.from_user.id)
        if not r:
            await message.answer("Сначала выбери блюдо.", reply_markup=main_menu)
            return
        shopping.setdefault(message.from_user.id, [])
        for item in r.ingredients:
            if item not in shopping[message.from_user.id]:
                shopping[message.from_user.id].append(item)
        await message.answer(f"🛒 Добавил продукты для блюда: {r.name}", reply_markup=action_menu)

    @dp.message(F.text == "🛒 Список продуктов")
    async def show_shopping(message: Message):
        items = shopping.get(message.from_user.id, [])
        if not items:
            await message.answer("Список продуктов пока пустой.", reply_markup=main_menu)
        else:
            await message.answer("🛒 Список продуктов:\n" + "\n".join(f"• {x}" for x in items), reply_markup=main_menu)

    @dp.message()
    async def recipe_or_unknown(message: Message):
        r = find_recipe_by_button(message.text or "")
        if r:
            await show_recipe(message, r)
        else:
            await message.answer("Выбери вариант в меню 👇", reply_markup=main_menu)

    logging.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
