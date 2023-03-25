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

        backtick_split = reaction.message.content.split("`")

        if reaction.emoji in ["🔁", "🔄", "🔂", "🔀", "♻"]:
            if len(backtick_split) <= 3:
                return

            # Redo the prompt that was given in the reference message
            previous_job_id = backtick_split[3].split(",")[0]
            job = images.lookup_job(previous_job_id)
            model_id = job[4]
            params = json.loads(job[2])

            create_task = await asyncio.wait([asyncio.create_task(
                runpod.create_image(params, model_id, reaction.message, user)
            )])
            job_id = runpod.get_job_id_from_task(create_task)[0]
            await reaction.message.add_files(discord.File(f"images/{job_id}.png"))

        if reaction.emoji in ["❌", "🚫", "🛑", "❎"]:
            # Delete the message
            await reaction.message.delete()

        if reaction.emoji == "🅿":  # View parameters of prompt
            if len(backtick_split) <= 3:
                return
            previous_job_ids = backtick_split[3].split(", ")
            param_str = []
            for job_id in previous_job_ids:
                job = images.lookup_job(job_id)
                if job is None:
                    continue
                params = json.loads(job[2])
                param_str.append(f"`{job_id} - seed {job[1]}`:\n```json\n{params}```")
            await reaction.message.channel.send(f"{user.mention}, here are the parameters:\n\n" + "\n".join(param_str))


async def setup(bot):
    await bot.add_cog(OnReactionAdd(bot))
