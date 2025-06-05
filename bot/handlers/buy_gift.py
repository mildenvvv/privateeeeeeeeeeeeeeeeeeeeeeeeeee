from datetime import datetime

import aiohttp
from aiogram import types, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from api.gifts import GiftsApi
from utils.logger import log
from bot.states.gift_state import GiftStates
from bot.keyboards.inline import payment_keyboard
from bot.keyboards.default import go_back_menu, main_menu
from db.models import User, Transaction

router = Router()
gifts_api = GiftsApi()


@log.catch
async def return_to_main_menu(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        text='Вы вернулись в главное меню! Пожалуйста, используйте кнопки ниже, чтобы продолжить.',
        reply_markup=main_menu()
    )


@log.catch
async def fetch_gifts_list() -> list | None:
    try:
        async with aiohttp.ClientSession() as session:
            return await gifts_api.aio_get_available_gifts(session=session)
    except Exception as e:
        log.error(f"Error fetching gifts list: {e}")
        return None


@log.catch
async def process_gift_payment(
    message: types.Message,
    db_session,
    payment_info: types.SuccessfulPayment = None,
    from_balance: bool = False
) -> None:
    if not from_balance:
        payload = payment_info.invoice_payload
        parts = payload.split("_")
        gift_id = parts[1]
        user_id = parts[3]
        gifts_count = int(parts[5])
    else:
        parts = message.text.split()
        gift_id = parts[0]
        user_id = parts[1]
        gifts_count = int(parts[2])
        payload = f"gift_{gift_id}_to_{user_id}_count_{gifts_count}"

    gifts_list = await fetch_gifts_list()
    for gift in gifts_list:
        if str(gift_id) == str(gift.get('id')):
            gift_price = gift.get('star_count')

    if gift_price is None:
        raise ValueError("Неправильный gift ID или ошибка получения цены.")

    amount = int(gift_price) * gifts_count
    telegram_payment_charge_id = 'buy_gift_transaction' if from_balance else payment_info.telegram_payment_charge_id

    try:
        with db_session as db:
            user = db.query(User).filter(
                User.user_id == message.from_user.id).first()
            if not user:
                raise ValueError("Пользователь не найден в базе данных.")

            for _ in range(gifts_count):
                result = await gifts_api.send_gift(user_id=user_id, gift_id=gift_id)
                if result:
                    log.info(
                        f"Подарок {gift_id} успешно отправлен пользователю {user_id}.")
                else:
                    log.warning(
                        f"Ошибка отправки подарка {gift_id} пользователю {user_id}.")
                    await message.reply(f"Ошибка отправки подарка пользователю {user_id}. Звезды были сохранены.")

            transaction = Transaction(
                user_id=message.from_user.id,
                amount=amount,
                telegram_payment_charge_id=telegram_payment_charge_id,
                status="completed",
                time=datetime.now().isoformat(),
                payload=payload
            )
            db.add(transaction)
            db.commit()

        await message.reply(f"Подарок с ID {gift_id} успешно отправлен пользователю {user_id}.")
    except Exception as e:
        log.error(f"Ошибка при обработке подарков: {e}")
        await message.reply("Произошла ошибка при обработке подарков. Пожалуйста, попробуйте позже.")


@log.catch
@router.message(Command(commands=["buy_gift"]))
async def buy_gift_command(message: types.Message, state: FSMContext) -> None:
    gifts_list = await fetch_gifts_list()
    if not gifts_list:
        await message.reply("В данный момент нет доступных подарков.")
        return

    sorted_gifts = sorted(gifts_list, key=lambda gift: int(
        gift.get("id", 0)), reverse=False)
    gift_descriptions = [
        f'Подарок: {gift.get("sticker", {}).get("emoji", "🎁")}\n'
        f'ID: <code>{gift["id"]}</code>\n'
        f'Цена: {gift["star_count"]}⭐️\n'
        f'Доступно: {gift.get("remaining_count", "Неограничено")}/{gift.get("total_count", "Неограничено")}\n'
        for gift in sorted_gifts
    ]

    if not gift_descriptions:
        await message.reply("В данный момент нет доступных подарков.")
        return

    await message.answer("\n".join(gift_descriptions), parse_mode="HTML")
    await message.answer(
        text="Введите ID подарка, ID получателя и количество.\nПример: 12345678 87654321 10",
        reply_markup=go_back_menu()
    )
    await state.set_state(GiftStates.waiting_for_gift_id)


@log.catch
@router.message(StateFilter(GiftStates.waiting_for_gift_id))
async def process_gift_id_input(
    message: types.Message,
    state: FSMContext,
    db_session
) -> None:
    if message.text == "🔙 Назад в Главное Меню":
        await return_to_main_menu(message, state)
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.reply("Введите ID подарка, ID получателя и количество, разделенные пробелами.")
            return

        try:
            gift_id, user_id, gifts_count = map(int, parts)
        except ValueError:
            await message.reply("Все значения должны быть числами.")
            return

        payload = f"gift_{gift_id}_to_{user_id}_count_{gifts_count}"

        gifts_list = await fetch_gifts_list()
        gift_price = next(
            (gift["star_count"] for gift in gifts_list if int(gift["id"]) == gift_id), None)
        if gift_price is None:
            await message.reply("Подарок с указанным ID не найден.")
            return

        amount = gift_price * gifts_count

        with db_session as db:
            user = db.query(User).filter(
                User.user_id == message.from_user.id).first()
            if not user:
                await message.reply("Пользователь не найден.")
                return

            if user.balance >= amount:
                user.balance -= amount

                transaction = Transaction(
                    user_id=user.user_id,
                    amount=amount,
                    telegram_payment_charge_id="local_transaction",
                    status="completed",
                    time=datetime.now().isoformat(),
                    payload=payload
                )
                db.add(transaction)
                db.commit()

                await message.reply(f"Покупка успешна! Остаток на счете: {user.balance}⭐️.")
                await process_gift_payment(message=message, db_session=db_session, from_balance=True)
            else:
                required_amount = amount - user.balance
                prices = [types.LabeledPrice(
                    label="Дополнительный депозит", amount=required_amount)]
                await message.answer_invoice(
                    title="Дополнительный депозит",
                    description=f"Для покупки требуется {amount}⭐️, у вас {user.balance}⭐️.",
                    payload=payload,
                    currency="XTR",
                    prices=prices,
                    provider_token="",
                    reply_markup=payment_keyboard(price=required_amount)
                )
                await state.clear()

    except Exception as e:
        log.error(f"Ошибка: {e}")
        await message.reply("Произошла ошибка. Пожалуйста, попробуйте снова.")
