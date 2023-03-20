import asyncio
import json
import os.path
import sqlite3

import discord
import requests as requests
from discord import Message, User
from discord.ext import commands
from discord.ext.commands import Context


def fetch_config():
    with open('config.json') as f:
        return json.load(f)


config = fetch_config()


def fetch_users():
    with open('allowed_users.txt') as f:
        return [int(x) for x in f.read().splitlines()]


def fetch_models():
    with open('models.json') as f:
        return json.load(f)


def set_user_setting(user_id: int, setting: str, value):
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()
        user_model_sql = "SELECT model_id FROM user_settings WHERE user_id = ?"
        cur.execute(user_model_sql, [user_id])
        if cur.fetchone() is None:
            sql_statement = "INSERT INTO user_settings (user_id, ?) VALUES (?, ?)"
            cur.execute(sql_statement, [user_id, setting, value])
        else:
            sql_statement = f"UPDATE user_settings SET {setting} = ? WHERE user_id = ?"
            cur.execute(sql_statement, [value, user_id])
        con.commit()


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
    jobs = [asyncio.create_task(make_image(prompt, model, message, author)) for model in models]
    return await asyncio.wait(jobs)


@bot.command(aliases=["c", "make", "generate"])
async def create(ctx: Context, *args):
    if ctx.author.id not in allowed_users:
        print(f"{ctx.author.name} ({ctx.author.id}) tried to use the bot.")
        return

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

    create_task = await asyncio.wait([asyncio.create_task(
        create_image(prompt, message, ctx.author)
    )])

    job_id = get_job_ids_from_task(create_task)[0]

    await message.add_files(discord.File("images/" + str(job_id) + "-0.png"))


@bot.command()
async def settings(ctx: Context):
    if ctx.author.id not in allowed_users:
        print(f"{ctx.author.name} ({ctx.author.id}) tried to use the bot.")
        return

    user_model = get_setting_default(ctx.author.id, "model_id", 0)
    modelstr = models[user_model]['name']
    width = get_setting_default(ctx.author.id, "width", 512)
    height = get_setting_default(ctx.author.id, "height", 512)

    embed = discord.Embed(title=f"Settings - {ctx.author.name}",
                          description=f"Your current settings\n\nModel - {modelstr}\n"
                                      f"Width - {width}\nHeight - {height}\n\nTo change your model, "
                                      "use the `set model` command",
                          color=0x00ff00)
    await ctx.send("", embed=embed)


def get_model_list():
    model_list = [f"**{models[model_id]['name']}** - aliases: `{models[model_id]['aliases'].replace(',', ', ')}`"
                  for model_id in models]
    return "\n".join(model_list)


def set_user_model(user_id, model_id):
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()
        delete_previous_model_sql = "DELETE FROM user_settings WHERE user_id = ?"
        cur.execute(delete_previous_model_sql, [user_id])

        insert_new_model_sql = "INSERT INTO user_settings (user_id, model_id) VALUES (?, ?)"
        cur.execute(insert_new_model_sql, [user_id, model_id])


def get_model_from_alias(alias):
    for model_id in models:
        aliases = models[model_id]['aliases'].split(",")
        if alias.lower() in aliases or alias.lower() == models[model_id]['name'].lower():
            return model_id
    return None


def get_job_ids_from_task(task):
    ids = []
    for t in task:
        for ti in t:
            ids.append(ti.result())
    return ids


@bot.command()
async def multicreate(ctx: Context, *args):
    if ctx.author.id not in allowed_users:
        print(f"{ctx.author.name} ({ctx.author.id}) tried to use the bot.")
        return

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

    multicreate_task = await multicreate_image(prompt, message, ctx.author)

    job_ids = get_job_ids_from_task(multicreate_task)

    file_list = [discord.File(f"images/{jobs}") for jobs in job_ids]
    await message.edit(attachments=file_list)
    await ctx.reply("Your multicreate has finished.")


@bot.command()
async def set(ctx: Context, *args):
    if len(args) == 0:
        await ctx.send("Please provide a setting, this would be either `model`, `width` or `height`.")
        return
    
    setting = args[0].lower()
    
    if setting == "model":
        if len(args) == 1:
            await ctx.send("Please provide a model, here are the options:\n" + get_model_list())
            return

        model_arg = args[1]
        model_id = get_model_from_alias(model_arg)

        if model_id is None:
            await ctx.send("That model does not exist. Here are the options:\n" + get_model_list())
            return

        set_user_setting(ctx.author.id, "model_id", model_id)
        await ctx.reply(f"Your model has been set to {models[model_id]['name']}.")
        return

    if setting in ["width", "height"]:
        if len(args) == 1:
            await ctx.send(f"Please provide a {setting}.")
            return

        dimension = args[1]

        if not dimension.isdigit() or int(dimension) not in [128, 256, 384, 448, 512, 576, 640, 704, 768]:
            await ctx.send(f"That is not a valid {setting}, the valid {setting}s are "
                           "[128, 256, 384, 448, 512, 576, 640, 704, 768].")
            return

        set_user_setting(ctx.author.id, setting, int(dimension))
        await ctx.reply(f"Your {setting} has been set to {dimension}.")
        return

    await ctx.reply("That is not a valid setting, the valid settings are `model`, `width` and `height`.")


@bot.event
async def on_message(message: Message):
    if message.content not in ["no", "delete", "stop", "cancel", "nope", "retry", "redo", "r", "n"]:
        await bot.process_commands(message)
        return

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
        prompt = reference_message.content.split("`")[1]

        create_task = await asyncio.wait([asyncio.create_task(
            create_image(prompt, reference_message, message.author)
        )])
        job_id = get_job_ids_from_task(create_task)[0]
        await reference_message.add_files(discord.File(f"images/{job_id}-0.png"))
    else:
        await reference_message.delete()


if __name__ == "__main__":
    for file in ["config.json", "allowed_users.txt", "models.json", config['DATABASE_FILE']]:
        if not os.path.isfile(file):
            print("Please create a " + file + " file.")
            exit()
    if not os.path.exists("images"):
        os.mkdir("images")

    bot.run(config["DISCORD_TOKEN"])
