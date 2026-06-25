from datetime import datetime
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from keyboards.main import main_menu
router=Router()
def welcome():
    h=datetime.now().hour
    if 5<=h<11:
        return "☀️ <b>Доброе утро!</b>\n\nЧем позавтракаем?"
    elif 11<=h<17:
        return "🍲 <b>Пора подумать об обеде.</b>"
    else:
        return "🌙 <b>Что приготовим на ужин?</b>"
@router.message(CommandStart())
async def start(message:Message):
    await message.answer(welcome(),reply_markup=main_menu())
@router.callback_query(lambda c:c.data=='back:main')
async def back_to_main(callback:CallbackQuery):
    await callback.message.edit_text(welcome(),reply_markup=main_menu())
    await callback.answer()
