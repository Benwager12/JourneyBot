import json
import sqlite3

import helpers.file.config as config
from helpers.file import models


def get(user_id, param):
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        get_parameter = f"SELECT {param} FROM user_settings WHERE user_id = ?"
        cur.execute(get_parameter, [user_id])

        fetch = cur.fetchone()
        if fetch is None:
            return None

        return fetch[0]


def get_all(user_id):
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        get_parameter = f"SELECT * FROM user_settings WHERE user_id = ?"
        cur.execute(get_parameter, [user_id])

        fetch = cur.fetchone()
        if fetch is None:
            return None

        return fetch[0]


def set(user_id, param, value):
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        get_parameter = f"SELECT {param} FROM user_settings WHERE user_id = ?"
        cur.execute(get_parameter, [user_id])

        fetch = cur.fetchone()
        if fetch is None:
            insert = f"INSERT INTO user_settings (user_id, {param}) VALUES (?, ?)"
            cur.execute(insert, [user_id, value])
        else:
            update = f"UPDATE user_settings SET {param} = ? WHERE user_id = ?"
            cur.execute(update, [value, user_id])
        con.commit()


def get_default(user_id, param, default):
    return get(user_id, param) or default


def get_negative_prompt_list(author_id):
    negative_prompt_str = get_default(author_id, "negative_prompt", "{}")
    negative_prompt = json.loads(negative_prompt_str)

    negative_prompt_list = []
    for model_id in range(len(models.get_raw())):
        negative_prompt_list.append(
            f"{models.get(model_id)['name']} - `{negative_prompt.get(str(model_id), 'None')}`")

    return "\n".join(negative_prompt_list)
