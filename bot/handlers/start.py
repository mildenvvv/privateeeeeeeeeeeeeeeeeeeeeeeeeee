from aiogram import Router, types
from aiogram.filters import CommandStart

from db.models import User
from bot.keyboards.default import main_menu

router = Router()


@router.message(CommandStart())
async def start_handler(message: types.Message, db_session):
    with db_session as db:
        user = db.query(User).filter(User.username ==
                                     message.from_user.username).first()

        if user:
            await message.answer(
                f"Привет, {user.username}!\n"
                f"Ваш баланс: {user.balance}⭐️\n\n"
                f"Доступные команды:\n"
                f"/start - Запустить бота\n"
                f"/balance - Проверить баланс\n"
                f"/deposit - Пополнить средства\n"
                f"/buy_gift - Купить подарки\n"
                f"/auto_buy - Авто-покупка подарков\n"
                f"/help - Помощь",
                reply_markup=main_menu()
            )
        else:
            new_user = User(
                user_id=message.from_user.id,
                username=message.from_user.username
            )
            db.add(new_user)
            db.commit()
            await message.answer(
                f"Привет, {message.from_user.username}, ты здесь новенький! "
                f"Я успешно зарегистрировал тебя!\n"
                f"Твой баланс: 0⭐️\n"
                f"Используй команду /deposit, чтобы пополнить средства!",
                reply_markup=main_menu()
            )
