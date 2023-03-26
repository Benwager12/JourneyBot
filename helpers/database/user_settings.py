import json
import sqlite3

import discord

import helpers.file.config as config
from helpers.database import images
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


def favourite_exists(job_id, user_id):
    favourite_sql = "SELECT favourites FROM user_settings WHERE user_id = ?"
    
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(favourite_sql, [user_id])
        favourites = cur.fetchone()

        if favourites is None:
            return False
        else:
            if favourites[0] is None:
                return False
            favourites = json.loads(favourites[0])
            return job_id in favourites


def set_favourite(job_id, id):
    favourite_sql = "SELECT favourites FROM user_settings WHERE user_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(favourite_sql, [id])
        favourites = cur.fetchone()

        favourites = [] if favourites is None or favourites[0] is None else json.loads(favourites[0])
        favourites.append(job_id)

        favourites = json.dumps(favourites)
        update_sql = "UPDATE user_settings SET favourites = ? WHERE user_id = ?"
        cur.execute(update_sql, [favourites, id])
        con.commit()


def remove_favourite(job_id, id):
    favourite_sql = "SELECT favourites FROM user_settings WHERE user_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(favourite_sql, [id])
        favourites = cur.fetchone()

        favourites = [] if favourites is None or favourites[0] is None else json.loads(favourites[0])
        favourites.remove(job_id)

        favourites = json.dumps(favourites)
        update_sql = "UPDATE user_settings SET favourites = ? WHERE user_id = ?"
        cur.execute(update_sql, [favourites, id])
        con.commit()


def get_favourites(user_id):
    favourite_sql = "SELECT favourites FROM user_settings WHERE user_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(favourite_sql, [user_id])
        favourites = cur.fetchone()

        favourites = None if favourites is None or favourites[0] is None else json.loads(favourites[0])
        return favourites


def get_favourites_page(author_id: int, page_number: int, page_size: int = 5):
    user_favourites = get_favourites(author_id)

    if user_favourites is None:
        return None

    start = (page_number - 1) * page_size
    end = start + page_size
    print(start, end)

    return user_favourites[start:end]


def get_favourite_amount(author_id):
    count_favourites_sql = "SELECT favourites FROM user_settings WHERE user_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(count_favourites_sql, [author_id])
        favourites = cur.fetchone()
        favourites = None if favourites is None or favourites[0] is None else json.loads(favourites[0])

        count = len(favourites) if favourites is not None else 0
        return count


def get_favourite_page_amount(author_id, page_size):
    favourite_amount = get_favourite_amount(author_id)
    page_amount = favourite_amount // page_size

    if favourite_amount % page_size != 0:
        page_amount += 1
    return page_amount


def get_favourites_embed(author_id: int, page_number: int = 1, page_size: int = 5) -> (str, discord.Embed):
    paginated_favourites = get_favourites_page(author_id, page_number, page_size)
    favourite_amount = get_favourite_amount(author_id)
    page_amount = get_favourite_page_amount(author_id, page_size)

    if page_number > page_amount or page_number < 1:
        page_number = 1

    if favourite_amount == 0:
        return "You have no favourited images.", None

    job_string = []
    for job_number in range(0, 10 if len(paginated_favourites) > 10 else len(paginated_favourites)):
        job_id = paginated_favourites[job_number]
        job = images.lookup_job(job_id)
        job_param = json.loads(job[2])

        job_string.append(f"`{job_id}`: `{job_param['input']['prompt']}`")
    job_string = "\n".join(job_string)

    # Create an embed listing all the jobs with their job IDs
    embed = discord.Embed(
        title="Your Favourites",
        description=f"Your images are listed below\n\n{job_string}."
    )
    embed.set_footer(text=f"Page `{page_number} / {page_amount}`")

    return "", embed