		Телеграм-бот для расписаний СКФУ.
Необходимо реализовать: (! - Необходимо, !! - Жизненно необходимо)

1) !! Команды бота:
1.1) /start - Начать работу, поприветствовать юзера	
1.2) /help - Показ всех команд
1.3) /getGroup - *Поиск группы (см. пункт 2.1) и *запись в БД (см. пункт 4)	
1.4) /schedule - Вывод расписания на текущую *неделю (см. пункт 2) для *группы (см. пункт 1.3)
1.5) /notifyme - Подписка на *персонализированные уведомления (см. пункт 3)


2) !! Показ расписания на неделю (/schedule)
	2.1) !! Пропарсить сайт (URL = 'https://ecampus.ncfu.ru/schedule') по названиям ячеек:
		a) Института
		b) Специальности
		с) Группы (без подгруппы)
		Далее:
		2.1.1) Найти код группы для (URL = 'https://ecampus.ncfu.ru/schedule/group/<code_group>')
		2.1.2) Осуществить поиск по дням текущей недели, захватить всю информацию дня(с Понеделька по Субботу)
		2.1.3) Скомпоновать информацию о неделе для каждого дня в JSON (CSV?) отдельным файлом 
										      (с выгрузкой в БД?)
		
3) Подписка на индивидуальные уведомления о начале пары по твоему *расписанию (см. пункт 4)

4) ! Реализовать БД (SQLite) с загрузкой пользователей и их личных расписаний, 
	а также *индивидуальных уведомлений (см. пункт 3) в БД

5) Загрузить проект в Docker File для выгрузки на сервере AWS, чтобы поддерживать БД на сервере 
									и постоянный онлайн бота

*6) Место для дополнительных фич
