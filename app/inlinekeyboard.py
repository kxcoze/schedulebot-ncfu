from aiogram import types
from aiogram.utils.callback_data import CallbackData


cbd_poll = CallbackData(
    "poll",
    "id",
)
cbd_choice = CallbackData("choice", "action", "result")


def show_ikeyboard_preferences():
    text = (
        "Для изменения времени оповещения нажмите кнопку \n"
        "<em><b>Время уведомления</b></em>\n\n"
        "Для выбора типа пар, на которые будут приходить уведомления "
        "нажмите кнопку \n<em><b>Тип пар</b></em>\n\n"
        "Для изменения номера подгруппы нажмите кнопку \n"
        "<em><b>Подгруппа</b></em>\n\n"
        "Для изменения иностранного языка, который будет учитываться "
        "при показе расписания или уведомления, нажмите кнопку \n"
        "<em><b>Иностранный язык</b></em>"
    )
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "Время уведомления", callback_data=cbd_poll.new(id="1")
        ),
        types.InlineKeyboardButton("Тип пар", callback_data=cbd_poll.new(id="2")),
    )

    markup.add(
        types.InlineKeyboardButton("Подгруппа", callback_data=cbd_poll.new(id="3")),
        types.InlineKeyboardButton(
            "Иностранный язык", callback_data=cbd_poll.new(id="4")
        ),
    )

    return text, markup


def show_type_preference_ikeyboard():
    text = (
        "От выбранного типа пары зависит, будут ли Вам приходить оповещения "
        "о парах, которые проводятся дистанционно или очно.\n"
        "<em>ВКС</em> — Уведомляются только дистанционные пары.\n"
        "<em>Очный</em> — Уведомляются только очные пары.\n"
        "<em>ВКС/Очный</em> — Уведомляются все пары.\n"
    )
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "ВКС", callback_data=cbd_choice.new(action="choose", result="distant")
        ),
        types.InlineKeyboardButton(
            "Очный", callback_data=cbd_choice.new(action="choose", result="full-time")
        ),
        types.InlineKeyboardButton(
            "ВКС/Очный", callback_data=cbd_choice.new(action="choose", result="all")
        ),
    )

    markup.add(
        types.InlineKeyboardButton(
            "« Вернуться назад",
            callback_data=cbd_poll.new(id="0"),
        )
    )
    return text, markup
