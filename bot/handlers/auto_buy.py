from aiogram import types, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from api.gifts import GiftsApi
from bot.states.auto_buy_state import AutoBuyStates
from bot.keyboards.default import main_menu, auto_buy_keyboard, go_back_menu, back_to_auto_buy_settings_menu_keyboard
from utils.logger import log
from db.models import AutoBuySettings, User

router = Router()
gifts_api = GiftsApi()


def get_or_create_auto_buy_settings(db, user_id) -> AutoBuySettings:
    settings = db.query(AutoBuySettings).filter(
        AutoBuySettings.user_id == user_id).first()
    if not settings:
        settings = AutoBuySettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.message(Command(commands=["auto_buy"]))
async def auto_buy_command(message: types.Message, state: FSMContext, db_session):
    with db_session as db:
        settings = get_or_create_auto_buy_settings(db, message.from_user.id)
        user = db.query(User).filter(
            User.user_id == message.from_user.id).first()

        username = user.username if user else "Unknown User"
        balance = user.balance if user else 0

        await message.answer(
            text=(
                f"{username}! Ваш баланс: {balance} ⭐️\n\n"
                f"⚙️ <b>Настройки Авто-Покупки</b>\n"
                f"Статус: {'🟢 Включено' if settings.status == 'enabled' else '🔴 Выключено'}\n\n"
                f"<b>Цена:</b>\n"
                f"От {settings.price_limit_from} до {settings.price_limit_to} ⭐️\n\n"
                f"<b>Лимит саплая:</b> {settings.supply_limit or 'Неограничено'} ⭐️\n"
                f"<b>Циклы Автопокупки:</b> {settings.cycles}\n"
            ),
            reply_markup=auto_buy_keyboard(),
            parse_mode="HTML"
        )
    await state.set_state(AutoBuyStates.menu)


async def display_updated_settings(message: types.Message, db_session, settings: AutoBuySettings) -> None:
    with db_session as db:
        user = db.query(User).filter(
            User.user_id == message.from_user.id).first()
        username = user.username if user else "Unknown User"
        balance = user.balance if user else 0
        db.refresh(settings)

        await message.answer(
            text=(
                f"{username}! Ваш баланс: {balance} ⭐️\n\n"
                f"⚙️ <b>Настройки Авто-Покупки</b>\n"
                f"Статус: {'🟢 Включено' if settings.status == 'enabled' else '🔴 Выключено'}\n\n"
                f"<b>Цена:</b>\n"
                f"От {settings.price_limit_from} до {settings.price_limit_to} ⭐️\n\n"
                f"<b>Лимит саплая:</b> {settings.supply_limit or 'Неограничено'} ⭐️\n"
                f"<b>Циклы Автопокупки:</b> {settings.cycles}"
            ),
            reply_markup=auto_buy_keyboard(),
            parse_mode="HTML"
        )


@router.message(StateFilter(AutoBuyStates.menu))
async def auto_buy_menu_handler(message: types.Message, state: FSMContext, db_session):
    with db_session as db:
        settings = get_or_create_auto_buy_settings(db, message.from_user.id)

        if message.text == "🔄 Включить/Выключить":
            settings.status = "enabled" if settings.status == "disabled" else "disabled"
            db.commit()
            db.refresh(settings)
            await message.answer(
                text=f"🔄 Статус Авто-Покупки изменен: {'🟢 Включено' if settings.status == 'enabled' else '🔴 Выключено'}."
            )
            await display_updated_settings(message, db_session, settings)

        elif message.text == "✏️ Лимит цены От/До":
            await message.answer(
                # Изменен текст подсказки и клавиатура
                text="Введите лимит цены в формате: `От/До` (например, 10 100).\nНажмите '🔙 Назад', чтобы отменить.",
                reply_markup=back_to_auto_buy_settings_menu_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(AutoBuyStates.set_price)

        elif message.text == "✏️ Лимит саплая":
            await message.answer(
                # Изменен текст подсказки и клавиатура
                text="Введите лимит саплая подарков (например, 50).\nНажмите '🔙 Назад', чтобы отменить.",
                reply_markup=back_to_auto_buy_settings_menu_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(AutoBuyStates.set_supply)

        elif message.text == "✏️ Количество Циклов":
            await message.answer(
                # Изменен текст подсказки и клавиатура
                text="<b>Введите количество циклов (например, 2)</b>\nКаждый цикл позволяет покупать установленное количество подарков (например, 3 цикла с 2 подарками за цикл купят 6 подарков всего).\nНажмите '🔙 Назад', чтобы отменить.",
                reply_markup=back_to_auto_buy_settings_menu_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(AutoBuyStates.set_cycles)

        elif message.text == "🔙 Назад в Главное Меню":
            await message.answer(
                text="Вернуться в главное меню!",
                reply_markup=main_menu()
            )
            await state.clear()


@router.message(StateFilter(AutoBuyStates.set_price))
async def auto_buy_set_price_handler(message: types.Message, state: FSMContext, db_session):
    with db_session as db:
        settings = get_or_create_auto_buy_settings(db, message.from_user.id)

        # Изменена проверка текста кнопки
        if message.text == "🔙 Назад":
            await display_updated_settings(message, db_session, settings)
            await state.set_state(AutoBuyStates.menu)
            return

        try:
            price_limits = message.text.split()
            if len(price_limits) != 2:
                raise ValueError("Вводный формат должен быть: `От/До`.")
            price_from, price_to = map(int, price_limits)
            settings.price_limit_from = price_from
            settings.price_limit_to = price_to
            db.commit()
            db.refresh(settings)

            await message.answer(
                text=f"✅ Лимит цены установлен: от {price_from} до {price_to} ⭐️."
            )
            await display_updated_settings(message, db_session, settings)
            await state.set_state(AutoBuyStates.menu)
        except ValueError:
            # Клавиатура здесь тоже должна быть back_to_auto_buy_settings_menu_keyboard
            await message.answer(
                text="Ошибка ввода! Введите лимит цены в формате: `От/До` (например, 10 100).",
                reply_markup=back_to_auto_buy_settings_menu_keyboard() # Изменено
            )

@router.message(StateFilter(AutoBuyStates.set_supply))
async def auto_buy_set_supply_handler(message: types.Message, state: FSMContext, db_session):
    with db_session as db:
        settings = get_or_create_auto_buy_settings(db, message.from_user.id)

        # Изменена проверка текста кнопки
        if message.text == "🔙 Назад":
            await display_updated_settings(message, db_session, settings)
            await state.set_state(AutoBuyStates.menu)
            return

        try:
            supply_limit = int(message.text)
            if supply_limit <= 0:
                raise ValueError("Лимит саплая должен быть положительным числом.")
            settings.supply_limit = supply_limit
            db.commit()
            db.refresh(settings)

            await message.answer(
                text=f"✅ Лимит саплая установлен: {supply_limit}."
            )
            await display_updated_settings(message, db_session, settings)
            await state.set_state(AutoBuyStates.menu)
        except ValueError:
            # Клавиатура здесь тоже должна быть back_to_auto_buy_settings_menu_keyboard
            await message.answer(
                text="Ошибка ввода! Введите положительное число для лимита саплая.",
                reply_markup=back_to_auto_buy_settings_menu_keyboard() # Изменено
            )

@router.message(StateFilter(AutoBuyStates.set_cycles))
async def auto_buy_set_cycles_handler(message: types.Message, state: FSMContext, db_session):
    with db_session as db:
        settings = get_or_create_auto_buy_settings(db, message.from_user.id)

        # Изменена проверка текста кнопки
        if message.text == "🔙 Назад":
            await display_updated_settings(message, db_session, settings)
            await state.set_state(AutoBuyStates.menu)
            return

        try:
            cycles = int(message.text)
            if cycles <= 0:
                raise ValueError("Количество циклов должно быть положительным.")
            settings.cycles = cycles
            db.commit()
            db.refresh(settings)

            await message.answer(
                text=f"✅ Количество циклов покупки установлено: {cycles}."
            )
            await display_updated_settings(message, db_session, settings)
            await state.set_state(AutoBuyStates.menu)
        except ValueError:
            # Клавиатура здесь тоже должна быть back_to_auto_buy_settings_menu_keyboard
            await message.answer(
                text="Ошибка ввода! Введите положительное число для количества циклов.",
                reply_markup=back_to_auto_buy_settings_menu_keyboard() # Изменено
            )