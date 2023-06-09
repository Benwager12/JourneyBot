import asyncio
import json
import os.path
import sqlite3

import discord
import requests as requests
from discord import utils
from discord.ext import commands

from helpers.checks.IsAllowedUser import is_allowed
from helpers.database import parse
from helpers.file import config

intents = discord.Intents.default()
intents.message_content = True


def get_prefix(_, message):
    if message.guild:
        return config.get("PREFIX", "*")
    else:
        return ""  # No prefix in DMs


bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

bot.add_check(is_allowed)


def setup_wizard():
    if not os.path.isfile("allowed_users.txt"):
        print("Allowed users file does not exist, creating...")
        print("Please enter the user IDs of the users who should be able to use the bot, "
              "separated by a comma and a space. You can get a user's ID by right clicking their name and "
              "clicking 'Copy ID'.")
        inputted_users = input("Allowed users: ").split(", ")
        with open("allowed_users.txt", "w") as f:
            f.write("\n".join(inputted_users))
    else:
        print("Allowed users file already exists, skipping...")

    if not os.path.isfile("config.json"):
        print("Config file does not exist, creating...")

        print("Please enter the token for your bot. You can get this from the Discord Developer Portal.")
        token = input("Token: ")
        config.set("DISCORD_TOKEN", token)

        print("Please enter your Runpod API key. You can get this from https://www.runpod.io/console/user/settings")
        runpod_key = input("Runpod API key: ")
        config.set("RUNPOD_KEY", runpod_key)

        print("Please enter your user id. This is so you can use the bot's commands as the owner.")
        owner_id = input("Owner ID: ")
        config.set("OWNER_ID", int(owner_id))

        print("Please enter the name of the database file. This is where the bot will store user settings.")
        database_file = input("Database file: ")
        config.set("DATABASE_FILE", database_file)

        config.save()
    else:
        print("Config file already exists, skipping...")

    if not os.path.isfile("models.json"):
        print("Model file does not exist, downloading...")
        model_file = requests.get("https://raw.githubusercontent.com/Benwager12/JourneyBot/master/models.json").json()
        with open("models.json", "w", encoding='utf-8') as f:
            json.dump(model_file, f, ensure_ascii=False, indent='\t')
    else:
        print("Model file already exists, skipping...")

    if not os.path.exists("images"):
        print("Images folder does not exist, creating...")
        os.mkdir("images")
    else:
        print("Images folder already exists, skipping...")

    if not os.path.isfile(config.get('DATABASE_FILE')):
        with open(config.get('DATABASE_FILE'), 'wb') as f:
            f.write(b'')

    if not os.path.isfile(".schema"):
        print("Model file does not exist, downloading...")
        schema_file = requests.get("https://raw.githubusercontent.com/Benwager12/JourneyBot/master/.schema")
        with open(".schema", "w", encoding='utf-8') as f:
            f.write(schema_file.text)
    else:
        print("Model file already exists, skipping...")

    print("Running schema to check if tables exist...")
    with sqlite3.connect(config.get('DATABASE_FILE')) as con:
        with open(".schema", "r") as f:
            print(f.read())
            con.executescript(f.read())

    modifications = parse.table_changes_to_match_schema()

    if modifications:
        for table, modifications_table in modifications.items():
            for col_name, modification in modifications_table.items():
                if modification.startswith("MISMATCH"):
                    _, current_type, expected_type = modification.split(" ")
                    print(f"Column '{col_name}' in table '{table}' has type '{current_type}', "
                          f"should have type '{expected_type}'.")

        print("Modifying tables to match schema...")
        with sqlite3.connect(config.get('DATABASE_FILE')) as con:
            modification_sql = parse.get_sql_modifications(modifications)
            con.executescript(modification_sql)

    print("Setup wizard complete!\n")


async def load_extensions():
    cog_names = [f'cogs.{folder.name}.{cog[:-3]}'
                 for folder in os.scandir('cogs')
                 for cog in os.listdir("cogs/" + folder.name) if cog.endswith('.py')
                 ]
    for cog in cog_names:
        await bot.load_extension(cog)
    print(f"Loaded cogs [{', '.join(cog_names)}].")


async def main():
    run_setup_wizard = False

    # Make sure all the files exist
    for file in ["config.json", "allowed_users.txt", "models.json"]:
        if not os.path.isfile(file):
            run_setup_wizard = True

    if not os.path.exists("images"):
        run_setup_wizard = True

    if len(parse.table_changes_to_match_schema()) > 0:
        run_setup_wizard = True

    if run_setup_wizard:
        print("Starting the setup wizard...")
        setup_wizard()

    await load_extensions()
    utils.setup_logging()
    print()
    await bot.start(config.get("DISCORD_TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
