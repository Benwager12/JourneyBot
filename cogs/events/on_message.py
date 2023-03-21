import asyncio
import json

import discord
from discord import Message
from discord.ext import commands

from helpers.database import images
from helpers.file import models
from helpers.jobs import runpod


class OnMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return

        if message.reference is None:
            return

        channel = await self.bot.fetch_channel(message.reference.channel_id)
        reference_message = await channel.fetch_message(message.reference.message_id)

        if reference_message.author != self.bot.user:
            return

        if message.content.lower().startswith(("retry", "redo", "r")):
            # Redo the prompt that was given in the reference message
            previous_job_id = reference_message.content.split("`")[3].split(",")[0]
            job = images.lookup_job(previous_job_id)
            model_id = job[4]

            # See if a model was specified
            if len(message.content.split(" ")) >= 2:
                model_id = models.get_model_from_alias(message.content.split(" ")[1])
                if model_id is None:
                    model_id = job[4]

            params = json.loads(job[2])

            create_task = await asyncio.wait([asyncio.create_task(
                runpod.create_image(params, model_id, reference_message, message.author)
            )])
            job_id = runpod.get_job_ids_from_task(create_task)[0]
            await reference_message.add_files(discord.File(f"images/{job_id}.png"))
            return

        if message.content.lower() in ["no", "delete", "stop", "cancel", "nope", "n"]:
            # Delete the message
            await reference_message.delete()
            return


async def setup(bot):
    await bot.add_cog(OnMessage(bot))
