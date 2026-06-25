import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway Variables.")

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍳 Завтрак"), KeyboardButton(text="🍲 Обед")],
        [KeyboardButton(text="🍽 Ужин"), KeyboardButton(text="🥗 Перекус")],
        [KeyboardButton(text="🎲 Что приготовить?")],
    ],
    resize_keyboard=True,
)

RECIPES = {
    "🍳 Завтрак": [
        """🍳 Омлет с помидорами\n\n⏱ 10–15 минут\n🔥 Примерно: 350–450 ккал на порцию\n\nИнгредиенты на двоих:\n• 4 яйца\n• 1 помидор\n• немного молока\n• зелень\n• соль\n\nРецепт:\n1. Взбей яйца с молоком и солью.\n2. Нарежь помидор.\n3. Обжарь помидор 1–2 минуты.\n4. Залей яйцами и готовь под крышкой.\n\nПорции:\nСерафим — побольше.\nТаня — поменьше + овощи.""",
        """🥣 Творог с мёдом и молоком\n\n⏱ 3 минуты\n🔥 Примерно: 300–500 ккал на порцию\n\nИнгредиенты на двоих:\n• творог 400–500 г\n• мёд 1–2 ч. л.\n• молоко по желанию\n\nРецепт:\n1. Разложить творог по тарелкам.\n2. Добавить немного мёда.\n3. Молоко — отдельно или чуть в творог.\n\nПорции:\nСерафим — 250–300 г.\nТаня — 150–200 г.""",
    ],
    "🍲 Обед": [
        """🍲 Курица с гречкой и салатом\n\n⏱ 30 минут\n🔥 Примерно: 500–750 ккал на порцию\n\nИнгредиенты на двоих:\n• куриное филе 350–450 г\n• гречка\n• огурец\n• помидор\n• зелень\n• немного масла\n\nРецепт:\n1. Отвари гречку.\n2. Курицу посоли и обжарь или потуши.\n3. Нарежь салат.\n4. Добавь немного масла и зелень.\n\nПорции:\nСерафим — больше курицы и гречки.\nТаня — больше салата, меньше крупы.""",
        """🍝 Паста с курицей\n\n⏱ 25–30 минут\n🔥 Примерно: 600–850 ккал на порцию\n\nИнгредиенты на двоих:\n• макароны 180–220 г сухих\n• курица 300–400 г\n• немного сливок или молока\n• сыр по желанию\n• соль, специи\n\nРецепт:\n1. Отвари макароны.\n2. Обжарь курицу кусочками.\n3. Добавь немного молока/сливок.\n4. Смешай с макаронами.\n\nПорции:\nСерафим — побольше пасты.\nТаня — поменьше пасты + овощи.""",
    ],
    "🍽 Ужин": [
        """🐟 Рыба с картошкой и салатом\n\n⏱ 30–40 минут\n🔥 Примерно: 450–700 ккал на порцию\n\nИнгредиенты на двоих:\n• рыба 350–450 г\n• картошка 4–5 шт.\n• огурец/помидор\n• зелень\n• немного масла\n\nРецепт:\n1. Картошку отвари или запеки.\n2. Рыбу посоли и приготовь на сковороде/в духовке.\n3. Сделай салат.\n\nПорции:\nСерафим — больше картошки.\nТаня — больше рыбы и салата, меньше картошки.""",
        """🥚 Омлет с овощами\n\n⏱ 15 минут\n🔥 Примерно: 300–450 ккал на порцию\n\nИнгредиенты на двоих:\n• 4 яйца\n• овощи: помидор, перец, зелень\n• немного молока\n• соль\n\nРецепт:\n1. Нарежь овощи.\n2. Слегка обжарь.\n3. Залей яйцами с молоком.\n4. Готовь под крышкой.\n\nХороший лёгкий ужин, когда не хочется тяжёлого.""",
    ],
    "🥗 Перекус": [
        """🍎 Лёгкий перекус\n\nВарианты:\n• творог + ягоды/мёд\n• яблоко + чай\n• кефир\n• йогурт без лишнего сахара\n• бутерброд с курицей\n\nЛучше выбрать то, что не превращается в полноценный второй ужин 😄""",
    ],
}

async def send_recipe(message: Message, category: str):
    await message.answer(random.choice(RECIPES[category]), reply_markup=main_menu)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer(
            "🍽 Привет! Я бот «Что готовим?»\n\n"
            "Помогу выбрать завтрак, обед, ужин или перекус для вас с Таней.",
            reply_markup=main_menu,
        )

    @dp.message(F.text.in_(RECIPES.keys()))
    async def category_handler(message: Message):
        await send_recipe(message, message.text)

    @dp.message(F.text == "🎲 Что приготовить?")
    async def random_handler(message: Message):
        category = random.choice(list(RECIPES.keys()))
        await message.answer(f"Выбрал категорию: {category}")
        await send_recipe(message, category)

    @dp.message()
    async def unknown(message: Message):
        await message.answer("Выбери вариант в меню 👇", reply_markup=main_menu)

    logging.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
