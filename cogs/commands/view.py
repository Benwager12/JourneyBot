import json

import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers.database import images
from helpers.jobs import runpod
from helpers.views.image_view import ImageView


async def view_job(job_id, ctx, message):
    if job_id.lower() in ['latest', 'last']:
        job_id = images.get_latest_job_id(ctx.author.id)
        if job_id is None:
            await ctx.reply("You have no jobs.")
            return

    job = images.lookup_job(job_id)

    alias_used = False

    if job is None:
        job = images.lookup_alias(job_id, ctx.author.id)
        if job is None:
            await ctx.reply(f"The job ID or alias `{job_id}` does not exist.")
            return
        alias_used = True
        job_id = job[0]

    job_prompt: str = job[2]
    if job_prompt.startswith("{"):
        job_prompt = json.loads(job_prompt)['input']['prompt']

    if message.content.startswith("Viewing job"):
        view_message = f"Now viewing `prompt: {job_prompt}`, (Job ID: `{job_id}`)."
        if alias_used:
            view_message = f"Now viewing alias `alias: {job[6]}`, (Job ID: `Invisible`)."
    else:
        backtick_split = message.content.split("`")
        new_job_ids = f"{backtick_split[3]}, Invisible" if alias_used else f"{backtick_split[3]}, {job_id}"
        if alias_used:
            view_message = f"Now viewing `[{backtick_split[1]}], [alias: {job[6]}]`, (Job ID: `{new_job_ids}`)."
        else:
            view_message = f"Now viewing `[{backtick_split[1]}], [prompt: {job_prompt}]` (Job ID: `{new_job_ids})."

    file_list = runpod.job_location(job_id)
    file_list = [discord.File(file) for file in file_list]

    for attachment in message.attachments:
        file_list.append(attachment)

    message = await message.edit(
        content=view_message,
        attachments=file_list,
        view=(ImageView() if not alias_used else None)
    )
    return message, alias_used


class View(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="View a job")
    async def view(self, ctx: Context, *job_ids):
        if len(job_ids) == 0:
            await ctx.reply("Please provide a job id.")
            return
        if len(job_ids) > 9:
            await ctx.reply("You can only view up to 9 jobs at once.")
            return

        message = await ctx.reply(f"Viewing job{'s' if len(job_ids) > 1 else ''}...")
        alias_used = False
        for job_id in job_ids:
            message, new_alias_used = await view_job(job_id, ctx, message)
            if not alias_used:
                alias_used = new_alias_used

        if not alias_used:
            await message.edit(view=ImageView())


async def setup(bot):
    await bot.add_cog(View(bot))
