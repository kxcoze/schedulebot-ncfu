import os

import json
import sqlite3
import parseSchedule

conn = sqlite3.connect(os.path.join("db", "users_codes.db"))
cursor = conn.cursor()

def get_cursor():
    return cursor

def init_db():
    print("EXECUTING")
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id TEXT PRIMARY KEY,
        group_code INT,
        notifications INT,
        schedule TEXT);
    """)
    

    cursor.execute("""CREATE TABLE IF NOT EXISTS univer_code(
        institute_name TEXT,
        speciality_name TEXT,
        group_name TEXT,
        group_code INT,
        CONSTRAINT pk PRIMARY KEY (institute_name, speciality_name, group_name));
    """)
    conn.commit()

def insert_user_with_schedule(data):
    # data[0] - user_id, data[1] - group_code, data[2] - notifications, data[3] - schedule
    cursor.execute("INSERT INTO users VALUES (?,?,?,?);", data)
    conn.commit()

def update_user_schedule(data):
    pass

def update_user_group_code(data):
    # data[0] - group_code, data[1] - user_id
    cursor.execute("UPDATE users SET group_code = (?) WHERE user_id = (?);", tuple(data))
    conn.commit()

def get_users():
    cursor.execute("SELECT * FROM users;")
    results = cursor.fetchall()
    print(results)

def get_group_code(data):
    cursor.execute(f"SELECT group_code FROM univer_code WHERE group_name = '{data}';")
    result = cursor.fetchone()
    print(result)

def insert_codes(data):
    # [0] - Институт, [1] - Специальность, [2] - Группа, [3] - Код группы
    data_to_insert = ['','','','']
    for item in data:
        data_to_insert[0] = item['instituteName'].lower()
        for speciality in item['specialities']:
            data_to_insert[1] = speciality['specialityName'].lower()
            for group in speciality['groups']:
                data_to_insert[2] = group['groupName'].lower()
                data_to_insert[3] = group['groupCode'].lower()
                
                try:
                    print(data_to_insert)
                    cursor.execute("INSERT INTO univer_code VALUES (?,?,?,?)", tuple(data_to_insert))
                    conn.commit()
                except:
                    print("ALREADY HAS")


def check_db_exists():
    cursor.execute("SELECT name FROM sqlite_master "
                   "WHERE type='table' AND name='users'")
    #cursor.execute("DROP TABLE users")
    #conn.commit()
    table_exists = cursor.fetchall()
    if table_exists:
        print("EXIST")
        #insert_user()
        #get_users()
        #insert_codes(parseSchedule.get_codes())
        while True:   
            get_group_code(input().lower())
        #update_user_group_code([22222, '43284'])
        return
    init_db()


if __name__ == '__main__':
    check_db_exists()
