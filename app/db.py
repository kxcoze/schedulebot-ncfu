import os

import sqlite3

import parsingSchedule

conn = sqlite3.connect(os.path.join("db", "users_codes.db"), check_same_thread=False)

cursor = conn.cursor()

def get_cursor():
    return cursor

def init_db():
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id TEXT PRIMARY KEY,
        group_code INT,
        subgroup TEXT, 
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


def insert_codes():
    try:
        delete_table('univer_code')
    except:
        # Succesfully deleted
        pass
    finally:
        init_db()

    data = parsingSchedule.get_codes()
    # [0] - Институт, [1] - Специальность, [2] - Группа, [3] - Код группы
    data_to_insert = ['','','','']
    for item in data:
        data_to_insert[0] = item['instituteName'].lower()
        for speciality in item['specialities']:
            data_to_insert[1] = speciality['specialityName'].lower()
            for group in speciality['groups']:
                data_to_insert[2] = group['groupName'].lower()
                data_to_insert[3] = group['groupCode'].lower()
                # Возможно стоит отправлять результаты вставки в логи?
                try:
                    print("NEW DATA -> ", data_to_insert)
                    cursor.execute("INSERT INTO univer_code VALUES (?,?,?,?)", tuple(data_to_insert))
                    conn.commit()
                except:
                    print("ALREADY HAS -> ", data_to_insert)

def insert(table, *args):
    values = tuple(args)
    placeholders = ', '.join('?' * len(values))
    cursor.execute(f"INSERT INTO {table} VALUES ({placeholders})", values)
    conn.commit()

def update(table, data, item, value):
    # type(data) - List -> List[0] - to_change, List[1] - value
    for comb in data:
        detected, to_change = comb[0], comb[1]
        cursor.execute(f"UPDATE {table} SET {detected} = ? WHERE {item} = ?", (to_change, value))
        conn.commit()

def get(table, *args):
    detected = args[0]
    item = args[1]
    value = args[2]
    cursor.execute(f"SELECT {detected} FROM {table} WHERE {item} = '{value}'")
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return -1

def fetchall(table, columns):
    columns_joined = ', '.join(columns)
    cursor.execute(f"SELECT {columns_joined} FROM {table}")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        dict_row = {}
        for index, column in enumerate(columns):
            dict_row[column] = row[index]
        result.append(dict_row)
    return result

def delete_table(table):
    cursor.execute(f"DROP TABLE {table}")
    conn.commit()

def delete(table, *args):
    item = args[0]
    value = args[1]
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
