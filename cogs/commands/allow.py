import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers.checks.IsOwnerId import is_owner_user
from helpers.file import allowed_users
from helpers.string import subcommand


class Allow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        if allowed_users.add(user.id):
            await ctx.reply(f"Added `{user.display_name}` to the allowed users list.")
        else:
            await ctx.reply(f"`{user.display_name}` is already on the allowed users list.")

    @_allow.command()
    async def remove(self, ctx: Context, user: discord.Member):
        if ctx.channel.type != discord.ChannelType.private and not is_owner_user(ctx.author.id):
            await ctx.reply("You are only allowed to remove users when you are in a guild.")
            return

        if allowed_users.remove(user.id):
            await ctx.reply(f"Removed `{user.display_name}` from the allowed users list.")
        else:
            await ctx.reply(f"`{user.display_name}` is not on the allowed users list.")


async def setup(bot):
    await bot.add_cog(Allow(bot))
