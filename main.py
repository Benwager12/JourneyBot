import asyncio
import json
import os.path
import sqlite3

import discord
import requests as requests
from discord import Message, User, Reaction
from discord.ext import commands
from discord.ext.commands import Context, CommandError, is_owner


def fetch_config():
    if not os.path.exists('config.json'):
        return
    with open('config.json') as f:
        return json.load(f)


def fetch_users():
    if not os.path.exists('allowed_users.txt'):
        return
    with open('allowed_users.txt') as f:
        return [int(x) for x in f.read().splitlines()]


def fetch_models():
    if not os.path.exists('models.json'):
        return
    with open('models.json') as f:
        return json.load(f)


config = fetch_config() or dict()
BASE_URL = "https://api.runpod.ai/v1"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='*', intents=intents)

allowed_users = fetch_users()
models = fetch_models()

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.get('RUNPOD_KEY', 'NO_KEY')}"
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

    model_id = get_setting(user_id, "model_id")
    negative_prompts = get_setting(user_id, "negative_prompt")

    if negative_prompts is None:
        negative_prompt = ""
    else:
        negative_prompt = json.loads(negative_prompts).get(str(model_id), "")

    settings_output = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "negative_prompt": negative_prompt
    }

    output_prompt, prompt_overrides = prompt_parse(prompt, ["width", "height", "negative_prompt", "model"])
    prompt_overrides['prompt'] = output_prompt

    final_params = {**settings_output, **prompt_overrides}

    for dim in ["width", "height"]:
        if final_params[dim] not in [128, 256, 384, 448, 512, 576, 640, 704, 768]:
            final_params[dim] = 512

    if final_params['negative_prompt'] == "":
        del final_params['negative_prompt']

    return {
        "input": final_params
    }


async def wait_job(message: Message, job_id: int, user_model: int):
    output = None
    message_beginning = message.content.split("\n")[0]
    if len(message_beginning.split("`")) < 4:
        job_ids = str(job_id)
    else:
        job_ids = message_beginning.split("`")[3]

    reference_message = await message.channel.fetch_message(message.reference.message_id)

    while output is None:
        await asyncio.sleep(5)
        code, response = get_job_status(job_id, user_model)

        match code:
            case 0:
                await message.edit(content=f"{message_beginning}\nHTTP request error!")
                return
            case 1:
                output = response
                await message.edit(content=f"{message_beginning.replace(job_ids, job_ids + ', ' + str(job_id))}"
                                           "\nImage has been generated, downloading...")
                print(f"Job {job_id} completed for user {reference_message.author} ({reference_message.id})")
                break
            case -1:
                await message.edit(content=f"{message_beginning}\nError: {response}")
                return
            case 2:
                await message.edit(content=f"{message_beginning}\nImage is in queue...")
                continue
            case 3:
                await message.edit(content=f"{message_beginning}\nImage is being generated...")
                continue

    for index, image in enumerate(output):
        image_url = image['image']
        r = requests.get(image_url)

        with open(f"images/{job_id}.png", "wb") as f:
            f.write(r.content)

    return output, message


async def create_image(prompt: str, message: Message, author: User):
    user_model = get_setting_default(author.id, "model_id", 0)
    params = make_params(author.id, prompt)

    return create_image_params(params, user_model, message, author)


async def create_image_params(params, model_id, message: Message, author: User):
    if "model" in params['input'].keys():
        new_model = get_model_from_alias(params['input']['model'])
        if new_model is not None:
            model_id = new_model
        del params['input']['model']

    print(f"User {author} ({author.id}) is creating an image with model {models[model_id]['name']} and prompt "
          f"\"{params['input']['prompt']}\".")

    con = sqlite3.connect(config['DATABASE_FILE'])
    cur = con.cursor()

    job_id = make_job(params, model_id)
    output, message = await wait_job(message, job_id, model_id)

    for image in output:
        sql_statement: str = f"INSERT INTO images (job_id, seed, parameters, author_id, model_id) VALUES (?, ?, ?, ?, ?)"
        cur.execute(sql_statement, [job_id, image['seed'], json.dumps(params), author.id, model_id])
    con.commit()
    return job_id


async def make_image(prompt, current_model, message, author):
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()

        params = make_params(author.id, prompt)
        prompt = params.get("prompt")

        job_id = make_job(params, current_model)
        output, message = await wait_job(message, job_id, current_model)

        for image in output:
            sql_statement: str = "INSERT INTO images (job_id, seed, parameters, author_id, model_id) VALUES (?, ?, ?, ?, ?)"
            cur.execute(sql_statement, [job_id, image['seed'], prompt, author.id, current_model])
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

    if len(args) >= 1 and args[0] == "-multi":
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
        user_model = get_setting_default(ctx.author.id, "model_id", 0)
        params = make_params(ctx.author.id, prompt)
        prompt = params['input']['prompt']
        message = await message.edit(content=f"Making a photo with prompt `{prompt}`... ")
        create_task = await asyncio.wait([asyncio.create_task(
            create_image_params(params, user_model, message, ctx.author)
        )])
    else:
        create_task = await multicreate_image(prompt, message, ctx.author)

    job_ids = get_job_ids_from_task(create_task)

    file_list = [discord.File(f"images/{jobs}.png") for jobs in job_ids]
    job_id_list = ", ".join([f"{job}" for job in job_ids])
    await message.edit(content=f"Making a photo with prompt `{prompt}`... (Jobs: `{job_id_list}`)",
                       attachments=file_list)
    await message.add_reaction("♻")
    await message.add_reaction("❌")

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


def get_model_list():
    model_list = []
    for current_model in models:
        model_list.append(
            f"**{current_model['name']}** - aliases: `{', '.join(current_model['aliases'])}`"
        )
    return "\n".join(model_list)


def lookup_job(job_id: str):
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()
        find_job_sql = "SELECT * FROM images WHERE job_id = ?"

        cur.execute(find_job_sql, [job_id])
        job = cur.fetchone()

        if job is None:
            return None
        return job


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
async def dimension(ctx: Context, dim: int = None, *args):
    dimension_sizes = [128, 256, 384, 448, 512, 576, 640, 704, 768]
    if dim is None:
        await ctx.send(f"Please provide a {ctx.invoked_with}, it can be between `{dimension_sizes}`.")
        return

    if dim not in dimension_sizes:
        await ctx.send(f"Please provide a {ctx.invoked_with} that is between `{dimension_sizes}`.")
        return

    if len(args) == 0:
        if ctx.invoked_with.lower() in ["width", "dimension", "dim", "d"]:
            set_user_setting(ctx.author.id, "width", dim)

        if ctx.invoked_with.lower() in ["height", "dimension", "dim", "d"]:
            set_user_setting(ctx.author.id, "height", dim)

        invoked_name = ctx.invoked_with.lower()

        if ctx.invoked_with.lower() in ["dimension", "dim", "d"]:
            invoked_name = "width and height"

        await ctx.reply(f"Your {invoked_name} has been set to {dim}.")
        return

    if not args[0].isdigit():
        await ctx.reply("Please make sure your second dimensions argument is a number.")
        return

    if len(args) >= 1 and ctx.invoked_with.lower() in ["dimension", "dim", "d"]:
        if int(args[0]) not in dimension_sizes:
            await ctx.reply("Make sure your second dimensions argument is in the list of valid dimensions.")
            return

        set_user_setting(ctx.author.id, "width", dim)
        set_user_setting(ctx.author.id, "height", int(args[0]))
        await ctx.reply(f"Your width and height have been set to {dim} and {args[0]}.")
        return

    await ctx.reply("Please provide the correct number of arguments.")


@settings.group()
async def negative(ctx: Context, model_name: str = None, *args):
    if model_name is None:
        await ctx.send("Please provide a model name, here are the options:\n" + get_model_list())
        return

    if model_name == "list":
        negative_prompt_str = get_setting_default(ctx.author.id, "negative_prompt", "{}")
        negative_prompt = json.loads(negative_prompt_str)
        negative_prompt_list = []
        for model_id in range(len(models)):
            negative_prompt_list.append(f"{models[model_id]['name']} - `{negative_prompt.get(str(model_id), 'None')}`")
        await ctx.reply("Your negative prompts:\n" + "\n".join(negative_prompt_list))
        return

    if model_name == "reset":
        set_user_setting(ctx.author.id, "negative_prompt", "{}")
        await ctx.reply("Your negative prompts have been reset.")
        return

    model_id = get_model_from_alias(model_name.lower())

    if model_id is None:
        await ctx.send("That model does not exist. Here are the options:\n" + get_model_list())
        return
    model_id = str(model_id)

    if len(args) == 0:
        await ctx.send("Please provide a negative prompt.")
        return

    if len(args) == 1 and args[0].lower() == "reset":
        negative_prompt_str = get_setting_default(ctx.author.id, "negative_prompt", "{}")
        negative_prompt = json.loads(negative_prompt_str)

        if model_id not in negative_prompt:
            await ctx.reply("You don't have a negative prompt set for that model.")
            return

        del negative_prompt[model_id]
        set_user_setting(ctx.author.id, "negative_prompt", json.dumps(negative_prompt))
        await ctx.reply(f"Your negative prompt for {models[int(model_id)]['name']} has been reset.")
        return

    negative_prompt_str = get_setting_default(ctx.author.id, "negative_prompt", "{}")
    negative_prompt = json.loads(negative_prompt_str)

    negative_prompt[model_id] = " ".join(args)
    set_user_setting(ctx.author.id, "negative_prompt", json.dumps(negative_prompt))
    await ctx.reply(f"Your negative prompt for {models[int(model_id)]['name']} has been set to "
                    f"`{negative_prompt[model_id]}`")


@bot.command()
async def view(ctx: Context, job_id: str = None, *args):
    if job_id is None:
        await ctx.reply("Please provide a job id.")
        return

    job = lookup_job(job_id)
    if job is None:
        await ctx.reply("That job id does not exist.")
        return

    if not (is_owner() or int(job[3]) == ctx.author.id):
        await ctx.reply("You cannot view something that is not your job.")
        return

    job_prompt: str = job[2]
    if job_prompt.startswith("{"):
        job_prompt = json.loads(job_prompt)['input']['prompt']

    if "params" in args:
        await ctx.reply(f"Here is the parameters for job `{job_id}\n```json\n{job[2]}```")
        return

    message = await ctx.reply(f"Now viewing prompt `{job_prompt}`, (Job ID: `{job_id}`).")
    await message.add_files(discord.File(f"images/{job_id}.png"))


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


def prompt_parse(prompt: str, argument_list=None):
    if argument_list is None:
        argument_list = []
    tokens = []
    token_index = 0
    in_quotes = False
    parameter_locations = []

    for c in prompt:
        if len(tokens) == token_index:
            tokens.append("")

        if c == " " and not in_quotes:
            token_index += 1
            continue

        if c == "\"":
            in_quotes = not in_quotes
            continue

        if tokens[token_index] == "--":
            parameter_locations.append(token_index)
            token_index += 1

        if len(tokens) == token_index:
            tokens.append("")

        tokens[token_index] += c

    parameters = {}

    for x in parameter_locations:
        if tokens[x + 1] in argument_list:
            parameters[tokens[x + 1]] = tokens[x + 2]

    for x in reversed(parameter_locations):
        if tokens[x + 1] in argument_list:
            for i in reversed(range(0, 3)):
                del tokens[x + i]

    index = 0
    while index < len(tokens):
        if tokens[index] == "--":
            del tokens[index]
            tokens[index] = "--" + tokens[index]
        index += 1

    for key, value in parameters.items():
        if value.lower() == "true":
            parameters[key] = True
        elif value.lower() == "false":
            parameters[key] = False
        elif value.isnumeric():
            parameters[key] = int(value)

    return " ".join(tokens), parameters


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

    if message.content.lower().startswith(("retry ", "redo ", "r ")):
        # Redo the prompt that was given in the reference message
        previous_job_id = reference_message.content.split("`")[3].split(",")[0]
        job = lookup_job(previous_job_id)
        model_id = job[4]

        # See if a model was specified
        if len(message.content.split(" ")) >= 2:
            model_id = get_model_from_alias(message.content.split(" ")[1])
            if model_id is None:
                model_id = job[4]

        params = json.loads(job[2])

        create_task = await asyncio.wait([asyncio.create_task(
            create_image_params(params, model_id, reference_message, message.author)
        )])
        job_id = get_job_ids_from_task(create_task)[0]
        await reference_message.add_files(discord.File(f"images/{job_id}.png"))
        return

    if message.content.lower() in ["no", "delete", "stop", "cancel", "nope", "n"]:
        # Delete the message
        await reference_message.delete()
        return

    if message.content.lower().startswith(("stylize ", "artify ", "rework ")):
        previous_job_id = reference_message.content.split("`")[3].split(",")[0]
        job = lookup_job(previous_job_id)
        model_id = job[4]

        new_prompt = " ".join(message.content.split(" ")[1::])
        params = json.loads(job[2])

        params['input']['init_image'] = reference_message.attachments[0].url
        params['input']['prompt'] = new_prompt
        params['input']['num_inference_steps'] = 10

        stylize_message = await message.reply(f"Creating stylize of image with prompt `{new_prompt}`...")
        create_task = await asyncio.wait([asyncio.create_task(
            create_image_params(params, model_id, stylize_message, message.author)
        )])
        job_id = get_job_ids_from_task(create_task)[0]

        await stylize_message.edit(content=f"Created stylize of image with prompt `{new_prompt}`... (Job ID: `{job_id}`")
        await stylize_message.add_files(discord.File(f"images/{job_id}.png"))


    # If no other keywords were used, then just process the commands
    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction: Reaction, user: User):
    if user == bot.user:
        return

    if reaction.message.author != bot.user:
        return

    if reaction.emoji in ["🔁", "🔄", "🔂", "🔀", "♻"]:
        # Redo the prompt that was given in the reference message
        previous_job_id = reaction.message.content.split("`")[3].split(",")[0]
        job = lookup_job(previous_job_id)
        model_id = job[4]
        params = json.loads(job[2])

        create_task = await asyncio.wait([asyncio.create_task(
            create_image_params(params, model_id, reaction.message, user)
        )])
        job_id = get_job_ids_from_task(create_task)[0]
        await reaction.message.add_files(discord.File(f"images/{job_id}.png"))

    if reaction.emoji in ["❌", "🚫", "🛑", "❎"]:
        # Delete the message
        await reaction.message.delete()

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
        print("Please enter your Runpod API key. You can get this from https://www.runpod.io/console/user/settings")
        runpod_key = input("Runpod API key: ")
        print("Please enter your user id. This is so you can use the bot's commands as the owner.")
        owner_id = input("Owner ID: ")
        print("Please enter the name of the database file. This is where the bot will store user settings.")
        database_file = input("Database file: ")

        config_json = {
            "DISCORD_TOKEN": token,
            "RUNPOD_KEY": runpod_key,
            "OWNER_ID": owner_id,
            "DATABASE_FILE": database_file
        }
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump(config_json, f, ensure_ascii=False, indent='\t')
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

    if not os.path.isfile(".schema"):
        print("Schema file does not exist, downloading...")
        schema_file = requests.get("https://raw.githubusercontent.com/Benwager12/JourneyBot/master/.schema")
        with open(".schema", "wb", encoding='utf-8') as f:
            f.write(schema_file.content)

    if not os.path.isfile(config['DATABASE_FILE']):
        with open(config['DATABASE_FILE'], "wb") as f:
            f.write(bytes())


def make_tables():
    schema_file = open(".schema").read()
    with sqlite3.connect(config['DATABASE_FILE']) as con:
        cur = con.cursor()
        cur.execute(schema_file)


if __name__ == "__main__":
    run_setup_wizard = False

    # Make sure all the files exist
    for file in ["config.json", "allowed_users.txt", "models.json"]:
        if not os.path.isfile(file):
            run_setup_wizard = True

    if not os.path.exists("images"):
        run_setup_wizard = True

    if run_setup_wizard:
        print("Starting the setup wizard...")
        setup_wizard()
        make_tables()

    bot.run(config["DISCORD_TOKEN"])

