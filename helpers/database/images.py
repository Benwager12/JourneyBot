import json
import os.path
import sqlite3
import time

import discord

from helpers.file import config


def lookup_job(job_id: str):
    find_job_sql = "SELECT * FROM images WHERE job_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(find_job_sql, [job_id])
        job = cur.fetchone()

        if job is None:
            return None
        return job


def belongs_to(job, user_id):
    return int(job[2]) == user_id


def insert_image(job_id, seed, params, author_id, model_id):
    insertion_sql = f"INSERT INTO images (job_id, seed, parameters, author_id, model_id, insertion_time) " \
                    f"VALUES (?, ?, ?, ?, ?, ?)"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(insertion_sql, [job_id, seed, json.dumps(params), author_id, model_id, time.time()])
    con.commit()


def get_all_jobs(author_id: int):
    all_jobs_sql = "SELECT * FROM images WHERE author_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(all_jobs_sql, [author_id])
        jobs = cur.fetchall()

        if jobs is None:
            return None
        return jobs


def get_all_jobs_page(author_id: int, page_number: int, page_size: int = 5):
    paginate_jobs_sql = "SELECT * FROM images WHERE author_id = ? LIMIT ? OFFSET ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(paginate_jobs_sql, [author_id, page_size, (page_number - 1) * page_size])
        jobs = cur.fetchall()

        if jobs is None:
            return None
        return jobs


def get_job_amount(author_id: int):
    count_jobs_sql = "SELECT COUNT(*) FROM images WHERE author_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(count_jobs_sql, [author_id])
        count = cur.fetchone()

        if count is None:
            return None
        return count[0]


def get_page_amount(author_id: int, page_size: int = 5):
    count_jobs_sql = "SELECT COUNT(*) FROM images WHERE author_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(count_jobs_sql, [author_id])
        count = cur.fetchone()

        if count is None:
            return None

        if count[0] % page_size == 0:
            return count[0] // page_size
        return (count[0] // page_size) + 1


def get_gallery_embed(author_id: int, page_number: int = 1, page_size: int = 5) -> (str, discord.Embed):
    paginated_jobs = get_all_jobs_page(author_id, page_number, page_size)
    job_amount = get_job_amount(author_id)
    page_amount = get_page_amount(author_id, page_size)

    if job_amount == 0:
        return "You have no images in your gallery.", None

    job_string = []
    for job_number in range(0, 10 if len(paginated_jobs) > 10 else len(paginated_jobs)):
        job = paginated_jobs[job_number]
        if not job[2].startswith("{"):
            prompt = job[2]
        else:
            prompt = json.loads(job[2])["input"]["prompt"]
        job_string.append(f"**`{job[0]}`**: `{prompt}`")
    job_string = "\n".join(job_string)

    # Create an embed listing all the jobs with their job IDs
    embed = discord.Embed(
        title="Your Gallery",
        description=f"Your images are listed below\n\n{job_string}."
    )
    embed.set_footer(text=f"Page `{page_number} / {page_amount}`")

    return "", embed


def get_latest_job_id(author_id: int):
    latest_job_sql = "SELECT job_id FROM images WHERE author_id = ? ORDER BY insertion_time DESC LIMIT 1"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(latest_job_sql, [author_id])
        job = cur.fetchone()

        if job is None:
            return None
        return job[0]


def alias_exists(alias, user_id):
    alias_sql = "SELECT * FROM images WHERE alias = ? AND author_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(alias_sql, [alias, user_id])
        alias = cur.fetchone()

        return not alias is None


def set_alias(job_id, alias):
    alias_sql = "UPDATE images SET alias = ? WHERE job_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(alias_sql, [alias, job_id])
    con.commit()


def lookup_alias(alias, user_id):
    alias_sql = "SELECT * FROM images WHERE alias = ? AND author_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(alias_sql, [alias, user_id])
        job_alias = cur.fetchone()

        return job_alias


def remove_alias(alias, user_id):
    delete_alias_sql = "UPDATE images SET alias = NULL WHERE alias = ? AND author_id = ?"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        cur.execute(delete_alias_sql, [alias, user_id])


def get_aliases(user_id):
    alias_sql = "SELECT * FROM images WHERE author_id = ? AND alias IS NOT NULL"

    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()

        cur.execute(alias_sql, [user_id])
        aliases = cur.fetchall()

        return aliases


def get_job_path(previous_job_id):
    if previous_job_id is None:
        return None

    if os.path.exists("images/" + str(previous_job_id)):
        return os.listdir("images/" + str(previous_job_id))
    elif os.path.exists("images/" + str(previous_job_id) + ".png"):
        return ["images/" + str(previous_job_id) + ".png"]
    else:
        return None
