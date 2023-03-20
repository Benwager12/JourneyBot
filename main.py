import asyncio
import json
import os.path
import sqlite3

import discord
import requests as requests
from discord import Message, User
from discord.ext import commands
from discord.ext.commands import Context, CommandError


def fetch_config():
    with open('config.json') as f:
        return json.load(f)


def fetch_users():
    with open('allowed_users.txt') as f:
        return [int(x) for x in f.read().splitlines()]


def fetch_models():
    with open('models.json') as f:
        return json.load(f)


config = fetch_config()
BASE_URL = "https://api.runpod.ai/v1"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='*', intents=intents)

allowed_users = fetch_users()
models = fetch_models()

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config['RUNPOD_KEY']}"
}


@bot.check
async def is_allowed_user(ctx: Context):
    return ctx.author.id in allowed_users or ctx.author.id == config['OWNER_ID']


@bot.event
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.CheckFailure):
        print(f"User {ctx.author} ({ctx.author.id}) tried to use command {ctx.command}")
        return

    print(f"Command {ctx.command} failed with error {error.__class__.__name__} for reason \"{error.__cause__}\".")
    raise error


def set_user_setting(user_id: int, setting: str, value):
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()
        user_model_sql = "SELECT model_id FROM user_settings WHERE user_id = ?"
        cur.execute(user_model_sql, [user_id])
        if cur.fetchone() is None:
            sql_statement = f"INSERT INTO user_settings (user_id, {setting}) VALUES (?, ?)"
            cur.execute(sql_statement, [user_id, value])
        else:
            sql_statement = f"UPDATE user_settings SET {setting} = ? WHERE user_id = ?"
            cur.execute(sql_statement, [value, user_id])
        con.commit()


def make_job(params, user_model) -> int:
    run_url = f"{BASE_URL}/{models[user_model]['endpoint_id']}/run"
    response = requests.post(run_url, headers=headers, json=params)
    response_json = response.json()

    return response_json['id']


def get_job_status(job_id, user_model) -> (int, str):
    status_url = f"{BASE_URL}/{models[user_model]['endpoint_id']}/status/{job_id}"
    response = requests.post(status_url, headers=headers)

    response_json = response.json()

    if not response.status_code == 200:
        return 0, f"Error {response.status_code}"

    response_status = response_json['status']

    if response_status == "FAILED":
        return -1, response_json

    if response_status == "COMPLETED":
        return 1, response_json['output']

    if response_status == "IN_QUEUE":
        return 2, response_status

    if response_status == "IN_PROGRESS":
        return 3, response_status
    return 4, response_status


def get_setting(user_id, param):
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()
        get_parameter = f"SELECT {param} FROM user_settings WHERE user_id = ?"
        cur.execute(get_parameter, [user_id])

        fetch = cur.fetchone()
        if fetch is None:
            return None
        else:
            return fetch[0]


def get_setting_default(user_id, param, default):
    return get_setting(user_id, param) or default


def make_params(user_id, prompt) -> dict:
    width = get_setting(user_id, "width")
    if width is None:
        width = 512

    height = get_setting(user_id, "height")
    if height is None:
        height = 512

    return {
        "input": {
            "prompt": prompt,
            "width": width,
            "height": height
        }
    }


async def wait_job(message: Message, job_id: int, user_model: int):
    output = None

    while output is None:
        await asyncio.sleep(5)
        code, response = get_job_status(job_id, user_model)

        print(f"{code}: {response}")
        match code:
            case 0:
                await message.edit(content=f"{message.content}\nHTTP request error!")
                return
            case 1:
                output = response
                await message.edit(content=f"{message.content}\nImage has been generated, downloading...")
                break
            case -1:
                await message.edit(content=f"{message.content}\nError: {response}")
                return
            case 2:
                await message.edit(content=f"{message.content}\nImage is in queue...")
                continue
            case 3:
                await message.edit(content=f"{message.content}\nImage is being generated...")
                continue

    for index, image in enumerate(output):
        image_url = image['image']
        r = requests.get(image_url)

        with open(f"images/{job_id}-{index}.png", "wb") as f:
            f.write(r.content)

    return output, message


async def create_image(prompt: str, message: Message, author: User):
    con = sqlite3.connect(config['DATABASE_FILE'])
    cur = con.cursor()

    user_model = get_setting_default(author.id, "model_id", 0)
    params = make_params(author.id, prompt)

    job_id = make_job(params, user_model)
    output, message = await wait_job(message, job_id, user_model)

    for image in output:
        sql_statement: str = f"INSERT INTO images (job_id, seed, prompt, author_id, model_id) VALUES (?, ?, ?, ?, ?)"
        cur.execute(sql_statement, [job_id, image['seed'], prompt, author.id, user_model])
    con.commit()
    return job_id


async def make_image(prompt, model, message, author):
    con = sqlite3.connect(config['DATABASE_FILE'])
    cur = con.cursor()

    params = make_params(author.id, prompt)
    job_id = make_job(params, model)
    output, message = await wait_job(message, job_id, model)

    for image in output:
        sql_statement: str = "INSERT INTO images (job_id, seed, prompt, author_id, model_id) VALUES (?, ?, ?, ?, ?)"
        cur.execute(sql_statement, [job_id, image['seed'], prompt, author.id, model])
    con.commit()

    return job_id


async def multicreate_image(prompt: str, message: Message, author: User):
    jobs = [asyncio.create_task(make_image(prompt, model_id, message, author)) for model_id in range(len(models))]
    return await asyncio.wait(jobs)


@bot.command(aliases=["c", "make", "generate", "mc", "mcreate", "mgenerate", "multicreate"])
async def create(ctx: Context, *args):
    multi = False

    if ctx.invoked_with in ["mc", "mcreate", "mgenerate", "multicreate"]:
        multi = True

    if len(args) >= 1 and args[0] == "multi":
        multi = True
        args = args[1:]

    if len(args) == 0:
        await ctx.send("Please provide a prompt.")
        return

    prompt = " ".join(args)

    if "`" in prompt:
        await ctx.reply("Please do not use backticks in your prompt.")
        return

    if "\"" in prompt or "'" in prompt:
        await ctx.reply("Please do not use quotes in your prompt.")
        return

    message = await ctx.reply("Making a photo with prompt `" + prompt + "`...")

    if not multi:
        create_task = await asyncio.wait([asyncio.create_task(create_image(prompt, message, ctx.author))])
    else:
        create_task = await multicreate_image(prompt, message, ctx.author)

    job_ids = get_job_ids_from_task(create_task)

    file_list = [discord.File(f"images/{jobs}-0.png") for jobs in job_ids]
    await message.edit(attachments=file_list)

    if multi:
        await ctx.reply("Your multicreate has finished.")


@bot.group(aliases=["set"])
async def settings(ctx: Context):
    if ctx.invoked_subcommand is not None:
        return
    settings_list = {
        "Model": models[get_setting_default(ctx.author.id, "model_id", 0)]['name'],
        "Width": get_setting_default(ctx.author.id, "width", 512),
        "Height": get_setting_default(ctx.author.id, "height", 512)
    }
    settings_string = "\n".join([f"{setting} - {settings_list[setting]}" for setting in settings_list])

    embed = discord.Embed(title=f"Settings - {ctx.author.name}",
                          description=f"Your current settings\n\n{settings_string}\n\nTo change your model, "
                                      "use the `set model` command",
                          color=0x00ff00)
    await ctx.send("", embed=embed)


@settings.command()
async def model(ctx: Context, model_name: str = None):
    if model_name is None:
        await ctx.send("Please provide a model name, here are the options:\n" + get_model_list())
        return

    model_id = get_model_from_alias(model_name.lower())

    if model_id is None:
        await ctx.send("That model does not exist. Here are the options:\n" + get_model_list())
        return

    set_user_setting(ctx.author.id, "model_id", model_id)
    await ctx.reply(f"Your model has been set to {models[model_id]['name']}.")


@settings.command(aliases=["width", "height", "dim", "d"])
async def dimension(ctx: Context, dim: int = None):
    dimension_sizes = [128, 256, 384, 448, 512, 576, 640, 704, 768]
    if dim is None:
        await ctx.send(f"Please provide a {ctx.invoked_with}, it can be between `{dimension_sizes}`.")
        return

    if dim not in dimension_sizes:
        await ctx.send(f"Please provide a {ctx.invoked_with} that is between `{dimension_sizes}`.")
        return

    if ctx.invoked_with.lower() in ["width", "dimension", "dim", "d"]:
        set_user_setting(ctx.author.id, "width", dim)

    if ctx.invoked_with.lower() in ["height", "dimension", "dim", "d"]:
        set_user_setting(ctx.author.id, "height", dim)

    invoked_name = ctx.invoked_with.lower()
    if ctx.invoked_with.lower() in ["dimension", "dim", "d"]:
        invoked_name = "width and height"

    await ctx.reply(f"Your {invoked_name} has been set to {dim}.")


def get_model_list():
    model_list = []
    for current_model in models:
        model_list.append(
            f"**{current_model['name']}** - aliases: `{', '.join(current_model['aliases'])}`"
        )
    return "\n".join(model_list)


def set_user_model(user_id, model_id):
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()
        delete_previous_model_sql = "DELETE FROM user_settings WHERE user_id = ?"
        cur.execute(delete_previous_model_sql, [user_id])

        insert_new_model_sql = "INSERT INTO user_settings (user_id, model_id) VALUES (?, ?)"
        cur.execute(insert_new_model_sql, [user_id, model_id])


def get_model_from_alias(alias):
    for index, current_model in enumerate(models):
        if alias.lower() in current_model['aliases'] or alias.lower() == current_model['name'].lower():
            return index
    return None


def get_job_ids_from_task(task):
    ids = []
    for t in task:
        for ti in t:
            ids.append(ti.result())
    return ids


@bot.event
async def on_ready():
    print("Bot created by Ben Wager.")
    invite_link = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=2048&scope=bot"
    print(f"Invite link: {invite_link}")


@bot.event
async def on_message(message: Message):
    if message.author == bot.user:
        await bot.process_commands(message)
        return

    if message.reference is None:
        await bot.process_commands(message)
        return

    channel = await bot.fetch_channel(message.reference.channel_id)
    reference_message = await channel.fetch_message(message.reference.message_id)

    if reference_message.author != bot.user:
        await bot.process_commands(message)
        return

    if message.content in ["retry", "redo", "r"]:
        # Redo the prompt that was given in the reference message
        prompt = reference_message.content.split("`")[1]

        create_task = await asyncio.wait([asyncio.create_task(
            create_image(prompt, reference_message, message.author)
        )])
        job_id = get_job_ids_from_task(create_task)[0]
        await reference_message.add_files(discord.File(f"images/{job_id}-0.png"))
        return

    if message.content in ["no", "delete", "stop", "cancel", "nope", "n"]:
        # Delete the message
        await reference_message.delete()
        return

    # If no other keywords were used, then just process the commands
    await bot.process_commands(message)


if __name__ == "__main__":
    # Make sure all the files exist
    for file in ["config.json", "allowed_users.txt", "models.json", config['DATABASE_FILE']]:
        if not os.path.isfile(file):
            print("Please create a " + file + " file.")
            exit()
    if not os.path.exists("images"):
        os.mkdir("images")

    bot.run(config["DISCORD_TOKEN"])

