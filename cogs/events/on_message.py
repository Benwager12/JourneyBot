import asyncio
import json

import discord
from discord import Message
from discord.ext import commands

from helpers.checks.IsOwnerId import is_owner_user
from helpers.database import images, user_settings
from helpers.file import models
from helpers.jobs import runpod, prompt
from helpers.views.image_view import ImageView
from helpers.views.page_view import GalleryPageView


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

            new_prompt, parsed_params = prompt.parse(new_prompt, ["negative", "steps", "model"])


            if 'negative' in parsed_params:
                parsed_params['negative_prompt'] = parsed_params['negative']
                del parsed_params['negative']

            if 'steps' in parsed_params and isinstance(parsed_params['steps'], int):
                parsed_params['num_inference_steps'] = min(100, max(parsed_params['steps'], 20))\
            if user_settings.get("runpod_key", message.author.id) is None else min(499, max(parsed_params['steps'], 20))
                del parsed_params['steps']

            if 'model' in parsed_params:
                new_model = models.get_model_from_alias(parsed_params['model'])
                if new_model is not None:
                    model_id = new_model
                del parsed_params['model']

            if new_prompt.strip() != "":
                final_prompt = f"{params['input']['prompt']}, {new_prompt}"
            else:
                final_prompt = params['input']['prompt']

            replacements = prompt.parse_replace(final_prompt)

            for replacement in replacements:
                final_prompt = final_prompt.replace(replacement, replacements[replacement])

            for replaced in replacements:
                replacement = replacements[replaced]
                final_prompt = final_prompt.replace(f"[{replacement}={replacement}]", "")
                print(final_prompt)

            while final_prompt.endswith((", ", ",")):
                final_prompt = final_prompt[:-2]
            parsed_params['prompt'] = final_prompt

            final_params = {**params['input'], **parsed_params}
            final_params = {
                "input": final_params
            }

            stylize_message = await message.reply(f"Creating stylize of image with prompt `{final_prompt}`...")
            create_task = await asyncio.wait([asyncio.create_task(
                runpod.create_image(final_params, model_id, stylize_message, message.author)
            )])
            job_id = runpod.get_job_ids_from_task(create_task)[0]

            await stylize_message.edit(
                content=f"Created stylize of image with prompt `{final_prompt}`... (Job ID: `{job_id}`)",
                view=ImageView(),
                attachments=[discord.File(f"images/{job_id}.png")]
            )

        if message.content.lower().startswith(("switchview ", "sv ")) and is_owner_user(message.author.id):
            view_name = message.content.split(" ")[1]

            if view_name.lower() in ["image", "images", "img", "imgs"]:
                await reference_message.edit(view=ImageView())
            if view_name == "none":
                await reference_message.edit(view=None)

        if message.content.lower() in ["view", "v"]:
            if len(reference_message.content.split("`")) >= 4:
                await reference_message.edit(view=ImageView())
            else:
                await reference_message.edit(view=GalleryPageView())


async def setup(bot):
    await bot.add_cog(OnMessage(bot))
