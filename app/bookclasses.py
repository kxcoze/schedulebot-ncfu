import json
import re
from abc import ABC, abstractmethod
from typing import List, Tuple

from aiogram import types
from aiogram.utils.callback_data import CallbackData

import db


class Book(ABC):

    WIDTH = 5
    list = CallbackData(
            'page',
            'name',
            'id',
            'page_num',
            'action',
    )  # page:<name>:<id>:<page_num>:<action>

    def __init__(self, user_id):
        self.user_id = user_id


    def search_nonempty_page(self, left, right, cur_page=0):
        seached_page = cur_page
        while seached_page > 0 and self.pages[left:right]:
            right -= self.WIDTH
            left -= self.WIDTH
            seached_page -= 1

        return left, right, seached_page


    def check_existing_data(self, checked_data: List, ind):
        last_index = -1

        for index, data in enumerate(self.pages):
            # print(data, checked_data, index, ind)
            if data == checked_data:
                if index == ind:
                    return ind
                last_index = index

        return last_index


    @property
    @abstractmethod
    def pages(self):
        pass

    @pages.setter
    @abstractmethod
    def pages(self, value):
        pass


    @abstractmethod
    def append_data(self, data1, data2, pos=0):
        pass


    @abstractmethod
    def show_page(self, cur_page=0):
        pass


    @abstractmethod
    def view_data_element(self, cur_page, ind):
        pass


    @abstractmethod
    def update_data_element_first_pos(self, new_data, ind):
        pass


    @abstractmethod
    def update_data_element_second_pos(self, new_data, ind):
        pass


    @abstractmethod
    def delete_data_element_by_num(self, ind):
        pass


    @abstractmethod
    def delete_data_element_by_info(self, data, ind):
        pass


    @staticmethod
    def back_to_main(cur_page, book):
        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                '« Вернуться назад',
                callback_data=Book.list.new(
                    name=book, id='-', page_num=cur_page, action='main')),
        )
        return markup


class Links(Book):
    def __init__(self, user_id):
        super().__init__(user_id)


    @property
    def pages(self):
        self._pages = json.loads(
            db.get('users', 'links', 'user_id', self.user_id))
        self._pages = [[str(e) for e in pair] for pair in self._pages]
        return self._pages


    @pages.setter
    def pages(self, value):
        if isinstance(value, list):
            self._pages = value
            user_data = json.dumps(self._pages, ensure_ascii=False)
            db.update('users', (('links', user_data), ), 'user_id', self.user_id)
        else:
            raise TypeError


    def show_page(self, cur_page=0):
        markup = types.InlineKeyboardMarkup()
        menu = []
        left = cur_page * self.WIDTH
        right = cur_page*self.WIDTH + self.WIDTH
        if not self.pages[left:right]:
            left, right, cur_page = self.search_nonempty_page(left, right, cur_page)

        if cur_page > 0:
            # Added button for back listing
            menu.append(types.InlineKeyboardButton(
                    '«',
                    callback_data=self.list.new(
                        name='links', id='-', page_num=cur_page-1, action='prev'))
                        )

        if self.pages:
            text = 'Ваши ссылки\n'
            offcut = self.pages[left:right]
            for ind, link in enumerate(offcut, start=left+1):
                text += (f"№{ind}\n"
                         f"Предмет/Преподаватель: {link[0]}\n"
                         f"Ссылка на пару: {link[1]}\n\n")
                menu.append(types.InlineKeyboardButton(
                        ind,
                        callback_data=self.list.new(
                            name='links', id=ind, page_num=cur_page, action='view'))
                            )
        else:
            text = (
                'Список Ваших ссылок пуст.\n'
                'Нажмите кнопку Добавить ссылку '
                'для добавления очередной ссылки. \n\n'
                'Поддерживается не более 15 ссылок. \n'
                'Если предмет/преподаватель указаны корректно, то '
                'при оповещении о начале пары. '
                'cсылка добавится автоматически.'
            )


        if right < len(self.pages):
            # Added button for forward listing
            menu.append(types.InlineKeyboardButton(
                    '»',
                    callback_data=self.list.new(
                        name='links', id='-', page_num=cur_page+1, action='next'))
                        )

        markup.row(*menu)

        markup.add(
            types.InlineKeyboardButton(
                'Добавить ссылку',
                callback_data=self.list.new(
                    name='links', id='-', page_num=cur_page, action='add')),
        )

        return text, markup


    def append_data(self, lesson, url, pos=0):
        if len(self.pages) >= 15:
            # Too many links!
            return -1
        list = self.pages
        list.insert(pos, [lesson, url])
        self.pages = list
        return 0


    def view_data_element(self, cur_page, ind):
        markup = types.InlineKeyboardMarkup()

        text = ''.join(f"№{ind+1}\n"
                       f"Предмет/Преподаватель: {self.pages[ind][0]}\n"
                       f"Ссылка на пару: {self.pages[ind][1]}\n")
        markup.row(
            types.InlineKeyboardButton(
                'Изменить предмет/препод.',
                callback_data=self.list.new(
                    name='links', id="1", page_num=cur_page, action='edit')),

            types.InlineKeyboardButton(
                'Изменить ссылку',
                callback_data=self.list.new(
                    name='links', id="2", page_num=cur_page, action='edit')),
        )
        markup.row(
            types.InlineKeyboardButton(
                'Удалить ссылку',
                callback_data=self.list.new(
                    name='links', id=ind, page_num=cur_page, action='delete')),

            types.InlineKeyboardButton(
                '« Вернуться назад',
                callback_data=self.list.new(
                    name='links', id='-', page_num=cur_page, action='main')),
        )
        return text, markup


    def update_data_element_first_pos(self, new_data, ind):
        user_pages = self.pages
        user_pages[ind][0] = new_data.strip()
        self.pages = user_pages


    def update_data_element_second_pos(self, new_data, ind):
        user_pages = self.pages
        user_pages[ind][1] = new_data.strip()
        self.pages = user_pages


    def delete_data_element_by_num(self, ind):
        list = self.pages
        if 0 <= ind < len(list):
            del list[ind]
            self.pages = list
            return 0
        else:
            return -1


    def delete_data_element_by_info(self, data):
        user_pages = self.pages
        for index, element in enumerate(user_pages):
            if element == data:
                del user_pages[index]
                self.pages = user_pages
                return 0

        return -1

    @staticmethod
    def parse_msg(text):
        searched_data = re.findall(
            r".(.?)$\D+: (.*)$\D+: (.*)",
            text,
            re.M,
        )
        return [list(e) for e in searched_data]


class Homework(Book):
    def __init__(self, user_id):
        super().__init__(user_id)


    @property
    def pages(self):
        self._pages = json.loads(
            db.get('users', 'homework', 'user_id', self.user_id))
        return self._pages


    @pages.setter
    def pages(self, value):
        if isinstance(value, list):
            self._pages = value
            user_data = json.dumps(self._pages, ensure_ascii=False)
            db.update('users', (('homework', user_data), ), 'user_id', self.user_id)
        else:
            raise TypeError


    def check_existing_data(self, checked_data: List, checked_ind):
        last_index = -1
        name = checked_data[0]
        homeworks = checked_data[1][0] if len(checked_data[1]) == 1 else []

        for index, data in enumerate(self.pages):
            # data = [lesson_name, [homeworks, ...]]
            # checked_data = [lesson_name, [homeworks, ...]
            if data == checked_data or homeworks in data[1] and checked_data[0] == data[0]:
                if index == checked_ind:
                    return checked_ind
                last_index = index

        return last_index


    def show_page(self, cur_page=0):
        markup = types.InlineKeyboardMarkup()
        menu = []
        left = cur_page * self.WIDTH
        right = cur_page*self.WIDTH + self.WIDTH
        if not self.pages[left:right]:
            left, right, cur_page = self.search_nonempty_page(left, right, cur_page)

        if cur_page > 0:
            # Added button for back listing
            menu.append(types.InlineKeyboardButton(
                    '«',
                    callback_data=self.list.new(
                        name='homework', id='-', page_num=cur_page-1, action='prev'))
                        )

        if self.pages:
            text = 'Ваши домашние задания\n'
            offcut = self.pages[left:right]
            for ind, homework in enumerate(offcut, start=left+1):
                text += (f"№{ind}\n"
                         f"Предмет: {homework[0]}\n"
                         f"Домашка: \n")
                for index, elem in enumerate(homework[1], start=1):
                    text += f"{index}) {elem}\n"
                menu.append(types.InlineKeyboardButton(
                        ind,
                        callback_data=self.list.new(
                            name='homework', id=ind, page_num=cur_page, action='view'))
                            )
                if homework != offcut[-1]:
                    text += "—————————————————————\n"
        else:
            text = (
                'Список Ваших домашних работ пуст.\n'
                'Нажмите кнопку Добавить предмет '
                'для добавления предмета. \n\n'
                'Поддерживается не более 15-ти предметов и 5-ти домашек '
                'для каждого предмета. \n'
            )


        if right < len(self.pages):
            # Added button for forward listing
            menu.append(types.InlineKeyboardButton(
                    '»',
                    callback_data=self.list.new(
                        name='homework', id='-', page_num=cur_page+1, action='next'))
                        )

        markup.row(*menu)

        markup.add(
            types.InlineKeyboardButton(
                'Добавить предмет',
                callback_data=self.list.new(
                    name='homework', id='-', page_num=cur_page, action='add')),
        )

        return text, markup


    def append_data(self, subject=None, homework='', pos=0, ind=-1):
        if len(self.pages) >= 15:
            # Too many homeworks!
            return -1
        list = self.pages
        if subject is not None:
            list.insert(pos, [subject, homework])
        elif ind != -1 and len(list[ind][1]) < 5:
            list[ind][1].append(homework)
        else:
            return -1

        self.pages = list
        return 0


    def view_data_element(self, cur_page, ind):
        markup = types.InlineKeyboardMarkup()
        user_page = self.pages[ind]
        text = ''.join(f"№{ind+1}\n"
                       f"Предмет: {user_page[0]}\n"
                       f"Домашка: \n")
        menu = []
        for index, elem in enumerate(user_page[1], start=1):
            text += f'{index}) {elem}\n'
            menu.append(
                types.InlineKeyboardButton(
                    index,
                    callback_data=self.list.new(
                        name='homework', id=index, page_num=ind, action='view2')),
            )

        markup.row(*menu)

        markup.row(
            types.InlineKeyboardButton(
                'Изменить предмет',
                callback_data=self.list.new(
                    name='homework', id="1", page_num=cur_page, action='edit')),

            types.InlineKeyboardButton(
                'Добавить домашку',
                callback_data=self.list.new(
                    name='homework', id=ind, page_num=cur_page, action='add2')),
        )

        markup.row(
            types.InlineKeyboardButton(
                'Удалить предмет',
                callback_data=self.list.new(
                    name='homework', id=ind, page_num=cur_page, action='delete')),

            types.InlineKeyboardButton(
                '« Вернуться назад',
                callback_data=self.list.new(
                    name='homework', id='-', page_num=cur_page, action='main')),
        )
        return text, markup


    def view2_data_element(self, ind_sub, ind_hmw):
        markup = types.InlineKeyboardMarkup()
        user_page = self.pages[ind_sub]

        text = (f"№{ind_sub+1}\n"
                f"Предмет: {user_page[0]}\n"
                f"Домашка: \n"
                f"{ind_hmw+1}) {user_page[1][ind_hmw]}")

        markup.add(
            types.InlineKeyboardButton(
                'Изменить домашку',
                callback_data=self.list.new(
                    name='homework', id=ind_sub+1, page_num=ind_hmw+1, action='edit2')),
        )

        markup.row(
            types.InlineKeyboardButton(
                'Удалить домашку',
                callback_data=self.list.new(
                    name='homework', id=ind_sub+1, page_num=ind_hmw+1, action='delete2')),

            types.InlineKeyboardButton(
                '« Вернуться назад',
                callback_data=self.list.new(
                    name='homework', id=ind_sub+1, page_num=0, action='view')),
        )
        return text, markup


    def update_data_element_first_pos(self, new_data, ind):
        user_pages = self.pages
        user_pages[ind][0] = new_data.strip()
        self.pages = user_pages


    def update_data_element_second_pos(self, new_data, ind_sub, ind_hmw):
        user_pages = self.pages
        user_pages[ind_sub][1][ind_hmw] = new_data.strip()
        self.pages = user_pages


    def delete_data_element_by_num(self, ind):
        list = self.pages
        if 0 <= ind < len(list):
            del list[ind]
            self.pages = list
            return 0
        else:
            return -1


    def delete_data_element_by_info(self, data):
        user_pages = self.pages
        for index, element in enumerate(user_pages):
            if element == data:
                del user_pages[index]
                self.pages = user_pages
                return 0

        return -1

    def delete_homework_by_ind(self, ind_sub, ind_hmw):
        user_pages = self.pages
        if 0 <= ind_sub < len(user_pages) and \
                0 <= ind_hmw < len(user_pages[ind_sub][1]):
            del user_pages[ind_sub][1][ind_hmw]
            self.pages = user_pages
            return 0
        else:
            return -1


    @staticmethod
    def parse_msg(text):
        lesson_name = re.findall(r".(.*?)\n.*: (.*)", text)
        elements = re.findall(r"\d*\) (.*)$|\—+", text, re.M)
        searched_data = []
        start = 0
        for lesson in lesson_name:
            list = []
            for index2, elem in enumerate(elements[start:]):
                if elem == '':
                    start += index2+1
                    break
                list.append(elem)
            searched_data.append([int(lesson[0]), lesson[1], list.copy()])
        return searched_data
