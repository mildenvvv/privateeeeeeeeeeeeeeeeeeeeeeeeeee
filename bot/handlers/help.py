from aiogram import types, Router
from aiogram.filters import Command

router = Router()


@router.message(Command(commands=["help"]))
async def help_command(message: types.Message):

    await message.reply("Введите /start для начала.\nПо вопросам обращайтесь к @mildeks")
