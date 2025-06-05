from aiogram import types, Router, F

from utils.logger import log
from bot.handlers.balance import process_deposit_payment
from bot.handlers.buy_gift import process_gift_payment


router = Router()


@log.catch
@router.message(F.successful_payment)
async def handle_successful_payment(message: types.Message, db_session):
    payment_info = message.successful_payment
    log.info(f"Successful payment: {payment_info}")

    payload = payment_info.invoice_payload
    if payload.startswith("deposit_"):
        await process_deposit_payment(message, db_session, payment_info)
    elif payload.startswith("gift_"):
        await process_gift_payment(message, db_session, payment_info)
    else:
        log.error(f"Unknown payment type: {payload}")
        await message.reply("Ошибка: Неизвестный тип платежа. Пожалуйста, свяжитесь с @mildeks")
