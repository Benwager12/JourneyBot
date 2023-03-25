import json

import discord
from discord.ext import commands
from discord.ext.commands import Context, is_owner, dm_only

from helpers.database import images
from helpers.views.image_view import ImageView


class View(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def view(self, ctx: Context, job_id: str = None):
        if job_id is None:
            await ctx.reply("Please provide a job id.")
            return

        if job_id.lower() == "all":
            if ctx.channel.type != discord.ChannelType.private:
                await ctx.reply("This command can only be used in private messages.")
                return
            reply, embed = images.get_gallery_embed(ctx.author.id)
            await ctx.send(reply, embed=embed)
            return

        if job_id.lower() in ['latest', 'last']:
            job_id = images.get_latest_job_id(ctx.author.id)
            if job_id is None:
                await ctx.reply("You have no jobs.")
                return

        job = images.lookup_job(job_id)

        alias_used = False

        if job is None:
            job = images.lookup_alias(job_id, ctx.author.id)
            job_id = job[0]

            alias_used = True
            if job is None:
                await ctx.reply("That job id does not exist.")
                return

        job_prompt: str = job[2]
        if job_prompt.startswith("{"):
            job_prompt = json.loads(job_prompt)['input']['prompt']

        view_message = f"Now viewing prompt `{job_prompt}`, (Job ID: `{job_id}`)."
        if alias_used:
            view_message = f"Now viewing alias `{job[7]}`."

        message = await ctx.reply(view_message)
        await message.edit(
            attachments=[discord.File(f"images/{job_id}.png")],
            view=(ImageView() if not alias_used else None)
        )


async def setup(bot):
    await bot.add_cog(View(bot))
