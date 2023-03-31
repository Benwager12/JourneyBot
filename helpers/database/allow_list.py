import sqlite3

from helpers.file import config


def add_user(user_id, added_by, guild_id):
    if is_user_allowed(user_id):
        return False
    add_user_sql = "INSERT INTO allow_list VALUES (?, ?, ?)"
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(add_user_sql, [user_id, added_by, guild_id])
    con.commit()
    return True


def remove_user(user_id):
    if not is_user_allowed(user_id):
        return False
    remove_user_sql = "DELETE FROM allow_list WHERE user_id = ?"
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(remove_user_sql, [user_id])
    con.commit()
    return True


def get_users():
    get_users_sql = "SELECT user_id FROM allow_list"
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(get_users_sql)
        users = cur.fetchall()
    return users


def get_user(user_id):
    get_user_sql = "SELECT * FROM allow_list WHERE user_id = ?"
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(get_user_sql, [user_id])
        user = cur.fetchone()
    return user


def is_user_allowed(user_id):
    get_user_sql = "SELECT * FROM allow_list WHERE user_id = ?"
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(get_user_sql, [user_id])
        user = cur.fetchone()
    return user is not None
