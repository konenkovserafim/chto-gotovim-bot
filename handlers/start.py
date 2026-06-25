from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.main import main_menu

router = Router()

WELCOME_TEXT = (
    "🍽 <b>Что готовим?</b>\n\n"
    "Помогу выбрать еду для вас с Таней: завтрак, обед, ужин, перекус или меню на день.\n\n"
    "Выбирай раздел 👇"
)


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@router.callback_query(lambda c: c.data == "back:main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu())
    await callback.answer()
