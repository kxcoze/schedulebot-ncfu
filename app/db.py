import os

import sqlite3
import parseSchedule

conn = sqlite3.connect(os.path.join("db", "users_codes.db"))

cursor = conn.cursor()

def get_cursor():
    return cursor

def init_db():
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

def insert(*args):
    table = args[0]
    data = tuple(args[1:5])
    cursor.execute(f"INSERT INTO {table} VALUES (?,?,?,?);", data)
    conn.commit()

def update(*args):
    table = args[0]
    detected = args[1]
    to_change = args[2]
    item = args[3]
    value = args[4]
    cursor.execute(f"UPDATE {table} SET {detected} = ? WHERE {item} = ?", (to_change, value))
    #cursor.execute(f"UPDATE {table} SET {detected} = " + to_change +
    #              f"WHERE {item} = {value};")
    conn.commit()

def get(*args):
    detected = args[0]
    table = args[1]
    item = args[2]
    value = args[3]
    cursor.execute(f"SELECT {detected} FROM {table} WHERE {item} = '{value}'")
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return -1

def delete_table(table):
    cursor.execute(f"DROP TABLE {table};")
    conn.commit()

def delete(*args):
    table = args[0]
    item = args[1]
    value = args[2]
    cursor.execute(f"DELETE FROM {table} WHERE {item} = {value}")
    conn.commit()

def check_db_exists():
    cursor.execute("SELECT name FROM sqlite_master "
                   "WHERE type='table' AND name='users'")
    conn.commit()
    table_exists = cursor.fetchall()
    if table_exists:
        return
    init_db()


check_db_exists()
