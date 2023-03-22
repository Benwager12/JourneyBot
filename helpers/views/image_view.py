import asyncio
import json

import discord
from discord import Interaction

from helpers.checks.IsAllowedUser import is_allowed_user
from helpers.database import images
from helpers.jobs import runpod


class ImageView(discord.ui.View):
    @discord.ui.button(label="Retry", style=discord.ButtonStyle.green)
    async def redo(self, interaction: Interaction, button: discord.ui.Button):
        if not is_allowed_user(interaction.user.id):
            await interaction.response.send_message(
                content="You are not allowed to use this button.",
                ephemeral=True
            )
            return
        previous_job_id = interaction.message.content.split("`")[3].split(",")[0]
        job = images.lookup_job(previous_job_id)
        model_id = job[4]
        params = json.loads(job[2])

        await interaction.response.send_message(
            content=f"Redoing the image with job id `{previous_job_id}`.",
            ephemeral=True
        )

        create_task = await asyncio.wait([asyncio.create_task(
            runpod.create_image(params, model_id, interaction.message, interaction.user)
        )])

        job_id = runpod.get_job_ids_from_task(create_task)[0]
        await interaction.message.add_files(discord.File(f"images/{job_id}.png"))

        message = await interaction.original_response()
        await message.edit(content=f"Finished redoing the image, the new job id is `{job_id}`.")

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def delete(self, interaction: Interaction, button: discord.ui.Button):
        previous_job_id = interaction.message.content.split("`")[3].split(",")[0]

        await interaction.message.delete()
        await interaction.response.send_message(
            content=f"Deleted the message, the job ID was `{previous_job_id}`.",
            ephemeral=True
        )

    @discord.ui.button(label="Parameters", style=discord.ButtonStyle.primary)
    async def view_params(self, interaction: Interaction, button: discord.ui.Button):
        previous_job_ids = interaction.message.content.split("`")[3].split(", ")
        param_str = []
        for job_id in previous_job_ids:
            job = images.lookup_job(job_id)
            if job is None:
                return
            try:
                params = json.loads(job[2])
            except json.JSONDecodeError:
                await interaction.response.send_message(
                    "This image was created before the parameters were saved, so I can't show them.",
                    ephemeral=True
                )
                return
            param_str.append(f"`{job_id}` - seed `{job[1]}`, model {job[4]}:\n```json\n{params}```")

        await interaction.response.send_message(
            f"Here are the parameters:\n\n" + "\n".join(param_str),
            ephemeral=True
        )