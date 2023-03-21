import json
import sqlite3

from helpers.database import user_settings
from helpers.file import config


def lookup_job(job_id: str):
    with sqlite3.connect(config.get('DATABASE_FILE', 'database.sqlite3')) as con:
        cur = con.cursor()
        find_job_sql = "SELECT * FROM images WHERE job_id = ?"

        cur.execute(find_job_sql, [job_id])
        job = cur.fetchone()

        if job is None:
            return None
        return job


def insert_image(job_id, seed, params, author_id):
    model_id = user_settings.get_default(author_id, 'model_id', 0)
    insertion_sql = f"INSERT INTO images (job_id, seed, parameters, author_id, model_id) VALUES (?, ?, ?, ?, ?)"

    with sqlite3.connect(config.get('DATABASE_FILE')) as con:
        cur = con.cursor()
        cur.execute(insertion_sql, [job_id, seed, json.dumps(params), author_id, model_id])
    con.commit()
