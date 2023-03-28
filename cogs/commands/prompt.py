import asyncio

import discord
from discord.ext import commands

from helpers.database import user_settings
from helpers.jobs import runpod, parameters
from helpers.jobs.runpod import job_location
from helpers.views.image_view import ImageView


class Prompt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["c", "make", "generate", "imagine"], help="Create a photo with a prompt.")
    async def create(self, ctx, *args):
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

        user_model = user_settings.get_default(ctx.author.id, "model_id", 0)

        params = parameters.make_params(ctx.author.id, prompt)
        prompt = params['input']['prompt']

        message = await message.edit(content=f"Making a photo with prompt `{prompt}`... ")
        create_task = await asyncio.wait([asyncio.create_task(
            runpod.create_image(params, user_model, message, ctx.author)
        )])

        job_id = runpod.get_job_id_from_task(create_task)[0]

        file_list = job_location(job_id)
        file_list = [discord.File(file) for file in file_list]

        await message.edit(
            content=f"Making a photo with prompt `{prompt}`... (Job: `{job_id}`)",
            attachments=file_list,
            view=ImageView()
        )


async def setup(bot):
    await bot.add_cog(Prompt(bot))
