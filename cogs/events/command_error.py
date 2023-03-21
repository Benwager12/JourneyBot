from discord.ext import commands
from discord.ext.commands import Context, CommandError
import traceback


class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.CheckFailure):
            print(f"User {ctx.author} ({ctx.author.id}) tried to use command {ctx.command}")
            return

        print(f"Command {ctx.command} failed with error {error.__class__.__name__} for reason \"{error.__cause__}\".")
        traceback.print_exception(error)
        print(error)


async def setup(bot):
    await bot.add_cog(OnCommandError(bot))
