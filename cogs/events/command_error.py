from discord.ext import commands
from discord.ext.commands import Context, CommandError, PrivateMessageOnly
import traceback

from helpers.checks.IsAllowedUser import AllowedUsersOnly


class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.CheckFailure):
            if isinstance(error, PrivateMessageOnly):
                await ctx.reply(str(error))
                return
            if isinstance(error, AllowedUsersOnly):
                await ctx.reply(str(error))
                return
            print(f"User {ctx.author} ({ctx.author.id}) tried to use command {ctx.command}")

        print(f"Command {ctx.command} failed with error {error.__class__.__name__} for reason \"{error.__cause__}\".")
        traceback.print_exception(error)


async def setup(bot):
    await bot.add_cog(OnCommandError(bot))
