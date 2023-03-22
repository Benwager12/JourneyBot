import asyncio
import json

import discord
from discord import Reaction, User
from discord.ext import commands

from helpers.database import images
from helpers.jobs import runpod


class OnReactionAdd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: User):
        if user == self.bot.user:
            return

        if reaction.message.author != self.bot.user:
            return

        # Check if the reaction has also been added by the bot
        for r in reaction.message.reactions:
            if reaction.me and r.emoji == reaction.emoji:
                break
        else:
            return

        if reaction.emoji in ["🔁", "🔄", "🔂", "🔀", "♻"]:
            # Redo the prompt that was given in the reference message
            previous_job_id = reaction.message.content.split("`")[3].split(",")[0]
            job = images.lookup_job(previous_job_id)
            model_id = job[4]
            params = json.loads(job[2])

            create_task = await asyncio.wait([asyncio.create_task(
                runpod.create_image(params, model_id, reaction.message, user)
            )])
            job_id = runpod.get_job_ids_from_task(create_task)[0]
            await reaction.message.add_files(discord.File(f"images/{job_id}.png"))

        if reaction.emoji in ["❌", "🚫", "🛑", "❎"]:
            # Delete the message
            await reaction.message.delete()

        if reaction.emoji == "⏮":
            # Go to the previous page
            await reaction.message.edit(content=reaction.message.content.split("`")[0] + "`" + reaction.message.content.split("`")[2])


async def setup(bot):
    await bot.add_cog(OnReactionAdd(bot))
