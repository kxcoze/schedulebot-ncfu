import json
from typing import List, Tuple

from aiogram import types
from aiogram.utils.callback_data import CallbackData

import db

WIDTH = 5

list = CallbackData(
        'page',
        'id',
        'page_num',
        'action',
)  # page:<id>:<page_num>:<action>


def search_nonempty_page(links, left, right, cur_page):
    page = cur_page
    while page > 0 and len(links[left:right]) == 0:
        right -= WIDTH
        left -= WIDTH
        page -= 1

    return left, right, page


def show_page(user_id, cur_page=0):
    links = get_links(user_id)
    left = cur_page * WIDTH
    right = cur_page*WIDTH + WIDTH

    if len(links[left:right]) == 0:
        left, right, cur_page = search_nonempty_page(links,
                                                     left, right, cur_page)

    add_prev = False
    add_next = False

    links_size = len(links)
    if cur_page > 0:
        add_prev = True

    if right < links_size:
        add_next = True

    if links_size == 0:
        text = ('Список ваших ссылок пуст.\n'
                'Нажмите кнопку <b>Добавить ссылку</b> '
                'для добавления очередной ссылки \n'
                'Заметьте поддерживается не более 15 ссылок \n'
                'Если предмет/преподаватель указаны корректно, то '
                'при оповещении о начале пары '
                'cсылка добавится автоматически.')
    else:
        text = '<b><em>Ваши ссылки</em></b>\n'
    markup = types.InlineKeyboardMarkup()
    menu = []
    if add_prev:
        menu.append(types.InlineKeyboardButton(
                '«',
                callback_data=list.new(
                    id='-', page_num=cur_page-1, action='prev'))
                    )
    for ind, link in enumerate(links[left:right], start=left+1):
        text += (f"№{ind}\n"
                 f"Предмет/Преподаватель: {link[0]}\n"
                 f"Ссылка на пару: {link[1]}\n\n")

        menu.append(types.InlineKeyboardButton(
                ind,
                callback_data=list.new(
                    id=ind, page_num=cur_page, action='view'))
                    )
    if add_next:
        menu.append(types.InlineKeyboardButton(
                '»',
                callback_data=list.new(
                    id='-', page_num=cur_page+1, action='next'))
                    )

    markup.row(*menu)

    markup.add(
        types.InlineKeyboardButton(
            'Добавить ссылку',
            callback_data=list.new(
                id='-', page_num=cur_page, action='add')),
    )
    return text, markup


def view_link_data(user_id, cur_page, ind):
    markup = types.InlineKeyboardMarkup()

    links = get_links(user_id)
    text = ''.join(f"№{ind+1}\n"
                   f"Предмет/Преподаватель: {links[ind][0]}\n"
                   f"Ссылка на пару: {links[ind][1]}\n")
    markup.row(
        types.InlineKeyboardButton(
            'Изменить предмет/препод.',
            callback_data=list.new(
                id="1", page_num=cur_page, action='edit')),

        types.InlineKeyboardButton(
            'Изменить ссылку',
            callback_data=list.new(
                id="2", page_num=cur_page, action='edit')),
    )
    markup.row(
        types.InlineKeyboardButton(
            'Удалить ссылку',
            callback_data=list.new(
                id=ind, page_num=cur_page, action='delete_link')),

        types.InlineKeyboardButton(
            '« Вернуться назад',
            callback_data=list.new(
                id='-', page_num=cur_page, action='main')),
    )
    return text, markup


def back_to_main(cur_page):
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            '« Вернуться назад',
            callback_data=list.new(
                id='-', page_num=cur_page, action='main')),
    )
    return markup


def get_links(user_id: str) -> List:
    user_links = json.loads(db.get('users', 'link', 'user_id', user_id))
    return user_links


def check_existing_link(user_id: str, checked_link: Tuple, ind: int) -> int:
    user_links = get_links(user_id)
    last_index = -1
    for index, link in enumerate(user_links):
        if tuple(link) == checked_link:
            if index == ind:
                return ind
            last_index = index

    return last_index


def append_link(user_id: str, lesson: str, url: str, position=0) -> int:
    user_links = get_links(user_id)
    if len(user_links) >= 15:
        # Ваших ссылок стало слишком много, удалите лишние
        return -1
    user_links.insert(position, [lesson, url])
    _update_db_link(user_id, user_links)
    return 0


def update_link_lesson(user_id: str, num: int, new_lesson: str):
    user_links = get_links(user_id)
    user_links[num][0] = new_lesson.strip()
    _update_db_link(user_id, user_links)


def update_link_url(user_id: str, num: int, new_url: str):
    user_links = get_links(user_id)
    user_links[num][1] = new_url.strip()
    _update_db_link(user_id, user_links)


def delete_link_by_num(user_id: str, ind: int) -> int:
    user_links = get_links(user_id)
    if 0 <= ind <= len(user_links)-1:
        del user_links[ind]
        _update_db_link(user_id, user_links)
        return 0
    else:
        return -1


def delete_link_by_info(user_id: str, link_to_delete: Tuple, ind: int) -> int:
    user_links = get_links(user_id)

    last_index = -1
    for index, link in enumerate(user_links):
        if tuple(link) == link_to_delete:
            if index == ind:
                del user_links[index]
                _update_db_link(user_id, user_links)
                return 0
            last_index = index

    if last_index != -1:
        del user_links[last_index]
        _update_db_link(user_id, user_links)
        return 0
    return -1


def _update_db_link(user_id: str, user_link: List) -> None:
    user_link = json.dumps(user_link, ensure_ascii=False)
    db.update('users', (('link', user_link), ), 'user_id', user_id)
