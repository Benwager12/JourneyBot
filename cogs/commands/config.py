import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers.checks.IsOwnerId import owner_check
from helpers.file import config


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="config")
    async def _config(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        await ctx.reply("No subcommand specified. Try using `get` and `set`.")

    @_config.group(name="set", aliases=["change", "update", "edit", "modify"])
    async def _set(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        await ctx.reply("No subcommand specified. Try using `owner`.")

    @_config.group(name="get", aliases=["show", "display", "view", "print"])
    async def _get(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        await ctx.reply("No subcommand specified. Try using `owner`, `runpod`.")

    @_get.command(name="runpod")
    @owner_check()
    async def _runpod_get(self, ctx: Context):
        runpod = config.get('RUNPOD_KEY')
        if not ctx.channel.type == discord.ChannelType.private:
            runpod = "*" * len(runpod)
        await ctx.reply(f"The runpod key is `{runpod}`.")

    @_get.command(name="discord")
    @owner_check()
    async def _discord_get(self, ctx: Context):
        disc_token = config.get('DISCORD_TOKEN')
        if not ctx.channel.type == discord.ChannelType.private:
            disc_token = "*" * len(disc_token)
        await ctx.reply(f"The discord token is `{disc_token}`.")

    @_get.command(name="owner")
    async def _owner_get(self, ctx: Context):
        owner_id = int(config.get('OWNER_ID'))
        potential_owner = await ctx.guild.fetch_member(owner_id)

        reply_message = f"The owner's ID is `{owner_id}`, "
        if potential_owner == ctx.author:
            await ctx.reply(reply_message + "and that's you!")
            return

        if potential_owner is None:
            await ctx.reply(reply_message + "but I can't find them in this server.")
        else:
            await ctx.reply(reply_message + f"but you may know them as `{potential_owner.display_name}`.")

    @_set.command(name="owner")
    @owner_check()
    async def _owner_set(self, ctx: Context, owner: discord.Member):
        config.set('OWNER_ID', owner.id)
        config.save()
        await ctx.reply(f"Ownership has been transferred to {owner.mention} ({owner.id}).")

    @_set.command(name="runpod")
    @owner_check()
    async def _runpod_set(self, ctx: Context, runpod: str = None):
        if runpod is None or ctx.channel.type != discord.ChannelType.private:
            await ctx.reply("You're gonna need to do this with a reset of the bot, sorry.")
            return
        config.set('RUNPOD_KEY', runpod)
        config.save()
        await ctx.reply(f"Runpod key has been set to `{runpod}`.")

    @_set.command(name="discord")
    async def _discord_set(self, ctx: Context):
        await ctx.reply("You're gonna need to do this with a reset of the bot, sorry.")


async def setup(bot):
    await bot.add_cog(Config(bot))
