import aiohttp
from datetime import datetime
from aiogram import types, Router, Bot
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext

from api.gifts import GiftsApi
from utils.logger import log
from bot.states.deposit_state import DepositStates
from bot.keyboards.default import balance_menu, main_menu, go_back_menu
from bot.keyboards.inline import payment_keyboard
from db.models import User, Transaction

router = Router()
gifts_api = GiftsApi()


# Utility Functions
@log.catch
async def get_user_by_username(db_session, username: str) -> User | None:
    with db_session as db:
        return db.query(User).filter(User.username == username).first()


@log.catch
async def get_user_by_id(db_session, user_id: int) -> User | None:
    with db_session as db:
        return db.query(User).filter(User.user_id == user_id).first()


@log.catch
async def return_to_main_menu(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        text="Вы вернулись в главное меню! Пожалуйста, используйте кнопки ниже, чтобы продолжить.",
        reply_markup=main_menu()
    )


@log.catch
@router.message(Command(commands=["balance"]))
async def get_balance_command(message: types.Message, state: FSMContext, db_session) -> None:
    # Проверяем, не нажата ли кнопка "Назад"
    if message.text == "🔙 Назад в Главное Меню":
        await return_to_main_menu(message, state)
        return
        
    user = await get_user_by_username(db_session, message.from_user.username)
    if not user:
        await message.reply("Пользователь не найден. Пожалуйста, попробуйте еще раз.")
        return

    await message.answer(
        f"{message.from_user.username} - Ваш баланс: {user.balance}⭐️",
        reply_markup=balance_menu()
    )


@log.catch
@router.message(lambda message: message.text == "🔙 Назад в Главное Меню")
async def handle_back_button(message: types.Message, state: FSMContext) -> None:
    await return_to_main_menu(message, state)


@log.catch
@router.message(Command(commands=["deposit"]))
async def deposit_command(message: types.Message, state: FSMContext, db_session) -> None:
    user = await get_user_by_username(db_session, message.from_user.username)
    if not user:
        await message.reply("Пользователь не найден. Пожалуйста, попробуйте еще раз.")
        return

    await message.answer(
        text=f"{message.from_user.username}, Ваш баланс: {user.balance}⭐️\nВведите сумму депозита (только цифры).\nПример: 15",
        reply_markup=go_back_menu()
    )
    await state.set_state(DepositStates.waiting_for_amount_deposit)


@log.catch
@router.message(StateFilter(DepositStates.waiting_for_amount_deposit))
async def process_deposit_input(message: types.Message, state: FSMContext) -> None:
    if message.text == "🔙 Назад в Главное Меню":
        await return_to_main_menu(message, state)
        return

    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной.")
    except ValueError:
        await message.reply("Пожалуйста, введите положительное число. Пример: 15")
        return

    payload = f"deposit_{amount}_to_{message.from_user.id}"

    log.info(
        f"Creating deposit for amount {amount} from user {message.from_user.id}")

    prices = [types.LabeledPrice(label="Deposit", amount=amount)]
    await message.answer_invoice(
        title="Deposit",
        description="Добавление средств на баланс",
        payload=payload,
        currency="XTR",
        prices=prices,
        provider_token="",
        reply_markup=payment_keyboard(price=amount)
    )
    await state.clear()


@log.catch
@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@log.catch
async def process_deposit_payment(message: types.Message, db_session, payment_info: types.SuccessfulPayment) -> None:
    payload = payment_info.invoice_payload
    parts = payload.split("_")
    amount = int(parts[1])
    user_id = int(parts[3])

    try:
        with db_session as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise ValueError("Пользователь не найден.")

            user.balance += amount

            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                telegram_payment_charge_id=payment_info.telegram_payment_charge_id,
                status="completed",
                time=datetime.now().isoformat(),
                payload=payload
            )
            db.add(transaction)
            db.commit()

        await message.reply(
            f"Депозит в размере {amount}⭐️ успешно зачислен на ваш счет.",
            reply_markup=main_menu()
        )
    except Exception as e:
        log.error(f"Deposit processing error: {e}")
        await message.reply("Ошибка при обработке вашего депозита. Пожалуйста, попробуйте позже.")


@log.catch
@router.message(Command("refund"))
async def command_refund_handler(message: types.Message, bot: Bot, command: CommandObject, db_session) -> None:
    """
    Handle refund command for administrators.

    Args:
        message: Incoming message object
        bot: Bot instance for API calls
        command: Parsed command object with arguments
        db_session: Database session

    Workflow:
        1. Verify admin privileges
        2. Validate transaction exists
        3. Process refund via Telegram API
        4. Update database records
        5. Confirm completion

    Error Handling:
        - Detailed error logging
        - User-friendly error messages
    """
    transaction_id = command.args
    if not transaction_id:
        await message.reply("Пожалуйста, укажите ID транзакции для возврата.")
        return

    try:
        with db_session as db:
            admin_user = db.query(User).filter(
                User.user_id == message.from_user.id).first()
            if not admin_user or admin_user.status != "admin":
                await message.reply("You don't have permission to execute this command.")
                return

            transaction = db.query(Transaction).filter(
                Transaction.telegram_payment_charge_id == transaction_id
            ).first()

            if not transaction:
                await message.reply("Transaction not found. Please check ID and try again.")
                return

            if transaction.status == "refunded":
                await message.reply("Funds for this transaction were already refunded.")
                return

            user = db.query(User).filter(
                User.user_id == transaction.user_id).first()
            if not user:
                await message.reply("User associated with transaction not found.")
                return

            refund_amount = transaction.amount
            target_user_id = transaction.user_id

        try:
            result = await bot.refund_star_payment(
                user_id=target_user_id,
                telegram_payment_charge_id=transaction_id
            )
            log.debug(result)
        except Exception as e:
            log.error(f"Error processing refund via Telegram API: {e}")
            await message.reply("Refund processing via Telegram API failed, please contact support.")
            return

        with db_session as db:
            transaction = db.query(Transaction).filter(
                Transaction.telegram_payment_charge_id == transaction_id
            ).first()

            if not transaction:
                await message.reply("Failed to find transaction for update. Please contact support.")
                return

            user = db.query(User).filter(
                User.user_id == transaction.user_id).first()
            if not user:
                await message.reply("Failed to find user for balance update. Please contact support.")
                return

            transaction.status = "refunded"
            user.balance -= refund_amount
            db.commit()

        await message.reply(
            f"Refund for transaction ID: {transaction_id} processed successfully. Refund amount: {refund_amount}⭐️."
        )

    except Exception as e:
        log.error(f"Refund processing error: {e}")
        await message.reply(f"Error processing refund: {e}")
