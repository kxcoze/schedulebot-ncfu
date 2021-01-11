import json
from typing import List, Tuple

import db


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
    db.update('users', [['link', user_link]], 'user_id', user_id)
