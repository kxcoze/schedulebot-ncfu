LANGUAGES = [
    "Азербайджанский",
    "Нидерландский",
    "Норвежский",
    "Английский",
    "Арабский",
    "Польский",
    "Армянский",
    "Португальский",
    "Белорусский",
    "Румынский",
    "Болгарский",
    "Русский",
    "Венгерский",
    "Сербский",
    "Вьетнамский",
    "Словацкий",
    "Голландский",
    "Таджикский",
    "Греческий",
    "Тайский",
    "Грузинский",
    "Дари",
    "Турецкий",
    "Датский",
    "Туркменский",
    "Иврит",
    "Украинский",
    "Испанский",
    "Узбекский",
    "Итальянский",
    "Фарси",
    "Кыргызский",
    "Финский",
    "Казахский",
    "Китайский",
    "Французский",
    "Корейский",
    "Хинди",
    "Латинский",
    "Хорватский",
    "Латышский",
    "Чешский",
    "Литовский",
    "Шведский",
    "Эстонский",
    "Молдавский",
    "Японский",
    "Монгольский",
    "Немецкий",
]


def get_formatted_schedule_bell():
    bell = _get_schedule_bell_ncfu()
    formatted_bell = "<b><em>Расписание звонков СКФУ</em></b>\n"

    for k, v in bell.items():
        if not k.isdigit():
            formatted_bell += k.split(",")[0] + " \t"
        else:
            formatted_bell += k + " пара \t\t\t"
        formatted_bell += v + "\n"

    return formatted_bell


def get_every_aliases_days_week():
    fweekdays = list(_get_eng_days_week().keys())
    result = fweekdays.copy()
    second_result = []
    for item in fweekdays:
        result.append(item[:3])
        if item.startswith("t"):
            result.append(item[1:])
            second_result.append(item[1:3])

    return result, second_result


def _format_rus_words(words):
    vowels = {"я": "ю", "а": "у"}
    checked = words[-1][-1]
    if checked in vowels.keys():
        words[-1] = words[-1][:-1] + vowels[checked]
        words[-2] = words[-2][:-2] + "ую" if len(words[-2]) > 0 else ""
    elif checked == "е":
        words[-2] = words[-2][:-2] + "ее" if len(words[-2]) > 0 else ""

    return words


def _get_eng_days_week():
    weekdays = {
        "week": -1,
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    return weekdays


def _get_schedule_bell_ncfu():
    bell = {
        "1": "8:00 - 9:30",
        "2": "9:40 - 11:10",
        "3": "11:20 - 12:50",
        "Большая перемена, 30 минут": "12:50 - 13:20",
        "4": "13:20 - 14:50",
        "5": "15:00 - 16:30",
        "Большая перемена, 20 минут": "16:30 - 16:50",
        "6": "16:50 - 18:20",
        "7": "18:30 - 20:00",
        "8": "20:10 - 21:40",
    }
    return bell


def _get_meaning_of_preferences():
    meaning = {"all": "Очный/ВКС", "full-time": "Очный", "distant": "ВКС"}
    return meaning
