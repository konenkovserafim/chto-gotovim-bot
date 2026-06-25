import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN is not set. Add it in Railway Variables.')

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

RECIPES = {
    'breakfast': {
        'title': '🔍 Завтрак',
        'items': [
            {
                'id': 'omelet', 'name': '🍳 Омлет с овощами', 'time': '15 минут', 'price': '~180 ₽', 'cal': 'Серафим ~520 ккал / Таня ~360 ккал',
                'ingredients': ['Яйца — 4 шт', 'Помидор — 1 шт', 'Молоко — 50 мл', 'Зелень', 'Соль'],
                'steps': ['Взбей яйца с молоком и солью.', 'Нарежь помидор и зелень.', 'Обжарь помидор 1–2 минуты.', 'Залей яйцами и готовь под крышкой 5–7 минут.'],
                'portions': 'Серафиму — 2–3 яйца, Тане — 1–2 яйца + больше овощей.'
            },
            {
                'id': 'oatmeal', 'name': '🥣 Овсянка с бананом', 'time': '10 минут', 'price': '~120 ₽', 'cal': 'Серафим ~480 ккал / Таня ~330 ккал',
                'ingredients': ['Овсянка — 100 г', 'Молоко — 300 мл', 'Банан — 1 шт', 'Мёд — 1 ч. л.'],
                'steps': ['Свари овсянку на молоке.', 'Нарежь банан.', 'Добавь банан и немного мёда.'],
                'portions': 'Серафиму — порция больше, Тане — меньше овсянки, банан пополам.'
            },
            {
                'id': 'cottage_cheese', 'name': '🧀 Творог с мёдом', 'time': '5 минут', 'price': '~220 ₽', 'cal': 'Серафим ~450 ккал / Таня ~280 ккал',
                'ingredients': ['Творог — 400–500 г', 'Мёд — 1–2 ч. л.', 'Молоко по желанию'],
                'steps': ['Разложи творог по тарелкам.', 'Добавь немного мёда.', 'Можно добавить чуть молока.'],
                'portions': 'Серафиму — 250–300 г, Тане — 150–200 г.'
            },
        ]
    },
    'lunch': {
        'title': '🍲 Обед',
        'items': [
            {
                'id': 'chicken_buckwheat', 'name': '🍗 Курица с гречкой и салатом', 'time': '35 минут', 'price': '~400 ₽', 'cal': 'Серафим ~750 ккал / Таня ~520 ккал',
                'ingredients': ['Куриное филе — 400 г', 'Гречка — 160 г сухой', 'Огурец', 'Помидор', 'Зелень', 'Масло — немного'],
                'steps': ['Отвари гречку.', 'Курицу посоли и обжарь/потуши.', 'Нарежь салат.', 'Разложи порции отдельно.'],
                'portions': 'Серафиму — больше гречки и курицы, Тане — больше салата и меньше крупы.'
            },
            {
                'id': 'pasta_chicken', 'name': '🍝 Паста с курицей', 'time': '30 минут', 'price': '~450 ₽', 'cal': 'Серафим ~850 ккал / Таня ~600 ккал',
                'ingredients': ['Макароны — 180 г сухих', 'Курица — 350 г', 'Молоко/сливки — немного', 'Сыр по желанию', 'Соль'],
                'steps': ['Отвари макароны.', 'Обжарь курицу.', 'Добавь немного молока/сливок.', 'Смешай с макаронами.'],
                'portions': 'Серафиму — порция пасты больше, Тане — меньше пасты + овощи при наличии.'
            },
            {
                'id': 'fish_potato', 'name': '🐟 Рыба с картофелем', 'time': '40 минут', 'price': '~500 ₽', 'cal': 'Серафим ~700 ккал / Таня ~500 ккал',
                'ingredients': ['Рыба — 400 г', 'Картофель — 500 г', 'Огурец/помидор', 'Соль', 'Масло — немного'],
                'steps': ['Отвари или запеки картофель.', 'Рыбу посоли и приготовь на сковороде/в духовке.', 'Добавь салат.'],
                'portions': 'Серафиму — больше картофеля, Тане — больше овощей.'
            },
        ]
    },
    'dinner': {
        'title': '🍽 Ужин',
        'items': [
            {
                'id': 'light_chicken_salad', 'name': '🥗 Куриный салат', 'time': '20 минут', 'price': '~350 ₽', 'cal': 'Серафим ~550 ккал / Таня ~380 ккал',
                'ingredients': ['Курица — 300 г', 'Огурец', 'Помидор', 'Зелень', 'Йогурт/немного масла'],
                'steps': ['Приготовь курицу.', 'Нарежь овощи.', 'Смешай, заправь слегка.'],
                'portions': 'Серафиму — больше курицы, Тане — больше овощей.'
            },
            {
                'id': 'eggs_veg', 'name': '🍳 Яичница с овощами', 'time': '15 минут', 'price': '~170 ₽', 'cal': 'Серафим ~500 ккал / Таня ~330 ккал',
                'ingredients': ['Яйца — 4 шт', 'Овощи', 'Зелень', 'Соль'],
                'steps': ['Нарежь овощи.', 'Обжарь 1–2 минуты.', 'Добавь яйца и доведи до готовности.'],
                'portions': 'Серафиму — 2–3 яйца, Тане — 1–2 яйца.'
            },
            {
                'id': 'cottage_dinner', 'name': '🥛 Творог с молоком', 'time': '5 минут', 'price': '~220 ₽', 'cal': 'Серафим ~430 ккал / Таня ~270 ккал',
                'ingredients': ['Творог — 400–500 г', 'Молоко', 'Мёд по желанию'],
                'steps': ['Разложи творог.', 'Добавь молоко/мёд по желанию.', 'Готово.'],
                'portions': 'Серафиму — 250–300 г, Тане — 150–200 г.'
            },
        ]
    },
    'snack': {
        'title': '🥗 Перекус',
        'items': [
            {
                'id': 'fruit_curd', 'name': '🍌 Фрукт + творог', 'time': '5 минут', 'price': '~180 ₽', 'cal': 'Серафим ~350 ккал / Таня ~230 ккал',
                'ingredients': ['Творог — 250–300 г', 'Банан/яблоко', 'Мёд по желанию'],
                'steps': ['Нарежь фрукт.', 'Добавь к творогу.', 'Перемешай.'],
                'portions': 'Серафиму — больше творога, Тане — меньше.'
            },
            {
                'id': 'sandwich', 'name': '🥪 Быстрый бутерброд', 'time': '5 минут', 'price': '~150 ₽', 'cal': 'Серафим ~400 ккал / Таня ~250 ккал',
                'ingredients': ['Хлеб', 'Сыр/курица', 'Огурец/помидор'],
                'steps': ['Собери бутерброды.', 'Добавь овощи.', 'Готово.'],
                'portions': 'Серафиму — 2 шт, Тане — 1 шт + овощи.'
            },
        ]
    }
}

favorites = set()
shopping = []

def reply_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🔍 Завтрак'), KeyboardButton(text='🍲 Обед')],
            [KeyboardButton(text='🍽 Ужин'), KeyboardButton(text='🥗 Перекус')],
            [KeyboardButton(text='🎲 Что приготовить?')],
            [KeyboardButton(text='❤️ Избранное'), KeyboardButton(text='🛒 Список продуктов')],
        ],
        resize_keyboard=True,
        input_field_placeholder='Выбери раздел'
    )


def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔍 Завтрак', callback_data='cat:breakfast'), InlineKeyboardButton(text='🍲 Обед', callback_data='cat:lunch')],
        [InlineKeyboardButton(text='🍽 Ужин', callback_data='cat:dinner'), InlineKeyboardButton(text='🥗 Перекус', callback_data='cat:snack')],
        [InlineKeyboardButton(text='🎲 Что приготовить?', callback_data='random')],
        [InlineKeyboardButton(text='❤️ Избранное', callback_data='favorites'), InlineKeyboardButton(text='🛒 Список продуктов', callback_data='shopping')],
    ])

def category_kb(cat):
    rows = []
    for r in RECIPES[cat]['items']:
        rows.append([InlineKeyboardButton(text=r['name'], callback_data=f'recipe:{cat}:{r["id"]}')])
    rows.append([InlineKeyboardButton(text='🎲 Случайный вариант', callback_data=f'catrandom:{cat}')])
    rows.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='home')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def recipe_kb(cat, rid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❤️ В избранное', callback_data=f'fav:{cat}:{rid}')],
        [InlineKeyboardButton(text='🛒 В список продуктов', callback_data=f'shop:{cat}:{rid}')],
        [InlineKeyboardButton(text='⬅️ К вариантам', callback_data=f'cat:{cat}'), InlineKeyboardButton(text='🏠 Меню', callback_data='home')]
    ])

def find_recipe(cat, rid):
    return next(r for r in RECIPES[cat]['items'] if r['id'] == rid)

def recipe_text(r):
    ingredients = '\n'.join(f'• {x}' for x in r['ingredients'])
    steps = '\n'.join(f'{i+1}. {x}' for i, x in enumerate(r['steps']))
    return f"""{r['name']}

⏱ Время: {r['time']}
💰 Примерная стоимость: {r['price']}
🔥 Калории: {r['cal']}

🛒 Ингредиенты:
{ingredients}

👨‍🍳 Рецепт:
{steps}

🍽 Порции:
{r['portions']}"""

async def show_home(target):
    text = '🍽 Привет! Я бот «Что готовим?»\n\nПомогу выбрать завтрак, обед, ужин или перекус для вас с Таней.'
    if isinstance(target, Message):
        await target.answer(text, reply_markup=reply_main_kb())
    else:
        await target.message.answer(text, reply_markup=reply_main_kb())

@dp.message(CommandStart())
async def start(message: Message):
    await show_home(message)



CATEGORY_BY_TEXT = {
    '🔍 Завтрак': 'breakfast',
    '🍳 Завтрак': 'breakfast',
    '🍲 Обед': 'lunch',
    '🍽 Ужин': 'dinner',
    '🥗 Перекус': 'snack',
}

@dp.message(F.text.in_(list(CATEGORY_BY_TEXT.keys())))
async def category_from_keyboard(message: Message):
    cat = CATEGORY_BY_TEXT[message.text]
    await message.answer(f"{RECIPES[cat]['title']}\n\nВыбери блюдо:", reply_markup=category_kb(cat))

@dp.message(F.text == '🎲 Что приготовить?')
async def random_from_keyboard(message: Message):
    cat = random.choice(list(RECIPES.keys()))
    r = random.choice(RECIPES[cat]['items'])
    await message.answer('🎲 Случайный вариант\n\n' + recipe_text(r), reply_markup=recipe_kb(cat, r['id']))

@dp.message(F.text == '❤️ Избранное')
async def favorites_from_keyboard(message: Message):
    if not favorites:
        await message.answer('❤️ Избранное пока пустое.')
        return
    lines = ['❤️ Избранное:']
    for cat, rid in favorites:
        lines.append('• ' + find_recipe(cat, rid)['name'])
    await message.answer('\n'.join(lines))

@dp.message(F.text == '🛒 Список продуктов')
async def shopping_from_keyboard(message: Message):
    if not shopping:
        await message.answer('🛒 Список продуктов пока пустой.')
        return
    await message.answer('🛒 Список продуктов:\n' + '\n'.join(f'• {x}' for x in shopping))

@dp.callback_query(F.data == 'home')
async def home(call: CallbackQuery):
    await show_home(call)
    await call.answer()

@dp.callback_query(F.data.startswith('cat:'))
async def category(call: CallbackQuery):
    cat = call.data.split(':')[1]
    await call.message.edit_text(f"{RECIPES[cat]['title']}\n\nВыбери блюдо:", reply_markup=category_kb(cat))
    await call.answer()

@dp.callback_query(F.data.startswith('recipe:'))
async def recipe(call: CallbackQuery):
    _, cat, rid = call.data.split(':')
    r = find_recipe(cat, rid)
    await call.message.edit_text(recipe_text(r), reply_markup=recipe_kb(cat, rid))
    await call.answer()

@dp.callback_query(F.data.startswith('catrandom:'))
async def cat_random(call: CallbackQuery):
    cat = call.data.split(':')[1]
    r = random.choice(RECIPES[cat]['items'])
    await call.message.edit_text(recipe_text(r), reply_markup=recipe_kb(cat, r['id']))
    await call.answer()

@dp.callback_query(F.data == 'random')
async def any_random(call: CallbackQuery):
    cat = random.choice(list(RECIPES.keys()))
    r = random.choice(RECIPES[cat]['items'])
    await call.message.edit_text('🎲 Случайный вариант\n\n' + recipe_text(r), reply_markup=recipe_kb(cat, r['id']))
    await call.answer()

@dp.callback_query(F.data.startswith('fav:'))
async def add_fav(call: CallbackQuery):
    _, cat, rid = call.data.split(':')
    favorites.add((cat, rid))
    await call.answer('Добавлено в избранное ❤️')

@dp.callback_query(F.data == 'favorites')
async def show_favs(call: CallbackQuery):
    if not favorites:
        text = '❤️ Избранное пока пустое.'
    else:
        lines = ['❤️ Избранное:']
        for cat, rid in favorites:
            lines.append('• ' + find_recipe(cat, rid)['name'])
        text = '\n'.join(lines)
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏠 Меню', callback_data='home')]]))
    await call.answer()

@dp.callback_query(F.data.startswith('shop:'))
async def add_shop(call: CallbackQuery):
    _, cat, rid = call.data.split(':')
    r = find_recipe(cat, rid)
    for ing in r['ingredients']:
        if ing not in shopping:
            shopping.append(ing)
    await call.answer('Ингредиенты добавлены в список 🛒')

@dp.callback_query(F.data == 'shopping')
async def show_shop(call: CallbackQuery):
    if not shopping:
        text = '🛒 Список продуктов пока пустой.'
    else:
        text = '🛒 Список продуктов:\n' + '\n'.join(f'• {x}' for x in shopping)
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏠 Меню', callback_data='home')]]))
    await call.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
