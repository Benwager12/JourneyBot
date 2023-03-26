import json

import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers.database import user_settings
from helpers.file import models


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help = "Change your settings."

    @commands.group(name="settings", aliases=["set"], help="Change your settings.")
    async def _settings(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return

        settings_list = {
            "Model": models.get(user_settings.get_default(ctx.author.id, "model_id", 0))['name'],
            "Width": user_settings.get_default(ctx.author.id, "width", 512),
            "Height": user_settings.get_default(ctx.author.id, "height", 512)
        }

        settings_string = "\n".join([f"{setting} - {settings_list[setting]}" for setting in settings_list])

        embed = discord.Embed(title=f"Settings - {ctx.author.name}",
                              description=f"Your current settings\n\n{settings_string}\n\nTo change your model, "
                                          "use the `set model` command",
                              color=0x00ff00)
        await ctx.send("", embed=embed)

    @_settings.command()
    async def model(self, ctx: Context, model_name: str = None):
        if model_name is None:
            await ctx.send("Please provide a model name, here are the options:\n" + models.get_models_aliases())
            return

        model_id = models.get_model_from_alias(model_name.lower())

        if model_id is None:
            await ctx.send("That model does not exist. Here are the options:\n" + models.get_models_aliases())
            return

        user_settings.set(ctx.author.id, "model_id", model_id)
        await ctx.reply(f"Your model has been set to {models.get(model_id)['name']}.")

    @_settings.command(aliases=["width", "height", "dim", "d"])
    async def dimension(self, ctx: Context, dim: int = None, *args):
        dimension_sizes = [128, 256, 384, 448, 512, 576, 640, 704, 768]
        if dim is None:
            await ctx.send(f"Please provide a {ctx.invoked_with}, it can be between `{dimension_sizes}`.")
            return

        if dim not in dimension_sizes:
            await ctx.send(f"Please provide a {ctx.invoked_with} that is between `{dimension_sizes}`.")
            return

        if len(args) == 0:
            if ctx.invoked_with.lower() in ["width", "dimension", "dim", "d"]:
                user_settings.set(ctx.author.id, "width", dim)

            if ctx.invoked_with.lower() in ["height", "dimension", "dim", "d"]:
                user_settings.set(ctx.author.id, "height", dim)

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

            user_settings.set(ctx.author.id, "width", dim)
            user_settings.set(ctx.author.id, "height", int(args[0]))
            await ctx.reply(f"Your width and height have been set to {dim} and {args[0]}.")
            return

        await ctx.reply("Please provide the correct number of arguments.")

    @_settings.group()
    async def negative(self, ctx: Context, model_name: str = None, *args):
        if model_name is None:
            await ctx.send("Please provide a model name, here are the options:\n" + models.get_models_aliases())
            return

        if model_name == "list" or model_name == "show":
            await ctx.reply(f"Your negative prompts:\n{user_settings.get_negative_prompt_list(ctx.author.id)}")
            return

        if model_name == "reset":
            user_settings.set(ctx.author.id, "negative_prompt", "{}")
            await ctx.reply("Your negative prompts have been reset.")
            return

        model_id = models.get_model_from_alias(model_name.lower())

        if model_id is None:
            await ctx.send("That model does not exist. Here are the options:\n" + models.get_models_aliases())
            return
        model_id = str(model_id)

        if len(args) == 0:
            await ctx.send("Please provide a negative prompt.")
            return

        if len(args) == 1 and args[0].lower() == "reset":
            negative_prompt_str = user_settings.get_default(ctx.author.id, "negative_prompt", "{}")
            negative_prompt = json.loads(negative_prompt_str)

            if model_id not in negative_prompt:
                await ctx.reply("You don't have a negative prompt set for that model.")
                return

            del negative_prompt[model_id]
            user_settings.set(ctx.author.id, "negative_prompt", json.dumps(negative_prompt))
            await ctx.reply(f"Your negative prompt for {models.get(int(model_id))['name']} has been reset.")
            return

        negative_prompt_str = user_settings.get_default(ctx.author.id, "negative_prompt", "{}")
        negative_prompt = json.loads(negative_prompt_str)

        negative_prompt[model_id] = " ".join(args)
        user_settings.set(ctx.author.id, "negative_prompt", json.dumps(negative_prompt))
        await ctx.reply(f"Your negative prompt for {models.get(int(model_id))['name']} has been set to "
                        f"`{negative_prompt[model_id]}`")


async def setup(bot):
    await bot.add_cog(Settings(bot))
