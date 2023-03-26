import asyncio
import json

import discord
from discord import Interaction

from helpers.checks.IsAllowedUser import is_allowed_user
from helpers.database import images, user_settings
from helpers.jobs import runpod


class PaginatedView(discord.ui.View):

    def __init__(self, page_function: callable = images.get_gallery_embed):
        super().__init__()
        self.page_function = page_function

    @discord.ui.button(label="First", style=discord.ButtonStyle.primary)
    async def first_page(self, interaction: Interaction, button: discord.ui.Button):
        footer = interaction.message.embeds[0].footer.text
        page = footer.split("`")[1].split(" / ")[0]
        if page == "1":
            await interaction.response.send_message(
                content="You are already on the first page.",
                ephemeral=True
            )
            return

        _, embed = self.page_function(interaction.user.id, 1)

        await interaction.message.edit(
            embed=embed,
            view=PaginatedView(self.page_function)
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: Interaction, button: discord.ui.Button):
        footer = interaction.message.embeds[0].footer.text
        page = footer.split("`")[1].split(" / ")[0]
        if page == "1":
            await interaction.response.send_message(
                content="You are already on the first page.",
                ephemeral=True
            )
            return

        _, embed = self.page_function(interaction.user.id, 1)

        await interaction.message.edit(
            embed=embed,
            view=PaginatedView(self.page_function)
        )

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: Interaction, button: discord.ui.Button):
        footer = interaction.message.embeds[0].footer.text
        page = footer.split("`")[1].split(" / ")[0]
        page_amount = footer.split("`")[1].split(" / ")[1]
        if page == page_amount:
            await interaction.response.send_message(
                content="You are already on the last page.",
                ephemeral=True
            )
            return

        _, embed = self.page_function(interaction.user.id, 1)

        await interaction.message.edit(
            embed=embed,
            view=PaginatedView(self.page_function)
        )

    @discord.ui.button(label="Last", style=discord.ButtonStyle.primary)
    async def last_page(self, interaction: Interaction, button: discord.ui.Button):
        footer = interaction.message.embeds[0].footer.text
        page = footer.split("`")[1].split(" / ")[0]
        page_amount = footer.split("`")[1].split(" / ")[1]
        if page == page_amount:
            await interaction.response.send_message(
                content="You are already on the last page.",
                ephemeral=True
            )
            return

        _, embed = self.page_function(interaction.user.id, 1)

        await interaction.message.edit(
            embed=embed,
            view=PaginatedView(self.page_function)
        )
