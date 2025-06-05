from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='/balance'),
                KeyboardButton(text='/buy_gift'),
                KeyboardButton(text='/deposit')
            ],
            [
                KeyboardButton(text="/start"),
                KeyboardButton(text='/auto_buy')
            ]
        ],
        resize_keyboard=True
    )
    return markup


def balance_menu():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='/deposit'),
                KeyboardButton(text="🔙 Назад в Главное Меню")  # Текст должен точно совпадать
            ],
        ],
        resize_keyboard=True
    )
    return markup


def go_back_menu():
    # Эта функция теперь будет использоваться только там, где нужно вернуться в самое главное меню
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔙 Назад в Главное Меню"),
            ],
        ],
        resize_keyboard=True
    )
    return markup


def auto_buy_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Включить/Выключить")
            ],
            [
                KeyboardButton(text="✏️ Лимит цены От/До"),
                KeyboardButton(text="✏️ Лимит саплая"),
                KeyboardButton(text="✏️ Количество Циклов"),
            ],
            [
                KeyboardButton(text="🔙 Назад в Главное Меню") # Эта кнопка возвращает в главное меню бота
            ]
        ],
        resize_keyboard=True
    )
    return markup


# НОВАЯ ФУНКЦИЯ ДЛЯ КЛАВИАТУРЫ "НАЗАД" В ПОДМЕНЮ АВТО-ПОКУПКИ
def back_to_auto_buy_settings_menu_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад")] # Кнопка просто "Назад"
        ],
        resize_keyboard=True
    )
    return markup