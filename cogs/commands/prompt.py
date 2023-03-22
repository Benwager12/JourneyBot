import asyncio

import discord
from discord.ext import commands

from helpers.database import user_settings
from helpers.jobs import runpod, parameters
from helpers.jobs.prompt import add_reaction_emojis_image


class Prompt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["c", "make", "generate"])
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

        job_ids = runpod.get_job_ids_from_task(create_task)

        file_list = [discord.File(f"images/{jobs}.png") for jobs in job_ids]
        job_id_list = ", ".join([f"{job}" for job in job_ids])
        await message.edit(content=f"Making a photo with prompt `{prompt}`... (Jobs: `{job_id_list}`)",
                           attachments=file_list)
        await add_reaction_emojis_image(message)


async def setup(bot):
    await bot.add_cog(Prompt(bot))
