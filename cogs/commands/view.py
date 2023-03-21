import json

import discord
from discord.ext import commands
from discord.ext.commands import Context, is_owner

from helpers.database import images


class View(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def view(self, ctx: Context, job_id: str = None):
        if job_id is None:
            await ctx.reply("Please provide a job id.")
            return

        job = images.lookup_job(job_id)

        if job is None:
            await ctx.reply("That job id does not exist.")
            return

        if not (is_owner() or int(job[3]) == ctx.author.id):
            await ctx.reply("You cannot view something that is not your job.")
            return

        job_prompt: str = job[2]
        if job_prompt.startswith("{"):
            job_prompt = json.loads(job_prompt)['input']['prompt']

        message = await ctx.reply(f"Now viewing prompt `{job_prompt}`, (Job ID: `{job_id}`).")
        await message.add_files(discord.File(f"images/{job_id}.png"))


async def setup(bot):
    await bot.add_cog(View(bot))