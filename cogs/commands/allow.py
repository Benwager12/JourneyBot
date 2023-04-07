import discord
import discord.ext.commands
from discord import Guild
from discord.ext import commands
from discord.ext.commands import Context

from helpers.checks.IsOwnerId import is_owner_user
from helpers.database import allow_list
from helpers.string import subcommand


class Allow(commands.Cog):
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self.help = "Allow users to use the bot."

    @commands.group(name="allow")
    async def _allow(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        subcommand_str = subcommand.subcommand_string(self._allow)
        await ctx.reply(f"No subcommand specified. Try using {subcommand_str}.")

    @_allow.command()
    async def add(self, ctx: Context, user: discord.Member):
        if ctx.channel.type != discord.ChannelType.private and not is_owner_user(ctx.author.id):
            await ctx.reply("You are only allowed to add users when you are in a guild.")
            return

        if allow_list.add_user(user.id, ctx.author.id, ctx.guild.id):
            await ctx.reply(f"Added `{user.display_name}` to the allowed users list.")
        else:
            await ctx.reply(f"`{user.display_name}` is already on the allowed users list.")

    @_allow.command()
    async def remove(self, ctx: Context, user: discord.Member):
        if ctx.channel.type != discord.ChannelType.private and not is_owner_user(ctx.author.id):
            await ctx.reply("You are only allowed to remove users when you are in a guild.")
            return

        if allow_list.remove_user(user.id):
            await ctx.reply(f"Removed `{user.display_name}` from the allowed users list.")
        else:
            await ctx.reply(f"`{user.display_name}` is not on the allowed users list.")

    @_allow.command()
    async def cleanup(self, ctx: Context):
        initial_users = allow_list.get_users()
        removed_users = []
        for user_id, added_by, guild_id in initial_users:
            guild: Guild = self.bot.get_guild(guild_id)
            member = await guild.fetch_member(user_id)
            added_user = await guild.fetch_member(added_by)
            if not member or not added_user and not is_owner_user(user_id):
                allow_list.remove_user(user_id)
                removed_users.append(user_id)
        removed_amount = len(removed_users)

        if removed_amount == 0:
            await ctx.reply("No users were removed from the allowed users list.")
            return
        await ctx.reply(f"Cleaned up the allowed users list, {removed_amount} users were removed.")
        print(f"Cleaned up the allowed users list, {removed_amount} users were removed. "
              f"Removed users: {removed_users}.")


async def setup(bot):
    await bot.add_cog(Allow(bot))
