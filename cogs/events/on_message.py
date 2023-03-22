import asyncio
import json

import discord
from discord import Message
from discord.ext import commands

from helpers.database import images
from helpers.file import models
from helpers.jobs import runpod, prompt
from helpers.jobs.prompt import add_reaction_emojis_image


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
        backtick_split = reference_message.content.split("`")

        if message.content.lower().startswith(("retry", "redo")):
            # Redo the prompt that was given in the reference message

            if len(backtick_split) <= 3:
                return
            previous_job_id = backtick_split[3].split(", ")[0]
            job = images.lookup_job(previous_job_id)

            if job is None:
                return

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

        if message.content.lower().startswith(("stylize ", "artify ", "rework ")):
            if len(backtick_split) <= 3:
                return

            previous_job_id = backtick_split[3].split(", ")[0]
            job = images.lookup_job(previous_job_id)

            if job is None:
                return

            model_id = job[4]

            new_prompt = " ".join(message.content.split(" ")[1::])
            params = json.loads(job[2])
            params['input']['seed'] = job[1]

            params['input']['init_image'] = reference_message.attachments[0].url
            combined_prompt = f"{params['input']['prompt']}, {new_prompt}"

            new_prompt, parsed_params = prompt.parse(combined_prompt, ["width", "height", "negative", "steps", "model"])

            if 'negative' in parsed_params:
                parsed_params['negative_prompt'] = parsed_params['negative']
                del parsed_params['negative']

            if 'steps' in parsed_params and isinstance(parsed_params['steps'], int):
                parsed_params['num_inference_steps'] = min(100, max(parsed_params['steps'], 20))
                del parsed_params['steps']

            if 'model' in parsed_params:
                new_model = models.get_model_from_alias(parsed_params['model'])
                if new_model is not None:
                    model_id = new_model
                del parsed_params['model']

            parsed_params['prompt'] = new_prompt

            final_params = {**params['input'], **parsed_params}
            final_params = {
                "input": final_params
            }

            stylize_message = await message.reply(f"Creating stylize of image with prompt `{new_prompt}`...")
            create_task = await asyncio.wait([asyncio.create_task(
                runpod.create_image(final_params, model_id, stylize_message, message.author)
            )])
            job_id = runpod.get_job_ids_from_task(create_task)[0]

            await stylize_message.edit(
                content=f"Created stylize of image with prompt `{new_prompt}`... (Job ID: `{job_id}`")
            await stylize_message.add_files(discord.File(f"images/{job_id}.png"))
            await add_reaction_emojis_image(stylize_message)
            return


async def setup(bot):
    await bot.add_cog(OnMessage(bot))
