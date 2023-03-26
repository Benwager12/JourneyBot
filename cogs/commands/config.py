import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers.checks import IsOwnerId
from helpers.checks.IsOwnerId import owner_check
from helpers.database import user_settings
from helpers.file import config
from helpers.string import subcommand


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="config", help="Configure the bot.")
    async def _config(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        subcommand_str = subcommand.subcommand_string(self._config)

        await ctx.reply(f"No subcommand specified. Try using {subcommand_str}.")

    @_config.group(name="set", aliases=["change", "update", "edit", "modify"])
    async def _set(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        subcommand_str = subcommand.subcommand_string(self._set)

        await ctx.reply(f"No subcommand specified. Try using {subcommand_str}.")

    @_config.group(name="get", aliases=["show", "display", "view", "print"])
    async def _get(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        subcommand_str = subcommand.subcommand_string(self._set)

        await ctx.reply(f"No subcommand specified. Try using {subcommand_str}.")

    @_get.command(name="runpod")
    async def _runpod_get(self, ctx: Context):
        global_runpod = config.get('RUNPOD_KEY')
        if not ctx.channel.type == discord.ChannelType.private:
            await ctx.reply("You cannot do this command in a public channel.")
            return

        user_runpod = user_settings.get(ctx.author.id, "runpod_key")

        if IsOwnerId.is_owner_user(ctx.author.id):
            await ctx.reply(f"The global runpod key is `{global_runpod}`"
                            f"{f', however your key is `{user_runpod}`' if user_runpod else ''}.")
        else:
            if user_runpod:
                await ctx.reply(f"Your runpod key is `{user_runpod}`.")
            else:
                await ctx.reply("You are using the global runpod key.")

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
        reply_message = f"The owner's ID is `{owner_id}`"

        if ctx.message.channel.type == discord.ChannelType.private:
            await ctx.reply(reply_message + ".")
            return

        reply_message += ", "

        potential_owner = await ctx.guild.fetch_member(owner_id)

        if potential_owner == ctx.author:
            await ctx.reply(reply_message + "and that's you!")
            return

        if potential_owner is None:
            await ctx.reply(reply_message + "but I can't find them in this server.")
        else:
            await ctx.reply(reply_message + f"but you may know them as `{potential_owner.display_name}`.")

    @_get.command(name="prefix")
    async def _prefix_get(self, ctx: Context):
        prefix = config.get('PREFIX', default="*")
        await ctx.reply(f"The prefix is `{prefix}`.")

    @_set.command(name="owner")
    @owner_check()
    async def _owner_set(self, ctx: Context, owner: discord.Member):
        config.set('OWNER_ID', owner.id)
        config.save()
        await ctx.reply(f"Ownership has been transferred to {owner.mention} ({owner.id}).")

    @_set.command(name="runpod")
    async def _runpod_set(self, ctx: Context, runpod: str = None):
        if ctx.channel.type != discord.ChannelType.private:
            await ctx.reply("Please do this in a a DM channel.")
            return

        if not runpod:
            if not IsOwnerId.is_owner_user(ctx.author):
                user_settings.set(ctx.author.id, "runpod_key", None)
                await ctx.reply("Your runpod key has been reset to default.")
                return

            await ctx.reply("You need to specify a runpod key.")
            return

        if IsOwnerId.is_owner_user(ctx.author.id):
            config.set('RUNPOD_KEY', runpod)
            config.save()
            await ctx.reply(f"Global runpod key has been set to `{runpod}`.")
            return
        else:
            user_settings.set(ctx.author.id, "runpod_key", runpod)
            await ctx.reply(f"Your runpod key has been set to `{runpod}`.")

    @_set.command(name="prefix")
    @owner_check()
    async def _prefix_set(self, ctx: Context, prefix: str = None):
        if not prefix:
            config.set('PREFIX', "*")
            await ctx.reply("The preset has been reset to the default.")
        else:
            config.set('PREFIX', prefix)
            await ctx.reply(f"The prefix has been set to `{prefix}`.")
        config.save()

    @_set.command(name="discord")
    async def _discord_set(self, ctx: Context):
        await ctx.reply("You're gonna need to do this with a reset of the bot, sorry.")


async def setup(bot):
    await bot.add_cog(Config(bot))
